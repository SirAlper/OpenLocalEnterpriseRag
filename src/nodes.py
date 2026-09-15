from typing import Literal
from langchain_huggingface import ChatHuggingFace
from src.rag_engine import RAGEngine
from src.prompts import (
    build_rag_messages, build_grader_messages,
    NO_CONTEXT_RESPONSE, FALLBACK_RESPONSE
)


class AgentNodes:
    """LangGraph düğüm fonksiyonlarını barındıran sınıf.

    Her düğüm metodu LangGraph'ın beklediği (state) -> dict imzasına sahiptir.
    """

    def __init__(self, chat_model: ChatHuggingFace, rag_engine: RAGEngine):
        self.chat_model = chat_model
        self.rag_engine = rag_engine

    # ──────────────────────────── UZMAN DÜĞÜMLER ────────────────────────────

    def retrieve(self, state: dict) -> dict:
        """Vektör veritabanından en alakalı belge parçalarını arar."""
        question = state["question"].strip()
        print(f"[LangGraph Node: retrieve] Belgeler aranıyor: '{question}'...")
        search_result = self.rag_engine.search(question)
        return {
            "context": search_result.get("context", ""),
            "sources": search_result.get("sources", [])
        }

    def generate(self, state: dict) -> dict:
        """ChatHuggingFace ile kurumsal yanıt üretir."""
        print("[LangGraph Node: generate] Yanıt üretiliyor...")
        context = state.get("context", "").strip()
        if not context:
            return {"answer": NO_CONTEXT_RESPONSE}

        messages = build_rag_messages(context, state["question"])
        response = self.chat_model.invoke(messages)
        return {"answer": response.content.strip()}

    def grade_hallucination(self, state: dict) -> dict:
        """Üretilen yanıtın bağlama sadakatini denetler."""
        print("[LangGraph Node: grade] Halüsinasyon denetimi yapılıyor...")
        context = state.get("context", "").strip()
        if not context:
            return {"hallucination_grade": "evet"}

        messages = build_grader_messages(context, state["question"], state.get("answer", ""))
        response = self.chat_model.invoke(messages)
        grade = response.content.strip()
        print(f"Hallucination denetim sonucu: {grade}")
        return {"hallucination_grade": grade}

    def fallback(self, state: dict) -> dict:
        """Halüsinasyon tespit edildiğinde güvenli yanıt döner."""
        print("[LangGraph Node: fallback] Güvenli fallback devreye girdi!")
        return {"answer": FALLBACK_RESPONSE}

    # ──────────────────────────── KARAR FONKSİYONLARI ────────────────────────────

    @staticmethod
    def decide_hallucinate(state: dict) -> Literal["end", "fallback"]:
        grade = str(state.get("hallucination_grade", "")).strip().lower()
        return "end" if ("evet" in grade or "yes" in grade) else "fallback"
