"""
Вспомогательные функции для построения фильтров по паттерну West Fin.
Использует subqueries вместо JOIN для оптимизации производительности.
"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Organization


def build_filter_subqueries(
    organizations: Optional[str],
    db: Session
) -> Optional[List[int]]:
    """
    Преобразует строковые параметры фильтров в список ID организаций.

    Args:
        organizations: Строка с названиями организаций через запятую "Org1,Org2,Org3"
        db: SQLAlchemy session

    Returns:
        Список ID организаций или None если фильтр не применяется

    Example:
        org_ids = build_filter_subqueries("ООО Ромашка,АО Солнце", db)
        # Returns: [1, 5] если такие организации найдены
    """
    if not organizations:
        return None

    org_list = [o.strip() for o in organizations.split(',') if o.strip()]
    if not org_list:
        return None

    # Subquery вместо JOIN для оптимизации
    org_filter = select(Organization.id).where(
        Organization.name.in_(org_list)
    )

    org_ids_result = db.execute(org_filter).fetchall()
    org_ids = [row[0] for row in org_ids_result]

    return org_ids if org_ids else None


def apply_org_filter(stmt, org_ids: Optional[List[int]], org_column):
    """
    Применяет фильтр организаций к SQL statement.

    Args:
        stmt: SQLAlchemy select statement
        org_ids: Список ID организаций или None
        org_column: Колонка organization_id в таблице (например, FinReceipt.organization_id)

    Returns:
        Модифицированный SQL statement с примененным фильтром

    Example:
        query = db.query(FinReceipt)
        org_ids = build_filter_subqueries(organizations, db)
        query = apply_org_filter(query, org_ids, FinReceipt.organization_id)
    """
    if org_ids is not None and len(org_ids) > 0:
        stmt = stmt.where(org_column.in_(org_ids))

    return stmt


def apply_payer_filters(
    stmt,
    payer_column,
    payers: Optional[str] = None,
    excluded_payers: Optional[str] = None
):
    """
    Применяет фильтры по плательщикам (включение/исключение).

    Логика фильтрации:
    1. Если указан payers - показать только этих плательщиков (IN)
    2. Если указан excluded_payers - скрыть указанных плательщиков (NOT IN)
    3. Приоритет: сначала IN, затем NOT IN

    Args:
        stmt: SQLAlchemy select statement
        payer_column: Колонка плательщика (например, FinReceipt.payer)
        payers: Строка "Плательщик1,Плательщик2" - показать только этих
        excluded_payers: Строка "Служебные,Тестовые" - скрыть этих

    Returns:
        Модифицированный SQL statement с примененными фильтрами

    Example:
        query = db.query(FinReceipt)
        query = apply_payer_filters(
            query,
            FinReceipt.payer,
            payers="АО Банк,ООО Финанс",
            excluded_payers="Служебные"
        )
    """
    payer_list = [p.strip() for p in payers.split(',') if payers and p.strip()] if payers else None
    excluded_payer_list = [p.strip() for p in excluded_payers.split(',') if excluded_payers and p.strip()] \
        if excluded_payers else None

    # Сначала включение (IN)
    if payer_list:
        stmt = stmt.where(payer_column.in_(payer_list))

    # Затем исключение (NOT IN)
    if excluded_payer_list:
        stmt = stmt.where(~payer_column.in_(excluded_payer_list))

    return stmt
