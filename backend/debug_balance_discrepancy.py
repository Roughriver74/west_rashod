from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# Проверим общий баланс всех контрактов
query = text("""
    WITH contract_balances AS (
        SELECT
            fc.id,
            fc.contract_number,
            fc.opening_balance,
            COALESCE(SUM(fr.amount), 0) as total_received,
            COALESCE(SUM(
                CASE
                    WHEN fed.payment_type ILIKE '%погашение долга%'
                    THEN fed.payment_amount
                    ELSE 0
                END
            ), 0) as total_principal,
            (
                COALESCE(fc.opening_balance, 0) +
                COALESCE(SUM(fr.amount), 0) -
                COALESCE(SUM(
                    CASE
                        WHEN fed.payment_type ILIKE '%погашение долга%'
                        THEN fed.payment_amount
                        ELSE 0
                    END
                ), 0)
            ) as balance
        FROM fin_contracts fc
        LEFT JOIN fin_expenses fe ON fe.contract_id = fc.id
        LEFT JOIN fin_expense_details fed ON fed.expense_operation_id = fe.operation_id
        LEFT JOIN fin_receipts fr ON fr.contract_id = fc.id
        GROUP BY fc.id, fc.contract_number, fc.opening_balance
    )
    SELECT
        COUNT(*) as total_contracts,
        COUNT(CASE WHEN balance > 100 THEN 1 END) as contracts_over_100,
        SUM(balance) as total_balance,
        SUM(CASE WHEN balance > 100 THEN balance ELSE 0 END) as balance_over_100
    FROM contract_balances
""")

result = db.execute(query).fetchone()

print(f"\n=== АНАЛИЗ БАЛАНСОВ КОНТРАКТОВ ===")
print(f"Всего контрактов: {result[0]}")
print(f"Контрактов с балансом > 100 руб: {result[1]}")
print(f"Общий баланс всех контрактов: {result[2]:,.2f} руб." if result[2] else "0.00 руб.")
print(f"Баланс контрактов > 100 руб: {result[3]:,.2f} руб." if result[3] else "0.00 руб.")

if result[2] and result[3]:
    diff = float(result[2]) - float(result[3])
    print(f"\nРазница: {diff:,.2f} руб.")
    print(f"Это может объяснить расхождение между карточкой и таблицей!")

db.close()
