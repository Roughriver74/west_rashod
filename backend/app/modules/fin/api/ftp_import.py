"""
API endpoints for FTP Import operations.
Uses AsyncIO-based background tasks instead of Celery.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.utils.auth import get_current_active_user
from app.db.models import User
from app.services.background_tasks import task_manager
from app.modules.fin.services.async_ftp_sync import AsyncFTPSyncService
from app.modules.fin.models import FinImportLog

logger = logging.getLogger(__name__)

router = APIRouter()


class FTPImportRequest(BaseModel):
    """Request model for FTP import."""
    clear_existing: bool = True


class FTPImportResponse(BaseModel):
    """Response model for FTP import task."""
    task_id: str
    status: str
    message: str


@router.post("/ftp", response_model=FTPImportResponse)
async def trigger_ftp_import(
    request: FTPImportRequest = FTPImportRequest(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Trigger FTP import task.

    Downloads files from FTP server and imports them into the database.
    Uses AsyncIO background tasks for non-blocking operation.
    """
    try:
        task_id = AsyncFTPSyncService.start_ftp_import(
            clear_existing=request.clear_existing,
            user_id=current_user.id
        )

        logger.info(f"FTP import task started: {task_id} by user {current_user.username}")

        return FTPImportResponse(
            task_id=task_id,
            status="started",
            message="FTP import task started successfully"
        )

    except Exception as e:
        logger.error(f"Error starting FTP import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start FTP import: {str(e)}")


@router.get("/ftp/status/{task_id}")
def get_import_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get status of FTP import task."""
    task = task_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task.to_dict()


@router.post("/ftp/cancel/{task_id}")
def cancel_import(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a running FTP import task."""
    success = task_manager.cancel_task(task_id)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel task (not found or already completed)")

    return {"task_id": task_id, "status": "cancelled", "message": "Task cancelled successfully"}


@router.get("/logs")
def get_import_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get FTP import logs."""
    query = db.query(FinImportLog)

    if status:
        query = query.filter(FinImportLog.status == status)

    total = query.count()
    logs = query.order_by(FinImportLog.import_date.desc()).offset(skip).limit(limit).all()

    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "import_date": log.import_date,
            "source_file": log.source_file,
            "table_name": log.table_name,
            "rows_inserted": log.rows_inserted,
            "rows_updated": log.rows_updated,
            "rows_failed": log.rows_failed,
            "status": log.status,
            "error_message": log.error_message,
            "processed_by": log.processed_by,
            "processing_time_seconds": float(log.processing_time_seconds) if log.processing_time_seconds else 0
        })

    return {"total": total, "items": items}


@router.delete("/logs/clear")
def clear_import_logs(
    older_than_days: int = Query(30, ge=1, le=365, description="Delete logs older than N days"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Clear old import logs."""
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    deleted = db.query(FinImportLog).filter(FinImportLog.import_date < cutoff).delete()
    db.commit()

    return {
        "message": f"Deleted {deleted} import logs older than {older_than_days} days"
    }
