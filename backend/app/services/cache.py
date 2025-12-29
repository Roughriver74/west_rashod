"""
Централизованный сервис кэширования для оптимизации производительности
"""
import json
import logging
from typing import Any, Optional, Callable
from functools import wraps
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Время жизни кэша (в секундах)
CACHE_TTL = {
    "kpi": 300,           # 5 минут для KPI метрик
    "analytics": 180,     # 3 минуты для аналитики
    "contracts": 300,     # 5 минут для списка договоров
    "turnover": 600,      # 10 минут для оборотной ведомости
    "references": 60,     # 1 минута для справочников
}


class CacheService:
    """Сервис кэширования с использованием Redis"""

    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            # Проверка подключения
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Cache disabled.")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        if not self.redis_client:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Установить значение в кэш с TTL"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.setex(
                key,
                ttl,
                json.dumps(value, default=str)  # default=str для date/datetime
            )
            logger.debug(f"Cache SET: {key} (TTL={ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Удалить значение из кэша"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """Очистить все ключи по паттерну (например: 'fin:kpi:*')"""
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                count = self.redis_client.delete(*keys)
                logger.info(f"Cache CLEAR: {pattern} ({count} keys)")
                return count
            return 0
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0


# Глобальный экземпляр
cache = CacheService()


def cached(ttl: int = 300, key_prefix: str = "fin"):
    """
    Декоратор для кэширования результатов функций

    Usage:
        @cached(ttl=300, key_prefix="fin:kpi")
        async def get_kpi_metrics(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Построить ключ кэша из имени функции и параметров
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Попытаться получить из кэша
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Вызвать функцию и сохранить результат
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper
    return decorator
