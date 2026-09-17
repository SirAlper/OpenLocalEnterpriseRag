from fastapi import APIRouter, HTTPException
from src.api.schemas import SyncTableRequest, TestQueryRequest
from src.api.state import get_db_connector, get_db_loader, get_rag_engine
from src.core.logger import get_logger

logger = get_logger("API.Database")
router = APIRouter(prefix="/api/v1/database", tags=["Database"])


@router.get("/status", summary="Database Connection Status and Schema")
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


@router.post("/test-query", summary="Execute Safe Read-Only SQL Query")
def run_database_query(req: TestQueryRequest):
    """Execute safe read-only SELECT query against the connected database."""
    connector = get_db_connector()
    result = connector.execute_query(req.query)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return {"status": "success", "data": result}


@router.post("/sync-table", summary="Sync Database Table into Vector Index")
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
