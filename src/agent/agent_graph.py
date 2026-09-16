from typing import TypedDict
from langgraph.graph import StateGraph, END
from src.agent.llm import create_chat_model
from src.rag.rag_engine import RAGEngine
from src.agent.nodes import AgentNodes
from src.agent.query_service import QueryService


class AgentState(TypedDict):
    question: str
    context: str
    sources: list[dict]
    answer: str
    hallucination_grade: str
    retry_count: int
    is_refined: bool


class EnterpriseRAGAgent:
    """LangGraph iş akışını oluşturan ve sorgu servisini başlatan orkestratör sınıf."""

    def __init__(self, rag_engine: RAGEngine):
        self.rag_engine = rag_engine
        self.chat_model = create_chat_model()
        self.nodes = AgentNodes(self.chat_model, self.rag_engine)
        self.app = self._build_graph()
        self.service = QueryService(self.app, self.nodes, self.chat_model)

    def _build_graph(self):
        """LangGraph durum grafını yapılandırır ve derler."""
        workflow = StateGraph(AgentState)

        workflow.add_node("retrieve", self.nodes.retrieve)
        workflow.add_node("generate", self.nodes.generate)
        workflow.add_node("grade", self.nodes.grade_hallucination)
        workflow.add_node("refine", self.nodes.refine)
        workflow.add_node("fallback", self.nodes.fallback)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", "grade")
        workflow.add_conditional_edges(
            "grade",
            self.nodes.decide_hallucinate,
            {"end": END, "refine": "refine", "fallback": "fallback"}
        )
        workflow.add_edge("refine", END)
        workflow.add_edge("fallback", END)

        return workflow.compile()


    # ──────────────────────────── SORGU SERVİSİ KÖPRÜLERİ ────────────────────────────

    def query(self, question: str) -> dict:
        """Toplu (batch) sorgu çalıştırma."""
        return self.service.query(question)

    def stream_events(self, question: str):
        """Durum, kaynak ve token bazlı canlı akış."""
        return self.service.stream_events(question)

    def stream_query(self, question: str):
        """Yalnızca metin token akışı."""
        return self.service.stream_query(question)
