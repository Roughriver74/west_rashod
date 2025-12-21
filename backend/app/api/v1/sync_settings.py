"""API endpoints for sync settings management."""
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, UserRoleEnum, SyncSettings
from app.utils.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync-settings", tags=["Sync Settings"])


class SyncSettingsUpdate(BaseModel):
    """Schema for updating sync settings."""
    auto_sync_enabled: Optional[bool] = None
    sync_interval_hours: Optional[int] = Field(None, ge=1, le=24)
    sync_time_hour: Optional[int] = Field(None, ge=0, le=23)
    sync_time_minute: Optional[int] = Field(None, ge=0, le=59)
    auto_classify: Optional[bool] = None
    sync_days_back: Optional[int] = Field(None, ge=1, le=365)


class SyncSettingsResponse(BaseModel):
    """Schema for sync settings response."""
    id: int
    auto_sync_enabled: bool
    sync_interval_hours: int
    sync_time_hour: Optional[int]
    sync_time_minute: int
    auto_classify: bool
    sync_days_back: int
    last_sync_started_at: Optional[datetime]
    last_sync_completed_at: Optional[datetime]
    last_sync_status: Optional[str]
    last_sync_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=SyncSettingsResponse)
def get_sync_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current sync settings."""
    # Only admins and managers can view sync settings
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can view sync settings"
        )

    settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()

    if not settings:
        # Create default settings
        settings = SyncSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


@router.put("", response_model=SyncSettingsResponse)
def update_sync_settings(
    settings_update: SyncSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update sync settings."""
    # Only admins can update sync settings
    if current_user.role != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update sync settings"
        )

    settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()

    if not settings:
        settings = SyncSettings(id=1)
        db.add(settings)

    # Update fields
    update_data = settings_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    settings.updated_by = current_user.id
    settings.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(settings)

    logger.info(f"Sync settings updated by {current_user.username}: {update_data}")

    return settings


@router.post("/trigger-now")
def trigger_sync_now(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Manually trigger sync task immediately."""
    # Only admins and managers can trigger sync
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can trigger sync"
        )

    try:
        from app.celery_app import sync_1c_transactions_task

        # Trigger async task
        task = sync_1c_transactions_task.delay()

        logger.info(f"Manual sync triggered by {current_user.username}, task_id: {task.id}")

        return {
            "success": True,
            "message": "Sync task started",
            "task_id": task.id
        }

    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger sync: {str(e)}"
        )


@router.get("/task-status/{task_id}")
def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get status of a sync task."""
    # Only admins and managers can check task status
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can check task status"
        )

    try:
        from app.celery_app import celery_app
        from celery.result import AsyncResult

        result = AsyncResult(task_id, app=celery_app)

        return {
            "task_id": task_id,
            "status": result.state,
            "result": result.result if result.ready() else None,
            "traceback": result.traceback if result.failed() else None
        }

    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )
