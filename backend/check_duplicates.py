from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Проверка на дубли по operation_id + payment_type + contract_number
query = text("""
    SELECT
        expense_operation_id,
        payment_type,
        contract_number,
        payment_amount,
        COUNT(*) as duplicate_count
    FROM fin_expense_details
    WHERE payment_type ILIKE '%погашение долга%'
    GROUP BY expense_operation_id, payment_type, contract_number, payment_amount
    HAVING COUNT(*) > 1
    ORDER BY duplicate_count DESC
    LIMIT 10
""")

result = db.execute(query)
duplicates = result.fetchall()

print("\n=== ДУБЛИКАТЫ В fin_expense_details ===")
if duplicates:
    print(f"Найдено {len(duplicates)} групп дублированных записей:")
    for row in duplicates:
        print(f"  Operation ID: {row[0]}, Contract: {row[2]}, Amount: {row[3]}, Count: {row[4]}")
else:
    print("Дубликаты не найдены")

# Проверка общего количества записей vs уникальных
query2 = text("""
    SELECT
        COUNT(*) as total_records,
        COUNT(DISTINCT (expense_operation_id, contract_number, payment_amount)) as unique_records
    FROM fin_expense_details
    WHERE payment_type ILIKE '%погашение долга%'
""")

result2 = db.execute(query2)
counts = result2.fetchone()
print(f"\n=== СТАТИСТИКА ===")
print(f"Всего записей: {counts[0]}")
print(f"Уникальных записей: {counts[1]}")

# Проверка: возможно ли двойное суммирование из-за JOIN
query3 = text("""
    SELECT
        COUNT(*) as rows_from_join,
        SUM(fed.payment_amount) as total_principal
    FROM fin_expense_details fed
    JOIN fin_expenses fe ON fed.expense_operation_id = fe.operation_id
    WHERE fed.payment_type ILIKE '%погашение долга%'
      AND fed.contract_number IS NOT NULL
""")

result3 = db.execute(query3)
join_stats = result3.fetchone()
print(f"\n=== РЕЗУЛЬТАТ JOIN С fin_expenses ===")
print(f"Количество строк после JOIN: {join_stats[0]}")
print(f"Сумма principal после JOIN: {join_stats[1]:,.2f}")

# Сравнение с суммой без JOIN
query4 = text("""
    SELECT
        COUNT(*) as rows_no_join,
        SUM(payment_amount) as total_principal
    FROM fin_expense_details
    WHERE payment_type ILIKE '%погашение долга%'
      AND contract_number IS NOT NULL
""")

result4 = db.execute(query4)
no_join_stats = result4.fetchone()
print(f"\n=== БЕЗ JOIN (только fin_expense_details) ===")
print(f"Количество строк: {no_join_stats[0]}")
print(f"Сумма principal: {no_join_stats[1]:,.2f}")

if join_stats[0] != no_join_stats[0]:
    print(f"\n⚠️ ВНИМАНИЕ: JOIN удваивает строки! {no_join_stats[0]} → {join_stats[0]}")
    print(f"Коэффициент дублирования: {join_stats[0] / no_join_stats[0]:.2f}x")

db.close()
