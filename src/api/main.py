import os
import time
import json
import asyncio
import queue
import threading
from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.rag.document_loader import DocumentLoader
from src.rag.rag_engine import RAGEngine
from src.agent.agent_graph import EnterpriseRAGAgent
from src.connectors.db_connector import DatabaseConnector, create_sample_sqlite_db
from src.connectors.db_loader import DatabaseTableLoader
from src.core.config import (
    DOCS_PATH,
    EMBEDDING_MODEL_NAME,
    LLM_MODEL_NAME,
    DATABASE_URL,
    SAMPLE_DB_PATH,
    CORS_ORIGINS,
    MAX_UPLOAD_SIZE_MB,
    ALLOWED_UPLOAD_EXTENSIONS,
)
from src.core.logger import get_logger

logger = get_logger("API")

# Lazy initialized singletons
rag_engine: Optional[RAGEngine] = None
agent: Optional[EnterpriseRAGAgent] = None
document_loader: Optional[DocumentLoader] = None
db_connector: Optional[DatabaseConnector] = None
db_loader: Optional[DatabaseTableLoader] = None
query_lock = asyncio.Lock()


def get_rag_engine() -> RAGEngine:
    global rag_engine
    if rag_engine is None:
        rag_engine = RAGEngine()
    return rag_engine


def get_agent() -> EnterpriseRAGAgent:
    global agent
    if agent is None:
        agent = EnterpriseRAGAgent(get_rag_engine())
    return agent


def get_document_loader() -> DocumentLoader:
    global document_loader
    if document_loader is None:
        document_loader = DocumentLoader(DOCS_PATH)
    return document_loader


def get_db_connector() -> DatabaseConnector:
    global db_connector
    if db_connector is None:
        db_connector = DatabaseConnector()
    return db_connector


def get_db_loader() -> DatabaseTableLoader:
    global db_loader
    if db_loader is None:
        db_loader = DatabaseTableLoader(get_db_connector())
    return db_loader


