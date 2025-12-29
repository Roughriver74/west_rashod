"""
Детальная проверка расхождения между API
"""
import sys
from datetime import date
from app.db.session import SessionLocal
from app.db.models import User
from app.modules.fin.api.analytics import get_credit_balances, get_contracts_summary

db = SessionLocal()
user = db.query(User).first()

date_from = date(2025, 1, 1)

print("\n=== ДЕТАЛЬНЫЙ АНАЛИЗ С ФИЛЬТРОМ date_from=2025-01-01 ===\n")

# API 1: get_credit_balances
balances = get_credit_balances(
    date_from=date_from,
    date_to=None,
    organizations=None,
    payers=None,
    excluded_payers=None,
    contracts=None,
    db=db,
    current_user=user
)

print(f"get_credit_balances:")
print(f"  Closing Balance: {balances.closing_balance:,.2f} руб.")

# API 2: get_contracts_summary
contracts = get_contracts_summary(
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

total_balance = sum(c.balance for c in contracts.data)
print(f"\nget_contracts_summary:")
print(f"  Количество контрактов: {len(contracts.data)}")
print(f"  Общий баланс: {total_balance:,.2f} руб.")

print(f"\nРАЗНИЦА: {abs(balances.closing_balance - total_balance):,.2f} руб.")

# Топ-10 контрактов по балансу
print(f"\nТоп-10 контрактов по балансу:")
top_contracts = sorted(contracts.data, key=lambda x: x.balance, reverse=True)[:10]
for i, contract in enumerate(top_contracts, 1):
    print(f"{i}. {contract.contractNumber[:40]:<40} {contract.balance:>15,.2f} руб.")
    print(f"   Received: {contract.totalReceived:>15,.2f}, Principal: {contract.principal:>15,.2f}")

# Проверим контракты с очень большим балансом (больше 1 млрд)
large_balance_contracts = [c for c in contracts.data if c.balance > 1_000_000_000]
if large_balance_contracts:
    print(f"\n⚠️  ВНИМАНИЕ: Найдено {len(large_balance_contracts)} контрактов с балансом > 1 млрд руб.!")
    print("Это может указывать на проблему в расчёте баланса.")
    for contract in large_balance_contracts[:5]:
        print(f"\n  Контракт: {contract.contractNumber}")
        print(f"  Баланс: {contract.balance:,.2f} руб.")
        print(f"  Received: {contract.totalReceived:,.2f}")
        print(f"  Principal: {contract.principal:,.2f}")
        print(f"  Операций: {contract.operationsCount}")

db.close()
