import torch
from typing import TypedDict
from langgraph.graph import StateGraph, END
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from src.config import LLM_MODEL_NAME
from src.rag_engine import RAGEngine


class AgentState(TypedDict):
    question: str
    context: str
    sources: list[dict]
    answer: str


class EnterpriseRAGAgent:
    def __init__(self, rag_engine: RAGEngine):
        self.rag_engine = rag_engine
        print("Yerel Dil Modeli (SLM) belleğe yükleniyor...")

        self.tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_NAME,
            torch_dtype=dtype,
            device_map="auto" if torch.cuda.is_available() else None
        )
        self.generator = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer
        )

        self.app = self._build_graph()

    def _retrieve_node(self, state: AgentState):
        print("retrieve node harekete geçti...")
        search_result = self.rag_engine.search(state["question"])
        return {
            "context": search_result["context"],
            "sources": search_result["sources"]
        }

    def _generate_node(self, state: AgentState):
        messages = [
            {
                "role": "system",
                "content": (
                    "Sen kurumsal bir yapay zeka asistanısın. "
                    "Sadece sana sunulan şirket belgelerine (Bağlam) dayanarak net, profesyonel ve doğru bir yanıt ver. "
                    "Eğer istenen bilgi belgelerde bulunmuyorsa kesinlikle uydurma ve 'Bu bilgi şirket belgelerinde bulunmamaktadır.' şeklinde belirt."
                )
            },
            {
                "role": "user",
                "content": f"Bağlam:\n{state['context']}\n\nSoru: {state['question']}"
            }
        ]

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        outputs = self.generator(
            prompt,
            max_new_tokens=512,
            do_sample=False,
            return_full_text=False
        )
        answer = outputs[0]["generated_text"].strip()
        return {"answer": answer}

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    def query(self, question: str) -> dict:
        result = self.app.invoke({"question": question, "context": "", "sources": [], "answer": ""})
        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", [])
        }