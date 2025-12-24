"""Background task manager for async operations with database persistence."""
import asyncio
import json
import uuid
import logging
from typing import Dict, Optional, Any, Callable, Awaitable, List
from datetime import datetime, timedelta, timezone
from enum import Enum
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

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
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        def format_datetime(dt: Optional[datetime]) -> Optional[str]:
            """Format datetime to ISO string with timezone info."""
            if not dt:
                return None
            # Ensure datetime is timezone-aware (UTC)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

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
            "created_at": format_datetime(self.created_at),
            "started_at": format_datetime(self.started_at),
            "completed_at": format_datetime(self.completed_at),
            "metadata": self.metadata,
        }

    @classmethod
    def from_db_model(cls, db_task) -> "TaskInfo":
        """Create TaskInfo from database model."""
        from app.db.models import BackgroundTaskStatusEnum

        # Parse JSON fields
        result = None
        if db_task.result:
            try:
                result = json.loads(db_task.result)
            except (json.JSONDecodeError, TypeError):
                result = db_task.result

        metadata = {}
        if db_task.extra_data:
            try:
                metadata = json.loads(db_task.extra_data)
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        return cls(
            task_id=db_task.task_id,
            task_type=db_task.task_type,
            status=TaskStatus(db_task.status.value),
            progress=db_task.progress or 0,
            total=db_task.total or 0,
            processed=db_task.processed or 0,
            message=db_task.message or "",
            result=result,
            error=db_task.error,
            created_at=db_task.created_at,
            started_at=db_task.started_at,
            completed_at=db_task.completed_at,
            metadata=metadata,
        )


