"""Background task status API endpoints."""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.db.models import User, UserRoleEnum
from app.utils.auth import get_current_active_user
from app.services.background_tasks import task_manager, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Background Tasks"])


class TaskStatusResponse(BaseModel):
    """Task status response model."""
    task_id: str
    task_type: str
    status: str
    progress: int
    total: int
    processed: int
    message: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: dict = {}


class TaskListResponse(BaseModel):
    """Task list response model."""
    tasks: List[TaskStatusResponse]
    total: int


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get status of a background task."""
    task = task_manager.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    return TaskStatusResponse(**task.to_dict())


@router.get("", response_model=TaskListResponse)
def list_tasks(
    task_type: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user)
):
    """List all background tasks from database."""
    tasks = task_manager.get_all_tasks(task_type=task_type, limit=limit)

    return TaskListResponse(
        tasks=[TaskStatusResponse(**t.to_dict()) for t in tasks],
        total=len(tasks)
    )


@router.post("/{task_id}/cancel")
def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a running task."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can cancel tasks"
        )

    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task with status {task.status.value}"
        )

    success = task_manager.cancel_task(task_id)
    if success:
        return {"message": "Task cancelled", "task_id": task_id}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel task"
        )


@router.post("/cleanup")
def cleanup_old_tasks(
    max_age_hours: int = 24,
    current_user: User = Depends(get_current_active_user)
):
    """Remove old completed/failed tasks."""
    if current_user.role != UserRoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can cleanup tasks"
        )

    removed = task_manager.cleanup_old_tasks(max_age_hours=max_age_hours)
    return {"message": f"Removed {removed} old tasks", "removed_count": removed}
