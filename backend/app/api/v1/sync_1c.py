"""1C OData sync API endpoints."""
from typing import Optional
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, UserRoleEnum
from app.schemas.sync import Sync1CRequest, Sync1CResult, Sync1CConnectionTest
from app.utils.auth import get_current_active_user
from app.services.odata_1c_client import OData1CClient, create_1c_client_from_env
from app.services.bank_transaction_1c_import import BankTransaction1CImporter
from app.core.config import settings

router = APIRouter(prefix="/sync-1c", tags=["1C Integration"])


@router.get("/test-connection", response_model=Sync1CConnectionTest)
def test_connection(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Test connection to 1C OData service."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can test 1C connection"
        )

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
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can sync from 1C"
        )

    try:
        client = create_1c_client_from_env()
        importer = BankTransaction1CImporter(db, client)

        # Default date range: last 30 days
        date_from = sync_request.date_from or (date.today() - timedelta(days=30))
        date_to = sync_request.date_to or date.today()

        result = importer.import_bank_transactions(
            department_id=sync_request.department_id,
            date_from=date_from,
            date_to=date_to,
            auto_classify=sync_request.auto_classify
        )

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
        return Sync1CResult(
            success=False,
            message=f"Sync failed: {str(e)}",
            errors=[str(e)]
        )


@router.post("/organizations/sync", response_model=Sync1CResult)
def sync_organizations(
    department_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync organizations from 1C."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can sync from 1C"
        )

    try:
        from app.db.models import Organization
        client = create_1c_client_from_env()

        # Get organizations from 1C
        org_docs = client.get_organizations()

        created = 0
        updated = 0
        errors = []

        for org_doc in org_docs:
            try:
                ref_key = org_doc.get("Ref_Key")
                if not ref_key:
                    continue

                # Check if exists
                existing = db.query(Organization).filter(
                    Organization.external_id_1c == ref_key
                ).first()

                if existing:
                    # Update
                    existing.name = org_doc.get("Description", existing.name)
                    existing.inn = org_doc.get("ИНН", existing.inn)
                    existing.kpp = org_doc.get("КПП", existing.kpp)
                    existing.synced_at = datetime.utcnow()
                    updated += 1
                else:
                    # Create
                    org = Organization(
                        name=org_doc.get("Description", "Unknown"),
                        inn=org_doc.get("ИНН"),
                        kpp=org_doc.get("КПП"),
                        external_id_1c=ref_key,
                        department_id=department_id,
                        synced_at=datetime.utcnow()
                    )
                    db.add(org)
                    created += 1

            except Exception as e:
                errors.append(f"Error processing organization: {str(e)}")

        db.commit()

        return Sync1CResult(
            success=True,
            message=f"Synced organizations: {created} created, {updated} updated",
            statistics={
                "created": created,
                "updated": updated,
                "total": len(org_docs)
            },
            errors=errors
        )

    except Exception as e:
        db.rollback()
        return Sync1CResult(
            success=False,
            message=f"Sync failed: {str(e)}",
            errors=[str(e)]
        )


@router.post("/categories/sync", response_model=Sync1CResult)
def sync_categories(
    department_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Sync budget categories from 1C."""
    if current_user.role not in [UserRoleEnum.ADMIN, UserRoleEnum.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can sync from 1C"
        )

    try:
        from app.db.models import BudgetCategory, ExpenseTypeEnum
        client = create_1c_client_from_env()

        # Get categories from 1C
        cat_docs = client.get_cash_flow_categories()

        created = 0
        updated = 0
        errors = []

        for cat_doc in cat_docs:
            try:
                ref_key = cat_doc.get("Ref_Key")
                if not ref_key:
                    continue

                # Check if exists
                existing = db.query(BudgetCategory).filter(
                    BudgetCategory.external_id_1c == ref_key
                ).first()

                if existing:
                    # Update
                    existing.name = cat_doc.get("Description", existing.name)
                    updated += 1
                else:
                    # Create
                    cat = BudgetCategory(
                        name=cat_doc.get("Description", "Unknown"),
                        type=ExpenseTypeEnum.OPEX,  # Default
                        external_id_1c=ref_key,
                        department_id=department_id,
                        is_folder=cat_doc.get("IsFolder", False)
                    )
                    db.add(cat)
                    created += 1

            except Exception as e:
                errors.append(f"Error processing category: {str(e)}")

        db.commit()

        return Sync1CResult(
            success=True,
            message=f"Synced categories: {created} created, {updated} updated",
            statistics={
                "created": created,
                "updated": updated,
                "total": len(cat_docs)
            },
            errors=errors
        )

    except Exception as e:
        db.rollback()
        return Sync1CResult(
            success=False,
            message=f"Sync failed: {str(e)}",
            errors=[str(e)]
        )
