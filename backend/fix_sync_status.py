"""Script to fix sync status based on latest completed task."""
import sys
from datetime import datetime

from app.db.session import SessionLocal
from app.db.models import SyncSettings, BackgroundTask, BackgroundTaskStatusEnum

def fix_sync_status():
    """Update sync settings based on latest completed task."""
    db = SessionLocal()

    try:
        # Get sync settings
        settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()

        if not settings:
            print("❌ SyncSettings not found")
            return

        print(f"Current status: {settings.last_sync_status}")
        print(f"Last started: {settings.last_sync_started_at}")
        print(f"Last completed: {settings.last_sync_completed_at}")

        if settings.last_sync_status != "IN_PROGRESS":
            print("✅ Status is already correct")
            return

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
            print("⚠️  No completed tasks found")
            return

        print(f"\nFound task: {latest_task.task_id}")
        print(f"Task status: {latest_task.status.value}")
        print(f"Task completed: {latest_task.completed_at}")

        # Update settings
        settings.last_sync_completed_at = latest_task.completed_at or datetime.utcnow()

        if latest_task.status == BackgroundTaskStatusEnum.COMPLETED:
            settings.last_sync_status = "SUCCESS"

            # Parse result
            if latest_task.result:
                import json
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

        print(f"\n✅ Status updated to: {settings.last_sync_status}")
        print(f"Message: {settings.last_sync_message}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_sync_status()
