import torch
from typing import TypedDict
from langgraph.graph import StateGraph, END
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig
from src.config import LLM_MODEL_NAME, USE_4BIT_QUANTIZATION
from src.rag_engine import RAGEngine


class AgentState(TypedDict):
    question: str
    context: str
    sources: list[dict]
    answer: str


class EnterpriseRAGAgent:
    def __init__(self, rag_engine: RAGEngine):
        self.rag_engine = rag_engine
        is_cuda = torch.cuda.is_available()
        device_str = "CUDA GPU" if is_cuda else "CPU"
        print(f"Yerel Dil Modeli ({LLM_MODEL_NAME}) {device_str} üzerinde yükleniyor...")

        self.tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)

        # PyTorch 4-bit Kuantizasyon & Bellek Optimizasyonu
        quantization_config = None
        torch_dtype = torch.bfloat16 if is_cuda else torch.float32

        if is_cuda and USE_4BIT_QUANTIZATION:
            print("[PyTorch] 4-bit (NF4) Kuantizasyon aktif ediliyor...")
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16
            )

        model_kwargs = {
            "torch_dtype": torch_dtype,
            "device_map": "auto" if is_cuda else None,
        }
        if quantization_config:
            model_kwargs["quantization_config"] = quantization_config
        elif is_cuda:
            model_kwargs["attn_implementation"] = "sdpa"

        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_NAME,
            **model_kwargs
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

        with torch.inference_mode():
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