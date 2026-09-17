import time
from fastapi import APIRouter, Depends, HTTPException, Request
from src.api.schemas import SyncTableRequest, TestQueryRequest
from src.api.state import get_db_connector, get_db_loader, get_rag_engine
from src.auth.dependencies import require_role
from src.auth.models import User
from src.core.audit import audit_logger
from src.core.logger import get_logger

logger = get_logger("API.Database")
router = APIRouter(prefix="/api/v1/database", tags=["Database"])


@router.get("/status", summary="Database Connection Status and Schema")
def get_database_status(_: User = Depends(require_role("admin", "editor", "viewer"))):
    """Return database connection status, dialect type, and accessible tables."""
    connector = get_db_connector()
    conn_info = connector.test_connection()
    schema_summary = connector.get_schema_summary() if connector.is_connected else ""
    return {
        "status": "success",
        "connection": conn_info,
        "schema_summary": schema_summary
    }


@router.post("/test-query", summary="Execute Safe Read-Only SQL Query")
def run_database_query(
    req: TestQueryRequest,
    http_req: Request,
    current_admin: User = Depends(require_role("admin")),
):
    """Execute safe read-only SELECT query against the connected database."""
    start_time = time.time()
    ip_addr = http_req.client.host if http_req.client else None
    connector = get_db_connector()
    result = connector.execute_query(req.query)
    duration_ms = int((time.time() - start_time) * 1000)

    if result.get("status") == "error":
        audit_logger.log(
            username=current_admin.username,
            role=current_admin.role,
            action="db_query",
            detail=f"Rejected query: {req.query}",
            ip_address=ip_addr,
            duration_ms=duration_ms,
            status="error",
        )
        raise HTTPException(status_code=400, detail=result.get("message"))

    audit_logger.log(
        username=current_admin.username,
        role=current_admin.role,
        action="db_query",
        detail=f"Executed query: {req.query}",
        answer_preview=f"Returned {result.get('row_count', 0)} rows",
        ip_address=ip_addr,
        duration_ms=duration_ms,
        status="success",
    )
    return {"status": "success", "data": result}


@router.post("/sync-table", summary="Sync Database Table into Vector Index")
def sync_database_table(
    req: SyncTableRequest,
    http_req: Request,
    current_admin: User = Depends(require_role("admin")),
):
    """Convert relational table rows into contextual text chunks and index into ChromaDB."""
    start_time = time.time()
    ip_addr = http_req.client.host if http_req.client else None
    connector = get_db_connector()
    loader = get_db_loader()
    engine = get_rag_engine()

    if not connector.is_connected:
        audit_logger.log(
            username=current_admin.username,
            role=current_admin.role,
            action="db_sync_table",
            detail=f"Failed sync table '{req.table_name}' (DB disconnected)",
            ip_address=ip_addr,
            status="error",
        )
        raise HTTPException(status_code=400, detail="Database connection is not active.")

    chunks, ids, metadatas = loader.load_table_as_chunks(
        table_name=req.table_name,
        text_columns=req.text_columns,
        title_column=req.title_column,
        id_column=req.id_column
    )

    duration_ms = int((time.time() - start_time) * 1000)

    if not chunks:
        audit_logger.log(
            username=current_admin.username,
            role=current_admin.role,
            action="db_sync_table",
            detail=f"Table '{req.table_name}' had 0 rows to index",
            ip_address=ip_addr,
            duration_ms=duration_ms,
            status="warning",
        )
        return {
            "status": "warning",
            "message": f"Table '{req.table_name}' has no rows to index.",
            "chunk_count": 0
        }

    # Remove old table records and upsert new chunks
    engine.delete_document(f"db_{req.table_name}")
    engine.add_documents(chunks, ids, metadatas)

    audit_logger.log(
        username=current_admin.username,
        role=current_admin.role,
        action="db_sync_table",
        detail=f"Synced table '{req.table_name}' ({len(chunks)} chunks)",
        ip_address=ip_addr,
        duration_ms=duration_ms,
        status="success",
    )

    logger.info(f"Successfully indexed {len(chunks)} rows from table '{req.table_name}'.")
    return {
        "status": "success",
        "message": f"Successfully indexed {len(chunks)} rows from table '{req.table_name}'.",
        "table_name": req.table_name,
        "chunk_count": len(chunks)
    }
