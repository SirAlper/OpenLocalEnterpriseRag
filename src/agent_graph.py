import os
import torch
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig, TextIteratorStreamer
from threading import Thread
from src.config import LLM_MODEL_NAME, USE_4BIT_QUANTIZATION
from src.rag_engine import RAGEngine


class AgentState(TypedDict):
    question: str
    context: str
    sources: list[dict]
    answer: str
    hallucination_grade: str


class EnterpriseRAGAgent:
    def __init__(self, rag_engine: RAGEngine):
        self.rag_engine = rag_engine
        is_cuda = torch.cuda.is_available()
        device_str = "CUDA GPU" if is_cuda else "CPU"
        print(f"Yerel Dil Modeli ({LLM_MODEL_NAME}) {device_str} üzerinde yükleniyor...")

        is_local = os.path.exists(LLM_MODEL_NAME)
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME, local_files_only=is_local)

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
            "local_files_only": is_local,
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

    @staticmethod
    def _is_greeting(query: str) -> bool:
        """Kullanıcı girdisinin selamlama olup olmadığını kontrol eder."""
        greetings = ["merhaba", "selam", "günaydın", "iyi günler", "iyi akşamlar", "hey", "nasılsın", "kolay gelsin", "merhabalar"]
        cleaned = query.strip().lower()
        return any(cleaned.startswith(g) or cleaned == g for g in greetings)

    def _build_messages(self, context: str, question: str) -> list[dict]:
        """Kullanıcı sorusu ve bağlam için optimize edilmiş chat şablonunu oluşturur."""
        system_instruction = (
            "Sen kurumsal bir yapay zeka asistanısın. "
            "Sana sunulan Bağlamdaki şirket belgelerine birebir sadık kalarak, soruyu Türkçe, net ve profesyonel bir şekilde yanıtla. "
            "Asla belgede yer almayan bilgileri uydurma."
        )

        user_content = f"Bağlam:\n{context}\n\nSoru: {question}"

        return [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_content}
        ]

    def _build_hallucination_message(self, context: str, question: str, answer: str) -> list[dict]:
        """Kullanıcının sorusuna oluşturulan cevabın sunulan şirket belgelerine sadık kalıp kalmadığını kontrol eder."""
        system_instruction = (
            "Sen bir denetçisin. Sana sunulan Bağlamdaki şirket belgelerini ve üretilen Cevabı incele.\n"
            "Cevaptaki tüm iddialar ve bilgiler Bağlam tarafından doğrulanıyor mu?\n"
            "Sadece tek bir kelime olarak 'evet' veya 'hayır' cevabı ver."
        )

        user_content = f"Bağlam:\n{context}\n\nSoru: {question}\n\nCevap:\n{answer}"

        return [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_content}
        ]

    def decide_hallucinate(self, state: AgentState) -> Literal["end", "fallback"]:
        """Hallucination sonucuna göre grafiğin rotasını belirler."""
        grade = str(state.get("hallucination_grade", "")).strip().lower()
        if "evet" in grade or "yes" in grade:
            return "end"
        return "fallback"

    def _retrieve_node(self, state: AgentState):
        print("retrieve node harekete geçti...")
        search_result = self.rag_engine.search(state["question"])
        return {
            "context": search_result["context"],
            "sources": search_result["sources"]
        }

    def _generate_node(self, state: AgentState):
        context = state.get("context", "").strip()
        question = state["question"]

        # Bağlam boşsa doğrudan güvenli yanıt dön (LLM halüsinasyonunu engelle)
        if not context:
            if self._is_greeting(question):
                return {"answer": "Merhaba! Ben kurumsal yapay zeka asistanınızım. Şirket içi belgelerinizle ilgili sorularınızı yanıtlayabilirim."}
            return {"answer": "Bu bilgi şirket belgelerinde bulunmamaktadır."}

        messages = self._build_messages(context, question)

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        model_inputs = self.tokenizer([prompt], return_tensors="pt").to(self.model.device)

        with torch.inference_mode():
            outputs = self.model.generate(
                **model_inputs,
                max_new_tokens=256,
                do_sample=False,
                repetition_penalty=1.0
            )

        # Sadece yeni üretilen token'ları çöz (prompt kısmını at)
        input_len = model_inputs["input_ids"].shape[1]
        generated_tokens = outputs[0][input_len:]
        answer = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()

        return {"answer": answer}

    def _grade_hallucination_node(self, state: AgentState):
        context = state.get("context", "").strip()
        question = state["question"]
        answer = state.get("answer", "")

        # Eğer bağlam boşsa (zaten selamlama veya güvenli red mesajı üretilmiştir), denetlemeye gerek yok
        if not context:
            return {"hallucination_grade": "evet"}

        messages = self._build_hallucination_message(context, question, answer)

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        model_inputs = self.tokenizer([prompt], return_tensors="pt").to(self.model.device)

        with torch.inference_mode():
            outputs = self.model.generate(
                **model_inputs,
                max_new_tokens=5,
                do_sample=False,
                repetition_penalty=1.0
            )

        # Sadece yeni üretilen token'ları çöz (prompt kısmını at)
        input_len = model_inputs["input_ids"].shape[1]
        generated_tokens = outputs[0][input_len:]
        hallucination_grade = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        print(f"Hallucination denetim sonucu: {hallucination_grade}")

        return {"hallucination_grade": hallucination_grade}

    def _fallback_node(self, state: AgentState):
        """Halüsinasyon tespit edildiğinde devreye giren güvenli yanıt düğümü."""
        print("Halüsinasyon tespit edildi, fallback devreye girdi!")
        return {"answer": "Bu bilgi şirket belgelerinde tam olarak doğrulanamamaktadır."}

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)
        workflow.add_node("grade", self._grade_hallucination_node)
        workflow.add_node("fallback", self._fallback_node)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", "grade")

        workflow.add_conditional_edges(
            "grade",
            self.decide_hallucinate,
            {
                "end": END,
                "fallback": "fallback"
            }
        )
        workflow.add_edge("fallback", END)

        return workflow.compile()

    def query(self, question: str) -> dict:
        result = self.app.invoke({"question": question, "context": "", "sources": [], "answer": "", "hallucination_grade": ""})
        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", [])
        }

    def stream_events(self, question: str):
        """Kullanıcı sorusuna bağlam bularak kaynakları ve token akışını event olarak üretir."""
        # 1. RAG ile ilgili belgeleri ve bağlamı getir
        search_result = self.rag_engine.search(question)
        context = search_result.get("context", "").strip()
        sources = search_result.get("sources", [])

        # Bulunan kaynakları bildir
        yield {"type": "sources", "sources": sources}

        # 2. Bağlam boşsa doğrudan güvenli yanıt akıt (LLM halüsinasyonunu engelle)
        if not context:
            if self._is_greeting(question):
                fallback_msg = "Merhaba! Ben kurumsal yapay zeka asistanınızım. Şirket içi belgelerinizle ilgili sorularınızı yanıtlayabilirim."
            else:
                fallback_msg = "Bu bilgi şirket belgelerinde bulunmamaktadır."

            for word in fallback_msg.split(" "):
                yield {"type": "token", "token": word + " "}
            yield {"type": "done"}
            return

        # 3. Chat şablonunu oluştur
        messages = self._build_messages(context, question)

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # 4. Tokenize et ve cihaza aktar
        model_inputs = self.tokenizer([prompt], return_tensors="pt").to(self.model.device)

        # 5. Streamer oluştur
        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )

        generation_kwargs = dict(
            model_inputs,
            streamer=streamer,
            max_new_tokens=256,
            do_sample=False,
            repetition_penalty=1.0
        )

        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        for new_text in streamer:
            if new_text:
                yield {"type": "token", "token": new_text}

        yield {"type": "done"}

    def stream_query(self, question: str):
        """Kullanıcı sorusuna sadece metin token akışı üretir."""
        for event in self.stream_events(question):
            if event["type"] == "token":
                yield event["token"]

        
