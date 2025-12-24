"""
1C Bank Transactions Import Service

Сервис для импорта банковских операций из 1С через OData
"""

import logging
import re
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.db.models import (
    BankTransaction,
    BankTransactionTypeEnum,
    BankTransactionStatusEnum,
    PaymentSourceEnum,
    DocumentTypeEnum,
    Organization,
    Contractor,
    BusinessOperationMapping
)
from app.services.odata_1c_client import OData1CClient
from app.services.transaction_classifier import TransactionClassifier

logger = logging.getLogger(__name__)


class BankTransaction1CImportResult:
    """Результат импорта банковских операций из 1С"""

    def __init__(self):
        self.success = True
        self.message = ""
        self.total_fetched = 0  # Получено из 1С
        self.total_processed = 0  # Обработано
        self.total_created = 0  # Создано новых
        self.total_updated = 0  # Обновлено существующих
        self.total_skipped = 0  # Пропущено (дубликаты)
        self.auto_categorized = 0  # Автоматически категоризировано
        self.auto_stubs_created = 0  # Автоматически создано stub-маппингов
        self.receipts_created = 0  # Поступлений создано
        self.payments_created = 0  # Списаний создано
        self.cash_receipts_created = 0  # ПКО создано
        self.cash_payments_created = 0  # РКО создано
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_fetched': self.total_fetched,
            'total_processed': self.total_processed,
            'total_created': self.total_created,
            'total_updated': self.total_updated,
            'total_skipped': self.total_skipped,
            'auto_categorized': self.auto_categorized,
            'auto_stubs_created': self.auto_stubs_created,
            'errors': self.errors
        }


