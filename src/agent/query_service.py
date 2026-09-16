from typing import Generator
from langchain_huggingface import ChatHuggingFace
from src.agent.nodes import AgentNodes
from src.agent.prompts import build_rag_messages, NO_CONTEXT_RESPONSE


class QueryService:
    """Service managing batch queries and event-based execution flows for the RAG Agent."""

    def __init__(self, app, nodes: AgentNodes, chat_model: ChatHuggingFace):
        self.app = app
        self.nodes = nodes
        self.chat_model = chat_model

    def query(self, question: str) -> dict:
        """Run the LangGraph workflow and return the verified answer, sources, and audit status."""
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
        """Yield workflow stage events and deliver the final answer upon completion."""
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
        yield {"type": "status", "message": "🔍 Searching relevant enterprise documents...", "node": "retrieve"}
        retrieve_out = self.nodes.retrieve(state)
        state["context"] = retrieve_out["context"]
        state["sources"] = retrieve_out["sources"]
        yield {"type": "sources", "sources": state["sources"]}

        context = state["context"].strip()
        if not context:
            yield {"type": "done", "answer": NO_CONTEXT_RESPONSE, "sources": [], "is_refined": False}
            return

        # 2. GENERATE
        yield {"type": "status", "message": "✍️ Preparing response...", "node": "generate"}
        generate_out = self.nodes.generate(state)
        state["answer"] = generate_out["answer"]

        # 3. GRADE (Hallucination Audit)
        yield {"type": "status", "message": "🛡️ Verifying factual accuracy...", "node": "grade"}
        grade_out = self.nodes.grade_hallucination(state)
        state["hallucination_grade"] = grade_out["hallucination_grade"]

        decision = self.nodes.decide_hallucinate(state)
        if decision == "refine":
            yield {
                "type": "status",
                "message": "✍️ Re-evaluating and refining response to match documents...",
                "node": "refine"
            }
            refine_out = self.nodes.refine(state)
            state["answer"] = refine_out["answer"]
            state["is_refined"] = True
            state["retry_count"] = refine_out["retry_count"]
            yield {"type": "grade", "grade": state["hallucination_grade"], "passed": True, "is_refined": True}
        elif decision == "fallback":
            yield {
                "type": "warning",
                "message": "⚠️ Generated response could not be fully verified against company documents.",
                "node": "fallback"
            }
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
        """Yield final answer upon workflow completion."""
        for event in self.stream_events(question):
            if event["type"] == "done":
                yield event["answer"]
