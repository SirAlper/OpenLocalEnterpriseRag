from typing import Optional
from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import require_role
from src.auth.models import User
from src.core.audit import audit_logger
from src.core.logger import get_logger

logger = get_logger("API.Admin")
router = APIRouter(prefix="/api/v1/admin", tags=["Admin & Audit Trail"])


@router.get("/audit-logs", summary="List and Filter Compliance Audit Logs")
def get_audit_logs(
    username: Optional[str] = Query(None, description="Filter by user"),
    action: Optional[str] = Query(None, description="Filter by action (query, upload, delete, login, etc.)"),
    status: Optional[str] = Query(None, description="Filter by status (success, error, denied)"),
    start_date: Optional[str] = Query(None, description="Filter from ISO timestamp"),
    end_date: Optional[str] = Query(None, description="Filter to ISO timestamp"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_role("admin")),
):
    """
    Retrieve tamper-evident audit logs with multi-parameter filtering (Admin only).
    """
    total = audit_logger.count_logs(username=username, action=action, status=status)
    logs = audit_logger.query_logs(
        username=username,
        action=action,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return {
        "status": "success",
        "total": total,
        "count": len(logs),
        "limit": limit,
        "offset": offset,
        "logs": logs,
    }


@router.get("/audit-stats", summary="Audit Trail Metrics and Compliance Summary")
def get_audit_stats(_: User = Depends(require_role("admin"))):
    """
    Summary of enterprise actions, queries processed, and compliance indicators (Admin only).
    """
    total_logs = audit_logger.count_logs()
    total_queries = audit_logger.count_logs(action="query")
    total_uploads = audit_logger.count_logs(action="upload")
    total_deletions = audit_logger.count_logs(action="delete")
    total_logins = audit_logger.count_logs(action="login")
    total_errors = audit_logger.count_logs(status="error")

    return {
        "status": "success",
        "total_records": total_logs,
        "queries_executed": total_queries,
        "documents_uploaded": total_uploads,
        "documents_deleted": total_deletions,
        "login_events": total_logins,
        "error_events": total_errors,
    }
