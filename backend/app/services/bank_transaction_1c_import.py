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
            for key, value in transaction_data.items():
                setattr(existing, key, value)

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
            for key, value in transaction_data.items():
                setattr(existing, key, value)

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
            for key, value in transaction_data.items():
                setattr(existing, key, value)

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
            for key, value in transaction_data.items():
                setattr(existing, key, value)

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

    def _parse_receipt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг данных поступления из 1С в формат BankTransaction"""
        date_str = data.get('Date', '')
        transaction_date = self._parse_date(date_str)

        statement_data = self._parse_statement_data(data.get('ДанныеВыписки', ''))

        result = {
            'transaction_date': transaction_date,
            'amount': Decimal(str(data.get('СуммаДокумента', 0))),
            'payment_purpose': data.get('НазначениеПлатежа', ''),
            'business_operation': data.get('ХозяйственнаяОперация', None),
            'document_number': data.get('Number', ''),
            'document_date': self._parse_date(data.get('ДатаВходящегоДокумента')),
            'notes': data.get('Комментарий', ''),
            'status': BankTransactionStatusEnum.NEW,
            'document_type': DocumentTypeEnum.PAYMENT_ORDER,
            'payment_source': PaymentSourceEnum.BANK
        }

        if statement_data:
            result.update({
                'counterparty_name': statement_data.get('Плательщик'),
                'counterparty_inn': statement_data.get('ПлательщикИНН'),
                'counterparty_kpp': statement_data.get('ПлательщикКПП'),
                'counterparty_account': statement_data.get('ПлательщикСчет'),
                'counterparty_bank': statement_data.get('ПлательщикБанк1'),
                'counterparty_bik': statement_data.get('ПлательщикБИК'),
                'account_number': statement_data.get('ПолучательСчет')
            })

        organization_id = self._resolve_organization_id(data)
        if organization_id:
            result['organization_id'] = organization_id

        return result

    def _parse_payment_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг данных списания из 1С в формат BankTransaction"""
        date_str = data.get('Date', '')
        transaction_date = self._parse_date(date_str)

        statement_data = self._parse_statement_data(data.get('ДанныеВыписки', ''))

        result = {
            'transaction_date': transaction_date,
            'amount': Decimal(str(data.get('СуммаДокумента', 0))),
            'payment_purpose': data.get('НазначениеПлатежа', ''),
            'business_operation': data.get('ХозяйственнаяОперация', None),
            'document_number': data.get('Number', ''),
            'document_date': self._parse_date(data.get('ДатаВходящегоДокумента')),
            'notes': data.get('Комментарий', ''),
            'status': BankTransactionStatusEnum.NEW,
            'document_type': DocumentTypeEnum.PAYMENT_ORDER,
            'payment_source': PaymentSourceEnum.BANK
        }

        if statement_data:
            result.update({
                'counterparty_name': statement_data.get('Получатель'),
                'counterparty_inn': statement_data.get('ПолучательИНН'),
                'counterparty_kpp': statement_data.get('ПолучательКПП'),
                'counterparty_account': statement_data.get('ПолучательСчет'),
                'counterparty_bank': statement_data.get('ПолучательБанк1'),
                'counterparty_bik': statement_data.get('ПолучательБИК'),
                'account_number': statement_data.get('ПлательщикСчет')
            })

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

    def _parse_cash_receipt_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг данных приходного кассового ордера (ПКО) из 1С"""
        date_str = data.get('Date', '')
        transaction_date = self._parse_date(date_str)

        result = {
            'transaction_date': transaction_date,
            'amount': Decimal(str(data.get('СуммаДокумента', 0))),
            'payment_purpose': data.get('ОснованиеПлатежа', '') or data.get('НазначениеПлатежа', ''),
            'business_operation': data.get('ХозяйственнаяОперация', None),
            'document_number': data.get('Number', ''),
            'document_date': transaction_date,
            'notes': data.get('Комментарий', ''),
            'status': BankTransactionStatusEnum.NEW,
            'document_type': DocumentTypeEnum.CASH_ORDER,
            'payment_source': PaymentSourceEnum.CASH
        }

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

        result = {
            'transaction_date': transaction_date,
            'amount': Decimal(str(data.get('СуммаДокумента', 0))),
            'payment_purpose': data.get('ОснованиеПлатежа', '') or data.get('НазначениеПлатежа', ''),
            'business_operation': data.get('ХозяйственнаяОперация', None),
            'document_number': data.get('Number', ''),
            'document_date': transaction_date,
            'notes': data.get('Комментарий', ''),
            'status': BankTransactionStatusEnum.NEW,
            'document_type': DocumentTypeEnum.CASH_ORDER,
            'payment_source': PaymentSourceEnum.CASH
        }

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
        """Получить или создать организацию на основе данных 1С"""
        org_key = data.get('Организация_Key')
        if not org_key:
            org_key = self._extract_guid_from_nav_link(data.get('Организация@navigationLinkUrl'))

        if not org_key:
            return None

        organization = self._get_or_create_organization(org_key)
        return organization.id if organization else None

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
        """Создать stub-маппинг для хозяйственной операции, если его ещё нет"""
        if not business_operation:
            return

        existing = self.db.query(BusinessOperationMapping).filter(
            BusinessOperationMapping.business_operation == business_operation
        ).first()

        if existing:
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

        result.auto_stubs_created += 1
        logger.debug(f"Created stub mapping for business operation: {business_operation}")
