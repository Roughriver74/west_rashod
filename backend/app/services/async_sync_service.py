"""Async synchronization service for background 1C imports."""
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.background_tasks import task_manager, TaskStatus
from app.services.odata_1c_client import create_1c_client_from_env
from app.services.bank_transaction_1c_import import BankTransaction1CImporter
from app.db.models import (
    BankTransaction, BankTransactionTypeEnum, BankTransactionStatusEnum,
    PaymentSourceEnum, DocumentTypeEnum, Organization, Contractor
)

logger = logging.getLogger(__name__)


class AsyncSyncService:
    """Service for running sync operations in background."""

    TASK_TYPE_BANK_TRANSACTIONS = "sync_bank_transactions"
    TASK_TYPE_ORGANIZATIONS = "sync_organizations"
    TASK_TYPE_CATEGORIES = "sync_categories"
    TASK_TYPE_CONTRACTORS = "sync_contractors"

    @classmethod
    def start_bank_transactions_sync(
        cls,
        date_from: date,
        date_to: date,
        auto_classify: bool = True,
        user_id: int = None
    ) -> str:
        """Start async bank transactions sync."""
        # Estimate total based on date range (rough estimate)
        days = (date_to - date_from).days + 1
        estimated_total = days * 50  # Estimate 50 transactions per day

        task_id = task_manager.create_task(
            task_type=cls.TASK_TYPE_BANK_TRANSACTIONS,
            total=estimated_total,
            metadata={
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "auto_classify": auto_classify,
                "user_id": user_id,
            }
        )

        # Run async task
        task_manager.run_async_task(
            task_id,
            cls._sync_bank_transactions_async,
            date_from=date_from,
            date_to=date_to,
            auto_classify=auto_classify
        )

        return task_id

    @classmethod
    async def _sync_bank_transactions_async(
        cls,
        task_id: str,
        date_from: date,
        date_to: date,
        auto_classify: bool
    ) -> Dict[str, Any]:
        """Async worker for bank transactions sync."""
        db = SessionLocal()
        try:
            client = create_1c_client_from_env()

            task_manager.update_progress(
                task_id, 0,
                message="Подключение к 1С..."
            )

            # Test connection
            is_connected, message = client.test_connection()
            if not is_connected:
                raise Exception(f"Не удалось подключиться к 1С: {message}")

            task_manager.update_progress(
                task_id, 5,
                message="Получение данных из 1С..."
            )

            # Fetch all documents in batches for progress tracking
            all_docs = []

            # Fetch bank receipts
            task_manager.update_progress(task_id, 10, message="Загрузка поступлений...")
            receipts = client.get_bank_receipts(date_from, date_to)
            all_docs.extend([("receipt", doc) for doc in receipts])

            await asyncio.sleep(0.1)  # Yield to allow cancellation

            # Fetch bank payments
            task_manager.update_progress(task_id, 20, message="Загрузка списаний...")
            payments = client.get_bank_payments(date_from, date_to)
            all_docs.extend([("payment", doc) for doc in payments])

            await asyncio.sleep(0.1)

            # Fetch cash receipts
            task_manager.update_progress(task_id, 30, message="Загрузка ПКО...")
            cash_receipts = client.get_cash_receipts(date_from, date_to)
            all_docs.extend([("cash_receipt", doc) for doc in cash_receipts])

            await asyncio.sleep(0.1)

            # Fetch cash payments
            task_manager.update_progress(task_id, 40, message="Загрузка РКО...")
            cash_payments = client.get_cash_payments(date_from, date_to)
            all_docs.extend([("cash_payment", doc) for doc in cash_payments])

            total_docs = len(all_docs)
            if total_docs == 0:
                return {
                    "success": True,
                    "message": "Нет данных для импорта",
                    "total_fetched": 0,
                    "total_created": 0,
                    "total_updated": 0,
                }

            # Update total with actual count
            task = task_manager.get_task(task_id)
            if task:
                task.total = total_docs

            task_manager.update_progress(
                task_id, 0,
                message=f"Обработка {total_docs} документов..."
            )

            # Process documents
            created = 0
            updated = 0
            skipped = 0
            errors = []

            importer = BankTransaction1CImporter(
                db=db,
                odata_client=client,
                auto_classify=auto_classify
            )

            for i, (doc_type, doc) in enumerate(all_docs):
                try:
                    # Process single document
                    result = cls._process_document(db, importer, doc_type, doc)
                    if result == "created":
                        created += 1
                    elif result == "updated":
                        updated += 1
                    else:
                        skipped += 1

                    # Commit every 100 items to avoid long transactions
                    if (i + 1) % 100 == 0:
                        try:
                            db.commit()
                        except Exception as commit_error:
                            logger.error(f"Commit error at item {i + 1}: {commit_error}")
                            db.rollback()
                            errors.append(f"Commit failed at {i + 1}: {str(commit_error)}")

                    # Update progress every 10 items
                    if i % 10 == 0 or i == total_docs - 1:
                        progress = 40 + int((i / total_docs) * 55)  # 40-95%
                        task_manager.update_progress(
                            task_id,
                            i + 1,
                            message=f"Обработано {i + 1} из {total_docs} ({created} создано, {updated} обновлено)"
                        )

                    # Yield periodically to allow cancellation
                    if i % 50 == 0:
                        await asyncio.sleep(0.01)

                except Exception as e:
                    errors.append(str(e))
                    logger.error(f"Error processing document: {e}")
                    db.rollback()

            # Final commit
            try:
                db.commit()
            except Exception as e:
                logger.error(f"Final commit error: {e}")
                db.rollback()
                errors.append(f"Final commit failed: {str(e)}")

            task_manager.update_progress(
                task_id, total_docs,
                message="Завершено!"
            )

            return {
                "success": True,
                "message": f"Импорт завершён: {created} создано, {updated} обновлено, {skipped} пропущено",
                "total_fetched": total_docs,
                "total_created": created,
                "total_updated": updated,
                "total_skipped": skipped,
                "errors": errors[:10],  # Limit errors
            }

        except Exception as e:
            db.rollback()
            logger.exception("Async sync failed")
            raise
        finally:
            db.close()

    @classmethod
    def _process_document(
        cls,
        db: Session,
        importer: BankTransaction1CImporter,
        doc_type: str,
        doc: Dict
    ) -> str:
        """Process a single document. Returns 'created', 'updated', or 'skipped'."""
        ref_key = doc.get("Ref_Key")
        if not ref_key:
            return "skipped"

        # Check if exists
        existing = db.query(BankTransaction).filter(
            BankTransaction.external_id_1c == ref_key
        ).first()

        # Parse common fields
        amount = Decimal(str(doc.get("СуммаДокумента", 0) or 0))
        if amount == 0:
            return "skipped"

        tx_date = None
        date_str = doc.get("Date") or doc.get("Дата")
        if date_str:
            try:
                if "T" in str(date_str):
                    tx_date = datetime.fromisoformat(str(date_str).replace("Z", "+00:00")).date()
                else:
                    tx_date = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        if not tx_date:
            return "skipped"

        # Determine transaction type
        if doc_type in ("receipt", "cash_receipt"):
            tx_type = BankTransactionTypeEnum.CREDIT
        else:
            tx_type = BankTransactionTypeEnum.DEBIT

        # Determine payment source
        if doc_type in ("cash_receipt", "cash_payment"):
            payment_source = PaymentSourceEnum.CASH
        else:
            payment_source = PaymentSourceEnum.BANK

        # Get counterparty info
        counterparty_name = doc.get("Контрагент") or doc.get("Плательщик") or doc.get("Получатель")
        if isinstance(counterparty_name, dict):
            counterparty_name = counterparty_name.get("Description", "")

        counterparty_inn = doc.get("ИННКонтрагента") or doc.get("ИНН")
        payment_purpose = doc.get("НазначениеПлатежа", "")

        if existing:
            # Update existing
            existing.amount = amount
            existing.transaction_date = tx_date
            existing.counterparty_name = str(counterparty_name)[:500] if counterparty_name else None
            existing.counterparty_inn = str(counterparty_inn)[:20] if counterparty_inn else None
            existing.payment_purpose = str(payment_purpose)[:2000] if payment_purpose else None
            return "updated"
        else:
            # Create new
            doc_number = doc.get("Number") or doc.get("Номер") or ""
            transaction = BankTransaction(
                external_id_1c=ref_key,
                document_number=str(doc_number)[:50],
                document_date=tx_date,
                transaction_date=tx_date,
                amount=amount,
                currency="RUB",
                transaction_type=tx_type,
                payment_source=payment_source,
                counterparty_name=str(counterparty_name)[:500] if counterparty_name else None,
                counterparty_inn=str(counterparty_inn)[:20] if counterparty_inn else None,
                payment_purpose=str(payment_purpose)[:2000] if payment_purpose else None,
                status=BankTransactionStatusEnum.NEW,
                is_active=True,
            )
            db.add(transaction)
            return "created"

    @classmethod
    def start_contractors_sync(cls, user_id: int = None) -> str:
        """Start async contractors sync."""
        task_id = task_manager.create_task(
            task_type=cls.TASK_TYPE_CONTRACTORS,
            total=100,  # Will be updated
            metadata={"user_id": user_id}
        )

        task_manager.run_async_task(
            task_id,
            cls._sync_contractors_async
        )

        return task_id

    @classmethod
    async def _sync_contractors_async(cls, task_id: str) -> Dict[str, Any]:
        """Async worker for contractors sync."""
        db = SessionLocal()
        try:
            client = create_1c_client_from_env()

            task_manager.update_progress(task_id, 0, message="Подключение к 1С...")

            # Fetch contractors
            task_manager.update_progress(task_id, 10, message="Загрузка контрагентов...")
            contractors = client.get_contractors()

            total = len(contractors)
            task = task_manager.get_task(task_id)
            if task:
                task.total = total

            if total == 0:
                return {"success": True, "message": "Нет контрагентов", "total": 0}

            created = 0
            updated = 0
            errors = []

            for i, c in enumerate(contractors):
                try:
                    ref_key = c.get("Ref_Key")
                    name = c.get("Description") or c.get("НаименованиеПолное") or ""
                    inn = c.get("ИНН")

                    if not ref_key or not name:
                        continue

                    existing = db.query(Contractor).filter(
                        Contractor.external_id_1c == ref_key
                    ).first()

                    if existing:
                        existing.name = name[:500]
                        existing.inn = inn[:20] if inn else None
                        updated += 1
                    else:
                        contractor = Contractor(
                            name=name[:500],
                            inn=inn[:20] if inn else None,
                            external_id_1c=ref_key,
                            is_active=True,
                        )
                        db.add(contractor)
                        created += 1

                    # Commit every 100 items
                    if (i + 1) % 100 == 0:
                        try:
                            db.commit()
                        except Exception as commit_error:
                            logger.error(f"Commit error: {commit_error}")
                            db.rollback()
                            errors.append(f"Commit failed: {str(commit_error)}")

                    # Update progress every 50 items
                    if i % 50 == 0:
                        task_manager.update_progress(
                            task_id, i + 1,
                            message=f"Обработано {i + 1} из {total}"
                        )
                        await asyncio.sleep(0.01)

                except Exception as e:
                    errors.append(str(e))
                    logger.error(f"Error processing contractor: {e}")
                    db.rollback()

            # Final commit
            try:
                db.commit()
            except Exception as e:
                logger.error(f"Final commit error: {e}")
                db.rollback()
                errors.append(f"Final commit failed: {str(e)}")

            return {
                "success": True,
                "message": f"Контрагенты: {created} создано, {updated} обновлено",
                "total": total,
                "created": created,
                "updated": updated,
                "errors": errors[:10],
            }

        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
