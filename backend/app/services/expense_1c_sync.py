"""
Сервис синхронизации заявок на расход из 1С через OData.

Адаптировано из west_buget_it БЕЗ department_id (single-tenant архитектура).
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import (
    Expense,
    ExpenseStatusEnum,
    ExpenseTypeEnum,
    Organization,
    Contractor,
    BudgetCategory
)
from app.services.odata_1c_client import OData1CClient

logger = logging.getLogger(__name__)


class Expense1CSyncResult:
    """Результат синхронизации заявок на расход из 1С."""

    def __init__(self):
        self.total_fetched = 0  # Получено из 1С
        self.total_processed = 0  # Обработано
        self.total_created = 0  # Создано новых
        self.total_updated = 0  # Обновлено существующих
        self.total_skipped = 0  # Пропущено (дубликаты без изменений)
        self.errors: List[str] = []

    @property
    def success(self) -> bool:
        """Успешно ли завершилась синхронизация."""
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь для JSON ответа."""
        return {
            'total_fetched': self.total_fetched,
            'total_processed': self.total_processed,
            'total_created': self.total_created,
            'total_updated': self.total_updated,
            'total_skipped': self.total_skipped,
            'errors': self.errors[:10],  # Ограничить количество ошибок
            'success': self.success
        }


