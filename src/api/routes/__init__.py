from src.api.routes.documents import router as documents_router
from src.api.routes.query import router as query_router
from src.api.routes.database import router as database_router
from src.api.routes.auth import router as auth_router
from src.api.routes.admin import router as admin_router

__all__ = [
    "documents_router",
    "query_router",
    "database_router",
    "auth_router",
    "admin_router",
]
