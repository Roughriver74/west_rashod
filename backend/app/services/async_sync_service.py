"""Async synchronization service for background 1C imports."""
import logging
import asyncio
import signal
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Optional, Dict, Any, List, Callable
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.background_tasks import task_manager, TaskStatus
from app.services.odata_1c_client import create_1c_client_from_env
from app.services.bank_transaction_1c_import import BankTransaction1CImporter
from app.db.models import (
    BankTransaction, BankTransactionTypeEnum, BankTransactionStatusEnum,
    PaymentSourceEnum, Organization, Contractor,
    BudgetCategory, ExpenseTypeEnum
)

logger = logging.getLogger(__name__)


def with_timeout(func: Callable, timeout_seconds: int, *args, **kwargs):
    """
    Выполняет функцию с таймаутом. Если функция не завершится за timeout_seconds,
    выбрасывает TimeoutError.

    Args:
        func: Функция для выполнения
        timeout_seconds: Максимальное время выполнения в секундах
        *args, **kwargs: Аргументы для функции

    Returns:
        Результат выполнения функции

    Raises:
        TimeoutError: Если функция не завершилась за отведённое время
    """
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func, *args, **kwargs)

    try:
        result = future.result(timeout=timeout_seconds)
        return result
    except FuturesTimeoutError:
        # Попытка отменить задачу
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise TimeoutError(f"Функция {func.__name__} превысила таймаут {timeout_seconds} сек")
    finally:
        executor.shutdown(wait=False)


