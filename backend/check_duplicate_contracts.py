from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("\n=== ПРОВЕРКА ДУБЛИРОВАНИЯ КОНТРАКТОВ ПО ПЛАТЕЛЬЩИКАМ ===\n")

# Проверим, есть ли контракты с несколькими разными payers
query = text("""
    SELECT
        fc.contract_number,
        COUNT(DISTINCT fe.recipient) as unique_payers,
        STRING_AGG(DISTINCT fe.recipient, ', ' ORDER BY fe.recipient) as payers
    FROM fin_contracts fc
    JOIN fin_expenses fe ON fe.contract_id = fc.id
    WHERE fe.recipient IS NOT NULL
    GROUP BY fc.contract_number
    HAVING COUNT(DISTINCT fe.recipient) > 1
    ORDER BY COUNT(DISTINCT fe.recipient) DESC
    LIMIT 10
""")

result = db.execute(query).fetchall()

if result:
    print(f"Найдено контрактов с несколькими плательщиками: {len(result)}")
    print("\nПримеры:")
    for row in result:
        print(f"\n  Контракт: {row[0]}")
        print(f"  Уникальных плательщиков: {row[1]}")
        print(f"  Плательщики: {row[2][:100]}..." if len(row[2]) > 100 else f"  Плательщики: {row[2]}")
else:
    print("Нет контрактов с несколькими плательщиками")

# Теперь проверим, как это влияет на результаты get_contracts_summary
query2 = text("""
    SELECT
        fc.contract_number,
        fe.recipient as payer,
        COUNT(*) as expense_count,
        SUM(fe.amount) as total_amount
    FROM fin_contracts fc
    JOIN fin_expenses fe ON fe.contract_id = fc.id
    GROUP BY fc.contract_number, fe.recipient
    ORDER BY fc.contract_number, fe.recipient
    LIMIT 20
""")

result2 = db.execute(query2).fetchall()

print(f"\n\n=== ПРИМЕР ГРУППИРОВКИ (первые 20 строк) ===")
print(f"{'Контракт':<30} {'Плательщик':<40} {'Операций':<10} {'Сумма':<15}")
print("-" * 100)

prev_contract = None
for row in result2:
    contract = row[0]
    payer = row[1] or "NULL"
    count = row[2]
    amount = float(row[3])

    # Выделить, если это дубликат контракта
    marker = " **ДУБЛЬ**" if contract == prev_contract else ""
    print(f"{contract:<30} {payer[:38]:<40} {count:<10} {amount:>13,.2f}{marker}")
    prev_contract = contract

db.close()
