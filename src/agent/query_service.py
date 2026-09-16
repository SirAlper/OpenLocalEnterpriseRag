from typing import Generator
from langchain_huggingface import ChatHuggingFace
from src.agent.nodes import AgentNodes
from src.agent.prompts import build_rag_messages, NO_CONTEXT_RESPONSE


class QueryService:
    """RAG Ajanı için toplu sorgu ve durum bazlı akış yöntemlerini yöneten servis."""

    def __init__(self, app, nodes: AgentNodes, chat_model: ChatHuggingFace):
        self.app = app
        self.nodes = nodes
        self.chat_model = chat_model

    def query(self, question: str) -> dict:
        """LangGraph iş akışını çalıştırarak nihai yanıtı, kaynakları ve denetim sonucunu döner."""
        result = self.app.invoke({
            "question": question,
            "context": "",
            "sources": [],
            "answer": "",
            "hallucination_grade": "",
            "retry_count": 0,
            "is_refined": False
        })
        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "hallucination_grade": result.get("hallucination_grade", ""),
            "is_refined": result.get("is_refined", False)
        }

    def stream_events(self, question: str) -> Generator[dict, None, None]:
        """LangGraph iş akışının durum adımlarını ve nihai yanıtı tek seferde döner."""
        state = {
            "question": question,
            "context": "",
            "sources": [],
            "answer": "",
            "hallucination_grade": "",
            "retry_count": 0,
            "is_refined": False
        }

        # 1. RETRIEVE
        yield {"type": "status", "message": "🔍 İlgili şirket belgeleri taranıyor...", "node": "retrieve"}
        retrieve_out = self.nodes.retrieve(state)
        state["context"] = retrieve_out["context"]
        state["sources"] = retrieve_out["sources"]
        yield {"type": "sources", "sources": state["sources"]}

        context = state["context"].strip()
        if not context:
            yield {"type": "done", "answer": NO_CONTEXT_RESPONSE, "sources": [], "is_refined": False}
            return

        # 2. GENERATE
        yield {"type": "status", "message": "✍️ Yanıt hazırlanıyor...", "node": "generate"}
        generate_out = self.nodes.generate(state)
        state["answer"] = generate_out["answer"]

        # 3. GRADE (Halüsinasyon Denetimi)
        yield {"type": "status", "message": "🛡️ Kaynak uyumu ve doğruluk denetleniyor...", "node": "grade"}
        grade_out = self.nodes.grade_hallucination(state)
        state["hallucination_grade"] = grade_out["hallucination_grade"]

        decision = self.nodes.decide_hallucinate(state)
        if decision == "refine":
            yield {"type": "status", "message": "✍️ Yanıt yeniden değerlendiriliyor ve belgelere göre sadeleştiriliyor...", "node": "refine"}
            refine_out = self.nodes.refine(state)
            state["answer"] = refine_out["answer"]
            state["is_refined"] = True
            state["retry_count"] = refine_out["retry_count"]
            yield {"type": "grade", "grade": state["hallucination_grade"], "passed": True, "is_refined": True}
        elif decision == "fallback":
            yield {"type": "warning", "message": "⚠️ Üretilen yanıt şirket belgeleriyle doğrulanamadı.", "node": "fallback"}
            fallback_out = self.nodes.fallback(state)
            state["answer"] = fallback_out["answer"]
            yield {"type": "grade", "grade": state["hallucination_grade"], "passed": False, "is_refined": False}
        else:
            yield {"type": "grade", "grade": state["hallucination_grade"], "passed": True, "is_refined": False}

        yield {
            "type": "done",
            "answer": state["answer"],
            "sources": state["sources"],
            "is_refined": state.get("is_refined", False)
        }

    def stream_query(self, question: str) -> Generator[str, None, None]:
        """İş akışı tamamlandığında nihai yanıtı döner."""
        for event in self.stream_events(question):
            if event["type"] == "done":
                yield event["answer"]

