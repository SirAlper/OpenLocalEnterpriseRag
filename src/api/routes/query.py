import json
import asyncio
import queue
import threading
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.schemas import QueryRequest
from src.api.state import get_agent, query_lock
from src.core.logger import get_logger

logger = get_logger("API.Query")
router = APIRouter(tags=["AI Query"])


@router.post("/api/v1/query", summary="Query Enterprise AI Assistant")
async def query_rag(request: QueryRequest):
    """Execute LangGraph workflow and return verified answer, reference sources, and audit status."""
    try:
        logger.info(f"Received user question: {request.question}")
        current_agent = get_agent()
        async with query_lock:
            result = await asyncio.to_thread(current_agent.query, request.question)

        return {
            "status": "success",
            "answer": result["answer"],
            "sources": result["sources"],
            "hallucination_grade": result.get("hallucination_grade", ""),
            "is_refined": result.get("is_refined", False)
        }
    except Exception as e:
        logger.error(f"Error during query execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/query-stream", summary="Query Enterprise AI Assistant (Event Stream)")
async def query_rag_stream(request: QueryRequest):
    """Stream LangGraph stage events and deliver final answer via NDJSON format."""
    try:
        logger.info(f"Received streaming question: {request.question}")
        current_agent = get_agent()

        async def event_generator():
            async with query_lock:
                q: queue.Queue = queue.Queue()
                sentinel = object()

                def worker():
                    try:
                        for ev in current_agent.stream_events(request.question):
                            q.put(ev)
                    except Exception as err:
                        logger.error(f"Error in stream worker: {err}")
                        q.put({"type": "error", "message": str(err)})
                    finally:
                        q.put(sentinel)

                thread = threading.Thread(target=worker)
                thread.start()

                while True:
                    while q.empty() and thread.is_alive():
                        await asyncio.sleep(0.05)
                    if not q.empty():
                        item = q.get()
                        if item is sentinel:
                            break
                        yield json.dumps(item, ensure_ascii=False) + "\n"
                    elif not thread.is_alive():
                        break

        return StreamingResponse(event_generator(), media_type="application/x-ndjson")
    except Exception as e:
        logger.error(f"Error initiating streaming query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
