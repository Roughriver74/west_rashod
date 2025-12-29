from app.db.session import SessionLocal
from sqlalchemy import text, func
from app.modules.fin.models import FinReceipt, FinExpense, FinContract

db = SessionLocal()

print("\n=== АНАЛИЗ ПОКРЫТИЯ КОНТРАКТОВ ===\n")

# 1. Контракты с расходами (expenses)
contracts_with_expenses = db.query(FinContract.id).join(
    FinExpense, FinExpense.contract_id == FinContract.id
).distinct().count()

# 2. Все контракты
total_contracts = db.query(FinContract).count()

# 3. Контракты с поступлениями
contracts_with_receipts = db.query(FinContract.id).join(
    FinReceipt, FinReceipt.contract_id == FinContract.id
).distinct().count()

print(f"Всего контрактов: {total_contracts}")
print(f"Контрактов с расходами (в таблице): {contracts_with_expenses}")
print(f"Контрактов с поступлениями: {contracts_with_receipts}")

# 4. Поступления без привязки к контрактам
receipts_total = db.query(func.coalesce(func.sum(FinReceipt.amount), 0)).scalar()
receipts_with_contract = db.query(func.coalesce(func.sum(FinReceipt.amount), 0)).filter(
    FinReceipt.contract_id.isnot(None)
).scalar()

print(f"\nПоступления:")
print(f"  Всего: {float(receipts_total):,.2f} руб.")
print(f"  С привязкой к контрактам: {float(receipts_with_contract):,.2f} руб.")
print(f"  Без привязки: {float(receipts_total - receipts_with_contract):,.2f} руб.")

# 5. Проверим балансы через оба метода
# Метод 1: как get_credit_balances (все транзакции)
total_receipts = float(db.query(func.coalesce(func.sum(FinReceipt.amount), 0)).scalar() or 0)
total_principal_query = text("""
    SELECT COALESCE(SUM(fed.payment_amount), 0)
    FROM fin_expense_details fed
    JOIN fin_expenses fe ON fed.expense_operation_id = fe.operation_id
    WHERE fed.payment_type ILIKE '%погашение долга%'
""")
total_principal = float(db.execute(total_principal_query).scalar() or 0)

credit_balances_method = total_receipts - total_principal

print(f"\nМетод get_credit_balances (все транзакции):")
print(f"  Поступления: {total_receipts:,.2f}")
print(f"  Погашение долга: {total_principal:,.2f}")
print(f"  Баланс: {credit_balances_method:,.2f}")

# Метод 2: как get_contracts_summary (только контракты с expenses)
contracts_summary_query = text("""
    WITH contract_receipts AS (
        SELECT fc.contract_number, COALESCE(SUM(fr.amount), 0) as received
        FROM fin_contracts fc
        LEFT JOIN fin_receipts fr ON fr.contract_id = fc.id
        GROUP BY fc.contract_number
    ),
    contract_principal AS (
        SELECT fed.contract_number, COALESCE(SUM(fed.payment_amount), 0) as principal
        FROM fin_expense_details fed
        WHERE fed.payment_type ILIKE '%погашение долга%'
        GROUP BY fed.contract_number
    )
    SELECT
        COALESCE(SUM(cr.received), 0) as total_received,
        COALESCE(SUM(cp.principal), 0) as total_principal
    FROM fin_contracts fc
    JOIN fin_expenses fe ON fe.contract_id = fc.id
    LEFT JOIN contract_receipts cr ON cr.contract_number = fc.contract_number
    LEFT JOIN contract_principal cp ON cp.contract_number = fc.contract_number
    GROUP BY fc.id
""")

result = db.execute(contracts_summary_query).fetchall()
contracts_summary_received = sum(float(r[0]) for r in result)
contracts_summary_principal = sum(float(r[1]) for r in result)
contracts_summary_balance = contracts_summary_received - contracts_summary_principal

print(f"\nМетод get_contracts_summary (только контракты с expenses):")
print(f"  Поступления: {contracts_summary_received:,.2f}")
print(f"  Погашение долга: {contracts_summary_principal:,.2f}")
print(f"  Баланс: {contracts_summary_balance:,.2f}")

print(f"\nРАЗНИЦА: {abs(credit_balances_method - contracts_summary_balance):,.2f} руб.")

db.close()
