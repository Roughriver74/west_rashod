"""1C OData sync API endpoints."""
import logging
from typing import Optional
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, UserRoleEnum
from app.schemas.sync import (
    Sync1CRequest,
    Sync1CResult,
    Sync1CConnectionTest
)
from app.utils.auth import get_current_active_user
from app.services.odata_1c_client import OData1CClient, create_1c_client_from_env
from app.services.bank_transaction_1c_import import BankTransaction1CImporter
from app.services.async_sync_service import AsyncSyncService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync-1c", tags=["1C Integration"])


class AsyncSyncRequest(BaseModel):
    """Request for async sync operation."""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    auto_classify: bool = True


class AsyncSyncResponse(BaseModel):
    """Response with task ID for async operation."""
    task_id: str
    message: str


@router.get("/test-connection", response_model=Sync1CConnectionTest)
def test_connection(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Test connection to 1C OData service."""
    # Role check removed - all authenticated users can test 1C connection

    try:
        client = create_1c_client_from_env()
        is_connected, message = client.test_connection()

        return Sync1CConnectionTest(
            success=is_connected,
            message=message,
            details={
                "url": settings.ODATA_1C_URL,
                "username": settings.ODATA_1C_USERNAME,
            }
        )
    except Exception as e:
        return Sync1CConnectionTest(
            success=False,
            message=f"Connection failed: {str(e)}",
            details={"error": str(e)}
        )


@router.post("/bank-transactions/sync", response_model=Sync1CResult)
def sync_bank_transactions(
    sync_request: Sync1CRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync bank transactions from 1C."""
    logger.info(f"=== SYNC BANK TRANSACTIONS START ===")
    logger.info(f"User: {current_user.username}, Request: {sync_request}")

    # Role check removed - all authenticated users can sync from 1C

    try:
        logger.info("Creating 1C client...")
        client = create_1c_client_from_env()
        importer = BankTransaction1CImporter(
            db=db,
            odata_client=client,
            auto_classify=sync_request.auto_classify
        )

        # Parse dates from string or use defaults
        if sync_request.date_from:
            date_from = datetime.fromisoformat(sync_request.date_from.replace('Z', '+00:00')).date()
        else:
            date_from = date.today() - timedelta(days=30)

        if sync_request.date_to:
            date_to = datetime.fromisoformat(sync_request.date_to.replace('Z', '+00:00')).date()
        else:
            date_to = date.today()

        logger.info(f"Importing transactions from {date_from} to {date_to}")
        result = importer.import_transactions(
            date_from=date_from,
            date_to=date_to
        )

        logger.info(f"Import result: success={result.success}, message={result.message}")
        logger.info(f"Stats: fetched={result.total_fetched}, created={result.total_created}, updated={result.total_updated}")
        if result.errors:
            logger.warning(f"Errors ({len(result.errors)}): {result.errors[:5]}")

        return Sync1CResult(
            success=result.success,
            message=result.message,
            statistics={
                "total_fetched": result.total_fetched,
                "total_created": result.total_created,
                "total_updated": result.total_updated,
                "total_skipped": result.total_skipped,
                "receipts_created": result.receipts_created,
                "payments_created": result.payments_created,
                "cash_receipts_created": result.cash_receipts_created,
                "cash_payments_created": result.cash_payments_created,
            },
            errors=result.errors
        )

    except Exception as e:
        logger.error(f"Sync failed with exception: {e}", exc_info=True)
        return Sync1CResult(
            success=False,
            message=f"Sync failed: {str(e)}",
            errors=[str(e)]
        )


@router.post("/organizations/sync", response_model=Sync1CResult)
def sync_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync organizations from 1C."""
    logger.info(f"=== SYNC ORGANIZATIONS START ===")
    logger.info(f"User: {current_user.username}")

    # Role check removed - all authenticated users can sync from 1C

    try:
        from app.db.models import Organization
        client = create_1c_client_from_env()

        # Get organizations from 1C
        logger.info("Fetching organizations from 1C...")
        org_docs = client.get_organizations()
        logger.info(f"Fetched {len(org_docs)} organizations from 1C")
        if org_docs:
            logger.debug(f"Sample org doc keys: {list(org_docs[0].keys())}")

        created = 0
        updated = 0
        errors = []

        for org_doc in org_docs:
            try:
                ref_key = org_doc.get("Ref_Key")
                # Get name from various 1C fields
                name = (
                    org_doc.get("Description")
                    or org_doc.get("НаименованиеПолное")
                    or org_doc.get("НаименованиеСокращенное")
                    or f"Организация {ref_key[:8] if ref_key else 'Unknown'}"
                )
                full_name = org_doc.get("НаименованиеПолное") or name
                short_name = org_doc.get("НаименованиеСокращенное") or name

                if not ref_key:
                    continue

                # Check if exists by external_id or name
                existing = db.query(Organization).filter(
                    Organization.external_id_1c == ref_key
                ).first()

                if not existing:
                    # Also check by name (unique constraint)
                    existing = db.query(Organization).filter(
                        Organization.name == name
                    ).first()

                if existing:
                    # Update
                    existing.name = name[:255]
                    existing.full_name = full_name[:500] if full_name else None
                    existing.short_name = short_name[:255] if short_name else None
                    existing.inn = org_doc.get("ИНН", existing.inn)
                    existing.kpp = org_doc.get("КПП", existing.kpp)
                    existing.external_id_1c = ref_key  # Link to 1C
                    existing.synced_at = datetime.utcnow()
                    updated += 1
                else:
                    # Create
                    org = Organization(
                        name=name[:255],
                        full_name=full_name[:500] if full_name else None,
                        short_name=short_name[:255] if short_name else None,
                        inn=org_doc.get("ИНН"),
                        kpp=org_doc.get("КПП"),
                        external_id_1c=ref_key,
                        synced_at=datetime.utcnow()
                    )
                    db.add(org)
                    db.flush()  # Flush to catch unique errors early
                    created += 1

            except Exception as e:
                db.rollback()
                logger.error(f"Error processing org '{name}': {e}")
                errors.append(f"Org '{name}': {str(e)}")

        db.commit()
        logger.info(f"=== SYNC ORGANIZATIONS DONE: created={created}, updated={updated}, errors={len(errors)} ===")

        # Update bank information in transactions
        logger.info("Updating bank information in transactions...")
        from app.services.bank_info_updater import update_transactions_bank_info

        bank_stats = update_transactions_bank_info(db, client)
        logger.info(f"Bank info update: {bank_stats}")

        return Sync1CResult(
            success=True,
            message=f"Synced organizations: {created} created, {updated} updated. Updated bank info in {bank_stats.get('updated', 0)} transactions.",
            statistics={
                "created": created,
                "updated": updated,
                "total": len(org_docs),
                "bank_info_updated": bank_stats.get('updated', 0),
                "bank_info_errors": bank_stats.get('errors', 0)
            },
            errors=errors
        )

    except Exception as e:
        logger.error(f"Sync organizations failed: {e}", exc_info=True)
        db.rollback()
        return Sync1CResult(
            success=False,
            message=f"Sync failed: {str(e)}",
            errors=[str(e)]
        )


@router.post("/categories/sync", response_model=Sync1CResult)
def sync_categories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync budget categories from 1C with hierarchy support."""
    logger.info(f"=== SYNC CATEGORIES START ===")
    logger.info(f"User: {current_user.username}")

    try:
        from app.db.models import BudgetCategory, ExpenseTypeEnum
        client = create_1c_client_from_env()

        # Get categories from 1C
        logger.info("Fetching categories from 1C...")
        cat_docs = client.get_cash_flow_categories()
        logger.info(f"Fetched {len(cat_docs)} categories from 1C")

        created = 0
        updated = 0
        errors = []

        # Пустой GUID для корневых элементов
        EMPTY_GUID = "00000000-0000-0000-0000-000000000000"

        # Первый проход: создать/обновить все категории (без parent_id)
        for cat_doc in cat_docs:
            name = cat_doc.get("Description", "Unknown")
            try:
                ref_key = cat_doc.get("Ref_Key")
                if not ref_key:
                    continue

                is_folder = cat_doc.get("IsFolder", False)
                code_1c = cat_doc.get("Code", "")

                # Check if exists
                existing = db.query(BudgetCategory).filter(
                    BudgetCategory.external_id_1c == ref_key
                ).first()

                if existing:
                    # Update
                    existing.name = name
                    existing.is_folder = is_folder
                    existing.code_1c = code_1c
                    updated += 1
                else:
                    # Create
                    cat = BudgetCategory(
                        name=name,
                        type=ExpenseTypeEnum.OPEX,  # Default
                        external_id_1c=ref_key,
                        is_folder=is_folder,
                        code_1c=code_1c
                    )
                    db.add(cat)
                    created += 1

            except Exception as e:
                logger.error(f"Error processing category '{name}': {e}")
                errors.append(f"Cat '{name}': {str(e)}")

        # Flush для получения id новых записей
        db.flush()

        # Второй проход: установить parent_id через Parent_Key
        # Создаём маппинг external_id_1c -> id
        all_categories = db.query(BudgetCategory).filter(
            BudgetCategory.external_id_1c.isnot(None)
        ).all()
        ext_id_to_id = {cat.external_id_1c: cat.id for cat in all_categories}

        parent_set = 0
        for cat_doc in cat_docs:
            ref_key = cat_doc.get("Ref_Key")
            parent_key = cat_doc.get("Parent_Key")

            if not ref_key:
                continue

            # Если есть родитель и это не пустой GUID
            if parent_key and parent_key != EMPTY_GUID:
                cat = db.query(BudgetCategory).filter(
                    BudgetCategory.external_id_1c == ref_key
                ).first()

                if cat and parent_key in ext_id_to_id:
                    cat.parent_id = ext_id_to_id[parent_key]
                    parent_set += 1

        db.commit()
        logger.info(f"=== SYNC CATEGORIES DONE: created={created}, updated={updated}, parents_set={parent_set}, errors={len(errors)} ===")

        return Sync1CResult(
            success=True,
            message=f"Синхронизация категорий: {created} создано, {updated} обновлено, {parent_set} связей с родителями",
            statistics={
                "created": created,
                "updated": updated,
                "parents_set": parent_set,
                "total": len(cat_docs)
            },
            errors=errors
        )

    except Exception as e:
        logger.error(f"Sync categories failed: {e}", exc_info=True)
        db.rollback()
        return Sync1CResult(
            success=False,
            message=f"Ошибка синхронизации: {str(e)}",
            errors=[str(e)]
        )


# ============== ASYNC ENDPOINTS ==============


@router.post("/bank-transactions/sync-async", response_model=AsyncSyncResponse)
async def start_async_bank_transactions_sync(
    sync_request: AsyncSyncRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Start async bank transactions sync (returns immediately with task ID)."""
    logger.info(f"=== ASYNC SYNC BANK TRANSACTIONS START ===")
    logger.info(f"User: {current_user.username}, Request: {sync_request}")

    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can sync from 1C"
        )

    # Parse dates
    if sync_request.date_from:
        date_from = datetime.fromisoformat(sync_request.date_from.replace('Z', '+00:00')).date()
    else:
        date_from = date.today() - timedelta(days=30)

    if sync_request.date_to:
        date_to = datetime.fromisoformat(sync_request.date_to.replace('Z', '+00:00')).date()
    else:
        date_to = date.today()

    # Start async task
    task_id = AsyncSyncService.start_bank_transactions_sync(
        date_from=date_from,
        date_to=date_to,
        auto_classify=sync_request.auto_classify,
        user_id=current_user.id
    )

    logger.info(f"Started async sync task: {task_id}")

    return AsyncSyncResponse(
        task_id=task_id,
        message=f"Sync started. Track progress at /api/v1/tasks/{task_id}"
    )


@router.post("/organizations/sync-async", response_model=AsyncSyncResponse)
async def start_async_organizations_sync(
    current_user: User = Depends(get_current_active_user)
):
    """Start async organizations sync."""
    logger.info("=== ASYNC SYNC ORGANIZATIONS START ===")
    logger.info(f"User: {current_user.username}")

    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can sync from 1C"
        )

    task_id = AsyncSyncService.start_organizations_sync(user_id=current_user.id)

    logger.info(f"Started async organizations sync task: {task_id}")

    return AsyncSyncResponse(
        task_id=task_id,
        message=f"Organizations sync started. Track progress at /api/v1/tasks/{task_id}"
    )


@router.post("/categories/sync-async", response_model=AsyncSyncResponse)
async def start_async_categories_sync(
    current_user: User = Depends(get_current_active_user)
):
    """Start async categories sync."""
    logger.info("=== ASYNC SYNC CATEGORIES START ===")
    logger.info(f"User: {current_user.username}")

    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can sync from 1C"
        )

    task_id = AsyncSyncService.start_categories_sync(user_id=current_user.id)

    logger.info(f"Started async categories sync task: {task_id}")

    return AsyncSyncResponse(
        task_id=task_id,
        message=f"Categories sync started. Track progress at /api/v1/tasks/{task_id}"
    )


@router.post("/contractors/sync-async", response_model=AsyncSyncResponse)
async def start_async_contractors_sync(
    current_user: User = Depends(get_current_active_user)
):
    """Start async contractors sync (returns immediately with task ID)."""
    logger.info(f"=== ASYNC SYNC CONTRACTORS START ===")
    logger.info(f"User: {current_user.username}")

    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can sync from 1C"
        )

    task_id = AsyncSyncService.start_contractors_sync(user_id=current_user.id)

    logger.info(f"Started async contractors sync task: {task_id}")

    return AsyncSyncResponse(
        task_id=task_id,
        message=f"Contractors sync started. Track progress at /api/v1/tasks/{task_id}"
    )


@router.post("/full/sync-async", response_model=AsyncSyncResponse)
async def start_async_full_sync(
    sync_request: AsyncSyncRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Start full async sync (organizations, categories, bank transactions)."""
    logger.info("=== ASYNC FULL SYNC START ===")
    logger.info(f"User: {current_user.username}, Request: {sync_request}")

    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can sync from 1C"
        )

    if sync_request.date_from:
        date_from = datetime.fromisoformat(sync_request.date_from.replace('Z', '+00:00')).date()
    else:
        date_from = date.today() - timedelta(days=30)

    if sync_request.date_to:
        date_to = datetime.fromisoformat(sync_request.date_to.replace('Z', '+00:00')).date()
    else:
        date_to = date.today()

    task_id = AsyncSyncService.start_full_sync(
        date_from=date_from,
        date_to=date_to,
        auto_classify=sync_request.auto_classify,
        user_id=current_user.id
    )

    logger.info(f"Started async full sync task: {task_id}")

    return AsyncSyncResponse(
        task_id=task_id,
        message=f"Full sync started. Track progress at /api/v1/tasks/{task_id}"
    )


@router.post("/expenses/sync-async", response_model=AsyncSyncResponse)
async def start_async_expenses_sync(
    sync_request: AsyncSyncRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Start async expenses sync from 1C."""
    logger.info("=== ASYNC SYNC EXPENSES START ===")
    logger.info(f"User: {current_user.username}, Request: {sync_request}")

    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can sync expenses from 1C"
        )

    # Parse dates
    if sync_request.date_from:
        date_from = datetime.fromisoformat(sync_request.date_from.replace('Z', '+00:00')).date()
    else:
        date_from = date.today() - timedelta(days=30)

    if sync_request.date_to:
        date_to = datetime.fromisoformat(sync_request.date_to.replace('Z', '+00:00')).date()
    else:
        date_to = date.today()

    # Start async task
    task_id = AsyncSyncService.start_expenses_sync(
        date_from=date_from,
        date_to=date_to,
        user_id=current_user.id
    )

    logger.info(f"Started async expenses sync task: {task_id}")

    return AsyncSyncResponse(
        task_id=task_id,
        message=f"Expenses sync started. Track progress at /api/v1/tasks/{task_id}"
    )
