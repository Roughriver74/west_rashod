from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Посмотрим на конкретный пример дубликатов со всеми полями
query = text("""
    SELECT *
    FROM fin_expense_details
    WHERE expense_operation_id = 'Списание с расчетного счета 0В00-005526 от 25.07.2022 14:11:20'
      AND contract_number = 'Договор № КР/062020-000209 от 13.03.2020г.'
      AND payment_type ILIKE '%погашение долга%'
    ORDER BY id
""")

result = db.execute(query)
rows = result.fetchall()

print("\n=== ПРИМЕР ДУБЛИРОВАННЫХ ЗАПИСЕЙ ===")
print(f"Найдено записей: {len(rows)}\n")

if rows:
    # Получим названия колонок
    columns = result.keys()

    for i, row in enumerate(rows, 1):
        print(f"--- Запись {i} ---")
        for col, val in zip(columns, row):
            print(f"{col}: {val}")
        print()

# Проверим, есть ли различия в ID между дублями
query2 = text("""
    WITH duplicates AS (
        SELECT
            id,
            expense_operation_id,
            contract_number,
            payment_amount,
            ROW_NUMBER() OVER (
                PARTITION BY expense_operation_id, contract_number, payment_amount, payment_type
                ORDER BY id
            ) as rn
        FROM fin_expense_details
        WHERE payment_type ILIKE '%погашение долга%'
          AND contract_number IS NOT NULL
    )
    SELECT
        COUNT(*) as total_duplicates,
        COUNT(CASE WHEN rn = 1 THEN 1 END) as first_occurrence,
        COUNT(CASE WHEN rn = 2 THEN 1 END) as second_occurrence,
        COUNT(CASE WHEN rn > 2 THEN 1 END) as more_than_two
    FROM duplicates
""")

result2 = db.execute(query2)
stats = result2.fetchone()

print("\n=== СТАТИСТИКА ДУБЛЕЙ ===")
print(f"Всего записей (включая дубли): {stats[0]}")
print(f"Первое вхождение (оригинальные): {stats[1]}")
print(f"Второе вхождение (дубликаты): {stats[2]}")
print(f"Более 2 вхождений: {stats[3]}")

db.close()