def auto_index_on_startup():
    """Scan data/ folder on server startup and automatically index any unindexed documents into ChromaDB."""
    if not os.path.exists(DOCS_PATH):
        os.makedirs(DOCS_PATH, exist_ok=True)
        return

    engine = get_rag_engine()
    loader = get_document_loader()
    db_stats = engine.get_stats()
    indexed_files = set(db_stats.get("document_chunks", {}).keys())

    data_files = [
        f for f in os.listdir(DOCS_PATH)
        if os.path.isfile(os.path.join(DOCS_PATH, f)) and os.path.splitext(f)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS
    ]

    unindexed = [f for f in data_files if f not in indexed_files]

    if not unindexed:
        logger.info(f"[Auto-Indexing] No unindexed documents found in data/. ({len(indexed_files)} files indexed)")
        return

    logger.info(f"[Auto-Indexing] Detected {len(unindexed)} new document(s), indexing...")
    for filename in unindexed:
        file_path = os.path.join(DOCS_PATH, filename)
        chunks, ids, metadatas = loader.load_and_chunk_file(file_path)
        if chunks:
            engine.add_documents(chunks, ids, metadatas)
            logger.info(f"  ✓ '{filename}' -> {len(chunks)} chunks indexed.")
        else:
            logger.warning(f"  ✗ '{filename}' -> no parseable text found.")

    logger.info("[Auto-Indexing] Completed successfully!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan context manager to initialize models and connections on startup."""
    global rag_engine, agent, document_loader, db_connector, db_loader
    logger.info("Initializing Enterprise RAG services...")

    # Initialize sample database if needed
    if not DATABASE_URL and not os.path.exists(SAMPLE_DB_PATH):
        try:
            create_sample_sqlite_db(SAMPLE_DB_PATH)
            logger.info(f"Sample database created at '{SAMPLE_DB_PATH}'.")
        except Exception as e:
            logger.warning(f"Could not create sample database: {e}")

    # Eagerly initialize core singletons on server start
    rag_engine = get_rag_engine()
    agent = get_agent()
    document_loader = get_document_loader()
    db_connector = get_db_connector()
    db_loader = get_db_loader()

    auto_index_on_startup()
    logger.info("Enterprise RAG services initialized successfully.")
    yield
    logger.info("Enterprise RAG services shutdown.")


app = FastAPI(
    title="Enterprise Local RAG API",
    description="Privacy-first, on-premise RAG and Agentic AI gateway with zero cloud dependencies.",
    version="1.1.0",
    lifespan=lifespan
)

# CORS configuration (reads allowed origins from config/env)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class SyncTableRequest(BaseModel):
    table_name: str
    text_columns: Optional[List[str]] = None
    title_column: Optional[str] = None
    id_column: Optional[str] = None


class TestQueryRequest(BaseModel):
    query: str


@app.get("/api/v1/stats", summary="System and Vector Store Statistics")
def get_system_stats():
    """Return hardware acceleration details, active models, and index statistics."""
    engine = get_rag_engine()
    connector = get_db_connector()
    db_stats = engine.get_stats()

    is_cuda = False
    try:
        import torch
        is_cuda = torch.cuda.is_available()
    except ImportError:
        pass

    device = "CUDA (NVIDIA GPU)" if is_cuda else "CPU"
    db_conn_info = connector.test_connection()

    return {
        "status": "success",
        "device": device,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "llm_model": LLM_MODEL_NAME,
        "total_chunks": db_stats["total_chunks"],
        "total_documents": db_stats["total_documents"],
        "documents": db_stats["document_chunks"],
        "database": db_conn_info
    }


@app.get("/api/v1/documents", summary="List Indexed Documents")
def list_documents():
    """List files in data/ directory along with their chunk counts in ChromaDB."""
    if not os.path.exists(DOCS_PATH):
        os.makedirs(DOCS_PATH, exist_ok=True)

    engine = get_rag_engine()
    db_stats = engine.get_stats()
    chunk_map = db_stats.get("document_chunks", {})

    files = []
    for filename in os.listdir(DOCS_PATH):
        file_path = os.path.join(DOCS_PATH, filename)
        if os.path.isfile(file_path):
            stat = os.stat(file_path)
            files.append({
                "filename": filename,
                "size_kb": round(stat.st_size / 1024, 2),
                "chunk_count": chunk_map.get(filename, 0),
                "modified_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            })

    return {"status": "success", "count": len(files), "documents": files}


@app.delete("/api/v1/documents/{filename}", summary="Delete Document and Vector Chunks")
def delete_document(filename: str):
    """Permanently delete specified file from data/ directory and remove chunks from ChromaDB."""
    # Prevent path traversal in deletion
    safe_filename = os.path.basename(filename).strip()
    if not safe_filename or safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid filename format.")

    file_path = os.path.join(DOCS_PATH, safe_filename)
    file_deleted = False

    if os.path.exists(file_path):
        os.remove(file_path)
        file_deleted = True

    engine = get_rag_engine()
    deleted_chunks = engine.delete_document(safe_filename)

    if not file_deleted and deleted_chunks == 0:
        raise HTTPException(status_code=404, detail=f"'{safe_filename}' was not found.")

    logger.info(f"Deleted document '{safe_filename}' (Chunks deleted: {deleted_chunks})")
    return {
        "status": "success",
        "message": f"'{safe_filename}' was deleted successfully.",
        "deleted_chunks": deleted_chunks,
        "file_deleted": file_deleted
    }


@app.post("/api/v1/upload-file", summary="Upload and Index Document")
async def upload_file(file: UploadFile = File(...)):
    """Upload a new PDF, DOCX, or TXT document, chunk it, and index it into ChromaDB."""
    if not os.path.exists(DOCS_PATH):
        os.makedirs(DOCS_PATH, exist_ok=True)

    raw_filename = file.filename or ""
    safe_filename = os.path.basename(raw_filename).strip()
    if not safe_filename or safe_filename.startswith("..") or "/" in safe_filename or "\\" in safe_filename:
        raise HTTPException(status_code=400, detail="Invalid or unsafe filename.")

    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
        )

    # 1. Save uploaded file with size checking (up to MAX_UPLOAD_SIZE_MB)
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file_path = os.path.join(DOCS_PATH, safe_filename)
    total_bytes = 0

    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    buffer.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum allowed size of {MAX_UPLOAD_SIZE_MB}MB."
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"File upload write error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write uploaded file: {e}")

    # 2. Chunk uploaded file
    loader = get_document_loader()
    chunks, ids, metadatas = loader.load_and_chunk_file(file_path)

    if not chunks:
        return {
            "status": "warning",
            "message": f"'{safe_filename}' uploaded, but no parseable text was extracted.",
            "chunk_count": 0
        }

    # 3. Upsert to vector database (clean older chunks if file previously existed)
    engine = get_rag_engine()
    engine.delete_document(safe_filename)
    engine.add_documents(chunks, ids, metadatas)

    logger.info(f"Successfully uploaded and indexed '{safe_filename}' ({len(chunks)} chunks).")
    return {
        "status": "success",
        "message": f"'{safe_filename}' successfully uploaded and indexed.",
        "filename": safe_filename,
        "chunk_count": len(chunks)
    }


@app.post("/api/v1/query", summary="Query Enterprise AI Assistant")
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


@app.post("/api/v1/query-stream", summary="Query Enterprise AI Assistant (Event Stream)")
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


@app.get("/api/v1/database/status", summary="Database Connection Status and Schema")
def get_database_status():
    """Return database connection status, dialect type, and accessible tables."""
    connector = get_db_connector()
    conn_info = connector.test_connection()
    schema_summary = connector.get_schema_summary() if connector.is_connected else ""
    return {
        "status": "success",
        "connection": conn_info,
        "schema_summary": schema_summary
    }


@app.post("/api/v1/database/test-query", summary="Execute Safe Read-Only SQL Query")
def run_database_query(req: TestQueryRequest):
    """Execute safe read-only SELECT query against the connected database."""
    connector = get_db_connector()
    result = connector.execute_query(req.query)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return {"status": "success", "data": result}


@app.post("/api/v1/database/sync-table", summary="Sync Database Table into Vector Index")
def sync_database_table(req: SyncTableRequest):
    """Convert relational table rows into contextual text chunks and index into ChromaDB."""
    connector = get_db_connector()
    loader = get_db_loader()
    engine = get_rag_engine()

    if not connector.is_connected:
        raise HTTPException(status_code=400, detail="Database connection is not active.")

    chunks, ids, metadatas = loader.load_table_as_chunks(
        table_name=req.table_name,
        text_columns=req.text_columns,
        title_column=req.title_column,
        id_column=req.id_column
    )

    if not chunks:
        return {
            "status": "warning",
            "message": f"Table '{req.table_name}' has no rows to index.",
            "chunk_count": 0
        }

    # Remove old table records and upsert new chunks
    engine.delete_document(f"db_{req.table_name}")
    engine.add_documents(chunks, ids, metadatas)

    logger.info(f"Successfully indexed {len(chunks)} rows from table '{req.table_name}'.")
    return {
        "status": "success",
        "message": f"Successfully indexed {len(chunks)} rows from table '{req.table_name}'.",
        "table_name": req.table_name,
        "chunk_count": len(chunks)
    }


if __name__ == "__main__":
    import uvicorn
    # Use reload=False to prevent reloading model weights on disk modifications
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
