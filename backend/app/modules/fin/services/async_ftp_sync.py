"""
Async FTP sync service for fin module.
Replaces Celery tasks with AsyncIO-based background tasks.
Uses the same pattern as app/services/async_sync_service.py
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.background_tasks import task_manager, TaskStatus
from app.modules.fin.services.ftp_client import FinFTPClient
from app.modules.fin.services.xlsx_parser import FinXLSXParser
from app.modules.fin.services.importer import FinDataImporter

logger = logging.getLogger(__name__)


class AsyncFTPSyncService:
    """
    Async service for FTP file import operations.
    Replaces Celery-based tasks from west_fin.
    """

    TASK_TYPE_FTP_IMPORT = "fin_ftp_import"
    TASK_TYPE_FTP_DOWNLOAD = "fin_ftp_download"

    @classmethod
    def start_ftp_import(
        cls,
        clear_existing: bool = True,
        user_id: Optional[int] = None
    ) -> str:
        """
        Start async FTP import task.

        Downloads files from FTP, parses them, and imports into database.

        Args:
            clear_existing: Whether to clear existing data before import
            user_id: ID of user who initiated the import

        Returns:
            task_id for tracking progress
        """
        task_id = task_manager.create_task(
            task_type=cls.TASK_TYPE_FTP_IMPORT,
            total=100,  # Will be updated dynamically
            metadata={
                "clear_existing": clear_existing,
                "user_id": user_id,
            },
            user_id=user_id
        )

        # Run async task
        task_manager.run_async_task(
            task_id,
            cls._ftp_import_async,
            clear_existing=clear_existing
        )

        return task_id

    @classmethod
    async def _ftp_import_async(
        cls,
        task_id: str,
        clear_existing: bool
    ) -> Dict[str, Any]:
        """
        Async worker for FTP import.

        Args:
            task_id: Task ID for progress tracking
            clear_existing: Whether to clear existing data

        Returns:
            Import result summary
        """
        db = SessionLocal()
        downloaded_files = []
        temp_dir = None

        try:
            # Phase 1: Connect to FTP and list files
            task_manager.update_progress(
                task_id, 0,
                message="Подключение к FTP серверу..."
            )

            ftp_client = FinFTPClient()

            if not ftp_client.connect():
                raise Exception("Не удалось подключиться к FTP серверу")

            task_manager.update_progress(
                task_id, 5,
                message="Получение списка файлов..."
            )

            xlsx_files = ftp_client.list_xlsx_files()

            if not xlsx_files:
                ftp_client.disconnect()
                return {
                    "success": True,
                    "message": "Нет файлов для импорта на FTP сервере",
                    "files_downloaded": 0,
                    "files_processed": 0,
                    "receipts": {"inserted": 0, "updated": 0, "failed": 0},
                    "expenses": {"inserted": 0, "updated": 0, "failed": 0},
                    "details": {"inserted": 0, "failed": 0},
                }

            total_files = len(xlsx_files)
            logger.info(f"Found {total_files} XLSX files on FTP")

            # Phase 2: Download files
            task_manager.update_progress(
                task_id, 10,
                message=f"Скачивание {total_files} файлов..."
            )

            for i, filename in enumerate(xlsx_files):
                success, local_path = ftp_client.download_file(filename)
                if success:
                    downloaded_files.append(local_path)

                progress = 10 + int((i + 1) / total_files * 20)
                task_manager.update_progress(
                    task_id, progress,
                    message=f"Скачано {i + 1}/{total_files} файлов"
                )

                # Yield control
                await asyncio.sleep(0.01)

            ftp_client.disconnect()

            if not downloaded_files:
                return {
                    "success": False,
                    "message": "Не удалось скачать ни одного файла",
                    "files_downloaded": 0,
                    "files_processed": 0,
                }

            # Phase 3: Import files
            task_manager.update_progress(
                task_id, 30,
                message="Начало импорта данных..."
            )

            importer = FinDataImporter(db)

            # Clear existing data if requested
            if clear_existing:
                task_manager.update_progress(
                    task_id, 32,
                    message="Очистка существующих данных..."
                )
                importer.clear_existing_data()

            # Sort files: receipts first, then expenses, then details
            sorted_files = cls._sort_files_for_import(downloaded_files)

            total_receipts = {"inserted": 0, "updated": 0, "failed": 0}
            total_expenses = {"inserted": 0, "updated": 0, "failed": 0}
            total_details = {"inserted": 0, "failed": 0}
            files_processed = 0
            errors = []

            for i, file_path in enumerate(sorted_files):
                try:
                    filename = Path(file_path).name
                    progress = 35 + int((i + 1) / len(sorted_files) * 60)

                    task_manager.update_progress(
                        task_id, progress,
                        message=f"Обработка {filename}..."
                    )

                    success = importer.import_file(file_path)

                    if success:
                        files_processed += 1
                    else:
                        errors.append(f"Ошибка импорта {filename}")

                    # Yield control
                    await asyncio.sleep(0.01)

                except Exception as e:
                    error_msg = f"Ошибка обработки {Path(file_path).name}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)

            # Get import statistics from logs
            stats = cls._get_import_stats(db)

            task_manager.update_progress(
                task_id, 100,
                message="Импорт завершён"
            )

            return {
                "success": True,
                "message": f"Импорт завершён: обработано {files_processed}/{len(sorted_files)} файлов",
                "files_downloaded": len(downloaded_files),
                "files_processed": files_processed,
                "receipts": stats.get("receipts", total_receipts),
                "expenses": stats.get("expenses", total_expenses),
                "details": stats.get("details", total_details),
                "errors": errors[:10],
            }

        except Exception as e:
            db.rollback()
            logger.exception("FTP import failed")
            raise
        finally:
            db.close()
            # Cleanup downloaded files
            cls._cleanup_files(downloaded_files)

    @classmethod
    def _sort_files_for_import(cls, file_paths: List[str]) -> List[str]:
        """
        Sort files for correct import order.
        Receipts first, then expenses, then details.
        """
        receipts = []
        expenses = []
        details = []
        others = []

        for path in file_paths:
            filename = Path(path).name.lower()

            if "поступлени" in filename or "receipt" in filename:
                receipts.append(path)
            elif "списани" in filename or "payment" in filename or "expense" in filename:
                if "расшифровк" in filename or "detail" in filename:
                    details.append(path)
                else:
                    expenses.append(path)
            elif "расшифровк" in filename or "detail" in filename:
                details.append(path)
            else:
                others.append(path)

        return receipts + expenses + details + others

    @classmethod
    def _get_import_stats(cls, db: Session) -> Dict[str, Dict[str, int]]:
        """Get import statistics from the latest import logs."""
        from app.modules.fin.models import FinImportLog

        stats = {
            "receipts": {"inserted": 0, "updated": 0, "failed": 0},
            "expenses": {"inserted": 0, "updated": 0, "failed": 0},
            "details": {"inserted": 0, "failed": 0},
        }

        try:
            # Get latest logs (within last hour)
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(hours=1)

            logs = db.query(FinImportLog).filter(
                FinImportLog.import_date >= cutoff
            ).all()

            for log in logs:
                if log.table_name == "fin_receipts":
                    stats["receipts"]["inserted"] += log.rows_inserted or 0
                    stats["receipts"]["updated"] += log.rows_updated or 0
                    stats["receipts"]["failed"] += log.rows_failed or 0
                elif log.table_name == "fin_expenses":
                    stats["expenses"]["inserted"] += log.rows_inserted or 0
                    stats["expenses"]["updated"] += log.rows_updated or 0
                    stats["expenses"]["failed"] += log.rows_failed or 0
                elif log.table_name == "fin_expense_details":
                    stats["details"]["inserted"] += log.rows_inserted or 0
                    stats["details"]["failed"] += log.rows_failed or 0

        except Exception as e:
            logger.error(f"Error getting import stats: {e}")

        return stats

    @classmethod
    def _cleanup_files(cls, file_paths: List[str]) -> None:
        """Clean up downloaded files after import."""
        for file_path in file_paths:
            try:
                path = Path(file_path)
                if path.exists():
                    path.unlink()
                    logger.debug(f"Deleted temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {file_path}: {e}")

    @classmethod
    def start_ftp_download_only(cls, user_id: Optional[int] = None) -> str:
        """
        Start async task to only download files from FTP (without import).

        Args:
            user_id: ID of user who initiated the download

        Returns:
            task_id for tracking progress
        """
        task_id = task_manager.create_task(
            task_type=cls.TASK_TYPE_FTP_DOWNLOAD,
            total=100,
            metadata={"user_id": user_id},
            user_id=user_id
        )

        task_manager.run_async_task(
            task_id,
            cls._ftp_download_async
        )

        return task_id

    @classmethod
    async def _ftp_download_async(cls, task_id: str) -> Dict[str, Any]:
        """
        Async worker for FTP download only.
        """
        downloaded_files = []

        try:
            task_manager.update_progress(
                task_id, 0,
                message="Подключение к FTP серверу..."
            )

            ftp_client = FinFTPClient()

            if not ftp_client.connect():
                raise Exception("Не удалось подключиться к FTP серверу")

            task_manager.update_progress(
                task_id, 10,
                message="Получение списка файлов..."
            )

            xlsx_files = ftp_client.list_xlsx_files()

            if not xlsx_files:
                ftp_client.disconnect()
                return {
                    "success": True,
                    "message": "Нет файлов на FTP сервере",
                    "files": [],
                }

            total_files = len(xlsx_files)

            for i, filename in enumerate(xlsx_files):
                success, local_path = ftp_client.download_file(filename)
                if success:
                    downloaded_files.append({
                        "filename": filename,
                        "local_path": local_path,
                        "size": Path(local_path).stat().st_size
                    })

                progress = 10 + int((i + 1) / total_files * 90)
                task_manager.update_progress(
                    task_id, progress,
                    message=f"Скачано {i + 1}/{total_files} файлов"
                )

                await asyncio.sleep(0.01)

            ftp_client.disconnect()

            return {
                "success": True,
                "message": f"Скачано {len(downloaded_files)} файлов",
                "files": downloaded_files,
            }

        except Exception as e:
            logger.exception("FTP download failed")
            raise


# Convenience functions for backward compatibility
def start_ftp_import(clear_existing: bool = True, user_id: int = None) -> str:
    """Start FTP import task."""
    return AsyncFTPSyncService.start_ftp_import(
        clear_existing=clear_existing,
        user_id=user_id
    )


def start_ftp_download(user_id: int = None) -> str:
    """Start FTP download task."""
    return AsyncFTPSyncService.start_ftp_download_only(user_id=user_id)
