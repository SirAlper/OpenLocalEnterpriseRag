from typing import TypedDict
from langgraph.graph import StateGraph, END
from src.llm import create_chat_model
from src.rag_engine import RAGEngine
from src.nodes import AgentNodes
from src.prompts import (
    build_rag_messages, NO_CONTEXT_RESPONSE, FALLBACK_RESPONSE
)


class AgentState(TypedDict):
    question: str
    context: str
    sources: list[dict]
    answer: str
    hallucination_grade: str


class EnterpriseRAGAgent:
    def __init__(self, rag_engine: RAGEngine):
        self.rag_engine = rag_engine
        self.chat_model = create_chat_model()
        self.nodes = AgentNodes(self.chat_model, self.rag_engine)
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("retrieve", self.nodes.retrieve)
        workflow.add_node("generate", self.nodes.generate)
        workflow.add_node("grade", self.nodes.grade_hallucination)
        workflow.add_node("fallback", self.nodes.fallback)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", "grade")
        workflow.add_conditional_edges("grade", self.nodes.decide_hallucinate, {"end": END, "fallback": "fallback"})
        workflow.add_edge("fallback", END)

        return workflow.compile()

    # ──────────────────────────── SORGU YÖNTEMLERİ ────────────────────────────

    def query(self, question: str) -> dict:
        """LangGraph iş akışını toplu (batch) olarak çalıştırır."""
        result = self.app.invoke({
            "question": question, "context": "",
            "sources": [], "answer": "", "hallucination_grade": ""
        })
        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "hallucination_grade": result.get("hallucination_grade", "")
        }

    def stream_events(self, question: str):
        """LangGraph iş akışı ile tam senkronize canlı akış üretir."""
        state: AgentState = {
            "question": question, "context": "",
            "sources": [], "answer": "", "hallucination_grade": ""
        }

        # 1. RETRIEVE
        yield {"type": "status", "message": "🔍 İlgili şirket belgeleri taranıyor...", "node": "retrieve"}
        retrieve_out = self.nodes.retrieve(state)
        state["context"] = retrieve_out["context"]
        state["sources"] = retrieve_out["sources"]
        yield {"type": "sources", "sources": state["sources"]}

        context = state["context"].strip()
        if not context:
            for word in NO_CONTEXT_RESPONSE.split(" "):
                yield {"type": "token", "token": word + " "}
            yield {"type": "done", "answer": NO_CONTEXT_RESPONSE, "sources": []}
            return

        # 2. GENERATE (ChatHuggingFace Canlı Akış)
        yield {"type": "status", "message": "✍️ Yanıt oluşturuluyor...", "node": "generate"}
        messages = build_rag_messages(context, question)

        generated_chunks = []
        for chunk in self.chat_model.stream(messages):
            if chunk.content:
                generated_chunks.append(chunk.content)
                yield {"type": "token", "token": chunk.content}

        state["answer"] = "".join(generated_chunks).strip()

        # 3. GRADE (Halüsinasyon Denetimi)
        yield {"type": "status", "message": "🛡️ Kaynak uyumu ve doğruluk denetleniyor...", "node": "grade"}
        grade_out = self.nodes.grade_hallucination(state)
        state["hallucination_grade"] = grade_out["hallucination_grade"]

        decision = self.nodes.decide_hallucinate(state)
        if decision == "fallback":
            yield {"type": "warning", "message": "⚠️ Üretilen yanıt şirket belgeleriyle doğrulanamadı.", "node": "fallback"}
            yield {"type": "grade", "grade": state["hallucination_grade"], "passed": False}
        else:
            yield {"type": "grade", "grade": state["hallucination_grade"], "passed": True}

        yield {"type": "done", "answer": state["answer"], "sources": state["sources"]}

    def stream_query(self, question: str):
        """Sadece metin token akışı üretir."""
        for event in self.stream_events(question):
            if event["type"] == "token":
                yield event["token"]
