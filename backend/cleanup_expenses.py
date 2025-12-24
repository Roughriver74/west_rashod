"""
Скрипт для очистки таблицы expenses и связанных данных.
ВНИМАНИЕ: Это действие необратимо!
"""

import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

def cleanup_expenses():
    """Полностью очистить таблицу expenses и обнулить связи в bank_transactions."""

    engine = create_engine(settings.DATABASE_URL)

    try:
        with engine.begin() as conn:
            # 1. Обнулить ссылки на expenses в bank_transactions
            result1 = conn.execute(
                text("UPDATE bank_transactions SET expense_id = NULL WHERE expense_id IS NOT NULL")
            )
            print(f"✓ Обнулено expense_id в {result1.rowcount} транзакциях")

            result2 = conn.execute(
                text("UPDATE bank_transactions SET suggested_expense_id = NULL WHERE suggested_expense_id IS NOT NULL")
            )
            print(f"✓ Обнулено suggested_expense_id в {result2.rowcount} транзакциях")

            # 2. Удалить все заявки
            result3 = conn.execute(
                text("DELETE FROM expenses")
            )
            print(f"✓ Удалено {result3.rowcount} заявок из базы данных")

            # 3. Сбросить автоинкремент
            conn.execute(text("ALTER SEQUENCE expenses_id_seq RESTART WITH 1"))
            print(f"✓ Сброшен счетчик ID для таблицы expenses")

        print("\n✅ Очистка завершена успешно!")
        return True

    except Exception as e:
        print(f"\n❌ Ошибка при очистке: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ОЧИСТКА ТАБЛИЦЫ EXPENSES")
    print("=" * 60)
    print("\n⚠️  ВНИМАНИЕ! Это действие необратимо!")
    print("Будут удалены:")
    print("  - Все заявки на расход")
    print("  - Связи заявок с банковскими транзакциями")
    print("\n")

    confirm = input("Вы уверены? Введите 'ДА' для подтверждения: ")

    if confirm.upper() == "ДА":
        success = cleanup_expenses()
        sys.exit(0 if success else 1)
    else:
        print("\n❌ Очистка отменена")
        sys.exit(0)
