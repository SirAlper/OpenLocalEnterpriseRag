import os
import shutil
import time
import json
import torch
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
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
)

app = FastAPI(
    title="Enterprise Local RAG API",
    description="Privacy-first, on-premise RAG and Agentic AI gateway with zero cloud dependencies.",
    version="1.1.0"
)

# CORS configuration (enables direct access from frontend / Streamlit apps)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core services
rag_engine = RAGEngine()
agent = EnterpriseRAGAgent(rag_engine)
document_loader = DocumentLoader(DOCS_PATH)

# Initialize database connector (prepare sample_enterprise.db if no URL configured)
if not DATABASE_URL and not os.path.exists(SAMPLE_DB_PATH):
    try:
        create_sample_sqlite_db(SAMPLE_DB_PATH)
    except Exception as e:
        print(f"[Sample DB] Could not create sample database: {e}")

db_connector = DatabaseConnector()
db_loader = DatabaseTableLoader(db_connector)


def auto_index_on_startup():
    """Scan data/ folder on server startup and automatically index any unindexed documents into ChromaDB."""
    if not os.path.exists(DOCS_PATH):
        os.makedirs(DOCS_PATH)
        return

    db_stats = rag_engine.get_stats()
    indexed_files = set(db_stats.get("document_chunks", {}).keys())

    supported_exts = {".pdf", ".docx", ".txt"}
    data_files = [
        f for f in os.listdir(DOCS_PATH)
        if os.path.isfile(os.path.join(DOCS_PATH, f)) and os.path.splitext(f)[1].lower() in supported_exts
    ]

    unindexed = [f for f in data_files if f not in indexed_files]

    if not unindexed:
        print(f"[Auto-Indexing] No unindexed documents found in data/. ({len(indexed_files)} files already indexed)")
        return

    print(f"[Auto-Indexing] Detected {len(unindexed)} new document(s), indexing...")
    for filename in unindexed:
        file_path = os.path.join(DOCS_PATH, filename)
        chunks, ids, metadatas = document_loader.load_and_chunk_file(file_path)
        if chunks:
            rag_engine.add_documents(chunks, ids, metadatas)
            print(f"  ✓ '{filename}' -> {len(chunks)} chunks indexed.")
        else:
            print(f"  ✗ '{filename}' -> no parseable text found.")

    print("[Auto-Indexing] Completed successfully!")


# Run auto-indexing on server startup
auto_index_on_startup()


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
    db_stats = rag_engine.get_stats()
    device = "CUDA (NVIDIA GPU)" if torch.cuda.is_available() else "CPU"
    db_conn_info = db_connector.test_connection()

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
        os.makedirs(DOCS_PATH)

    db_stats = rag_engine.get_stats()
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
    file_path = os.path.join(DOCS_PATH, filename)
    file_deleted = False

    if os.path.exists(file_path):
        os.remove(file_path)
        file_deleted = True

    deleted_chunks = rag_engine.delete_document(filename)

    if not file_deleted and deleted_chunks == 0:
        raise HTTPException(status_code=404, detail=f"'{filename}' was not found.")

    return {
        "status": "success",
        "message": f"'{filename}' was deleted successfully.",
        "deleted_chunks": deleted_chunks,
        "file_deleted": file_deleted
    }


@app.post("/api/v1/upload-file", summary="Upload and Index Document")
async def upload_file(file: UploadFile = File(...)):
    """Upload a new PDF, DOCX, or TXT document, chunk it, and index it into ChromaDB."""
    if not os.path.exists(DOCS_PATH):
        os.makedirs(DOCS_PATH)

    # 1. Save uploaded file to data/ directory
    file_path = os.path.join(DOCS_PATH, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Chunk uploaded file (Incremental Indexing)
    chunks, ids, metadatas = document_loader.load_and_chunk_file(file_path)

    if not chunks:
        return {
            "status": "warning",
            "message": f"'{file.filename}' uploaded, but no parseable text was extracted.",
            "chunk_count": 0
        }

    # 3. Upsert to vector database (clean older chunks if file previously existed)
    rag_engine.delete_document(file.filename)
    rag_engine.add_documents(chunks, ids, metadatas)

    return {
        "status": "success",
        "message": f"'{file.filename}' successfully uploaded and indexed.",
        "filename": file.filename,
        "chunk_count": len(chunks)
    }


@app.post("/api/v1/query", summary="Query Enterprise AI Assistant")
def query_rag(request: QueryRequest):
    """Execute LangGraph workflow and return verified answer, reference sources, and audit status."""
    try:
        print(f"[API /query] Received user question: {request.question}")
        result = agent.query(request.question)
        return {
            "status": "success",
            "answer": result["answer"],
            "sources": result["sources"],
            "hallucination_grade": result.get("hallucination_grade", ""),
            "is_refined": result.get("is_refined", False)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/query-stream", summary="Query Enterprise AI Assistant (Event Stream)")
def query_rag_stream(request: QueryRequest):
    """Stream LangGraph stage events and deliver final answer via NDJSON format."""
    try:
        print(f"[API /query-stream] Received streaming question: {request.question}")

        def event_generator():
            for event in agent.stream_events(request.question):
                yield json.dumps(event, ensure_ascii=False) + "\n"

        return StreamingResponse(event_generator(), media_type="application/x-ndjson")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/database/status", summary="Database Connection Status and Schema")
def get_database_status():
    """Return database connection status, dialect type, and accessible tables."""
    conn_info = db_connector.test_connection()
    schema_summary = db_connector.get_schema_summary() if db_connector.is_connected else ""
    return {
        "status": "success",
        "connection": conn_info,
        "schema_summary": schema_summary
    }


@app.post("/api/v1/database/test-query", summary="Execute Safe Read-Only SQL Query")
def run_database_query(req: TestQueryRequest):
    """Execute safe read-only SELECT query against the connected database."""
    result = db_connector.execute_query(req.query)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return {"status": "success", "data": result}


@app.post("/api/v1/database/sync-table", summary="Sync Database Table into Vector Index")
def sync_database_table(req: SyncTableRequest):
    """Convert relational table rows into contextual text chunks and index into ChromaDB."""
    if not db_connector.is_connected:
        raise HTTPException(status_code=400, detail="Database connection is not active.")

    chunks, ids, metadatas = db_loader.load_table_as_chunks(
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
    rag_engine.delete_document(f"db_{req.table_name}")
    rag_engine.add_documents(chunks, ids, metadatas)

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
