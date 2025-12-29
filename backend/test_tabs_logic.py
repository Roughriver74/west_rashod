"""
Проверка логики для двух вкладок:
1. "По задолженности" - контракты с остатком > 100 руб
2. "По активности" - контракты с операциями в периоде
"""
from datetime import date
from app.db.session import SessionLocal
from app.db.models import User
from app.modules.fin.api.analytics import get_contracts_summary

db = SessionLocal()
user = db.query(User).first()

date_from = date(2025, 1, 1)

print("\n=== ПРОВЕРКА ЛОГИКИ ВКЛАДОК ===\n")

# Получить все контракты
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

print(f"Всего контрактов в результате: {len(contracts.data)}\n")

# Вкладка 1: "По задолженности" (balance > 100)
debt_contracts = [c for c in contracts.data if c.balance > 100]
print(f"ВКЛАДКА 1 - 'По задолженности' (balance > 100 руб):")
print(f"  Контрактов: {len(debt_contracts)}")
print(f"  Общий остаток: {sum(c.balance for c in debt_contracts):,.2f} руб.")

# Вкладка 2: "По активности" (операции в периоде)
activity_contracts = [
    c for c in contracts.data
    if c.operationsCount > 0 or c.totalReceived > 0 or c.principal > 0
]
print(f"\nВКЛАДКА 2 - 'По активности' (операции в периоде):")
print(f"  Контрактов: {len(activity_contracts)}")
print(f"  Общая сумма выплат: {sum(c.totalPaid for c in activity_contracts):,.2f} руб.")

# Контракты, которые есть в обеих вкладках
both = [c for c in debt_contracts if c in activity_contracts]
print(f"\nПересечение (контракты в обеих вкладках): {len(both)}")

# Контракты только с долгом (без активности в периоде)
only_debt = [c for c in debt_contracts if c not in activity_contracts]
print(f"Только с долгом (без активности): {len(only_debt)}")
if only_debt:
    print("  Примеры:")
    for c in only_debt[:3]:
        print(f"    {c.contractNumber[:40]:<40} Balance: {c.balance:>12,.2f} руб, Операций: {c.operationsCount}")

# Контракты только с активностью (но без долга)
only_activity = [c for c in activity_contracts if c not in debt_contracts]
print(f"\nТолько с активностью (без долга): {len(only_activity)}")
if only_activity:
    print("  Примеры:")
    for c in only_activity[:3]:
        print(f"    {c.contractNumber[:40]:<40} Balance: {c.balance:>12,.2f} руб, Операций: {c.operationsCount}")

# Проверка: все контракты должны попадать хотя бы в одну вкладку
all_unique = set(debt_contracts) | set(activity_contracts)
print(f"\n✓ Проверка: Все {len(contracts.data)} контрактов попадают в хотя бы одну вкладку: {len(all_unique) == len(contracts.data)}")

db.close()
