"""
Скрипт для удаления дубликатов из fin_expense_details.
Оставляет запись с меньшим ID (более раннюю по времени создания).
"""
from app.db.session import SessionLocal
from sqlalchemy import text
import sys

def remove_duplicates(dry_run=True):
    db = SessionLocal()

    try:
        # Сначала подсчитаем сколько будет удалено
        count_query = text("""
            WITH duplicates AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY expense_operation_id, contract_number, payment_amount, payment_type
                        ORDER BY id ASC
                    ) as rn
                FROM fin_expense_details
            )
            SELECT COUNT(*) as to_delete
            FROM duplicates
            WHERE rn > 1
        """)

        result = db.execute(count_query)
        to_delete = result.fetchone()[0]

        print(f"\n{'=' * 60}")
        print(f"УДАЛЕНИЕ ДУБЛИКАТОВ ИЗ fin_expense_details")
        print(f"{'=' * 60}")
        print(f"Записей к удалению: {to_delete}")

        if to_delete == 0:
            print("✅ Дубликаты не найдены")
            return

        if dry_run:
            print(f"\n⚠️  РЕЖИМ ТЕСТИРОВАНИЯ (dry_run=True)")
            print("Для реального удаления запустите: python remove_duplicates.py --execute")

            # Покажем примеры того, что будет удалено
            preview_query = text("""
                WITH duplicates AS (
                    SELECT
                        id,
                        expense_operation_id,
                        contract_number,
                        payment_amount,
                        created_at,
                        ROW_NUMBER() OVER (
                            PARTITION BY expense_operation_id, contract_number, payment_amount, payment_type
                            ORDER BY id ASC
                        ) as rn
                    FROM fin_expense_details
                )
                SELECT
                    id,
                    expense_operation_id,
                    contract_number,
                    payment_amount,
                    created_at
                FROM duplicates
                WHERE rn > 1
                LIMIT 5
            """)

            result = db.execute(preview_query)
            examples = result.fetchall()

            print("\nПримеры записей, которые будут удалены:")
            for row in examples:
                print(f"  ID {row[0]}: {row[1][:50]}... Amount: {row[3]}, Created: {row[4]}")
        else:
            # Реальное удаление
            print(f"\n🔥 УДАЛЕНИЕ {to_delete} ДУБЛИКАТОВ...")

            delete_query = text("""
                DELETE FROM fin_expense_details
                WHERE id IN (
                    SELECT id
                    FROM (
                        SELECT
                            id,
                            ROW_NUMBER() OVER (
                                PARTITION BY expense_operation_id, contract_number, payment_amount, payment_type
                                ORDER BY id ASC
                            ) as rn
                        FROM fin_expense_details
                    ) duplicates
                    WHERE rn > 1
                )
            """)

            result = db.execute(delete_query)
            db.commit()

            print(f"✅ Успешно удалено: {result.rowcount} записей")

            # Проверим результат
            verify_query = text("""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT (expense_operation_id, contract_number, payment_amount, payment_type)) as unique_records
                FROM fin_expense_details
                WHERE payment_type ILIKE '%погашение долга%'
            """)

            result = db.execute(verify_query)
            stats = result.fetchone()

            print(f"\n=== СТАТИСТИКА ПОСЛЕ УДАЛЕНИЯ ===")
            print(f"Всего записей: {stats[0]}")
            print(f"Уникальных записей: {stats[1]}")

            if stats[0] == stats[1]:
                print("✅ Дубликаты успешно удалены!")
            else:
                print(f"⚠️  Остались дубликаты: {stats[0] - stats[1]}")

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    if "--execute" in sys.argv:
        print("\n⚠️  ВНИМАНИЕ: Будут удалены реальные данные!")
        response = input("Продолжить? (yes/no): ")
        if response.lower() == "yes":
            remove_duplicates(dry_run=False)
        else:
            print("Отменено пользователем")
    else:
        remove_duplicates(dry_run=True)