class BackgroundTaskManager:
    """Manager for background tasks with database persistence and progress tracking."""

    _instance: Optional["BackgroundTaskManager"] = None
    _cache: Dict[str, TaskInfo] = {}  # In-memory cache for active tasks
    _running_tasks: Dict[str, asyncio.Task] = {}
    _subscribers: Dict[str, list] = {}  # task_id -> list of callbacks
    _last_db_update: Dict[str, datetime] = {}  # Track last DB update per task
    _db_update_interval: float = 1.0  # Minimum seconds between DB updates
    _executor: Optional["concurrent.futures.ThreadPoolExecutor"] = None
    _max_workers: int = 3  # Maximum concurrent sync tasks

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._cache = {}
            cls._running_tasks = {}
            cls._subscribers = {}
            cls._last_db_update = {}
            cls._executor = None
        return cls._instance

    def _get_executor(self):
        """Get or create thread pool executor."""
        import concurrent.futures
        if self._executor is None:
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="sync_task_"
            )
        return self._executor

    def _get_db_session(self) -> Session:
        """Get a new database session."""
        from app.db.session import SessionLocal
        return SessionLocal()

    def _save_to_db(self, task: TaskInfo, db: Optional[Session] = None) -> None:
        """Save task to database."""
        from app.db.models import BackgroundTask, BackgroundTaskStatusEnum

        close_session = False
        if db is None:
            db = self._get_db_session()
            close_session = True

        try:
            db_task = db.query(BackgroundTask).filter(
                BackgroundTask.task_id == task.task_id
            ).first()

            if db_task is None:
                db_task = BackgroundTask(
                    task_id=task.task_id,
                    task_type=task.task_type,
                )
                db.add(db_task)

            # Update fields
            db_task.status = BackgroundTaskStatusEnum(task.status.value)
            db_task.progress = task.progress
            db_task.total = task.total
            db_task.processed = task.processed
            db_task.message = task.message or ""
            db_task.error = task.error
            db_task.started_at = task.started_at
            db_task.completed_at = task.completed_at

            # Serialize JSON fields
            if task.result is not None:
                db_task.result = json.dumps(task.result, ensure_ascii=False, default=str)
            if task.metadata:
                db_task.extra_data = json.dumps(task.metadata, ensure_ascii=False, default=str)

            db.commit()
            self._last_db_update[task.task_id] = datetime.now()

        except Exception as e:
            logger.error(f"Error saving task {task.task_id} to DB: {e}")
            db.rollback()
        finally:
            if close_session:
                db.close()

    def _should_update_db(self, task_id: str) -> bool:
        """Check if enough time has passed since last DB update."""
        last_update = self._last_db_update.get(task_id)
        if last_update is None:
            return True
        return (datetime.now() - last_update).total_seconds() >= self._db_update_interval

    def _load_from_db(self, task_id: str) -> Optional[TaskInfo]:
        """Load task from database."""
        from app.db.models import BackgroundTask

        db = self._get_db_session()
        try:
            db_task = db.query(BackgroundTask).filter(
                BackgroundTask.task_id == task_id
            ).first()

            if db_task:
                return TaskInfo.from_db_model(db_task)
            return None
        finally:
            db.close()

    def create_task(
        self,
        task_type: str,
        total: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> str:
        """Create a new task and return its ID."""
        from app.db.models import BackgroundTask, BackgroundTaskStatusEnum

        task_id = str(uuid.uuid4())

        # Create in database first
        db = self._get_db_session()
        try:
            db_task = BackgroundTask(
                task_id=task_id,
                task_type=task_type,
                status=BackgroundTaskStatusEnum.PENDING,
                total=total,
                user_id=user_id,
                extra_data=json.dumps(metadata or {}, ensure_ascii=False, default=str),
            )
            db.add(db_task)
            db.commit()

            # Also cache in memory
            task_info = TaskInfo(
                task_id=task_id,
                task_type=task_type,
                status=TaskStatus.PENDING,
                total=total,
                metadata=metadata or {},
            )
            self._cache[task_id] = task_info
            self._last_db_update[task_id] = datetime.now()

            logger.info(f"Created task {task_id} of type {task_type}")
            return task_id

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating task: {e}")
            raise
        finally:
            db.close()

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task info by ID."""
        # Check cache first
        if task_id in self._cache:
            return self._cache[task_id]

        # Load from database
        task = self._load_from_db(task_id)
        if task:
            # Cache if task is active
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                self._cache[task_id] = task
        return task

    def get_all_tasks(self, task_type: Optional[str] = None, limit: int = 50) -> List[TaskInfo]:
        """Get all tasks from database, optionally filtered by type."""
        from app.db.models import BackgroundTask

        db = self._get_db_session()
        try:
            query = db.query(BackgroundTask).order_by(BackgroundTask.created_at.desc())

            if task_type:
                query = query.filter(BackgroundTask.task_type == task_type)

            query = query.limit(limit)

            return [TaskInfo.from_db_model(t) for t in query.all()]
        finally:
            db.close()

    def update_progress(
        self,
        task_id: str,
        processed: int,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update task progress."""
        task = self._cache.get(task_id)
        if not task:
            task = self._load_from_db(task_id)
            if task:
                self._cache[task_id] = task

        if task:
            task.processed = processed
            task.progress = int((processed / task.total) * 100) if task.total > 0 else 0
            task.message = message
            if metadata:
                task.metadata.update(metadata)

            # Update cache
            self._cache[task_id] = task

            # Save to DB periodically (not every update for performance)
            if self._should_update_db(task_id):
                self._save_to_db(task)

            self._notify_subscribers(task_id, task)

    def start_task(self, task_id: str) -> None:
        """Mark task as running."""
        task = self._cache.get(task_id) or self._load_from_db(task_id)
        if task:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            self._cache[task_id] = task
            self._save_to_db(task)  # Always save status changes
            logger.info(f"Task {task_id} started")
            self._notify_subscribers(task_id, task)

    def complete_task(self, task_id: str, result: Any = None) -> None:
        """Mark task as completed."""
        task = self._cache.get(task_id) or self._load_from_db(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.progress = 100
            task.result = result
            self._cache[task_id] = task
            self._save_to_db(task)  # Always save final state
            logger.info(f"Task {task_id} completed")
            self._notify_subscribers(task_id, task)

            # Remove from cache after completion (will be loaded from DB if needed)
            self._cache.pop(task_id, None)

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        task = self._cache.get(task_id) or self._load_from_db(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now(timezone.utc)
            task.error = error
            self._cache[task_id] = task
            self._save_to_db(task)  # Always save final state
            logger.error(f"Task {task_id} failed: {error}")
            self._notify_subscribers(task_id, task)

            # Remove from cache after failure
            self._cache.pop(task_id, None)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        # Загружаем задачу из кэша или БД
        task = self._cache.get(task_id) or self._load_from_db(task_id)

        if not task:
            logger.warning(f"Cannot cancel task {task_id}: task not found")
            return False

        # Проверяем, можно ли отменить задачу
        if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            logger.warning(f"Cannot cancel task {task_id}: status is {task.status.value}")
            return False

        # Если задача выполняется в asyncio - отменяем её
        if task_id in self._running_tasks:
            try:
                self._running_tasks[task_id].cancel()
                logger.info(f"Cancelled asyncio task {task_id}")
            except Exception as e:
                logger.warning(f"Failed to cancel asyncio task {task_id}: {e}")

        # Обновляем статус задачи в любом случае
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now(timezone.utc)
        task.message = "Задача отменена пользователем"
        task.progress = 100  # Помечаем как завершённую
        self._cache[task_id] = task
        self._save_to_db(task)
        self._notify_subscribers(task_id, task)

        # Удаляем из кэша
        self._cache.pop(task_id, None)

        logger.info(f"Task {task_id} cancelled successfully")
        return True

    def run_async_task(
        self,
        task_id: str,
        coro: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> None:
        """Run an async task in the background using ThreadPoolExecutor.

        This is necessary because the async tasks perform synchronous database
        operations which would otherwise block the event loop.
        """
        async def wrapper():
            try:
                self.start_task(task_id)

                # Run the coroutine in a thread pool to avoid blocking event loop
                # since it contains synchronous DB operations
                loop = asyncio.get_event_loop()
                executor = self._get_executor()

                # Create a synchronous wrapper
                def sync_wrapper():
                    # Create new event loop for this thread
                    import asyncio
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(coro(task_id, *args, **kwargs))
                        return result
                    finally:
                        new_loop.close()

                # Run in shared executor with limited workers
                result = await loop.run_in_executor(executor, sync_wrapper)

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
                            logger.warning("Skipping async callback - no running event loop")
                    except RuntimeError:
                        logger.warning("Skipping async callback - no event loop")
                else:
                    # Sync callback
                    callback(task)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Remove old completed/failed tasks from database."""
        from app.db.models import BackgroundTask, BackgroundTaskStatusEnum

        db = self._get_db_session()
        try:
            cutoff = datetime.now() - timedelta(hours=max_age_hours)

            result = db.query(BackgroundTask).filter(
                BackgroundTask.status.in_([
                    BackgroundTaskStatusEnum.COMPLETED,
                    BackgroundTaskStatusEnum.FAILED,
                    BackgroundTaskStatusEnum.CANCELLED
                ]),
                BackgroundTask.completed_at < cutoff
            ).delete(synchronize_session=False)

            db.commit()

            # Clean up memory caches too
            for task_id in list(self._cache.keys()):
                task = self._cache[task_id]
                if (task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
                    and task.completed_at and task.completed_at < cutoff):
                    self._cache.pop(task_id, None)
                    self._subscribers.pop(task_id, None)
                    self._last_db_update.pop(task_id, None)

            return result
        except Exception as e:
            db.rollback()
            logger.error(f"Error cleaning up old tasks: {e}")
            return 0
        finally:
            db.close()

    def shutdown(self):
        """Shutdown the task manager and cleanup resources."""
        logger.info("Shutting down BackgroundTaskManager...")

        # Cancel all running tasks
        for task_id, task in list(self._running_tasks.items()):
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled task {task_id}")

        # Shutdown executor
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=False)
            self._executor = None
            logger.info("ThreadPoolExecutor shut down")

        logger.info("BackgroundTaskManager shutdown complete")


# Global task manager instance
task_manager = BackgroundTaskManager()
