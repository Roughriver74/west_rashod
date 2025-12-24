#!/usr/bin/env python3
"""
Диагностический скрипт для проверки полей банковского счёта и банка из 1С
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.odata_1c_client import OData1CClient
from app.db.models import Organization
import logging
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def diagnose_bank_fields():
    """Проверить, какие поля приходят из 1С для банковского счёта"""

    # Создаем подключение к БД
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Создаем OData клиент
    odata_client = OData1CClient(
        base_url=settings.ODATA_1C_URL,
        username=settings.ODATA_1C_USERNAME,
        password=settings.ODATA_1C_PASSWORD
    )

    try:
        # Берём первую организацию с внешним ID
        org = db.query(Organization).filter(
            Organization.external_id_1c.isnot(None)
        ).first()

        if not org:
            logger.error("Не найдено организаций с внешним ID 1С")
            return

        logger.info(f"Используем организацию: {org.name} (ID: {org.external_id_1c})")

        # Запрашиваем банковские счета с расширением Банк
        endpoint = f"Catalog_БанковскиеСчетаОрганизаций?$format=json&$expand=Банк&$filter=Owner_Key eq guid'{org.external_id_1c}'&$top=1"

        logger.info(f"\n{'='*80}")
        logger.info("Запрос к 1С:")
        logger.info(f"Endpoint: {endpoint}")
        logger.info(f"{'='*80}\n")

        response = odata_client._make_request(
            method='GET',
            endpoint=endpoint,
            params=None
        )

        accounts = response.get('value', [])

        if not accounts:
            logger.warning("Не найдено банковских счетов для этой организации")
            return

        account = accounts[0]

        logger.info(f"\n{'='*80}")
        logger.info("ДАННЫЕ БАНКОВСКОГО СЧЁТА:")
        logger.info(f"{'='*80}")
        logger.info(json.dumps(account, indent=2, ensure_ascii=False))

        # Анализируем данные банка
        bank_data = account.get('Банк')
        if bank_data and isinstance(bank_data, dict):
            logger.info(f"\n{'='*80}")
            logger.info("ДАННЫЕ БАНКА (через $expand):")
            logger.info(f"{'='*80}")
            logger.info(json.dumps(bank_data, indent=2, ensure_ascii=False))

            # Пробуем все возможные поля для БИК
            possible_bik_fields = ['БИК', 'Код', 'Code', 'BIK', 'БанкБИК']
            logger.info(f"\n{'='*80}")
            logger.info("ПОИСК БИК В ДАННЫХ БАНКА:")
            logger.info(f"{'='*80}")
            for field in possible_bik_fields:
                value = bank_data.get(field)
                if value:
                    logger.info(f"✓ Найдено: {field} = {value}")
                else:
                    logger.info(f"✗ Отсутствует: {field}")

        # Проверяем, есть ли ключ банка для запроса отдельно
        bank_key = account.get('Банк_Key')
        if bank_key and bank_key != "00000000-0000-0000-0000-000000000000":
            logger.info(f"\n{'='*80}")
            logger.info(f"ЗАПРОС БАНКА ПО КЛЮЧУ: {bank_key}")
            logger.info(f"{'='*80}")

            try:
                # Пробуем Catalog_КлассификаторБанков
                try:
                    logger.info("Пробуем Catalog_КлассификаторБанков...")
                    bank_info = odata_client._make_request(
                        method='GET',
                        endpoint=f"Catalog_КлассификаторБанков(guid'{bank_key}')",
                        params={'$format': 'json'}
                    )
                    logger.info("\n✓ ДАННЫЕ ИЗ Catalog_КлассификаторБанков:")
                    logger.info(json.dumps(bank_info, indent=2, ensure_ascii=False))

                    # Поиск БИК
                    logger.info(f"\n{'='*80}")
                    logger.info("ПОИСК БИК В Catalog_КлассификаторБанков:")
                    logger.info(f"{'='*80}")
                    for field in possible_bik_fields:
                        value = bank_info.get(field)
                        if value:
                            logger.info(f"✓ Найдено: {field} = {value}")
                        else:
                            logger.info(f"✗ Отсутствует: {field}")

                except Exception as e:
                    logger.warning(f"Catalog_КлассификаторБанков недоступен: {e}")

                    # Пробуем Catalog_Банки
                    try:
                        logger.info("\nПробуем Catalog_Банки...")
                        bank_info = odata_client._make_request(
                            method='GET',
                            endpoint=f"Catalog_Банки(guid'{bank_key}')",
                            params={'$format': 'json'}
                        )
                        logger.info("\n✓ ДАННЫЕ ИЗ Catalog_Банки:")
                        logger.info(json.dumps(bank_info, indent=2, ensure_ascii=False))

                        # Поиск БИК
                        logger.info(f"\n{'='*80}")
                        logger.info("ПОИСК БИК В Catalog_Банки:")
                        logger.info(f"{'='*80}")
                        for field in possible_bik_fields:
                            value = bank_info.get(field)
                            if value:
                                logger.info(f"✓ Найдено: {field} = {value}")
                            else:
                                logger.info(f"✗ Отсутствует: {field}")

                    except Exception as e2:
                        logger.error(f"Catalog_Банки также недоступен: {e2}")

            except Exception as e:
                logger.error(f"Ошибка при запросе банка: {e}")

        logger.info(f"\n{'='*80}")
        logger.info("ДИАГНОСТИКА ЗАВЕРШЕНА")
        logger.info(f"{'='*80}\n")

    except Exception as e:
        logger.error(f"Ошибка диагностики: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Запуск диагностики полей банка из 1С...")
    diagnose_bank_fields()
