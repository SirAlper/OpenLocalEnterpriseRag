from src.api.routes.documents import router as documents_router
from src.api.routes.query import router as query_router
from src.api.routes.database import router as database_router

__all__ = ["documents_router", "query_router", "database_router"]
