import time
import json
import asyncio
import queue
import threading
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.api.schemas import QueryRequest
from src.api.state import get_agent, query_concurrency_gate
from src.auth.dependencies import require_role
from src.auth.models import User
from src.core.audit import audit_logger
from src.core.logger import get_logger

logger = get_logger("API.Query")
router = APIRouter(tags=["AI Query"])


@router.post("/api/v1/query", summary="Query Enterprise AI Assistant")
async def query_rag(
    request: QueryRequest,
    http_req: Request,
    current_user: User = Depends(require_role("admin", "editor", "viewer")),
):
    """Execute LangGraph workflow and return verified answer, reference sources, and audit status."""
    start_time = time.time()
    ip_addr = http_req.client.host if http_req.client else None
    try:
        thread_id = f"{current_user.username}_{request.session_id}" if request.session_id else None
        logger.info(
            f"Received question from '{current_user.username}' (role: {current_user.role}, thread: {thread_id}): {request.question}"
        )
        current_agent = get_agent()
        async with query_concurrency_gate:
            result = await asyncio.to_thread(current_agent.query, request.question, thread_id=thread_id)

        duration_ms = int((time.time() - start_time) * 1000)
        source_names = [s.get("source") for s in result.get("sources", []) if s.get("source")]

        audit_logger.log(
            username=current_user.username,
            role=current_user.role,
            action="query",
            detail=request.question,
            sources=source_names,
            answer_preview=result.get("answer", ""),
            ip_address=ip_addr,
            duration_ms=duration_ms,
            status="success",
        )

        return {
            "status": "success",
            "answer": result["answer"],
            "sources": result["sources"],
            "hallucination_grade": result.get("hallucination_grade", ""),
            "is_refined": result.get("is_refined", False)
        }
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        audit_logger.log(
            username=current_user.username,
            role=current_user.role,
            action="query",
            detail=request.question,
            ip_address=ip_addr,
            duration_ms=duration_ms,
            status="error",
        )
        logger.error(f"Error during query execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/query-stream", summary="Query Enterprise AI Assistant (Event Stream)")
async def query_rag_stream(
    request: QueryRequest,
    current_user: User = Depends(require_role("admin", "editor", "viewer")),
):
    """Stream LangGraph stage events and deliver final answer via NDJSON format."""
    try:
        thread_id = f"{current_user.username}_{request.session_id}" if request.session_id else None
        logger.info(
            f"Received streaming question from '{current_user.username}' (thread: {thread_id}): {request.question}"
        )
        current_agent = get_agent()

        async def event_generator():
            async with query_concurrency_gate:
                q: queue.Queue = queue.Queue()
                sentinel = object()

                def worker():
                    try:
                        for ev in current_agent.stream_events(request.question, thread_id=thread_id):
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