class BankTransaction1CImporter:
    """Импортер банковских операций из 1С"""

    def __init__(
        self,
        db: Session,
        odata_client: OData1CClient,
        auto_classify: bool = True
    ):
        """
        Initialize importer

        Args:
            db: Database session
            odata_client: 1C OData client
            auto_classify: Apply AI classification automatically
        """
        self.db = db
        self.odata_client = odata_client
        self.auto_classify = auto_classify

        if auto_classify:
            self.classifier = TransactionClassifier(db)
        else:
            self.classifier = None

        # Кэши для оптимизации производительности
        self._organization_cache: Dict[str, Optional[Organization]] = {}
        self._bank_account_cache: Dict[str, tuple[Optional[str], Optional[str], Optional[str]]] = {}
        self._counterparty_cache: Dict[str, Dict[str, Any]] = {}
        self._business_operation_mapping_cache: set = set()

        # Предзагрузка существующих маппингов бизнес-операций
        self._preload_business_operation_mappings()

    def _preload_business_operation_mappings(self):
        """Предзагрузка существующих маппингов бизнес-операций для быстрой проверки"""
        try:
            existing_mappings = self.db.query(BusinessOperationMapping.business_operation).all()
            self._business_operation_mapping_cache = {m[0] for m in existing_mappings if m[0]}
            logger.debug(f"Preloaded {len(self._business_operation_mapping_cache)} business operation mappings")
        except Exception as e:
            logger.warning(f"Failed to preload business operation mappings: {e}")

    def import_transactions(
        self,
        date_from: date,
        date_to: date,
        batch_size: int = 100
    ) -> BankTransaction1CImportResult:
        """
        Импортировать банковские операции из 1С за период

        Args:
            date_from: Начальная дата периода
            date_to: Конечная дата периода
            batch_size: Размер батча для запроса к 1С

        Returns:
            Результат импорта
        """
        result = BankTransaction1CImportResult()

        logger.info(
            f"Starting 1C import: date_from={date_from}, date_to={date_to}, "
            f"auto_classify={self.auto_classify}"
        )

        try:
            # Импорт поступлений безналичных (CREDIT, BANK)
            receipts_result = self._import_receipts(date_from, date_to, batch_size)
            result.total_fetched += receipts_result.total_fetched
            result.total_processed += receipts_result.total_processed
            result.total_created += receipts_result.total_created
            result.total_updated += receipts_result.total_updated
            result.total_skipped += receipts_result.total_skipped
            result.auto_categorized += receipts_result.auto_categorized
            result.receipts_created = receipts_result.total_created
            result.errors.extend(receipts_result.errors)

            # Импорт списаний безналичных (DEBIT, BANK)
            payments_result = self._import_payments(date_from, date_to, batch_size)
            result.total_fetched += payments_result.total_fetched
            result.total_processed += payments_result.total_processed
            result.total_created += payments_result.total_created
            result.total_updated += payments_result.total_updated
            result.total_skipped += payments_result.total_skipped
            result.auto_categorized += payments_result.auto_categorized
            result.payments_created = payments_result.total_created
            result.errors.extend(payments_result.errors)

            # Импорт кассовых поступлений (CREDIT, CASH) - ПКО
            cash_receipts_result = self._import_cash_receipts(date_from, date_to, batch_size)
            result.total_fetched += cash_receipts_result.total_fetched
            result.total_processed += cash_receipts_result.total_processed
            result.total_created += cash_receipts_result.total_created
            result.total_updated += cash_receipts_result.total_updated
            result.total_skipped += cash_receipts_result.total_skipped
            result.auto_categorized += cash_receipts_result.auto_categorized
            result.cash_receipts_created = cash_receipts_result.total_created
            result.errors.extend(cash_receipts_result.errors)

            # Импорт кассовых списаний (DEBIT, CASH) - РКО
            cash_payments_result = self._import_cash_payments(date_from, date_to, batch_size)
            result.total_fetched += cash_payments_result.total_fetched
            result.total_processed += cash_payments_result.total_processed
            result.total_created += cash_payments_result.total_created
            result.total_updated += cash_payments_result.total_updated
            result.total_skipped += cash_payments_result.total_skipped
            result.auto_categorized += cash_payments_result.auto_categorized
            result.cash_payments_created = cash_payments_result.total_created
            result.errors.extend(cash_payments_result.errors)

            # Set success and message
            result.success = True
            result.message = f"Импорт завершён: {result.total_created} создано, {result.total_updated} обновлено"
            logger.info(f"1C import completed: {result.to_dict()}")

        except Exception as e:
            logger.error(f"1C import failed: {e}", exc_info=True)
            result.success = False
            result.message = f"Ошибка импорта: {str(e)}"
            result.errors.append(f"Import failed: {str(e)}")

        return result

    def _import_receipts(
        self,
        date_from: date,
        date_to: date,
        batch_size: int
    ) -> BankTransaction1CImportResult:
        """Импорт поступлений (CREDIT)"""
        result = BankTransaction1CImportResult()
        skip = 0

        while True:
            try:
                receipts = self.odata_client.get_bank_receipts(
                    date_from=date_from,
                    date_to=date_to,
                    top=batch_size,
                    skip=skip
                )

                if not receipts:
                    break

                result.total_fetched += len(receipts)

                for receipt in receipts:
                    try:
                        self._process_receipt(receipt, result)
                    except Exception as e:
                        error_msg = f"Failed to process receipt {receipt.get('Ref_Key')}: {str(e)}"
                        logger.error(error_msg)
                        result.errors.append(error_msg)

                self.db.commit()

                if len(receipts) < batch_size:
                    break

                skip += batch_size

            except Exception as e:
                logger.error(f"Failed to fetch receipts batch (skip={skip}): {e}")
                result.errors.append(f"Failed to fetch receipts: {str(e)}")
                break

        return result

    def _import_payments(
        self,
        date_from: date,
        date_to: date,
        batch_size: int
    ) -> BankTransaction1CImportResult:
        """Импорт списаний (DEBIT)"""
        result = BankTransaction1CImportResult()
        skip = 0

        while True:
            try:
                payments = self.odata_client.get_bank_payments(
                    date_from=date_from,
                    date_to=date_to,
                    top=batch_size,
                    skip=skip
                )

                if not payments:
                    break

                result.total_fetched += len(payments)

                for payment in payments:
                    try:
                        self._process_payment(payment, result)
                    except Exception as e:
                        error_msg = f"Failed to process payment {payment.get('Ref_Key')}: {str(e)}"
                        logger.error(error_msg)
                        result.errors.append(error_msg)

                self.db.commit()

                if len(payments) < batch_size:
                    break

                skip += batch_size

            except Exception as e:
                logger.error(f"Failed to fetch payments batch (skip={skip}): {e}")
                result.errors.append(f"Failed to fetch payments: {str(e)}")
                break

        return result

    def _import_cash_receipts(
        self,
        date_from: date,
        date_to: date,
        batch_size: int
    ) -> BankTransaction1CImportResult:
        """Импорт кассовых поступлений (ПКО)"""
        result = BankTransaction1CImportResult()
        skip = 0

        while True:
            try:
                cash_receipts = self.odata_client.get_cash_receipts(
                    date_from=date_from,
                    date_to=date_to,
                    top=batch_size,
                    skip=skip
                )

                if not cash_receipts:
                    break

                result.total_fetched += len(cash_receipts)

                for cash_receipt in cash_receipts:
                    try:
                        self._process_cash_receipt(cash_receipt, result)
                    except Exception as e:
                        error_msg = f"Failed to process cash receipt {cash_receipt.get('Ref_Key')}: {str(e)}"
                        logger.error(error_msg)
                        result.errors.append(error_msg)

                self.db.commit()

                if len(cash_receipts) < batch_size:
                    break

                skip += batch_size

            except Exception as e:
                logger.error(f"Failed to fetch cash receipts batch (skip={skip}): {e}")
                result.errors.append(f"Failed to fetch cash receipts: {str(e)}")
                break

        return result

    def _import_cash_payments(
        self,
        date_from: date,
        date_to: date,
        batch_size: int
    ) -> BankTransaction1CImportResult:
        """Импорт кассовых списаний (РКО)"""
        result = BankTransaction1CImportResult()
        skip = 0

        while True:
            try:
                cash_payments = self.odata_client.get_cash_payments(
                    date_from=date_from,
                    date_to=date_to,
                    top=batch_size,
                    skip=skip
                )

                if not cash_payments:
                    break

                result.total_fetched += len(cash_payments)

                for cash_payment in cash_payments:
                    try:
                        self._process_cash_payment(cash_payment, result)
                    except Exception as e:
                        error_msg = f"Failed to process cash payment {cash_payment.get('Ref_Key')}: {str(e)}"
                        logger.error(error_msg)
                        result.errors.append(error_msg)

                self.db.commit()

                if len(cash_payments) < batch_size:
                    break

                skip += batch_size

            except Exception as e:
                logger.error(f"Failed to fetch cash payments batch (skip={skip}): {e}")
                result.errors.append(f"Failed to fetch cash payments: {str(e)}")
                break

        return result

    def _process_receipt(
        self,
        receipt_data: Dict[str, Any],
        result: BankTransaction1CImportResult
    ):
        """Обработать одно поступление"""
        external_id = receipt_data.get('Ref_Key')

        if not external_id:
            raise ValueError("Missing Ref_Key in receipt data")

        existing = self.db.query(BankTransaction).filter(
            BankTransaction.external_id_1c == external_id
        ).first()

        transaction_data = self._parse_receipt_data(receipt_data)

        if transaction_data.get('business_operation'):
            self._ensure_business_operation_mapping_exists(
                transaction_data['business_operation'],
                result
            )

        if existing:
            # Обновляем ТОЛЬКО данные из 1С, сохраняя пользовательские поля
            self._update_transaction_from_1c(existing, transaction_data)
            result.total_updated += 1
            logger.debug(f"Updated receipt {external_id}")

        else:
            transaction_data['external_id_1c'] = external_id
            transaction_data['transaction_type'] = BankTransactionTypeEnum.CREDIT
            transaction_data['import_source'] = 'ODATA_1C'
            transaction_data['imported_at'] = datetime.utcnow()

            transaction = BankTransaction(**transaction_data)

            if self.auto_classify and self.classifier:
                self._apply_classification(transaction)
                if transaction.category_id:
                    result.auto_categorized += 1

            self.db.add(transaction)
            result.total_created += 1
            logger.debug(f"Created receipt {external_id}")

        result.total_processed += 1

    def _process_payment(
        self,
        payment_data: Dict[str, Any],
        result: BankTransaction1CImportResult
    ):
        """Обработать одно списание"""
        external_id = payment_data.get('Ref_Key')

        if not external_id:
            raise ValueError("Missing Ref_Key in payment data")

        existing = self.db.query(BankTransaction).filter(
            BankTransaction.external_id_1c == external_id
        ).first()

        transaction_data = self._parse_payment_data(payment_data)

        if transaction_data.get('business_operation'):
            self._ensure_business_operation_mapping_exists(
                transaction_data['business_operation'],
                result
            )

        if existing:
            # Обновляем ТОЛЬКО данные из 1С, сохраняя пользовательские поля
            self._update_transaction_from_1c(existing, transaction_data)
            result.total_updated += 1
            logger.debug(f"Updated payment {external_id}")

        else:
            transaction_data['external_id_1c'] = external_id
            transaction_data['transaction_type'] = BankTransactionTypeEnum.DEBIT
            transaction_data['import_source'] = 'ODATA_1C'
            transaction_data['imported_at'] = datetime.utcnow()

            transaction = BankTransaction(**transaction_data)

            if self.auto_classify and self.classifier:
                self._apply_classification(transaction)
                if transaction.category_id:
                    result.auto_categorized += 1

            self.db.add(transaction)
            result.total_created += 1
            logger.debug(f"Created payment {external_id}")

        result.total_processed += 1

    def _process_cash_receipt(
        self,
        receipt_data: Dict[str, Any],
        result: BankTransaction1CImportResult
    ):
        """Обработать один приходный кассовый ордер (ПКО)"""
        external_id = receipt_data.get('Ref_Key')

        if not external_id:
            raise ValueError("Missing Ref_Key in cash receipt data")

        existing = self.db.query(BankTransaction).filter(
            BankTransaction.external_id_1c == external_id
        ).first()

        transaction_data = self._parse_cash_receipt_data(receipt_data)

        if transaction_data.get('business_operation'):
            self._ensure_business_operation_mapping_exists(
                transaction_data['business_operation'],
                result
            )

        if existing:
            # Обновляем ТОЛЬКО данные из 1С, сохраняя пользовательские поля
            self._update_transaction_from_1c(existing, transaction_data)
            result.total_updated += 1
            logger.debug(f"Updated cash receipt (PKO) {external_id}")

        else:
            transaction_data['external_id_1c'] = external_id
            transaction_data['transaction_type'] = BankTransactionTypeEnum.CREDIT
            transaction_data['import_source'] = 'ODATA_1C'
            transaction_data['imported_at'] = datetime.utcnow()

            transaction = BankTransaction(**transaction_data)

            if self.auto_classify and self.classifier:
                self._apply_classification(transaction)
                if transaction.category_id:
                    result.auto_categorized += 1

            self.db.add(transaction)
            result.total_created += 1
            logger.debug(f"Created cash receipt (PKO) {external_id}")

        result.total_processed += 1

    def _process_cash_payment(
        self,
        payment_data: Dict[str, Any],
        result: BankTransaction1CImportResult
    ):
        """Обработать один расходный кассовый ордер (РКО)"""
        external_id = payment_data.get('Ref_Key')

        if not external_id:
            raise ValueError("Missing Ref_Key in cash payment data")

        existing = self.db.query(BankTransaction).filter(
            BankTransaction.external_id_1c == external_id
        ).first()

        transaction_data = self._parse_cash_payment_data(payment_data)

        if transaction_data.get('business_operation'):
            self._ensure_business_operation_mapping_exists(
                transaction_data['business_operation'],
                result
            )

        if existing:
            # Обновляем ТОЛЬКО данные из 1С, сохраняя пользовательские поля
            self._update_transaction_from_1c(existing, transaction_data)
            result.total_updated += 1
            logger.debug(f"Updated cash payment (RKO) {external_id}")

        else:
            transaction_data['external_id_1c'] = external_id
            transaction_data['transaction_type'] = BankTransactionTypeEnum.DEBIT
            transaction_data['import_source'] = 'ODATA_1C'
            transaction_data['imported_at'] = datetime.utcnow()

            transaction = BankTransaction(**transaction_data)

            if self.auto_classify and self.classifier:
                self._apply_classification(transaction)
                if transaction.category_id:
                    result.auto_categorized += 1

            self.db.add(transaction)
            result.total_created += 1
            logger.debug(f"Created cash payment (RKO) {external_id}")

        result.total_processed += 1

    def _update_transaction_from_1c(
        self,
        existing: BankTransaction,
        transaction_data: Dict[str, Any]
    ) -> None:
        """
        Обновляет существующую транзакцию данными из 1С,
        НЕ затирая пользовательские поля (категория, статус, confidence и т.д.)
        """
        # Поля, которые НЕЛЬЗЯ перезаписывать - это пользовательские данные
        protected_fields = {
            'status',                    # Статус обработки (NEW, CATEGORIZED, APPROVED и т.д.)
            'category_id',               # Назначенная категория
            'suggested_category_id',     # Предложенная категория
            'category_confidence',       # Уверенность классификации
            'approved_by',               # Кто подтвердил
            'approved_at',               # Когда подтверждено
            'expense_id',                # Связь с заявкой на расход
            'notes',                     # Пользовательские заметки (если уже есть)
        }

        # Поля из 1С, которые можно обновлять
        for key, value in transaction_data.items():
            if key in protected_fields:
                # Для notes - обновляем только если в существующей записи пусто
                if key == 'notes' and not getattr(existing, key, None):
                    setattr(existing, key, value)
                continue
            setattr(existing, key, value)

    def _parse_receipt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг данных поступления из 1С в формат BankTransaction"""
        date_str = data.get('Date', '')
        transaction_date = self._parse_date(date_str)

        statement_data = self._parse_statement_data(data.get('ДанныеВыписки', ''))

        payment_purpose = data.get('НазначениеПлатежа', '')

        result = {
            'transaction_date': transaction_date,
            'amount': Decimal(str(data.get('СуммаДокумента', 0))),
            'payment_purpose': payment_purpose,
            'business_operation': data.get('ХозяйственнаяОперация', None),
            'document_number': data.get('Number', ''),
            'document_date': self._parse_date(data.get('ДатаВходящегоДокумента')),
            'notes': data.get('Комментарий', ''),
            'status': BankTransactionStatusEnum.NEW,
            'document_type': DocumentTypeEnum.PAYMENT_ORDER,
            'payment_source': PaymentSourceEnum.BANK
        }

        # Извлекаем НДС из назначения платежа
        vat_amount, vat_rate = self._extract_vat_from_text(payment_purpose)
        if vat_amount is not None:
            result['vat_amount'] = vat_amount
        if vat_rate is not None:
            result['vat_rate'] = vat_rate
        # Если есть сумма НДС но нет ставки, пытаемся вычислить ставку
        elif vat_amount and result['amount']:
            amount_without_vat = result['amount'] - vat_amount
            if amount_without_vat > 0:
                calculated_rate = (vat_amount / amount_without_vat) * 100
                # Округляем до ближайшей стандартной ставки (0, 10, 20)
                if abs(calculated_rate - 20) < 1:
                    result['vat_rate'] = Decimal('20')
                elif abs(calculated_rate - 10) < 0.5:
                    result['vat_rate'] = Decimal('10')
                elif calculated_rate < 0.5:
                    result['vat_rate'] = Decimal('0')

        if statement_data:
            result.update({
                'counterparty_name': statement_data.get('Плательщик'),
                'counterparty_inn': statement_data.get('ПлательщикИНН'),
                'counterparty_kpp': statement_data.get('ПлательщикКПП'),
                'counterparty_account': statement_data.get('ПлательщикСчет'),
                'counterparty_bank': statement_data.get('ПлательщикБанк1'),
                'counterparty_bik': statement_data.get('ПлательщикБИК'),
            })
            # Номер счёта из ДанныеВыписки (fallback)
            if statement_data.get('ПолучательСчет'):
                result['account_number'] = statement_data.get('ПолучательСчет')

        # Получаем информацию о банковском счёте из справочника 1С
        account_number, bank_name, bank_bik = self._resolve_bank_account_info(data)
        if account_number:
            result['account_number'] = account_number
        if bank_name:
            result['our_bank_name'] = bank_name
        if bank_bik:
            result['our_bank_bik'] = bank_bik

        organization_id = self._resolve_organization_id(data)
        if organization_id:
            result['organization_id'] = organization_id

        return result

    def _parse_payment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг данных списания из 1С в формат BankTransaction"""
        date_str = data.get('Date', '')
        transaction_date = self._parse_date(date_str)

        statement_data = self._parse_statement_data(data.get('ДанныеВыписки', ''))

        payment_purpose = data.get('НазначениеПлатежа', '')

        result = {
            'transaction_date': transaction_date,
            'amount': Decimal(str(data.get('СуммаДокумента', 0))),
            'payment_purpose': payment_purpose,
            'business_operation': data.get('ХозяйственнаяОперация', None),
            'document_number': data.get('Number', ''),
            'document_date': self._parse_date(data.get('ДатаВходящегоДокумента')),
            'notes': data.get('Комментарий', ''),
            'status': BankTransactionStatusEnum.NEW,
            'document_type': DocumentTypeEnum.PAYMENT_ORDER,
            'payment_source': PaymentSourceEnum.BANK
        }

        # Извлекаем НДС из назначения платежа
        vat_amount, vat_rate = self._extract_vat_from_text(payment_purpose)
        if vat_amount is not None:
            result['vat_amount'] = vat_amount
        if vat_rate is not None:
            result['vat_rate'] = vat_rate
        # Если есть сумма НДС но нет ставки, пытаемся вычислить ставку
        elif vat_amount and result['amount']:
            amount_without_vat = result['amount'] - vat_amount
            if amount_without_vat > 0:
                calculated_rate = (vat_amount / amount_without_vat) * 100
                # Округляем до ближайшей стандартной ставки (0, 10, 20)
                if abs(calculated_rate - 20) < 1:
                    result['vat_rate'] = Decimal('20')
                elif abs(calculated_rate - 10) < 0.5:
                    result['vat_rate'] = Decimal('10')
                elif calculated_rate < 0.5:
                    result['vat_rate'] = Decimal('0')

        if statement_data:
            result.update({
                'counterparty_name': statement_data.get('Получатель'),
                'counterparty_inn': statement_data.get('ПолучательИНН'),
                'counterparty_kpp': statement_data.get('ПолучательКПП'),
                'counterparty_account': statement_data.get('ПолучательСчет'),
                'counterparty_bank': statement_data.get('ПолучательБанк1'),
                'counterparty_bik': statement_data.get('ПолучательБИК'),
            })
            # Номер счёта из ДанныеВыписки (fallback)
            if statement_data.get('ПлательщикСчет'):
                result['account_number'] = statement_data.get('ПлательщикСчет')

        # Получаем информацию о банковском счёте из справочника 1С
        account_number, bank_name, bank_bik = self._resolve_bank_account_info(data)
        if account_number:
            result['account_number'] = account_number
        if bank_name:
            result['our_bank_name'] = bank_name
        if bank_bik:
            result['our_bank_bik'] = bank_bik

        organization_id = self._resolve_organization_id(data)
        if organization_id:
            result['organization_id'] = organization_id

        return result

    def _parse_statement_data(self, statement_str: str) -> Dict[str, str]:
        """Парсинг поля ДанныеВыписки"""
        if not statement_str:
            return {}

        result = {}
        lines = statement_str.split('\n')

        for line in lines:
            if '=' not in line:
                continue

            key, value = line.split('=', 1)
            result[key.strip()] = value.strip()

        return result

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Парсинг даты из строки ISO формата"""
        if not date_str or date_str == '0001-01-01T00:00:00':
            return None

        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.date()
        except (ValueError, AttributeError):
            return None

    def _extract_vat_from_text(self, text: str) -> tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Извлечение НДС из текста назначения платежа.

        Ищет паттерны:
        - "В Т.Ч. НДС 5953-49"
        - "В ТОМ ЧИСЛЕ НДС - 32971.00 рублей"
        - "НДС 20% 1000"
        - "НДС 10% - 3344,56руб"
        - "в т.ч. ндс 20% 1000.00"

        Returns:
            tuple: (vat_amount, vat_rate) или (None, None)
        """
        if not text:
            return None, None

        text_upper = text.upper()

        # Паттерн 1: "НДС 20% - 3344,56" или "НДС 10% 1000.00"
        # Ставка и сумма с опциональным дефисом между ними
        pattern1 = r'НДС\s+(\d+)\s*%\s*-?\s*([\d\s\.,]+)(?:РУБ|РУБЛЕЙ)?'
        match = re.search(pattern1, text_upper)
        if match:
            rate_str = match.group(1)
            amount_str = match.group(2).replace(' ', '').replace(',', '.')
            # Удаляем множественные точки (если есть)
            parts = amount_str.split('.')
            if len(parts) > 2:
                amount_str = ''.join(parts[:-1]) + '.' + parts[-1]
            try:
                vat_rate = Decimal(rate_str)
                vat_amount = Decimal(amount_str)
                return vat_amount, vat_rate
            except (ValueError, Exception):
                pass

        # Паттерн 2: "В ТОМ ЧИСЛЕ НДС - 32971.00" или "В Т.Ч. НДС 5953-49"
        # Различные варианты "в том числе" + сумма
        pattern2 = r'(?:В\s+ТОМ\s+ЧИСЛЕ|В\s+Т\.?\s*Ч\.?)\s+НДС\s*-?\s*([\d\s\.,\-]+)(?:РУБ|РУБЛЕЙ)?'
        match = re.search(pattern2, text_upper)
        if match:
            vat_str = match.group(1).replace(' ', '').replace('-', '.').replace(',', '.')
            # Удаляем множественные точки
            parts = vat_str.split('.')
            if len(parts) > 2:
                vat_str = ''.join(parts[:-1]) + '.' + parts[-1]
            try:
                vat_amount = Decimal(vat_str)
                return vat_amount, None
            except (ValueError, Exception):
                pass

        # Паттерн 3: Просто "НДС - 1000.00" или "НДС 1000"
        pattern3 = r'(?<![А-Я])НДС\s*-?\s*([\d\s\.,]+)(?:РУБ|РУБЛЕЙ)?(?!\s*%)'
        match = re.search(pattern3, text_upper)
        if match:
            # Проверяем что это не "НДС 20%" (не ставка)
            amount_str = match.group(1).replace(' ', '').replace(',', '.')
            parts = amount_str.split('.')
            if len(parts) > 2:
                amount_str = ''.join(parts[:-1]) + '.' + parts[-1]
            try:
                vat_amount = Decimal(amount_str)
                # Игнорируем если это похоже на ставку (< 100)
                if vat_amount >= 100:
                    return vat_amount, None
            except (ValueError, Exception):
                pass

        # Паттерн 4: Только ставка "НДС 20%"
        pattern4 = r'НДС\s+(\d+)\s*%'
        match = re.search(pattern4, text_upper)
        if match:
            rate_str = match.group(1)
            try:
                vat_rate = Decimal(rate_str)
                return None, vat_rate
            except (ValueError, Exception):
                pass

        return None, None

    def _parse_cash_receipt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг данных приходного кассового ордера (ПКО) из 1С"""
        date_str = data.get('Date', '')
        transaction_date = self._parse_date(date_str)

        # Назначение платежа для кассовых документов - это поле "Основание"
        payment_purpose = (
            data.get('Основание', '') or
            data.get('ОснованиеПлатежа', '') or
            data.get('НазначениеПлатежа', '')
        )

        result = {
            'transaction_date': transaction_date,
            'amount': Decimal(str(data.get('СуммаДокумента', 0))),
            'payment_purpose': payment_purpose,
            'business_operation': data.get('ХозяйственнаяОперация', None),
            'document_number': data.get('Number', ''),
            'document_date': transaction_date,
            'notes': data.get('Комментарий', ''),
            'status': BankTransactionStatusEnum.NEW,
            'document_type': DocumentTypeEnum.CASH_ORDER,
            'payment_source': PaymentSourceEnum.CASH,
            'account_number': 'Касса',  # Default for cash operations
        }

        # Get cash register name from 1C
        if data.get('Касса'):
            cash_register = data.get('Касса')
            if isinstance(cash_register, dict):
                result['account_number'] = cash_register.get('Description', 'Касса')
            elif isinstance(cash_register, str):
                result['account_number'] = cash_register

        if data.get('Контрагент_Key'):
            counterparty_data = self.odata_client.get_counterparty_by_key(data.get('Контрагент_Key'))
            if counterparty_data:
                result['counterparty_name'] = counterparty_data.get('Description', '')
                result['counterparty_inn'] = counterparty_data.get('ИНН', '')
                result['counterparty_kpp'] = counterparty_data.get('КПП', '')

        organization_id = self._resolve_organization_id(data)
        if organization_id:
            result['organization_id'] = organization_id

        return result

    def _parse_cash_payment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг данных расходного кассового ордера (РКО) из 1С"""
        date_str = data.get('Date', '')
        transaction_date = self._parse_date(date_str)

        # Назначение платежа для кассовых документов - это поле "Основание"
        payment_purpose = (
            data.get('Основание', '') or
            data.get('ОснованиеПлатежа', '') or
            data.get('НазначениеПлатежа', '')
        )

        result = {
            'transaction_date': transaction_date,
            'amount': Decimal(str(data.get('СуммаДокумента', 0))),
            'payment_purpose': payment_purpose,
            'business_operation': data.get('ХозяйственнаяОперация', None),
            'document_number': data.get('Number', ''),
            'document_date': transaction_date,
            'notes': data.get('Комментарий', ''),
            'status': BankTransactionStatusEnum.NEW,
            'document_type': DocumentTypeEnum.CASH_ORDER,
            'payment_source': PaymentSourceEnum.CASH,
            'account_number': 'Касса',  # Default for cash operations
        }

        # Get cash register name from 1C
        if data.get('Касса'):
            cash_register = data.get('Касса')
            if isinstance(cash_register, dict):
                result['account_number'] = cash_register.get('Description', 'Касса')
            elif isinstance(cash_register, str):
                result['account_number'] = cash_register

        if data.get('Контрагент_Key'):
            counterparty_data = self.odata_client.get_counterparty_by_key(data.get('Контрагент_Key'))
            if counterparty_data:
                result['counterparty_name'] = counterparty_data.get('Description', '')
                result['counterparty_inn'] = counterparty_data.get('ИНН', '')
                result['counterparty_kpp'] = counterparty_data.get('КПП', '')

        organization_id = self._resolve_organization_id(data)
        if organization_id:
            result['organization_id'] = organization_id

        return result

    def _resolve_organization_id(self, data: Dict[str, Any]) -> Optional[int]:
        """Получить или создать организацию на основе данных 1С (с кэшированием)"""
        org_key = data.get('Организация_Key')
        if not org_key:
            org_key = self._extract_guid_from_nav_link(data.get('Организация@navigationLinkUrl'))

        if not org_key:
            return None

        # Проверяем кэш
        if org_key in self._organization_cache:
            org = self._organization_cache[org_key]
            return org.id if org else None

        organization = self._get_or_create_organization(org_key)
        self._organization_cache[org_key] = organization
        return organization.id if organization else None

    def _resolve_bank_account_info(self, data: Dict[str, Any]) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Получить информацию о банковском счёте из справочника 1С (с кэшированием)

        Returns:
            Tuple of (account_number, bank_name, bank_bik)
        """
        # Пробуем разные названия полей для банковского счёта
        account_key = (
            data.get('БанковскийСчет_Key') or
            data.get('СчетОрганизации_Key') or
            data.get('БанковскийСчётОрганизации_Key') or
            self._extract_guid_from_nav_link(data.get('БанковскийСчет@navigationLinkUrl')) or
            self._extract_guid_from_nav_link(data.get('СчетОрганизации@navigationLinkUrl'))
        )

        if not account_key or account_key == "00000000-0000-0000-0000-000000000000":
            # Логируем только если не нашли ключ счёта (это важно для отладки)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"No valid account_key found. Available keys: {list(data.keys())}")
            return None, None, None

        # Проверяем кэш
        if account_key in self._bank_account_cache:
            return self._bank_account_cache[account_key]

        try:
            account_data = self.odata_client.get_bank_account_by_key(account_key)

            if account_data:
                # Получаем номер счёта
                account_number = (
                    account_data.get('НомерСчета') or
                    account_data.get('Description') or
                    account_data.get('Code')
                )

                # Получаем информацию о банке
                bank_name = None
                bank_bik = None

                # Проверяем, есть ли расширенные данные банка (через $expand)
                bank_data = account_data.get('Банк')

                if bank_data and isinstance(bank_data, dict):
                    # Если банк загружен через $expand
                    bank_name = (
                        bank_data.get('Description') or
                        bank_data.get('Наименование') or
                        bank_data.get('НаименованиеПолное')
                    )
                    # БИК хранится в поле Code (английскими буквами)
                    bank_bik = bank_data.get('Code') or bank_data.get('Код') or bank_data.get('БИК')
                else:
                    # Попытка получить данные напрямую из account_data
                    bank_name = account_data.get('БанкНаименование')
                    bank_bik = account_data.get('БИК') or account_data.get('БанкБИК')

                    # Если есть ключ банка, запрашиваем его отдельно
                    bank_key = (
                        account_data.get('Банк_Key') or
                        self._extract_guid_from_nav_link(account_data.get('Банк@navigationLinkUrl'))
                    )

                    if bank_key and bank_key != "00000000-0000-0000-0000-000000000000":
                        try:
                            bank_info = self.odata_client.get_bank_by_key(bank_key)

                            if bank_info:
                                bank_name = (
                                    bank_info.get('Description') or
                                    bank_info.get('Наименование') or
                                    bank_info.get('НаименованиеПолное')
                                )
                                # БИК хранится в поле Code (английскими буквами)
                                bank_bik = bank_info.get('Code') or bank_info.get('Код') or bank_info.get('БИК')
                        except Exception as e:
                            logger.warning(f"Failed to fetch bank by key {bank_key}: {e}")

                if account_number:
                    # Логируем только если нашли название банка или БИК
                    if bank_name or bank_bik:
                        logger.info(f"✓ Resolved bank: {account_number} -> {bank_name} (БИК: {bank_bik or 'не указан'})")
                    result = (
                        str(account_number)[:20],  # Обрезаем до 20 символов
                        str(bank_name)[:500] if bank_name else None,
                        str(bank_bik)[:20] if bank_bik else None
                    )
                    # Кэшируем результат
                    self._bank_account_cache[account_key] = result
                    return result
                else:
                    logger.warning(f"Account number not found in account_data for key: {account_key}")
            else:
                logger.warning(f"No account data received for key: {account_key}")
        except Exception as e:
            logger.error(f"Failed to resolve bank account {account_key}: {e}")

        # Кэшируем отрицательный результат тоже
        self._bank_account_cache[account_key] = (None, None, None)
        return None, None, None

    def _resolve_bank_account_number(self, data: Dict[str, Any]) -> Optional[str]:
        """Получить номер банковского счёта из справочника 1С (обратная совместимость)"""
        account_number, _, _ = self._resolve_bank_account_info(data)
        return account_number

    def _get_or_create_organization(self, org_key: str) -> Optional[Organization]:
        """Найти или создать организацию по ключу 1С"""
        organization = (
            self.db.query(Organization)
            .filter(Organization.external_id_1c == org_key)
            .first()
        )

        if organization:
            return organization

        org_data = self.odata_client.get_organization_by_key(org_key)
        if not org_data:
            return None

        name = (
            org_data.get('Description')
            or org_data.get('НаименованиеПолное')
            or org_data.get('НаименованиеСокращенное')
            or f'Организация {org_key}'
        )

        organization = (
            self.db.query(Organization)
            .filter(Organization.name == name)
            .first()
        )

        if organization:
            if not organization.external_id_1c:
                organization.external_id_1c = org_key
            self._update_organization_fields(organization, org_data)
            return organization

        organization = Organization(
            name=name[:255],
            full_name=(org_data.get('НаименованиеПолное') or name)[:500],
            short_name=(org_data.get('НаименованиеСокращенное') or name)[:255],
            inn=org_data.get('ИНН'),
            kpp=org_data.get('КПП'),
            external_id_1c=org_key
        )

        self.db.add(organization)
        self.db.flush()

        return organization

    def _update_organization_fields(self, organization: Organization, org_data: Dict[str, Any]):
        """Обновить базовые сведения об организации"""
        full_name = org_data.get('НаименованиеПолное') or org_data.get('Description')
        short_name = org_data.get('НаименованиеСокращенное')

        if full_name:
            organization.full_name = full_name[:500]
        if short_name:
            organization.short_name = short_name[:255]
        if org_data.get('ИНН'):
            organization.inn = org_data.get('ИНН')
        if org_data.get('КПП'):
            organization.kpp = org_data.get('КПП')

    def _extract_guid_from_nav_link(self, link: Optional[str]) -> Optional[str]:
        """Извлечь GUID из navigationLinkUrl"""
        if not link:
            return None

        match = re.search(r"guid'([0-9a-fA-F-]{36})'", link)
        if match:
            return match.group(1)
        return None

    def _apply_classification(self, transaction: BankTransaction):
        """Применить AI классификацию к транзакции"""
        if not transaction.payment_purpose and not transaction.business_operation:
            return

        try:
            category_id, confidence, reasoning = self.classifier.classify(
                payment_purpose=transaction.payment_purpose,
                counterparty_name=transaction.counterparty_name,
                counterparty_inn=transaction.counterparty_inn,
                amount=transaction.amount,
                transaction_type=transaction.transaction_type,
                business_operation=transaction.business_operation
            )

            if category_id:
                if confidence >= 0.9:
                    transaction.category_id = category_id
                    transaction.category_confidence = Decimal(str(confidence))
                    transaction.status = BankTransactionStatusEnum.CATEGORIZED
                    logger.debug(f"Auto-categorized transaction: {reasoning}")
                else:
                    transaction.suggested_category_id = category_id
                    transaction.category_confidence = Decimal(str(confidence))
                    transaction.status = BankTransactionStatusEnum.NEEDS_REVIEW
                    logger.debug(f"Suggested category for review: {reasoning}")

        except Exception as e:
            logger.warning(f"Classification failed for transaction: {e}")

    def _ensure_business_operation_mapping_exists(
        self,
        business_operation: str,
        result: BankTransaction1CImportResult
    ) -> None:
        """Создать stub-маппинг для хозяйственной операции, если его ещё нет (с кэшированием)"""
        if not business_operation:
            return

        # Проверяем кэш
        if business_operation in self._business_operation_mapping_cache:
            return

        existing = self.db.query(BusinessOperationMapping).filter(
            BusinessOperationMapping.business_operation == business_operation
        ).first()

        if existing:
            self._business_operation_mapping_cache.add(business_operation)
            return

        stub_mapping = BusinessOperationMapping(
            business_operation=business_operation,
            category_id=None,
            priority=0,
            confidence=0.0,
            notes="Авто-создано при импорте из 1С - требуется назначить категорию вручную",
            is_active=False
        )

        self.db.add(stub_mapping)
        self.db.flush()

        # Добавляем в кэш
        self._business_operation_mapping_cache.add(business_operation)

        result.auto_stubs_created += 1
        logger.debug(f"Created stub mapping for business operation: {business_operation}")
