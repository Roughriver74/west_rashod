from app.db.session import SessionLocal
from sqlalchemy import text
from datetime import date

db = SessionLocal()

date_from = date(2025, 1, 1)

print("\n=== АНАЛИЗ КОНТРАКТОВ С БАЛАНСОМ, НО БЕЗ АКТИВНОСТИ В ПЕРИОДЕ ===\n")

# Контракты с балансом до 2025-01-01 (opening balance)
query = text("""
    WITH opening_balances AS (
        SELECT
            fc.contract_number,
            COALESCE(SUM(fr.amount), 0) as receipts_before,
            COALESCE(SUM(
                CASE
                    WHEN fed.payment_type ILIKE '%погашение долга%'
                    THEN fed.payment_amount
                    ELSE 0
                END
            ), 0) as principal_before,
            (
                COALESCE(SUM(fr.amount), 0) -
                COALESCE(SUM(
                    CASE
                        WHEN fed.payment_type ILIKE '%погашение долга%'
                        THEN fed.payment_amount
                        ELSE 0
                    END
                ), 0)
            ) as opening_balance
        FROM fin_contracts fc
        LEFT JOIN fin_receipts fr ON fr.contract_id = fc.id AND fr.document_date < :date_from
        LEFT JOIN fin_expenses fe ON fe.contract_id = fc.id AND fe.document_date < :date_from
        LEFT JOIN fin_expense_details fed ON fed.expense_operation_id = fe.operation_id
        GROUP BY fc.contract_number
        HAVING (
            COALESCE(SUM(fr.amount), 0) -
            COALESCE(SUM(
                CASE
                    WHEN fed.payment_type ILIKE '%погашение долга%'
                    THEN fed.payment_amount
                    ELSE 0
                END
            ), 0)
        ) > 100
    ),
    contracts_with_expenses_in_period AS (
        SELECT DISTINCT fc.contract_number
        FROM fin_contracts fc
        JOIN fin_expenses fe ON fe.contract_id = fc.id
        WHERE fe.document_date >= :date_from
    )
    SELECT
        ob.contract_number,
        ob.opening_balance,
        CASE WHEN cwep.contract_number IS NOT NULL THEN 'Есть' ELSE 'Нет' END as has_activity
    FROM opening_balances ob
    LEFT JOIN contracts_with_expenses_in_period cwep ON cwep.contract_number = ob.contract_number
    WHERE cwep.contract_number IS NULL  -- Только контракты БЕЗ активности в периоде
    ORDER BY ob.opening_balance DESC
    LIMIT 20
""")

result = db.execute(query, {"date_from": date_from}).fetchall()

if result:
    print(f"Найдено {len(result)} контрактов с балансом > 100 руб, но БЕЗ активности в периоде:")
    print(f"\n{'Контракт':<40} {'Opening Balance':<20} {'Активность в периоде'}")
    print("-" * 80)
    total_missing_balance = 0
    for row in result:
        contract = row[0]
        balance = float(row[1])
        activity = row[2]
        total_missing_balance += balance
        print(f"{contract:<40} {balance:>18,.2f}  {activity}")

    print(f"\n{'ИТОГО упущенный баланс:':<40} {total_missing_balance:>18,.2f} руб.")
    print(f"\nЭто может объяснить разницу в ~14.4 млн руб!")
else:
    print("Нет контрактов с балансом без активности в периоде")

db.close()
