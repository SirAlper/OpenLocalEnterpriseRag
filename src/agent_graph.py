import torch
from typing import TypedDict
from langgraph.graph import StateGraph, END
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from src.config import LLM_MODEL_NAME
from src.rag_engine import RAGEngine


class AgentState(TypedDict):
    question: str
    context: str
    answer: str


class EnterpriseRAGAgent:
    def __init__(self, rag_engine: RAGEngine):
        self.rag_engine = rag_engine
        print("Yerel Dil Modeli (SLM) belleğe yükleniyor...")

        self.tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_NAME,
            dtype=dtype,
            device_map="auto" if torch.cuda.is_available() else None
        )
        self.generator = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=512
        )

        self.app = self._build_graph()

    def _retrieve_node(self, state: AgentState):
        context = self.rag_engine.search(state["question"])
        return {"context": context}

    def _generate_node(self, state: AgentState):
        prompt = f"""[INST] Sen kurumsal bir yapay zeka asistanısın. Sadece verilen şirket belgelerine dayanarak net ve profesyonel bir yanıt ver. Eğer bilgi belgelerde yoksa 'Bilmiyorum' de.

Bağlam:
{state['context']}

Soru: {state['question']}
[/INST]"""

        outputs = self.generator(prompt)
        full_text = outputs[0]["generated_text"]
        # Prompt kısmını ayırıp sadece modeli cevabını alalım
        answer = full_text.split("[/INST]")[-1].strip()
        return {"answer": answer}

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    def query(self, question: str) -> str:
        result = self.app.invoke({"question": question})
        return result["answer"]