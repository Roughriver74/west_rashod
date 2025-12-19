"""
Business Operation Mapper (Маппер ХозяйственнаяОперация → Категория)

Гибкий маппинг хозяйственных операций из 1С на категории бюджета
через таблицу в БД (business_operation_mappings).

Преимущества гибкого подхода:
- Настройка маппинга для каждого отдела отдельно
- Изменение маппинга без изменения кода
- Приоритезация при множественных соответствиях
- Простая настройка через БД или UI
"""
from typing import Optional, List, Dict, Tuple
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BusinessOperationMapper:
    """
    Маппер хозяйственных операций на категории бюджета

    Использует таблицу business_operation_mappings для гибкой настройки соответствий.
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Database session
        """
        self.db = db
        self._cache: Dict[Tuple[str, int], Optional[Tuple[int, float]]] = {}  # Cache {(operation, dept_id): (cat_id, confidence)}

    def get_category_by_business_operation(
        self,
        business_operation: str,
        department_id: int
    ) -> Optional[int]:
        """
        Получить ID категории по хозяйственной операции

        Args:
            business_operation: ХозяйственнаяОперация из 1С
            department_id: ID отдела

        Returns:
            category_id или None если не найдено
        """
        if not business_operation:
            return None

        # Проверить кэш
        cache_key = (business_operation, department_id)
        if cache_key in self._cache:
            result = self._cache[cache_key]
            return result[0] if result else None

        # Найти маппинг в БД
        from app.db.models import BusinessOperationMapping

        mapping = (
            self.db.query(BusinessOperationMapping)
            .filter(
                BusinessOperationMapping.business_operation == business_operation,
                BusinessOperationMapping.department_id == department_id,
                BusinessOperationMapping.is_active == True
            )
            .order_by(BusinessOperationMapping.priority.desc())  # Самый высокий приоритет
            .first()
        )

        if mapping:
            # Сохранить в кэш
            self._cache[cache_key] = (mapping.category_id, float(mapping.confidence))
            logger.debug(
                f"Mapped business_operation '{business_operation}' → "
                f"category_id {mapping.category_id} (confidence: {mapping.confidence})"
            )
            return mapping.category_id
        else:
            # Сохранить в кэш отсутствие маппинга
            self._cache[cache_key] = None
            logger.debug(f"No mapping found for business_operation: '{business_operation}' (department_id={department_id})")
            return None

    def get_confidence_for_mapping(
        self,
        business_operation: str,
        department_id: int
    ) -> float:
        """
        Получить уровень уверенности для маппинга

        Args:
            business_operation: ХозяйственнаяОперация
            department_id: ID отдела

        Returns:
            Confidence (0.0-1.0, или 0.0 если маппинг не найден)
        """
        if not business_operation:
            return 0.0

        # Проверить кэш
        cache_key = (business_operation, department_id)
        if cache_key in self._cache:
            result = self._cache[cache_key]
            return result[1] if result else 0.0

        # Найти маппинг в БД
        from app.db.models import BusinessOperationMapping

        mapping = (
            self.db.query(BusinessOperationMapping)
            .filter(
                BusinessOperationMapping.business_operation == business_operation,
                BusinessOperationMapping.department_id == department_id,
                BusinessOperationMapping.is_active == True
            )
            .order_by(BusinessOperationMapping.priority.desc())
            .first()
        )

        if mapping:
            confidence = float(mapping.confidence)
            self._cache[cache_key] = (mapping.category_id, confidence)
            return confidence
        else:
            self._cache[cache_key] = None
            return 0.0

    def get_all_mappings(self, department_id: int) -> List[Dict]:
        """
        Получить все активные маппинги для отдела

        Args:
            department_id: ID отдела

        Returns:
            Список словарей с информацией о маппингах
        """
        from app.db.models import BusinessOperationMapping, BudgetCategory

        mappings = (
            self.db.query(BusinessOperationMapping)
            .join(BudgetCategory, BusinessOperationMapping.category_id == BudgetCategory.id)
            .filter(
                BusinessOperationMapping.department_id == department_id,
                BusinessOperationMapping.is_active == True
            )
            .order_by(BusinessOperationMapping.priority.desc(), BusinessOperationMapping.business_operation)
            .all()
        )

        return [
            {
                'id': m.id,
                'business_operation': m.business_operation,
                'category_id': m.category_id,
                'category_name': m.category_rel.name if m.category_rel else None,
                'priority': m.priority,
                'confidence': float(m.confidence),
                'notes': m.notes
            }
            for m in mappings
        ]

    def clear_cache(self):
        """Очистить кэш маппингов"""
        self._cache.clear()
        logger.debug("Business operation mapping cache cleared")
