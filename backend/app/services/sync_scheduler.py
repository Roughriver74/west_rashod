"""Async scheduler for automatic 1C synchronization."""
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import SyncSettings
from app.services.async_sync_service import AsyncSyncService

logger = logging.getLogger(__name__)


class SyncScheduler:
    """Async scheduler for periodic 1C sync based on database settings."""

    _instance: Optional["SyncScheduler"] = None
    _running: bool = False
    _task: Optional[asyncio.Task] = None
    _check_interval: int = 60  # Check settings every 60 seconds

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._running = False
            cls._task = None
        return cls._instance

    def _get_db(self) -> Session:
        """Get database session."""
        return SessionLocal()

    def _get_settings(self) -> Optional[SyncSettings]:
        """Get sync settings from database."""
        db = self._get_db()
        try:
            settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()
            return settings
        finally:
            db.close()

    def _should_run_sync(self, settings: SyncSettings) -> bool:
        """Check if sync should be run based on settings."""
        if not settings or not settings.auto_sync_enabled:
            return False

        now = datetime.utcnow()

        # If specific time is set, check if it's time to run
        if settings.sync_time_hour is not None:
            # Check if current time matches scheduled time (within 1 minute)
            current_hour = now.hour
            current_minute = now.minute

            if (current_hour == settings.sync_time_hour and
                current_minute == settings.sync_time_minute):
                # Check if we already ran today
                if settings.last_sync_started_at:
                    last_sync_date = settings.last_sync_started_at.date()
                    if last_sync_date == now.date():
                        return False
                return True
            return False

        # Interval-based sync
        if settings.last_sync_started_at:
            hours_since_last_sync = (now - settings.last_sync_started_at).total_seconds() / 3600
            return hours_since_last_sync >= settings.sync_interval_hours

        # No previous sync, run now
        return True

    async def _run_sync(self, settings: SyncSettings) -> None:
        """Run the sync task."""
        from app.services.background_tasks import task_manager, TaskStatus

        db = self._get_db()
        try:
            logger.info(f"Starting scheduled 1C sync (days_back={settings.sync_days_back})")

            # Update sync settings
            try:
                db_settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()
                if db_settings:
                    db_settings.last_sync_started_at = datetime.utcnow()
                    db_settings.last_sync_status = "IN_PROGRESS"
                    db_settings.last_sync_message = "Автоматическая синхронизация запущена"
                    db.commit()
                else:
                    logger.warning("SyncSettings record not found, skipping update")
            except Exception as e:
                logger.error(f"Failed to update SyncSettings: {e}")
                db.rollback()
                # Continue with sync even if settings update fails

            # Calculate date range
            date_to = date.today()
            date_from = date_to - timedelta(days=settings.sync_days_back)

            # Start async sync
            task_id = AsyncSyncService.start_full_sync(
                date_from=date_from,
                date_to=date_to,
                auto_classify=settings.auto_classify,
                user_id=None  # System-initiated
            )

            logger.info(f"Scheduled sync started with task_id: {task_id}")

            # Monitor task completion in background
            asyncio.create_task(self._monitor_task_completion(task_id))

        except Exception as e:
            logger.exception("Failed to start scheduled sync")
            # Update sync settings with error
            try:
                db_settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()
                if db_settings:
                    db_settings.last_sync_completed_at = datetime.utcnow()
                    db_settings.last_sync_status = "FAILED"
                    db_settings.last_sync_message = f"Ошибка запуска: {str(e)[:500]}"
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    async def _monitor_task_completion(self, task_id: str) -> None:
        """Monitor task and update SyncSettings when completed."""
        from app.services.background_tasks import task_manager, TaskStatus

        max_wait_time = 3600  # 1 hour max
        check_interval = 5  # Check every 5 seconds
        elapsed = 0

        while elapsed < max_wait_time:
            await asyncio.sleep(check_interval)
            elapsed += check_interval

            task = task_manager.get_task(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                break

            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                # Update SyncSettings with final status
                db = self._get_db()
                try:
                    db_settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()
                    if db_settings:
                        db_settings.last_sync_completed_at = datetime.utcnow()

                        if task.status == TaskStatus.COMPLETED:
                            db_settings.last_sync_status = "SUCCESS"
                            if task.result and isinstance(task.result, dict):
                                # Format result message
                                tx = task.result.get('transactions', {})
                                db_settings.last_sync_message = (
                                    f"Создано: {tx.get('total_created', 0)}, "
                                    f"Обновлено: {tx.get('total_updated', 0)}, "
                                    f"Пропущено: {tx.get('total_skipped', 0)}"
                                )
                            else:
                                db_settings.last_sync_message = task.message or "Синхронизация завершена"
                        elif task.status == TaskStatus.FAILED:
                            db_settings.last_sync_status = "FAILED"
                            db_settings.last_sync_message = f"Ошибка: {task.error or 'Неизвестная ошибка'}"
                        else:
                            db_settings.last_sync_status = "FAILED"
                            db_settings.last_sync_message = "Синхронизация отменена"

                        db.commit()
                        logger.info(f"Updated SyncSettings after task {task_id} completion")
                except Exception as e:
                    logger.error(f"Failed to update SyncSettings: {e}")
                finally:
                    db.close()
                break

        if elapsed >= max_wait_time:
            logger.warning(f"Task {task_id} monitoring timed out")

    def _should_run_expense_sync(self, settings: SyncSettings) -> bool:
        """Check if expense sync should be run based on settings."""
        if not settings or not settings.auto_sync_expenses_enabled:
            return False

        now = datetime.utcnow()

        # Interval-based sync for expenses
        if settings.last_sync_started_at:
            hours_since_last_sync = (now - settings.last_sync_started_at).total_seconds() / 3600
            return hours_since_last_sync >= settings.sync_expenses_interval_hours

        # No previous sync, run now
        return True

    async def _run_expense_sync(self, settings: SyncSettings) -> None:
        """Run the expense sync task."""
        from app.services.background_tasks import task_manager, TaskStatus

        db = self._get_db()
        try:
            logger.info(f"Starting scheduled expense sync (days_back={settings.sync_expenses_days_back})")

            # Calculate date range
            date_to = date.today()
            date_from = date_to - timedelta(days=settings.sync_expenses_days_back)

            # Start async expense sync
            task_id = AsyncSyncService.start_expenses_sync(
                date_from=date_from,
                date_to=date_to,
                user_id=None  # System-initiated
            )

            logger.info(f"Scheduled expense sync started with task_id: {task_id}")

        except Exception as e:
            logger.exception("Failed to start scheduled expense sync")
        finally:
            db.close()

    def _should_run_ftp_import(self, settings: SyncSettings) -> bool:
        """Check if FTP import should be run based on settings."""
        if not settings or not settings.ftp_import_enabled:
            return False

        now = datetime.utcnow()

        # If specific time is set, check if it's time to run
        if settings.ftp_import_time_hour is not None:
            current_hour = now.hour
            current_minute = now.minute

            if (current_hour == settings.ftp_import_time_hour and
                current_minute == settings.ftp_import_time_minute):
                # Check if we already ran today
                if settings.last_ftp_import_started_at:
                    last_import_date = settings.last_ftp_import_started_at.date()
                    if last_import_date == now.date():
                        return False
                return True
            return False

        # Interval-based import
        if settings.last_ftp_import_started_at:
            hours_since_last_import = (now - settings.last_ftp_import_started_at).total_seconds() / 3600
            return hours_since_last_import >= settings.ftp_import_interval_hours

        # No previous import, run now
        return True

    async def _run_ftp_import(self, settings: SyncSettings) -> None:
        """Run the FTP import task."""
        from app.modules.fin.services.async_ftp_sync import AsyncFTPSyncService

        db = self._get_db()
        try:
            logger.info(f"Starting scheduled FTP import (clear_existing={settings.ftp_import_clear_existing})")

            # Update settings
            try:
                db_settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()
                if db_settings:
                    db_settings.last_ftp_import_started_at = datetime.utcnow()
                    db_settings.last_ftp_import_status = "IN_PROGRESS"
                    db_settings.last_ftp_import_message = "Автоматический FTP импорт запущен"
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to update FTP import settings: {e}")
                db.rollback()

            # Start async FTP import
            task_id = AsyncFTPSyncService.start_ftp_import(
                clear_existing=settings.ftp_import_clear_existing,
                user_id=None  # System-initiated
            )

            logger.info(f"Scheduled FTP import started with task_id: {task_id}")

            # Monitor task completion in background
            asyncio.create_task(self._monitor_ftp_task_completion(task_id))

        except Exception as e:
            logger.exception("Failed to start scheduled FTP import")
            try:
                db_settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()
                if db_settings:
                    db_settings.last_ftp_import_completed_at = datetime.utcnow()
                    db_settings.last_ftp_import_status = "FAILED"
                    db_settings.last_ftp_import_message = f"Ошибка запуска: {str(e)[:500]}"
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    async def _monitor_ftp_task_completion(self, task_id: str) -> None:
        """Monitor FTP task and update SyncSettings when completed."""
        from app.services.background_tasks import task_manager, TaskStatus

        max_wait_time = 3600  # 1 hour max
        check_interval = 5  # Check every 5 seconds
        elapsed = 0

        while elapsed < max_wait_time:
            await asyncio.sleep(check_interval)
            elapsed += check_interval

            task = task_manager.get_task(task_id)
            if not task:
                logger.warning(f"FTP Task {task_id} not found")
                break

            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                db = self._get_db()
                try:
                    db_settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()
                    if db_settings:
                        db_settings.last_ftp_import_completed_at = datetime.utcnow()

                        if task.status == TaskStatus.COMPLETED:
                            db_settings.last_ftp_import_status = "SUCCESS"
                            if task.result and isinstance(task.result, dict):
                                receipts = task.result.get('receipts', {})
                                expenses = task.result.get('expenses', {})
                                db_settings.last_ftp_import_message = (
                                    f"Поступления: {receipts.get('inserted', 0)} добавлено, "
                                    f"Списания: {expenses.get('inserted', 0)} добавлено"
                                )
                            else:
                                db_settings.last_ftp_import_message = task.message or "FTP импорт завершён"
                        elif task.status == TaskStatus.FAILED:
                            db_settings.last_ftp_import_status = "FAILED"
                            db_settings.last_ftp_import_message = f"Ошибка: {task.error or 'Неизвестная ошибка'}"
                        else:
                            db_settings.last_ftp_import_status = "FAILED"
                            db_settings.last_ftp_import_message = "FTP импорт отменён"

                        db.commit()
                        logger.info(f"Updated FTP import settings after task {task_id} completion")
                except Exception as e:
                    logger.error(f"Failed to update FTP import settings: {e}")
                finally:
                    db.close()
                break

        if elapsed >= max_wait_time:
            logger.warning(f"FTP Task {task_id} monitoring timed out")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("Sync scheduler started")

        while self._running:
            try:
                settings = self._get_settings()

                # Check and run bank transaction sync
                if settings and self._should_run_sync(settings):
                    await self._run_sync(settings)

                # Check and run expense sync
                if settings and self._should_run_expense_sync(settings):
                    await self._run_expense_sync(settings)

                # Check and run FTP import
                if settings and self._should_run_ftp_import(settings):
                    await self._run_ftp_import(settings)

                # Wait before next check
                await asyncio.sleep(self._check_interval)

            except asyncio.CancelledError:
                logger.info("Sync scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self._check_interval)

        logger.info("Sync scheduler stopped")

    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Sync scheduler initialized")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Sync scheduler stopped")

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running


# Global scheduler instance
sync_scheduler = SyncScheduler()
