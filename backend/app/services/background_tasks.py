"""Background task manager for async operations."""
import asyncio
import uuid
import logging
from typing import Dict, Optional, Any, Callable, Awaitable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Information about a background task."""
    task_id: str
    task_type: str
    status: TaskStatus
    progress: int = 0
    total: int = 0
    processed: int = 0
    message: str = ""
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "progress": self.progress,
            "total": self.total,
            "processed": self.processed,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class BackgroundTaskManager:
    """Manager for background tasks with progress tracking."""

    _instance: Optional["BackgroundTaskManager"] = None
    _tasks: Dict[str, TaskInfo] = {}
    _running_tasks: Dict[str, asyncio.Task] = {}
    _subscribers: Dict[str, list] = {}  # task_id -> list of callbacks

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tasks = {}
            cls._running_tasks = {}
            cls._subscribers = {}
        return cls._instance

    def create_task(
        self,
        task_type: str,
        total: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new task and return its ID."""
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            total=total,
            metadata=metadata or {},
        )
        logger.info(f"Created task {task_id} of type {task_type}")
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task info by ID."""
        return self._tasks.get(task_id)

    def get_all_tasks(self, task_type: Optional[str] = None) -> list[TaskInfo]:
        """Get all tasks, optionally filtered by type."""
        tasks = list(self._tasks.values())
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def update_progress(
        self,
        task_id: str,
        processed: int,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update task progress."""
        task = self._tasks.get(task_id)
        if task:
            task.processed = processed
            task.progress = int((processed / task.total) * 100) if task.total > 0 else 0
            task.message = message
            if metadata:
                task.metadata.update(metadata)
            self._notify_subscribers(task_id, task)

    def start_task(self, task_id: str) -> None:
        """Mark task as running."""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            logger.info(f"Task {task_id} started")
            self._notify_subscribers(task_id, task)

    def complete_task(self, task_id: str, result: Any = None) -> None:
        """Mark task as completed."""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100
            task.result = result
            logger.info(f"Task {task_id} completed")
            self._notify_subscribers(task_id, task)

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = error
            logger.error(f"Task {task_id} failed: {error}")
            self._notify_subscribers(task_id, task)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                task.message = "Task cancelled by user"
                self._notify_subscribers(task_id, task)
            logger.info(f"Task {task_id} cancelled")
            return True
        return False

    def run_async_task(
        self,
        task_id: str,
        coro: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> None:
        """Run an async task in the background."""
        async def wrapper():
            try:
                self.start_task(task_id)
                result = await coro(task_id, *args, **kwargs)
                self.complete_task(task_id, result)
            except asyncio.CancelledError:
                logger.info(f"Task {task_id} was cancelled")
            except Exception as e:
                logger.exception(f"Task {task_id} failed with error")
                self.fail_task(task_id, str(e))
            finally:
                self._running_tasks.pop(task_id, None)

        task = asyncio.create_task(wrapper())
        self._running_tasks[task_id] = task

    def subscribe(self, task_id: str, callback: Callable[[TaskInfo], None]) -> None:
        """Subscribe to task updates."""
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(callback)

    def unsubscribe(self, task_id: str, callback: Callable[[TaskInfo], None]) -> None:
        """Unsubscribe from task updates."""
        if task_id in self._subscribers:
            self._subscribers[task_id] = [
                cb for cb in self._subscribers[task_id] if cb != callback
            ]

    def _notify_subscribers(self, task_id: str, task: TaskInfo) -> None:
        """Notify all subscribers of a task update."""
        import asyncio
        import inspect

        for callback in self._subscribers.get(task_id, []):
            try:
                # Handle both sync and async callbacks
                if inspect.iscoroutinefunction(callback):
                    # For async callbacks, try to create task if event loop exists
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(callback(task))
                        else:
                            # If no loop running, skip async callback
                            logger.warning(f"Skipping async callback - no running event loop")
                    except RuntimeError:
                        # No event loop
                        logger.warning(f"Skipping async callback - no event loop")
                else:
                    # Sync callback
                    callback(task)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Remove old completed/failed tasks."""
        from datetime import timedelta
        now = datetime.now()
        cutoff = now - timedelta(hours=max_age_hours)

        to_remove = [
            task_id for task_id, task in self._tasks.items()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
            and task.completed_at and task.completed_at < cutoff
        ]

        for task_id in to_remove:
            del self._tasks[task_id]
            self._subscribers.pop(task_id, None)

        return len(to_remove)


# Global task manager instance
task_manager = BackgroundTaskManager()
