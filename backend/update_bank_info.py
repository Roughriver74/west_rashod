#!/usr/bin/env python3
"""
Скрипт для обновления информации о банках в существующих транзакциях
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.odata_1c_client import OData1CClient
from app.db.models import Organization
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_organization_bank_accounts(odata_client: OData1CClient, org_external_id: str):
    """
    Получить все банковские счета организации из 1С

    Returns:
        Dict[account_number, (bank_name, bank_bik)]
    """
    try:
        # Запрашиваем банковские счета организации с расширением Банк
        endpoint = f"Catalog_БанковскиеСчетаОрганизаций?$format=json&$expand=Банк&$filter=Owner_Key eq guid'{org_external_id}'"

        response = odata_client._make_request(
            method='GET',
            endpoint=endpoint,
            params=None
        )

        accounts = {}
        for item in response.get('value', []):
            account_number = (
                item.get('НомерСчета') or
                item.get('Description') or
                item.get('Code')
            )

            if not account_number:
                continue

            # Получаем информацию о банке
            bank_name = None
            bank_bik = None

            bank_data = item.get('Банк')
            if bank_data and isinstance(bank_data, dict):
                bank_name = (
                    bank_data.get('Description') or
                    bank_data.get('Наименование') or
                    bank_data.get('НаименованиеПолное')
                )
                # БИК хранится в поле Code (английскими буквами)
                bank_bik = bank_data.get('Code') or bank_data.get('Код') or bank_data.get('БИК')

            # Fallback к прямым полям
            if not bank_name:
                bank_name = item.get('БанкНаименование')
            if not bank_bik:
                bank_bik = item.get('БИК') or item.get('БанкБИК')

            # Если все еще нет данных о банке, пробуем получить по ключу
            if not bank_name or not bank_bik:
                bank_key = item.get('Банк_Key')
                if bank_key and bank_key != "00000000-0000-0000-0000-000000000000":
                    try:
                        bank_info = odata_client.get_bank_by_key(bank_key)
                        if bank_info:
                            if not bank_name:
                                bank_name = (
                                    bank_info.get('Description') or
                                    bank_info.get('Наименование') or
                                    bank_info.get('НаименованиеПолное')
                                )
                            if not bank_bik:
                                # БИК хранится в поле Code (английскими буквами)
                                bank_bik = bank_info.get('Code') or bank_info.get('Код') or bank_info.get('БИК')
                    except Exception as e:
                        logger.warning(f"Failed to fetch bank by key {bank_key}: {e}")

            if bank_name or bank_bik:
                accounts[account_number] = (
                    bank_name[:500] if bank_name else None,
                    bank_bik[:20] if bank_bik else None
                )
                logger.info(f"  Счет {account_number}: {bank_name} (БИК: {bank_bik})")

        return accounts

    except Exception as e:
        logger.error(f"Failed to fetch bank accounts for org {org_external_id}: {e}")
        return {}


def update_bank_info():
    """Обновить информацию о банках в существующих транзакциях"""

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
        # Получаем список организаций с их внешними ID
        organizations = db.query(Organization).filter(
            Organization.external_id_1c.isnot(None)
        ).all()

        logger.info(f"Найдено организаций: {len(organizations)}")

        # Получаем уникальные пары (organization_id, account_number) где нет БИК
        query = text("""
            SELECT DISTINCT organization_id, account_number, COUNT(*) as cnt
            FROM bank_transactions
            WHERE our_bank_bik IS NULL
              AND account_number IS NOT NULL
              AND account_number != 'Касса'
              AND organization_id IS NOT NULL
            GROUP BY organization_id, account_number
            ORDER BY organization_id, account_number
        """)

        results = db.execute(query).fetchall()
        logger.info(f"Найдено уникальных счетов для обновления: {len(results)}")

        # Создаем маппинг organization_id -> Organization
        org_map = {org.id: org for org in organizations}

        updated_count = 0
        skipped_count = 0

        # Группируем по организациям
        org_accounts = {}
        for row in results:
            org_id = row[0]
            account_number = row[1]
            count = row[2]

            if org_id not in org_accounts:
                org_accounts[org_id] = []
            org_accounts[org_id].append((account_number, count))

        # Обрабатываем каждую организацию
        for org_id, accounts in org_accounts.items():
            org = org_map.get(org_id)
            if not org or not org.external_id_1c:
                logger.warning(f"Organization {org_id} not found or has no external_id_1c")
                skipped_count += sum(cnt for _, cnt in accounts)
                continue

            logger.info(f"\nОбработка организации: {org.name} (ID: {org_id})")
            logger.info(f"  Внешний ID: {org.external_id_1c}")
            logger.info(f"  Счетов для обновления: {len(accounts)}")

            # Получаем все банковские счета организации из 1С
            bank_accounts = get_organization_bank_accounts(odata_client, org.external_id_1c)

            if not bank_accounts:
                logger.warning(f"  Не удалось получить банковские счета из 1С")
                skipped_count += sum(cnt for _, cnt in accounts)
                continue

            # Обновляем каждый счет
            for account_number, count in accounts:
                if account_number in bank_accounts:
                    bank_name, bank_bik = bank_accounts[account_number]

                    # Обновляем транзакции (обновляем оба поля, даже если название уже есть)
                    update_query = text("""
                        UPDATE bank_transactions
                        SET our_bank_name = :bank_name,
                            our_bank_bik = :bank_bik
                        WHERE organization_id = :org_id
                          AND account_number = :account_number
                          AND our_bank_bik IS NULL
                    """)

                    result = db.execute(update_query, {
                        'bank_name': bank_name,
                        'bank_bik': bank_bik,
                        'org_id': org_id,
                        'account_number': account_number
                    })

                    db.commit()
                    updated_count += count
                    logger.info(f"  ✓ Обновлено {count} транзакций для счета {account_number}")
                else:
                    logger.warning(f"  ✗ Счет {account_number} не найден в 1С")
                    skipped_count += count

        logger.info(f"\n{'='*60}")
        logger.info(f"Обновление завершено!")
        logger.info(f"Обновлено транзакций: {updated_count}")
        logger.info(f"Пропущено транзакций: {skipped_count}")
        logger.info(f"{'='*60}")

    except Exception as e:
        logger.error(f"Error updating bank info: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Запуск скрипта обновления информации о банках...")
    update_bank_info()
