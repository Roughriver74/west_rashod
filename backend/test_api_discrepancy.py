"""
Тестовый скрипт для сравнения результатов API get_credit_balances и get_contracts_summary
"""
import sys
from datetime import date
from app.db.session import SessionLocal
from app.db.models import User
from app.modules.fin.api.analytics import get_credit_balances, get_contracts_summary

# Create database session
db = SessionLocal()

# Get any user for auth (required by endpoints)
user = db.query(User).first()
if not user:
    print("ERROR: No users found in database")
    sys.exit(1)

print("\n=== ТЕСТ API БЕЗ ФИЛЬТРОВ ===\n")

# Test 1: No filters
print("1. get_credit_balances (без фильтров):")
balances1 = get_credit_balances(
    date_from=None,
    date_to=None,
    organizations=None,
    payers=None,
    excluded_payers=None,
    contracts=None,
    db=db,
    current_user=user
)
print(f"   Opening Balance: {balances1.opening_balance:,.2f}")
print(f"   Period Received: {balances1.period_received:,.2f}")
print(f"   Period Principal Paid: {balances1.period_principal_paid:,.2f}")
print(f"   Period Interest Paid: {balances1.period_interest_paid:,.2f}")
print(f"   Closing Balance: {balances1.closing_balance:,.2f}")
print(f"   Total Debt: {balances1.total_debt:,.2f}")

print("\n2. get_contracts_summary (без фильтров):")
contracts1 = get_contracts_summary(
    date_from=None,
    date_to=None,
    organizations=None,
    payers=None,
    excluded_payers=None,
    contracts=None,
    page=1,
    limit=100000,
    search=None,
    db=db,
    current_user=user
)
total_received = sum(c.totalReceived for c in contracts1.data)
total_principal = sum(c.principal for c in contracts1.data)
total_balance = sum(c.balance for c in contracts1.data)
print(f"   Contracts: {len(contracts1.data)}")
print(f"   Total Received: {total_received:,.2f}")
print(f"   Total Principal: {total_principal:,.2f}")
print(f"   Total Balance: {total_balance:,.2f}")

print(f"\n   РАЗНИЦА в Closing Balance: {abs(balances1.closing_balance - total_balance):,.2f} руб.")

# Test 2: With date filter (from 2025-01-01)
print("\n\n=== ТЕСТ API С ФИЛЬТРОМ ПО ДАТЕ (с 2025-01-01) ===\n")

date_from = date(2025, 1, 1)

print("3. get_credit_balances (date_from=2025-01-01):")
balances2 = get_credit_balances(
    date_from=date_from,
    date_to=None,
    organizations=None,
    payers=None,
    excluded_payers=None,
    contracts=None,
    db=db,
    current_user=user
)
print(f"   Opening Balance: {balances2.opening_balance:,.2f}")
print(f"   Period Received: {balances2.period_received:,.2f}")
print(f"   Period Principal Paid: {balances2.period_principal_paid:,.2f}")
print(f"   Period Interest Paid: {balances2.period_interest_paid:,.2f}")
print(f"   Closing Balance: {balances2.closing_balance:,.2f}")
print(f"   Total Debt: {balances2.total_debt:,.2f}")

print("\n4. get_contracts_summary (date_from=2025-01-01):")
contracts2 = get_contracts_summary(
    date_from=date_from,
    date_to=None,
    organizations=None,
    payers=None,
    excluded_payers=None,
    contracts=None,
    page=1,
    limit=100000,
    search=None,
    db=db,
    current_user=user
)
total_received2 = sum(c.totalReceived for c in contracts2.data)
total_principal2 = sum(c.principal for c in contracts2.data)
total_balance2 = sum(c.balance for c in contracts2.data)
print(f"   Contracts: {len(contracts2.data)}")
print(f"   Total Received: {total_received2:,.2f}")
print(f"   Total Principal: {total_principal2:,.2f}")
print(f"   Total Balance: {total_balance2:,.2f}")

print(f"\n   РАЗНИЦА в Closing Balance: {abs(balances2.closing_balance - total_balance2):,.2f} руб.")

db.close()
