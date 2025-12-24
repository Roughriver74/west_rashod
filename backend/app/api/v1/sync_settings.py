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
    # Role check removed - all authenticated users can view sync settings

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
    # Role check removed - all authenticated users can update sync settings

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
async def trigger_sync_now(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Manually trigger sync task immediately."""
    import asyncio
    from datetime import date, timedelta
    from app.services.async_sync_service import AsyncSyncService
    from app.services.sync_scheduler import sync_scheduler

    try:
        # Get sync settings
        settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()
        if not settings:
            settings = SyncSettings(id=1)
            db.add(settings)
            db.commit()
            db.refresh(settings)

        # Calculate date range based on settings
        date_to = date.today()
        date_from = date_to - timedelta(days=settings.sync_days_back)

        # Start async sync task
        task_id = AsyncSyncService.start_full_sync(
            date_from=date_from,
            date_to=date_to,
            auto_classify=settings.auto_classify,
            user_id=current_user.id
        )

        # Update sync settings
        settings.last_sync_started_at = datetime.utcnow()
        settings.last_sync_status = "IN_PROGRESS"
        settings.last_sync_message = "Синхронизация запущена вручную"
        db.commit()

        # Start monitoring task completion in background
        asyncio.create_task(sync_scheduler._monitor_task_completion(task_id))

        logger.info(f"Manual sync triggered by {current_user.username}, task_id: {task_id}")

        return {
            "success": True,
            "message": "Синхронизация запущена",
            "task_id": task_id
        }

    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось запустить синхронизацию: {str(e)}"
        )


@router.post("/refresh-status")
def refresh_sync_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Refresh sync status based on latest completed task."""
    from app.db.models import BackgroundTask, BackgroundTaskStatusEnum
    import json

    try:
        # Get sync settings
        settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()

        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Настройки синхронизации не найдены"
            )

        if settings.last_sync_status != "IN_PROGRESS":
            return {
                "success": True,
                "message": "Статус уже актуален",
                "status": settings.last_sync_status
            }

        # Find latest completed full sync task
        latest_task = db.query(BackgroundTask).filter(
            BackgroundTask.task_type == "sync_full",
            BackgroundTask.status.in_([
                BackgroundTaskStatusEnum.COMPLETED,
                BackgroundTaskStatusEnum.FAILED,
                BackgroundTaskStatusEnum.CANCELLED
            ])
        ).order_by(BackgroundTask.created_at.desc()).first()

        if not latest_task:
            return {
                "success": False,
                "message": "Не найдено завершенных задач синхронизации"
            }

        # Update settings
        settings.last_sync_completed_at = latest_task.completed_at or datetime.utcnow()

        if latest_task.status == BackgroundTaskStatusEnum.COMPLETED:
            settings.last_sync_status = "SUCCESS"

            # Parse result
            if latest_task.result:
                try:
                    result = json.loads(latest_task.result)
                    tx = result.get('transactions', {})
                    settings.last_sync_message = (
                        f"Создано: {tx.get('total_created', 0)}, "
                        f"Обновлено: {tx.get('total_updated', 0)}, "
                        f"Пропущено: {tx.get('total_skipped', 0)}"
                    )
                except:
                    settings.last_sync_message = latest_task.message or "Синхронизация завершена"
            else:
                settings.last_sync_message = latest_task.message or "Синхронизация завершена"

        elif latest_task.status == BackgroundTaskStatusEnum.FAILED:
            settings.last_sync_status = "FAILED"
            settings.last_sync_message = f"Ошибка: {latest_task.error or 'Неизвестная ошибка'}"
        else:
            settings.last_sync_status = "FAILED"
            settings.last_sync_message = "Синхронизация отменена"

        db.commit()

        logger.info(f"Sync status refreshed by {current_user.username}: {settings.last_sync_status}")

        return {
            "success": True,
            "message": "Статус обновлен",
            "status": settings.last_sync_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh sync status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось обновить статус: {str(e)}"
        )


@router.get("/task-status/{task_id}")
def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get status of a sync task."""
    from app.services.background_tasks import task_manager, TaskStatus

    try:
        task = task_manager.get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Задача с ID {task_id} не найдена"
            )

        # Update SyncSettings if task is completed and settings are not updated
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()
            if settings and settings.last_sync_status == "IN_PROGRESS":
                settings.last_sync_completed_at = datetime.utcnow()

                if task.status == TaskStatus.COMPLETED:
                    settings.last_sync_status = "SUCCESS"
                    if task.result and isinstance(task.result, dict):
                        tx = task.result.get('transactions', {})
                        settings.last_sync_message = (
                            f"Создано: {tx.get('total_created', 0)}, "
                            f"Обновлено: {tx.get('total_updated', 0)}, "
                            f"Пропущено: {tx.get('total_skipped', 0)}"
                        )
                    else:
                        settings.last_sync_message = task.message or "Синхронизация завершена"
                elif task.status == TaskStatus.FAILED:
                    settings.last_sync_status = "FAILED"
                    settings.last_sync_message = f"Ошибка: {task.error or 'Неизвестная ошибка'}"
                else:
                    settings.last_sync_status = "FAILED"
                    settings.last_sync_message = "Синхронизация отменена"

                db.commit()
                logger.info(f"Updated SyncSettings from task-status endpoint for task {task_id}")

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": task.progress,
            "processed": task.processed,
            "total": task.total,
            "message": task.message,
            "result": task.result,
            "error": task.error,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось получить статус задачи: {str(e)}"
        )
