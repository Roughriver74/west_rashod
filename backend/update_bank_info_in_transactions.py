"""
Утилита для обновления банковской информации в существующих транзакциях

Использование:
    python update_bank_info_in_transactions.py [--dry-run] [--limit N]

Опции:
    --dry-run    Только показать, что будет обновлено, без записи в БД
    --limit N    Обработать только N транзакций (для тестирования)
"""
import sys
import argparse
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import BankTransaction
from app.services.odata_1c_client import OData1CClient
from app.core.config import settings


def load_all_bank_accounts(client: OData1CClient) -> dict[str, tuple[str, str]]:
    """
    Загрузить все банковские счета из 1С в кэш

    Returns:
        Dict[account_number, Tuple[bank_name, bank_bik]]
    """
    print("Загрузка банковских счетов из 1С...")
    accounts_cache = {}

    try:
        skip = 0
        page_size = 100

        while True:
            response = client._make_request(
                method='GET',
                endpoint='Catalog_БанковскиеСчетаОрганизаций',
                params={
                    '$format': 'json',
                    '$expand': 'Банк',
                    '$top': page_size,
                    '$skip': skip
                }
            )

            results = response.get('value', [])

            if not results:
                break

            for account_data in results:
                account_number = account_data.get('НомерСчета')

                if not account_number:
                    continue

                # Получаем информацию о банке
                bank_name = None
                bank_bik = None

                # Из расширенных данных $expand
                bank_data = account_data.get('Банк')
                if bank_data and isinstance(bank_data, dict):
                    bank_name = (
                        bank_data.get('Description') or
                        bank_data.get('Наименование') or
                        bank_data.get('НаименованиеПолное')
                    )
                    bank_bik = bank_data.get('Code') or bank_data.get('Код') or bank_data.get('БИК')

                # Fallback: данные напрямую из account_data
                if not bank_name or not bank_bik:
                    bank_name = bank_name or account_data.get('НаименованиеБанка')
                    bank_bik = bank_bik or account_data.get('БИКБанка')

                if bank_name and bank_bik:
                    accounts_cache[account_number] = (
                        str(bank_name)[:500],
                        str(bank_bik)[:20]
                    )

            skip += page_size

        print(f"✅ Загружено {len(accounts_cache)} банковских счетов")
        return accounts_cache

    except Exception as e:
        print(f"❌ Ошибка при загрузке банковских счетов: {e}")
        return accounts_cache


def update_transactions_bank_info(dry_run: bool = False, limit: int | None = None):
    """
    Обновить информацию о банке во всех транзакциях

    Args:
        dry_run: Только показать изменения, не записывать в БД
        limit: Максимальное количество обрабатываемых транзакций
    """
    db: Session = SessionLocal()

    try:
        # Инициализация 1C клиента
        client = OData1CClient(
            base_url=settings.ODATA_1C_URL,
            username=settings.ODATA_1C_USERNAME,
            password=settings.ODATA_1C_PASSWORD
        )

        # Получить транзакции без информации о банке
        query = db.query(BankTransaction).filter(
            BankTransaction.our_bank_name.is_(None),
            BankTransaction.account_number.isnot(None),
            BankTransaction.account_number != 'Касса'
        )

        if limit:
            query = query.limit(limit)

        transactions = query.all()

        total = len(transactions)
        updated = 0
        errors = 0

        print(f"\n{'=' * 80}")
        print(f"Обновление банковской информации в транзакциях")
        print(f"{'=' * 80}")
        print(f"Всего транзакций для обработки: {total}")
        print(f"Режим: {'DRY RUN (без записи в БД)' if dry_run else 'ЗАПИСЬ В БД'}")
        print(f"{'=' * 80}\n")

        # Загружаем все банковские счета из 1С
        accounts_cache = load_all_bank_accounts(client)
        print(f"\n{'=' * 80}\n")

        # Обрабатываем транзакции
        for i, transaction in enumerate(transactions, 1):
            account_number = transaction.account_number

            # Ищем в кэше
            if account_number in accounts_cache:
                bank_name, bank_bik = accounts_cache[account_number]

                print(f"[{i}/{total}] ✓ Счет {account_number}: {bank_name} (БИК: {bank_bik})")

                if not dry_run:
                    transaction.our_bank_name = bank_name
                    transaction.our_bank_bik = bank_bik

                updated += 1
            else:
                print(f"[{i}/{total}] ⚠️  Счет {account_number}: не найден в справочнике 1С")
                errors += 1

        # Сохранить изменения
        if not dry_run and updated > 0:
            db.commit()
            print(f"\n✅ Изменения сохранены в базу данных")

        # Результаты
        print(f"\n{'=' * 80}")
        print(f"Результаты обновления:")
        print(f"{'=' * 80}")
        print(f"Обработано транзакций: {total}")
        print(f"Обновлено успешно: {updated}")
        print(f"Ошибок/не найдено: {errors}")
        print(f"Загружено банковских счетов из 1С: {len(accounts_cache)}")

        if dry_run:
            print(f"\n⚠️  DRY RUN - изменения не были сохранены")
            print(f"Для записи в БД запустите без флага --dry-run")

        print(f"{'=' * 80}\n")

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Обновить банковскую информацию в существующих транзакциях'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Только показать изменения, не записывать в БД'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Обработать только N транзакций (для тестирования)'
    )

    args = parser.parse_args()

    return update_transactions_bank_info(
        dry_run=args.dry_run,
        limit=args.limit
    )


if __name__ == '__main__':
    sys.exit(main())