class Expense1CSync:
    """Сервис синхронизации заявок на расход из 1С."""

    def __init__(
        self,
        db: Session,
        odata_client: OData1CClient
    ):
        """
        Инициализация сервиса синхронизации.

        Args:
            db: Database session
            odata_client: 1C OData client
        """
        self.db = db
        self.odata_client = odata_client

    def sync_expenses(
        self,
        date_from: date,
        date_to: date,
        batch_size: int = 100,
        only_posted: bool = True
    ) -> Expense1CSyncResult:
        """
        Синхронизировать заявки на расход из 1С за период.

        Args:
            date_from: Начальная дата периода
            date_to: Конечная дата периода
            batch_size: Размер батча для запроса к 1С
            only_posted: Только проведенные документы

        Returns:
            Результат синхронизации
        """
        result = Expense1CSyncResult()

        logger.info(
            f"Starting 1C expense sync: date_from={date_from}, date_to={date_to}, "
            f"only_posted={only_posted}"
        )

        skip = 0
        while True:
            try:
                # Получить батч из 1С
                expense_docs = self.odata_client.get_expense_requests(
                    date_from=date_from,
                    date_to=date_to,
                    top=batch_size,
                    skip=skip,
                    only_posted=only_posted
                )

                if not expense_docs:
                    logger.info(f"No more expense documents to fetch (skip={skip})")
                    break

                result.total_fetched += len(expense_docs)
                logger.debug(f"Fetched {len(expense_docs)} expense documents from 1C (skip={skip})")

                # Обработать батч
                for doc in expense_docs:
                    try:
                        self._process_expense_document(doc, result)
                    except Exception as e:
                        error_msg = f"Error processing expense document {doc.get('Number', 'UNKNOWN')}: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        result.errors.append(error_msg)

                # Коммит после каждого батча
                try:
                    self.db.commit()
                    logger.debug(f"Committed batch: {result.total_created} created, {result.total_updated} updated")
                except Exception as e:
                    logger.error(f"Failed to commit batch: {e}")
                    self.db.rollback()
                    result.errors.append(f"Commit failed: {str(e)}")
                    break

                # Следующий батч
                skip += len(expense_docs)

                # Если получили меньше чем batch_size, значит это последний батч
                if len(expense_docs) < batch_size:
                    break

            except Exception as e:
                error_msg = f"Failed to fetch expenses from 1C: {str(e)}"
                logger.error(error_msg, exc_info=True)
                result.errors.append(error_msg)
                break

        logger.info(
            f"Expense sync completed: fetched={result.total_fetched}, "
            f"created={result.total_created}, updated={result.total_updated}, "
            f"skipped={result.total_skipped}, errors={len(result.errors)}"
        )

        return result

    def _process_expense_document(
        self,
        doc: Dict[str, Any],
        result: Expense1CSyncResult
    ) -> None:
        """
        Обработать один документ заявки из 1С.

        Args:
            doc: Документ из 1С OData
            result: Объект результата для обновления статистики
        """
        ref_key = doc.get('Ref_Key')
        if not ref_key:
            logger.warning("Skipping expense document without Ref_Key")
            result.total_skipped += 1
            return

        number = doc.get('Number', 'UNKNOWN')
        result.total_processed += 1

        # Проверить существование
        existing = self.db.query(Expense).filter(
            Expense.external_id_1c == ref_key
        ).first()

        # Маппинг данных из 1С
        expense_data = self._map_1c_to_expense(doc)

        if existing:
            # Обновить существующую заявку
            self._update_expense(existing, expense_data)
            result.total_updated += 1
            logger.debug(f"Updated expense {number} (id={existing.id})")
        else:
            # Создать новую заявку
            self._create_expense(expense_data, ref_key)
            result.total_created += 1
            logger.debug(f"Created expense {number}")

    def _map_1c_to_expense(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Маппинг полей документа 1С на поля модели Expense.

        Args:
            doc: Документ из 1С OData

        Returns:
            Словарь с данными для создания/обновления Expense
        """
        # Парсинг дат
        request_date = self._parse_date(doc.get('Date'))
        payment_date = self._parse_date(doc.get('ДатаПлатежа'))

        # Парсинг суммы
        amount = Decimal(str(doc.get('СуммаДокумента', 0) or 0))

        # Определение статуса
        status_1c = doc.get('Статус', '')
        posted = doc.get('Posted', False)
        status = self._map_status(status_1c, posted)

        # Флаги оплаты
        is_paid = status_1c == 'вс_Оплачена'
        is_closed = is_paid

        # Получение организации
        org_key = doc.get('Организация_Key')
        organization_id = self._get_or_create_organization(org_key) if org_key else None

        # Получение контрагента
        contractor_key = doc.get('Контрагент_Key')
        if contractor_key:
            contractor_id, contractor_name, contractor_inn = self._get_or_create_contractor(contractor_key)
        else:
            contractor_id, contractor_name, contractor_inn = None, None, None

        # Получение подразделения (если есть)
        subdivision_key = doc.get('Подразделение_Key')
        subdivision_name, subdivision_code = self._get_subdivision_info(subdivision_key) if subdivision_key else (None, None)

        # Получение категории (статьи ДДС)
        category_key = doc.get('СтатьяДвиженияДенежныхСредств_Key')
        category_id = self._get_or_create_category(category_key) if category_key else None

        # Комментарий и описание
        payment_purpose = doc.get('НазначениеПлатежа') or ''
        short_comment = doc.get('Комментарий') or ''

        # Title: используем начало НазначениеПлатежа или Комментарий
        title_source = payment_purpose or short_comment or f"Заявка на расход"
        title = title_source[:100] if len(title_source) > 100 else title_source

        # Description: полное НазначениеПлатежа
        description = payment_purpose if payment_purpose else None

        # Comment: краткий комментарий из 1С
        comment = short_comment

        return {
            'number': doc.get('Number', ''),
            'title': title,
            'description': description,
            'amount': amount,
            'request_date': request_date,
            'payment_date': payment_date,
            'payment_purpose': payment_purpose,
            'status': status,
            'is_paid': is_paid,
            'is_closed': is_closed,
            'organization_id': organization_id,
            'contractor_id': contractor_id,
            'contractor_name': contractor_name,
            'contractor_inn': contractor_inn,
            'category_id': category_id,
            'subdivision': subdivision_name,
            'subdivision_code': subdivision_code,
            'comment': comment,
            'imported_from_1c': True,
            'synced_at': datetime.utcnow()
        }

    def _map_status(self, status_1c: str, posted: bool) -> ExpenseStatusEnum:
        """
        Маппинг статуса 1С на статус west_rashod.

        Args:
            status_1c: Статус из 1С
            posted: Проведен ли документ

        Returns:
            Статус для west_rashod
        """
        # Если оплачена - PAID
        if status_1c == 'вс_Оплачена':
            return ExpenseStatusEnum.PAID

        # Если проведена, но не оплачена - PENDING (к оплате)
        if posted:
            return ExpenseStatusEnum.PENDING

        # Если не проведена - DRAFT
        return ExpenseStatusEnum.DRAFT

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """
        Парсинг даты из строки 1С.

        Args:
            date_str: Дата в формате ISO (YYYY-MM-DDTHH:MM:SS)

        Returns:
            Объект date или None
        """
        if not date_str:
            return None

        try:
            # 1С возвращает в формате ISO: "2025-12-24T00:00:00"
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.date()
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None

    def _get_or_create_organization(self, org_key: str) -> Optional[int]:
        """
        Найти или создать организацию по Ref_Key из 1С.

        Args:
            org_key: Ref_Key организации из 1С

        Returns:
            ID организации или None
        """
        # Поиск существующей
        org = self.db.query(Organization).filter(
            Organization.external_id_1c == org_key
        ).first()

        if org:
            return org.id

        # Если не найдена, попробовать загрузить из 1С
        try:
            org_doc = self.odata_client.get_organization_by_key(org_key)
            if not org_doc:
                logger.warning(f"Organization {org_key} not found in 1C")
                return None

            name = (
                org_doc.get('Description')
                or org_doc.get('НаименованиеПолное')
                or org_doc.get('НаименованиеСокращенное')
                or 'Неизвестная организация'
            )

            new_org = Organization(
                name=name[:255],
                full_name=org_doc.get('НаименованиеПолное', '')[:500],
                short_name=org_doc.get('НаименованиеСокращенное', '')[:255],
                inn=org_doc.get('ИНН'),
                kpp=org_doc.get('КПП'),
                external_id_1c=org_key,
                synced_at=datetime.utcnow()
            )
            self.db.add(new_org)
            self.db.flush()
            logger.info(f"Created organization from 1C: {name} (external_id={org_key})")
            return new_org.id

        except Exception as e:
            logger.error(f"Failed to fetch/create organization {org_key}: {e}")
            return None

    def _get_or_create_contractor(self, contractor_key: str) -> tuple[Optional[int], Optional[str], Optional[str]]:
        """
        Найти или создать контрагента по Ref_Key из 1С.

        Args:
            contractor_key: Ref_Key контрагента из 1С

        Returns:
            Кортеж (ID контрагента, имя, ИНН) или (None, None, None)
        """
        # Поиск существующего
        contractor = self.db.query(Contractor).filter(
            Contractor.external_id_1c == contractor_key
        ).first()

        if contractor:
            return contractor.id, contractor.name, contractor.inn

        # Если не найден, попробовать загрузить из 1С
        try:
            c_doc = self.odata_client.get_counterparty_by_key(contractor_key)
            if not c_doc:
                logger.warning(f"Contractor {contractor_key} not found in 1C")
                return None, None, None

            name = (
                c_doc.get('Description')
                or c_doc.get('Наименование')
                or c_doc.get('НаименованиеПолное')
                or 'Неизвестный контрагент'
            )
            inn = c_doc.get('ИНН', '')[:20] if c_doc.get('ИНН') else None

            new_contractor = Contractor(
                name=name[:500],
                inn=inn,
                external_id_1c=contractor_key,
                is_active=True
            )
            self.db.add(new_contractor)
            self.db.flush()
            logger.info(f"Created contractor from 1C: {name} (external_id={contractor_key})")
            return new_contractor.id, name, inn

        except Exception as e:
            logger.error(f"Failed to fetch/create contractor {contractor_key}: {e}")
            return None, None, None

    def _get_or_create_category(self, category_key: str) -> Optional[int]:
        """
        Найти или создать категорию (статью ДДС) по Ref_Key из 1С.

        Args:
            category_key: Ref_Key категории из 1С

        Returns:
            ID категории или None
        """
        # Поиск существующей
        category = self.db.query(BudgetCategory).filter(
            BudgetCategory.external_id_1c == category_key
        ).first()

        if category:
            return category.id

        # Если не найдена, попробовать загрузить из 1С
        try:
            cat_doc = self.odata_client.get_budget_category_by_key(category_key)
            if not cat_doc:
                logger.warning(f"Category {category_key} not found in 1C")
                return None

            name = (
                cat_doc.get('Description')
                or cat_doc.get('Наименование')
                or cat_doc.get('НаименованиеПолное')
                or 'Неизвестная категория'
            )

            # Определить тип (по умолчанию OPEX)
            category_type = ExpenseTypeEnum.OPEX

            new_category = BudgetCategory(
                name=name[:255],
                type=category_type,
                description=cat_doc.get('Description', '')[:500] if cat_doc.get('Description') else None,
                external_id_1c=category_key,
                code_1c=cat_doc.get('Code') or cat_doc.get('Код'),
                is_active=True
            )
            self.db.add(new_category)
            self.db.flush()
            logger.info(f"Created category from 1C: {name} (external_id={category_key})")
            return new_category.id

        except Exception as e:
            logger.error(f"Failed to fetch/create category {category_key}: {e}")
            return None

    def _get_subdivision_info(self, subdivision_key: str) -> tuple[Optional[str], Optional[str]]:
        """
        Получить информацию о подразделении из 1С.

        Args:
            subdivision_key: Ref_Key подразделения из 1С

        Returns:
            Кортеж (название, код) подразделения или (None, None)
        """
        if not subdivision_key or subdivision_key == "00000000-0000-0000-0000-000000000000":
            return None, None

        try:
            # Запросить справочник подразделений из 1С
            response = self.odata_client._make_request(
                method='GET',
                endpoint=f"Catalog_СтруктураПредприятия(guid'{subdivision_key}')",
                params={'$format': 'json'}
            )

            if not response:
                logger.warning(f"Subdivision {subdivision_key} not found in 1C")
                return None, None

            # Получить название и код
            name = (
                response.get('Description')
                or response.get('Наименование')
                or response.get('НаименованиеПолное')
            )
            code = response.get('Code') or response.get('Код')

            return name, code

        except Exception as e:
            logger.warning(f"Failed to fetch subdivision {subdivision_key}: {e}")
            return None, None

    def _update_expense(self, expense: Expense, data: Dict[str, Any]) -> None:
        """
        Обновить существующую заявку.

        Args:
            expense: Существующая заявка
            data: Новые данные
        """
        # Обновляем все поля кроме защищенных
        protected_fields = {'id', 'created_at', 'external_id_1c', 'notes'}

        for key, value in data.items():
            if key not in protected_fields and hasattr(expense, key):
                # Особая логика для category_id: обновляем только если текущее значение NULL
                if key == 'category_id' and expense.category_id is not None:
                    continue
                setattr(expense, key, value)

        expense.updated_at = datetime.utcnow()

    def _create_expense(self, data: Dict[str, Any], ref_key: str) -> Expense:
        """
        Создать новую заявку.

        Args:
            data: Данные заявки
            ref_key: Ref_Key из 1С

        Returns:
            Созданная заявка
        """
        data['external_id_1c'] = ref_key
        data['is_active'] = True

        expense = Expense(**data)
        self.db.add(expense)
        self.db.flush()

        return expense
