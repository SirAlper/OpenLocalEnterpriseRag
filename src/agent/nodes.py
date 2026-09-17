from typing import Literal
from langchain_huggingface import ChatHuggingFace
from src.rag.rag_engine import RAGEngine
from src.agent.prompts import (
    build_rag_messages, build_grader_messages, build_refine_messages,
    NO_CONTEXT_RESPONSE, FALLBACK_RESPONSE
)
from src.core.logger import get_logger

logger = get_logger("AgentNodes")


class AgentNodes:
    """Class containing LangGraph node functions.

    Each node method follows the standard LangGraph signature: (state: dict) -> dict.
    """

    def __init__(self, chat_model: ChatHuggingFace, rag_engine: RAGEngine):
        self.chat_model = chat_model
        self.rag_engine = rag_engine

    # ──────────────────────────── WORKFLOW NODES ────────────────────────────

    def retrieve(self, state: dict) -> dict:
        """Search vector database and reranker for the most relevant document chunks."""
        question = state["question"].strip()
        chat_history = state.get("chat_history", [])

        # Enrich search query with context from previous question if available
        if chat_history:
            recent_context = " ".join([
                turn.get("question", "") for turn in chat_history[-2:]
                if turn.get("question")
            ])
            search_query = f"{question} {recent_context}".strip()
        else:
            search_query = question

        logger.info(f"[retrieve] Searching documents for: '{question}' (query: '{search_query}')...")
        search_result = self.rag_engine.search(search_query)
        return {
            "context": search_result.get("context", ""),
            "sources": search_result.get("sources", []),
        }

    def generate(self, state: dict) -> dict:
        """Generate enterprise RAG response using ChatHuggingFace/ChatOllama."""
        logger.info("[generate] Generating response...")
        context = state.get("context", "").strip()
        chat_history = list(state.get("chat_history", []))

        if not context:
            chat_history.append({"question": state["question"], "answer": NO_CONTEXT_RESPONSE})
            return {"answer": NO_CONTEXT_RESPONSE, "chat_history": chat_history}

        messages = build_rag_messages(context, state["question"], chat_history)
        response = self.chat_model.invoke(messages)
        answer = response.content.strip()

        chat_history.append({"question": state["question"], "answer": answer})
        return {"answer": answer, "chat_history": chat_history}

    def grade_hallucination(self, state: dict) -> dict:
        """Audit the fidelity of the generated answer against the retrieved context."""
        logger.info("[grade] Auditing answer for hallucinations...")
        context = state.get("context", "").strip()
        if not context:
            return {"hallucination_grade": "yes"}

        messages = build_grader_messages(context, state["question"], state.get("answer", ""))
        response = self.chat_model.invoke(messages)
        grade = response.content.strip()
        logger.info(f"[grade] Audit result: '{grade}'")
        return {"hallucination_grade": grade}

    def refine(self, state: dict) -> dict:
        """Prune and re-evaluate draft answers that contain unverified or speculative statements."""
        logger.info("[refine] Rethinking and refining response to match context...")
        context = state.get("context", "").strip()
        question = state.get("question", "").strip()
        draft_answer = state.get("answer", "").strip()
        chat_history = list(state.get("chat_history", []))

        if not context:
            chat_history.append({"question": question, "answer": NO_CONTEXT_RESPONSE})
            return {"answer": NO_CONTEXT_RESPONSE, "is_refined": False, "chat_history": chat_history}

        messages = build_refine_messages(context, question, draft_answer)
        response = self.chat_model.invoke(messages)
        refined_answer = response.content.strip()
        logger.info("[refine] Response successfully refined.")

        if chat_history and chat_history[-1].get("question") == question:
            chat_history[-1]["answer"] = refined_answer
        else:
            chat_history.append({"question": question, "answer": refined_answer})

        return {
            "answer": refined_answer,
            "retry_count": state.get("retry_count", 0) + 1,
            "is_refined": True,
            "chat_history": chat_history,
        }

    def fallback(self, state: dict) -> dict:
        """Provide a safe fallback answer when factual consistency cannot be verified."""
        logger.warning("[fallback] Safe fallback triggered!")
        chat_history = list(state.get("chat_history", []))
        if chat_history and chat_history[-1].get("question") == state.get("question"):
            chat_history[-1]["answer"] = FALLBACK_RESPONSE
        else:
            chat_history.append({"question": state.get("question", ""), "answer": FALLBACK_RESPONSE})
        return {"answer": FALLBACK_RESPONSE, "chat_history": chat_history}

    # ──────────────────────────── CONDITIONAL EDGES ────────────────────────────

    @staticmethod
    def decide_hallucinate(state: dict) -> Literal["end", "refine", "fallback"]:
        grade = str(state.get("hallucination_grade", "")).strip().lower()
        is_passed = "yes" in grade or "evet" in grade
        if is_passed:
            return "end"

        # If not refined previously (retry_count < 1), route to refine node
        if state.get("retry_count", 0) < 1:
            logger.info("[decide] Hallucination suspected: Routing to refine node.")
            return "refine"

        logger.warning("[decide] Max retries reached: Routing to fallback node.")
        return "fallback"
