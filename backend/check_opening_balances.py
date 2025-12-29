from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Проверка начальных сальдо контрактов
query = text("""
    SELECT
        COUNT(*) as contracts_with_opening_balance,
        SUM(opening_balance) as total_opening_balance
    FROM fin_contracts
    WHERE opening_balance IS NOT NULL
      AND opening_balance != 0
""")

result = db.execute(query).fetchone()

print(f"\n=== НАЧАЛЬНЫЕ САЛЬДО ДОГОВОРОВ ===")
print(f"Контрактов с начальным сальдо: {result[0]}")
print(f"Сумма начальных сальдо: {result[1]:,.2f} руб." if result[1] else "Сумма: 0.00 руб.")

# Несколько примеров
query2 = text("""
    SELECT contract_number, opening_balance
    FROM fin_contracts
    WHERE opening_balance IS NOT NULL
      AND opening_balance != 0
    ORDER BY opening_balance DESC
    LIMIT 5
""")

rows = db.execute(query2).fetchall()
if rows:
    print(f"\nПримеры контрактов с начальным сальдо:")
    for row in rows:
        print(f"  {row[0]}: {row[1]:,.2f} руб.")
else:
    print("\nНет контрактов с начальным сальдо")

db.close()
