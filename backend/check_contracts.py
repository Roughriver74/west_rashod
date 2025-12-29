from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Проверим количество контрактов
query = text("""
    SELECT COUNT(DISTINCT contract_number) as contracts_count
    FROM fin_expense_details
    WHERE contract_number IS NOT NULL
      AND contract_number != ''
      AND payment_type ILIKE '%погашение долга%'
""")

result = db.execute(query)
count = result.fetchone()[0]

print(f"\nКонтрактов в БД: {count}")

# Проверим несколько примеров
query2 = text("""
    SELECT contract_number, SUM(payment_amount) as total_paid
    FROM fin_expense_details
    WHERE contract_number IS NOT NULL
      AND payment_type ILIKE '%погашение долга%'
    GROUP BY contract_number
    ORDER BY total_paid DESC
    LIMIT 5
""")

result2 = db.execute(query2)
rows = result2.fetchall()

print(f"\nТоп-5 контрактов по сумме погашений:")
for row in rows:
    print(f"  {row[0]}: {row[1]:,.2f} руб.")

# Проверим есть ли вообще поступления
query3 = text("""
    SELECT COUNT(*) as receipts_count,
           COUNT(DISTINCT contract_number) as unique_contracts
    FROM fin_receipts
    WHERE contract_number IS NOT NULL
""")

result3 = db.execute(query3)
receipts = result3.fetchone()

print(f"\nПоступления:")
print(f"  Всего записей: {receipts[0]}")
print(f"  Уникальных контрактов: {receipts[1]}")

db.close()