class AsyncSyncService:
    """Service for running sync operations in background."""

    TASK_TYPE_BANK_TRANSACTIONS = "sync_bank_transactions"
    TASK_TYPE_ORGANIZATIONS = "sync_organizations"
    TASK_TYPE_CATEGORIES = "sync_categories"
    TASK_TYPE_CONTRACTORS = "sync_contractors"
    TASK_TYPE_FULL_SYNC = "sync_full"

    @staticmethod
    def _set_task_total(task_id: str, total: int) -> None:
        """Safely set total items for progress calculation."""
        task = task_manager.get_task(task_id)
        if task:
            task.total = max(total, 1)

    @staticmethod
    def _fetch_bank_documents(client, date_from: date, date_to: date) -> List[tuple[str, Dict[str, Any]]]:
        """Fetch all bank-related documents from 1C with pagination."""
        all_docs: List[tuple[str, Dict[str, Any]]] = []

        # Fetch all receipts with pagination
        skip = 0
        while True:
            receipts = client.get_bank_receipts(date_from, date_to, top=1000, skip=skip)
            if not receipts:
                break
            all_docs.extend([("receipt", doc) for doc in receipts])
            skip += len(receipts)
            if len(receipts) < 1000:  # Last page
                break

        # Fetch all payments with pagination
        skip = 0
        while True:
            payments = client.get_bank_payments(date_from, date_to, top=1000, skip=skip)
            if not payments:
                break
            all_docs.extend([("payment", doc) for doc in payments])
            skip += len(payments)
            if len(payments) < 1000:  # Last page
                break

        # Fetch all cash receipts with pagination
        skip = 0
        while True:
            cash_receipts = client.get_cash_receipts(date_from, date_to, top=1000, skip=skip)
            if not cash_receipts:
                break
            all_docs.extend([("cash_receipt", doc) for doc in cash_receipts])
            skip += len(cash_receipts)
            if len(cash_receipts) < 1000:  # Last page
                break

        # Fetch all cash payments with pagination
        skip = 0
        while True:
            cash_payments = client.get_cash_payments(date_from, date_to, top=1000, skip=skip)
            if not cash_payments:
                break
            all_docs.extend([("cash_payment", doc) for doc in cash_payments])
            skip += len(cash_payments)
            if len(cash_payments) < 1000:  # Last page
                break

        return all_docs

    @classmethod
    async def _import_organizations(
        cls,
        task_id: str,
        db: Session,
        org_docs: List[Dict[str, Any]],
        processed_offset: int = 0,
        total_count: Optional[int] = None
    ) -> tuple[Dict[str, Any], int]:
        """Process organization documents and update progress."""
        total = len(org_docs)
        total_for_progress = total_count if total_count is not None else total
        cls._set_task_total(task_id, total_for_progress if total_for_progress else 1)

        if total == 0:
            message = "Нет организаций для синхронизации"
            task_manager.update_progress(task_id, processed_offset, message=message)
            return {
                "success": True,
                "message": message,
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": []
            }, processed_offset

        created = 0
        updated = 0
        errors: List[str] = []

        for i, org_doc in enumerate(org_docs):
            name = (
                org_doc.get("Description")
                or org_doc.get("НаименованиеПолное")
                or org_doc.get("НаименованиеСокращенное")
                or f"Организация {i + 1}"
            )
            try:
                ref_key = org_doc.get("Ref_Key")
                if not ref_key:
                    continue

                full_name = org_doc.get("НаименованиеПолное") or name
                short_name = org_doc.get("НаименованиеСокращенное") or name

                existing = db.query(Organization).filter(
                    Organization.external_id_1c == ref_key
                ).first()

                if not existing:
                    existing = db.query(Organization).filter(
                        Organization.name == name
                    ).first()

                if existing:
                    existing.name = name[:255]
                    existing.full_name = full_name[:500] if full_name else None
                    existing.short_name = short_name[:255] if short_name else None
                    existing.inn = org_doc.get("ИНН", existing.inn)
                    existing.kpp = org_doc.get("КПП", existing.kpp)
                    existing.external_id_1c = ref_key
                    existing.synced_at = datetime.utcnow()
                    updated += 1
                else:
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
                    db.flush()
                    created += 1

                if (i + 1) % 100 == 0:
                    try:
                        db.commit()
                    except Exception as commit_error:
                        logger.error(f"Commit error: {commit_error}")
                        db.rollback()
                        errors.append(f"Commit failed at {i + 1}: {str(commit_error)}")

                processed_value = processed_offset + i + 1
                if i % 20 == 0 or i == total - 1:
                    task_manager.update_progress(
                        task_id,
                        processed_value,
                        message=f"Организации: обработано {i + 1} из {total}"
                    )

                if i % 50 == 0:
                    await asyncio.sleep(0.01)

            except Exception as e:
                db.rollback()
                errors.append(f"Org '{name}': {str(e)}")
                logger.error(f"Error processing org '{name}': {e}")

        try:
            db.commit()
        except Exception as e:
            logger.error(f"Final commit error: {e}")
            db.rollback()
            errors.append(f"Final commit failed: {str(e)}")

        final_processed = processed_offset + total
        task_manager.update_progress(
            task_id,
            final_processed,
            message="Организации синхронизированы"
        )

        return {
            "success": True,
            "message": f"Организации: {created} создано, {updated} обновлено",
            "total": total,
            "created": created,
            "updated": updated,
            "errors": errors[:10],
        }, final_processed

    @classmethod
    async def _import_categories(
        cls,
        task_id: str,
        db: Session,
        cat_docs: List[Dict[str, Any]],
        processed_offset: int = 0,
        total_count: Optional[int] = None
    ) -> tuple[Dict[str, Any], int]:
        """Process category documents and update progress."""
        total = len(cat_docs)
        total_for_progress = total_count if total_count is not None else total
        cls._set_task_total(task_id, total_for_progress if total_for_progress else 1)

        if total == 0:
            message = "Нет категорий для синхронизации"
            task_manager.update_progress(task_id, processed_offset, message=message)
            return {
                "success": True,
                "message": message,
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": []
            }, processed_offset

        created = 0
        updated = 0
        errors: List[str] = []

        for i, cat_doc in enumerate(cat_docs):
            name = cat_doc.get("Description", "Unknown")
            try:
                ref_key = cat_doc.get("Ref_Key")
                if not ref_key:
                    continue

                existing = db.query(BudgetCategory).filter(
                    BudgetCategory.external_id_1c == ref_key
                ).first()

                if existing:
                    existing.name = name
                    updated += 1
                else:
                    cat = BudgetCategory(
                        name=name,
                        type=ExpenseTypeEnum.OPEX,
                        external_id_1c=ref_key,
                        is_folder=cat_doc.get("IsFolder", False)
                    )
                    db.add(cat)
                    db.flush()
                    created += 1

                if (i + 1) % 100 == 0:
                    try:
                        db.commit()
                    except Exception as commit_error:
                        logger.error(f"Commit error: {commit_error}")
                        db.rollback()
                        errors.append(f"Commit failed at {i + 1}: {str(commit_error)}")

                processed_value = processed_offset + i + 1
                if i % 20 == 0 or i == total - 1:
                    task_manager.update_progress(
                        task_id,
                        processed_value,
                        message=f"Категории: обработано {i + 1} из {total}"
                    )

                if i % 50 == 0:
                    await asyncio.sleep(0.01)

            except Exception as e:
                db.rollback()
                errors.append(f"Cat '{name}': {str(e)}")
                logger.error(f"Error processing category '{name}': {e}")

        try:
            db.commit()
        except Exception as e:
            logger.error(f"Final commit error: {e}")
            db.rollback()
            errors.append(f"Final commit failed: {str(e)}")

        final_processed = processed_offset + total
        task_manager.update_progress(
            task_id,
            final_processed,
            message="Категории синхронизированы"
        )

        return {
            "success": True,
            "message": f"Категории: {created} создано, {updated} обновлено",
            "total": total,
            "created": created,
            "updated": updated,
            "errors": errors[:10],
        }, final_processed

    @classmethod
    async def _import_bank_documents(
        cls,
        task_id: str,
        db: Session,
        importer: BankTransaction1CImporter,
        all_docs: List[tuple[str, Dict[str, Any]]],
        processed_offset: int = 0,
        total_count: Optional[int] = None
    ) -> tuple[Dict[str, Any], int]:
        """Process bank documents and update progress."""
        total_docs = len(all_docs)
        total_for_progress = total_count if total_count is not None else total_docs
        cls._set_task_total(task_id, total_for_progress if total_for_progress else 1)

        if total_docs == 0:
            message = "Нет данных для импорта"
            task_manager.update_progress(task_id, processed_offset, message=message)
            return {
                "success": True,
                "message": message,
                "total_fetched": 0,
                "total_created": 0,
                "total_updated": 0,
                "total_skipped": 0,
                "errors": [],
            }, processed_offset

        created = 0
        updated = 0
        skipped = 0
        errors: List[str] = []

        # Увеличенный размер батча для более эффективных коммитов
        batch_size = 500
        last_commit_index = 0

        logger.info(f"Starting import of {total_docs} bank documents (batch size: {batch_size})")

        for i, (doc_type, doc) in enumerate(all_docs):
            try:
                # Проверка отмены задачи
                task = task_manager.get_task(task_id)
                if task and task.status == TaskStatus.CANCELLED:
                    logger.info(f"Task {task_id} was cancelled by user at {i + 1}/{total_docs}")
                    break

                # Обработка документа с таймаутом 90 секунд
                # Если обработка зависнет, документ будет пропущен
                try:
                    result = with_timeout(
                        cls._process_document,
                        90,  # Таймаут 90 секунд (учитывая retry в HTTP-запросах)
                        db, importer, doc_type, doc
                    )
                    if result == "created":
                        created += 1
                    elif result == "updated":
                        updated += 1
                    else:
                        skipped += 1
                except TimeoutError as timeout_err:
                    logger.warning(f"Document {i + 1} ({doc_type}) timeout: {timeout_err}")
                    errors.append(f"Document {i + 1} ({doc_type}): timeout after 90 seconds")
                    skipped += 1
                    # Продолжаем обработку следующего документа

                # Коммит каждые batch_size записей
                if (i + 1) % batch_size == 0:
                    try:
                        db.commit()
                        last_commit_index = i + 1
                        logger.info(f"Committed batch at {i + 1}/{total_docs} ({created} created, {updated} updated, {skipped} skipped)")
                    except Exception as commit_error:
                        logger.error(f"Commit error at item {i + 1}: {commit_error}", exc_info=True)
                        db.rollback()
                        errors.append(f"Commit failed at {i + 1}: {str(commit_error)}")
                        # Продолжаем обработку после ошибки коммита

                # Обновление прогресса каждые 50 записей или на последней записи
                if i % 50 == 0 or i == total_docs - 1:
                    processed_value = processed_offset + i + 1
                    percent = int((i + 1) / total_docs * 100)
                    message = f"Обработано {i + 1}/{total_docs} ({percent}%) - создано: {created}, обновлено: {updated}, пропущено: {skipped}"
                    task_manager.update_progress(
                        task_id,
                        processed_value,
                        message=message
                    )

                    # Логирование каждые 500 записей для отслеживания прогресса
                    if (i + 1) % 500 == 0:
                        logger.info(f"Progress: {message}")

                # Небольшая пауза для разгрузки event loop
                if i % 100 == 0:
                    await asyncio.sleep(0.001)

            except Exception as e:
                # КРИТИЧНО: НЕ делаем rollback здесь - это блокирует всю обработку
                # Просто логируем ошибку и пропускаем проблемный документ
                error_msg = f"Document {i + 1} ({doc_type}): {str(e)}"
                errors.append(error_msg)
                logger.error(f"Error processing {error_msg}", exc_info=True)
                skipped += 1
                # Продолжаем обработку следующего документа

        # Финальный коммит для оставшихся записей
        try:
            if last_commit_index < total_docs:
                db.commit()
                logger.info(f"Final commit: total {created} created, {updated} updated, {skipped} skipped")
        except Exception as e:
            logger.error(f"Final commit error: {e}", exc_info=True)
            db.rollback()
            errors.append(f"Final commit failed: {str(e)}")

        final_processed = processed_offset + total_docs
        final_message = f"Завершено: {created} создано, {updated} обновлено, {skipped} пропущено"
        task_manager.update_progress(
            task_id,
            final_processed,
            message=final_message
        )

        logger.info(f"Import complete: {final_message}, {len(errors)} errors")

        return {
            "success": True,
            "message": f"Импорт завершён: {created} создано, {updated} обновлено, {skipped} пропущено",
            "total_fetched": total_docs,
            "total_created": created,
            "total_updated": updated,
            "total_skipped": skipped,
            "errors": errors[:10],  # Limit errors
        }, final_processed

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
                raise Exception(f"Не удалось подключиться к 1С OData: {message}")

            task_manager.update_progress(
                task_id, 0,
                message="Получение данных из 1С..."
            )

            all_docs = cls._fetch_bank_documents(client, date_from, date_to)
            total_docs = len(all_docs)
            cls._set_task_total(task_id, total_docs or 1)

            if total_docs == 0:
                message = "Нет данных для импорта"
                task_manager.update_progress(task_id, 1, message=message)
                return {
                    "success": True,
                    "message": message,
                    "total_fetched": 0,
                    "total_created": 0,
                    "total_updated": 0,
                    "total_skipped": 0,
                    "errors": [],
                }

            importer = BankTransaction1CImporter(
                db=db,
                odata_client=client,
                auto_classify=auto_classify
            )

            result, _ = await cls._import_bank_documents(
                task_id,
                db,
                importer,
                all_docs,
                processed_offset=0,
                total_count=total_docs
            )

            # Обновить банковскую информацию в транзакциях
            task_manager.update_progress(task_id, total_docs, message="Обновление банковской информации...")
            from app.services.bank_info_updater import update_transactions_bank_info
            bank_stats = update_transactions_bank_info(db, client)
            logger.info(f"Bank info update: {bank_stats}")

            # Добавить статистику банков в result
            result["bank_info_updated"] = bank_stats.get('updated', 0)
            result["bank_info_errors"] = bank_stats.get('errors', 0)
            if bank_stats.get('updated', 0) > 0:
                result["message"] = f"{result['message']}. Обновлено банков: {bank_stats.get('updated', 0)}"

            return result

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
        """Process a single document using importer methods.

        Returns 'created', 'updated', or 'skipped'.
        """
        ref_key = doc.get("Ref_Key")
        if not ref_key:
            logger.debug("Skipping document without Ref_Key")
            return "skipped"

        try:
            # Check if exists
            existing = db.query(BankTransaction).filter(
                BankTransaction.external_id_1c == ref_key
            ).first()

            # Parse amount
            amount = Decimal(str(doc.get("СуммаДокумента", 0) or 0))
            if amount == 0:
                logger.debug(f"Skipping document {ref_key} with zero amount")
                return "skipped"

            # Use importer's parsing methods for correct data extraction
            try:
                if doc_type == "receipt":
                    transaction_data = importer._parse_receipt_data(doc)
                    tx_type = BankTransactionTypeEnum.CREDIT
                    payment_source = PaymentSourceEnum.BANK
                elif doc_type == "payment":
                    transaction_data = importer._parse_payment_data(doc)
                    tx_type = BankTransactionTypeEnum.DEBIT
                    payment_source = PaymentSourceEnum.BANK
                elif doc_type == "cash_receipt":
                    transaction_data = importer._parse_cash_receipt_data(doc)
                    tx_type = BankTransactionTypeEnum.CREDIT
                    payment_source = PaymentSourceEnum.CASH
                elif doc_type == "cash_payment":
                    transaction_data = importer._parse_cash_payment_data(doc)
                    tx_type = BankTransactionTypeEnum.DEBIT
                    payment_source = PaymentSourceEnum.CASH
                else:
                    logger.warning(f"Unknown document type: {doc_type}")
                    return "skipped"
            except Exception as e:
                logger.warning(f"Failed to parse document {ref_key} ({doc_type}): {e}")
                return "skipped"

            if not transaction_data.get('transaction_date'):
                logger.debug(f"Skipping document {ref_key} without transaction date")
                return "skipped"

            # Ensure business_operation mapping exists (с использованием кэша импортера)
            if transaction_data.get('business_operation'):
                from app.db.models import BusinessOperationMapping
                business_op = transaction_data['business_operation']

                # Используем кэш импортера вместо прямого запроса к БД
                if business_op not in importer._business_operation_mapping_cache:
                    existing_mapping = db.query(BusinessOperationMapping).filter(
                        BusinessOperationMapping.business_operation == business_op
                    ).first()

                    if not existing_mapping:
                        stub_mapping = BusinessOperationMapping(
                            business_operation=business_op,
                            category_id=None,
                            priority=0,
                            confidence=0.0,
                            notes="Авто-создано при импорте из 1С",
                            is_active=False
                        )
                        db.add(stub_mapping)
                        db.flush()

                    # Добавляем в кэш
                    importer._business_operation_mapping_cache.add(business_op)

            if existing:
                # Update existing transaction with parsed data
                # Защищенные поля - не перезаписываем пользовательские изменения
                protected_fields = {
                    'status', 'category_id', 'suggested_category_id',
                    'category_confidence', 'approved_by', 'approved_at',
                    'expense_id', 'notes'
                }

                for key, value in transaction_data.items():
                    if key in protected_fields:
                        # Для notes - обновляем только если пусто
                        if key == 'notes' and not getattr(existing, key, None):
                            setattr(existing, key, value)
                        continue
                    if hasattr(existing, key) and value is not None:
                        setattr(existing, key, value)

                logger.debug(f"Updated transaction {ref_key}")
                return "updated"
            else:
                # Create new transaction
                transaction_data['external_id_1c'] = ref_key
                transaction_data['transaction_type'] = tx_type
                transaction_data['payment_source'] = payment_source
                transaction_data['import_source'] = 'ODATA_1C'
                transaction_data['imported_at'] = datetime.utcnow()
                transaction_data['is_active'] = True

                transaction = BankTransaction(**transaction_data)

                # Apply classification if enabled
                # RULES auto-apply, AI only suggests
                if importer.auto_classify and importer.classifier:
                    try:
                        category_id, confidence, reasoning, is_rule_based = importer.classifier.classify(
                            payment_purpose=transaction.payment_purpose,
                            counterparty_name=transaction.counterparty_name,
                            counterparty_inn=transaction.counterparty_inn,
                            amount=transaction.amount,
                            transaction_type=transaction.transaction_type,
                            business_operation=transaction.business_operation
                        )
                        if category_id:
                            if is_rule_based:
                                # RULE: auto-apply category
                                transaction.category_id = category_id
                                transaction.category_confidence = Decimal(str(confidence))
                                transaction.status = BankTransactionStatusEnum.CATEGORIZED
                            else:
                                # AI HEURISTIC: only suggest
                                transaction.suggested_category_id = category_id
                                transaction.category_confidence = Decimal(str(confidence))
                                transaction.status = BankTransactionStatusEnum.NEEDS_REVIEW
                    except Exception as e:
                        logger.warning(f"Classification failed for {ref_key}: {e}")

                db.add(transaction)
                logger.debug(f"Created transaction {ref_key}")
                return "created"

        except Exception as e:
            # ВАЖНО: НЕ делаем rollback и НЕ пробрасываем исключение
            # Это блокирует обработку всего батча
            # Вместо этого логируем ошибку и возвращаем "skipped"
            logger.error(f"Error processing document {ref_key} ({doc_type}): {e}", exc_info=True)
            return "skipped"

    @classmethod
    def start_organizations_sync(cls, user_id: int = None) -> str:
        """Start async organizations sync."""
        task_id = task_manager.create_task(
            task_type=cls.TASK_TYPE_ORGANIZATIONS,
            total=0,
            metadata={"user_id": user_id}
        )

        task_manager.run_async_task(
            task_id,
            cls._sync_organizations_async,
        )

        return task_id

    @classmethod
    async def _sync_organizations_async(cls, task_id: str) -> Dict[str, Any]:
        """Async worker for organizations sync."""
        db = SessionLocal()
        try:
            client = create_1c_client_from_env()

            task_manager.update_progress(task_id, 0, message="Подключение к 1С...")
            is_connected, message = client.test_connection()
            if not is_connected:
                raise Exception(f"Не удалось подключиться к 1С: {message}")

            task_manager.update_progress(task_id, 0, message="Загрузка организаций из 1С...")
            org_docs = client.get_organizations()

            result, _ = await cls._import_organizations(
                task_id,
                db,
                org_docs,
                processed_offset=0,
                total_count=len(org_docs)
            )

            # Обновить банковскую информацию в транзакциях
            task_manager.update_progress(task_id, len(org_docs), message="Обновление банковской информации...")
            from app.services.bank_info_updater import update_transactions_bank_info
            bank_stats = update_transactions_bank_info(db, client)
            logger.info(f"Bank info update: {bank_stats}")

            # Добавить статистику банков в result
            result["bank_info_updated"] = bank_stats.get('updated', 0)
            result["bank_info_errors"] = bank_stats.get('errors', 0)
            result["message"] = f"{result['message']}. Обновлено банков: {bank_stats.get('updated', 0)}"

            return result

        except Exception:
            db.rollback()
            logger.exception("Async organizations sync failed")
            raise
        finally:
            db.close()

    @classmethod
    def start_categories_sync(cls, user_id: int = None) -> str:
        """Start async categories sync."""
        task_id = task_manager.create_task(
            task_type=cls.TASK_TYPE_CATEGORIES,
            total=0,
            metadata={"user_id": user_id}
        )

        task_manager.run_async_task(
            task_id,
            cls._sync_categories_async,
        )

        return task_id

    @classmethod
    async def _sync_categories_async(cls, task_id: str) -> Dict[str, Any]:
        """Async worker for categories sync."""
        db = SessionLocal()
        try:
            client = create_1c_client_from_env()

            task_manager.update_progress(task_id, 0, message="Подключение к 1С...")
            is_connected, message = client.test_connection()
            if not is_connected:
                raise Exception(f"Не удалось подключиться к 1С: {message}")

            task_manager.update_progress(task_id, 0, message="Загрузка категорий из 1С...")
            cat_docs = client.get_cash_flow_categories()

            result, _ = await cls._import_categories(
                task_id,
                db,
                cat_docs,
                processed_offset=0,
                total_count=len(cat_docs)
            )

            return result

        except Exception:
            db.rollback()
            logger.exception("Async categories sync failed")
            raise
        finally:
            db.close()

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
            cls._set_task_total(task_id, total or 1)

            if total == 0:
                task_manager.update_progress(task_id, total or 1, message="Нет контрагентов")
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

    @classmethod
    def start_full_sync(
        cls,
        date_from: date,
        date_to: date,
        auto_classify: bool = True,
        user_id: int = None
    ) -> str:
        """Start full async sync (organizations, categories, transactions)."""
        task_id = task_manager.create_task(
            task_type=cls.TASK_TYPE_FULL_SYNC,
            total=0,
            metadata={
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "auto_classify": auto_classify,
                "user_id": user_id,
            }
        )

        task_manager.run_async_task(
            task_id,
            cls._sync_full_async,
            date_from=date_from,
            date_to=date_to,
            auto_classify=auto_classify
        )

        return task_id

    @classmethod
    async def _sync_full_async(
        cls,
        task_id: str,
        date_from: date,
        date_to: date,
        auto_classify: bool
    ) -> Dict[str, Any]:
        """Async worker for full sync."""
        db = SessionLocal()
        try:
            client = create_1c_client_from_env()
            task_manager.update_progress(task_id, 0, message="Подключение к 1С...")

            is_connected, message = client.test_connection()
            if not is_connected:
                raise Exception(f"Не удалось подключиться к 1С: {message}")

            task_manager.update_progress(task_id, 0, message="Загрузка данных из 1С...")
            org_docs = client.get_organizations()
            cat_docs = client.get_cash_flow_categories()
            bank_docs = cls._fetch_bank_documents(client, date_from, date_to)

            total_count = len(org_docs) + len(cat_docs) + len(bank_docs)
            total_for_progress = max(total_count, 1)
            cls._set_task_total(task_id, total_for_progress)

            if total_count == 0:
                task_manager.update_progress(task_id, total_for_progress, message="Нет данных для синхронизации")
                return {
                    "success": True,
                    "message": "Нет данных для синхронизации",
                    "organizations": {"total": 0, "created": 0, "updated": 0},
                    "categories": {"total": 0, "created": 0, "updated": 0},
                    "transactions": {
                        "total_fetched": 0,
                        "total_created": 0,
                        "total_updated": 0,
                        "total_skipped": 0,
                        "errors": [],
                    },
                }

            processed = 0

            org_result, processed = await cls._import_organizations(
                task_id,
                db,
                org_docs,
                processed_offset=processed,
                total_count=total_for_progress
            )

            cat_result, processed = await cls._import_categories(
                task_id,
                db,
                cat_docs,
                processed_offset=processed,
                total_count=total_for_progress
            )

            importer = BankTransaction1CImporter(
                db=db,
                odata_client=client,
                auto_classify=auto_classify
            )

            bank_result, processed = await cls._import_bank_documents(
                task_id,
                db,
                importer,
                bank_docs,
                processed_offset=processed,
                total_count=total_for_progress
            )

            # Обновить банковскую информацию в транзакциях
            task_manager.update_progress(task_id, processed, message="Обновление банковской информации...")
            from app.services.bank_info_updater import update_transactions_bank_info
            bank_stats = update_transactions_bank_info(db, client)
            logger.info(f"Bank info update: {bank_stats}")

            # Добавить статистику банков в результат транзакций
            bank_result["bank_info_updated"] = bank_stats.get('updated', 0)
            bank_result["bank_info_errors"] = bank_stats.get('errors', 0)

            final_message = "Полная синхронизация завершена"
            if bank_stats.get('updated', 0) > 0:
                final_message += f". Обновлено банков: {bank_stats.get('updated', 0)}"

            task_manager.update_progress(task_id, processed, message=final_message)

            return {
                "success": True,
                "message": final_message,
                "organizations": org_result,
                "categories": cat_result,
                "transactions": bank_result,
            }

        except Exception:
            db.rollback()
            logger.exception("Full sync failed")
            raise
        finally:
            db.close()
