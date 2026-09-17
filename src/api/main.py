from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import CORS_ORIGINS
from src.core.logger import get_logger
from src.api.state import (
    init_services,
    get_rag_engine,
    get_agent,
    get_document_loader,
    get_db_connector,
    get_db_loader,
    auto_index_on_startup,
    query_lock,
)
from src.api.routes import documents_router, query_router, database_router

logger = get_logger("API")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan context manager to initialize models and connections on startup."""
    init_services()
    yield
    logger.info("Enterprise RAG services shutdown.")


app = FastAPI(
    title="OpenLocalRagAgents API",
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

# Include modular API routers
app.include_router(documents_router)
app.include_router(query_router)
app.include_router(database_router)

__all__ = [
    "app",
    "get_rag_engine",
    "get_agent",
    "get_document_loader",
    "get_db_connector",
    "get_db_loader",
    "auto_index_on_startup",
    "query_lock",
]

if __name__ == "__main__":
    import uvicorn
    # Use reload=False to prevent reloading model weights on disk modifications
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)

