from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Проверка дублей в fin_expenses
query = text("""
    SELECT
        COUNT(*) as total_records,
        COUNT(DISTINCT operation_id) as unique_operations
    FROM fin_expenses
""")

result = db.execute(query)
stats = result.fetchone()

print("\n=== СТАТИСТИКА fin_expenses ===")
print(f"Всего записей: {stats[0]}")
print(f"Уникальных operation_id: {stats[1]}")

if stats[0] != stats[1]:
    print(f"⚠️ НАЙДЕНЫ ДУБЛИКАТЫ: {stats[0] - stats[1]} дублированных записей")

    # Найдем примеры дублей
    query2 = text("""
        SELECT
            operation_id,
            COUNT(*) as count,
            MIN(id) as first_id,
            MAX(id) as second_id
        FROM fin_expenses
        GROUP BY operation_id
        HAVING COUNT(*) > 1
        LIMIT 5
    """)

    result2 = db.execute(query2)
    duplicates = result2.fetchall()

    print(f"\nПримеры дублированных operation_id:")
    for row in duplicates:
        print(f"  {row[0]}: {row[1]} записей (IDs: {row[2]}, {row[3]})")
else:
    print("✅ Дубликаты не найдены")

# Проверка fin_receipts
query3 = text("""
    SELECT
        COUNT(*) as total_records,
        COUNT(DISTINCT operation_id) as unique_operations
    FROM fin_receipts
""")

result3 = db.execute(query3)
receipts_stats = result3.fetchone()

print("\n=== СТАТИСТИКА fin_receipts ===")
print(f"Всего записей: {receipts_stats[0]}")
print(f"Уникальных operation_id: {receipts_stats[1]}")

if receipts_stats[0] != receipts_stats[1]:
    print(f"⚠️ НАЙДЕНЫ ДУБЛИКАТЫ: {receipts_stats[0] - receipts_stats[1]} дублированных записей")
else:
    print("✅ Дубликаты не найдены")

db.close()
