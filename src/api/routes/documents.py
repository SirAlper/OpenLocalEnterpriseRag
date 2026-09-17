import os
import time
from fastapi import APIRouter, HTTPException, UploadFile, File
from src.api.state import get_rag_engine, get_db_connector, get_document_loader
from src.core.config import (
    DOCS_PATH,
    EMBEDDING_MODEL_NAME,
    LLM_MODEL_NAME,
    MAX_UPLOAD_SIZE_MB,
    ALLOWED_UPLOAD_EXTENSIONS,
)
from src.core.logger import get_logger

logger = get_logger("API.Documents")
router = APIRouter(tags=["Documents & System"])


@router.get("/api/v1/stats", summary="System and Vector Store Statistics")
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


@router.get("/api/v1/documents", summary="List Indexed Documents")
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


@router.delete("/api/v1/documents/{filename}", summary="Delete Document and Vector Chunks")
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


@router.post("/api/v1/upload-file", summary="Upload and Index Document")
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
