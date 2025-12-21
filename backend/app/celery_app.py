"""
Celery application for background tasks and scheduled sync.
"""
import logging
from datetime import datetime, timedelta, date
from celery import Celery
from celery.schedules import crontab, schedule

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models import SyncSettings
from app.services.odata_1c_client import create_1c_client_from_env
from app.services.bank_transaction_1c_import import BankTransaction1CImporter

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'west_rashod',
    broker=f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0' if settings.USE_REDIS else 'memory://',
    backend=f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0' if settings.USE_REDIS else 'db+' + settings.DATABASE_URL,
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)


def get_sync_schedule():
    """
    Get schedule from database settings.
    Returns crontab or schedule object based on settings.
    """
    db = SessionLocal()
    try:
        sync_settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()

        if not sync_settings or not sync_settings.auto_sync_enabled:
            # Disabled - return very long interval
            return schedule(run_every=timedelta(days=365))

        # If specific hour is set, use crontab (daily at specific time)
        if sync_settings.sync_time_hour is not None:
            return crontab(
                hour=sync_settings.sync_time_hour,
                minute=sync_settings.sync_time_minute
            )

        # Otherwise use interval
        return schedule(run_every=timedelta(hours=sync_settings.sync_interval_hours))

    except Exception as e:
        logger.error(f"Failed to get sync schedule from DB: {e}")
        # Default fallback: every 4 hours
        return schedule(run_every=timedelta(hours=4))
    finally:
        db.close()


# Celery Beat schedule (периодические задачи)
celery_app.conf.beat_schedule = {
    'auto-sync-1c-transactions': {
        'task': 'app.celery_app.sync_1c_transactions_task',
        'schedule': get_sync_schedule(),
        'options': {'queue': 'sync'}
    },
}


@celery_app.task(name='app.celery_app.sync_1c_transactions_task', bind=True)
def sync_1c_transactions_task(self):
    """
    Scheduled task to sync bank transactions and cash operations from 1C.
    Runs based on sync_settings configuration.
    """
    db = SessionLocal()

    try:
        # Get sync settings
        sync_settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()

        if not sync_settings:
            logger.warning("Sync settings not found, creating default")
            sync_settings = SyncSettings(id=1)
            db.add(sync_settings)
            db.commit()
            db.refresh(sync_settings)

        # Check if sync is enabled
        if not sync_settings.auto_sync_enabled:
            logger.info("Auto sync is disabled in settings")
            return {"status": "disabled", "message": "Auto sync is disabled"}

        # Update sync status
        sync_settings.last_sync_started_at = datetime.utcnow()
        sync_settings.last_sync_status = "IN_PROGRESS"
        db.commit()

        logger.info(f"Starting scheduled 1C sync (days_back={sync_settings.sync_days_back}, auto_classify={sync_settings.auto_classify})")

        # Calculate date range
        date_to = date.today()
        date_from = date_to - timedelta(days=sync_settings.sync_days_back)

        # Create OData client and importer
        client = create_1c_client_from_env()
        importer = BankTransaction1CImporter(
            db=db,
            odata_client=client,
            auto_classify=sync_settings.auto_classify
        )

        # Run import
        result = importer.import_transactions(
            date_from=date_from,
            date_to=date_to,
            batch_size=settings.SYNC_BATCH_SIZE
        )

        # Update sync status
        sync_settings.last_sync_completed_at = datetime.utcnow()
        sync_settings.last_sync_status = "SUCCESS" if result.success else "FAILED"
        sync_settings.last_sync_message = f"Created: {result.total_created}, Updated: {result.total_updated}, " \
                                          f"Receipts: {result.receipts_created}, Payments: {result.payments_created}, " \
                                          f"PKO: {result.cash_receipts_created}, RKO: {result.cash_payments_created}"
        db.commit()

        logger.info(f"Scheduled sync completed: {sync_settings.last_sync_message}")

        return {
            "status": "success",
            "message": sync_settings.last_sync_message,
            "statistics": result.to_dict()
        }

    except Exception as e:
        logger.exception("Scheduled sync failed")

        # Update sync status on error
        if db:
            try:
                sync_settings = db.query(SyncSettings).filter(SyncSettings.id == 1).first()
                if sync_settings:
                    sync_settings.last_sync_completed_at = datetime.utcnow()
                    sync_settings.last_sync_status = "FAILED"
                    sync_settings.last_sync_message = f"Error: {str(e)[:500]}"
                    db.commit()
            except:
                pass

        raise

    finally:
        if db:
            db.close()


@celery_app.task(name='app.celery_app.test_task')
def test_task():
    """Test task to verify Celery is working."""
    logger.info("Test task executed successfully")
    return {"status": "ok", "message": "Test task completed"}
