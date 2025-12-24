"""
Тест парсинга НДС из реальных данных
"""

import re
from decimal import Decimal
from typing import Optional


def extract_vat_from_text(text: str) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Извлечение НДС из текста назначения платежа.

    Returns:
        tuple: (vat_amount, vat_rate) или (None, None)
    """
    if not text:
        return None, None

    text_upper = text.upper()

    # Паттерн 0: "НДС не облагается" или "НДС НЕ ОБЛАГАЕТСЯ" - ставка 0%
    pattern0 = r'НДС\s+НЕ\s+ОБЛАГАЕТСЯ'
    if re.search(pattern0, text_upper):
        return None, Decimal('0')

    # Паттерн 0.5: "В т.ч. НДС (20%) 900,00 руб." - процент в скобках
    # "В ТОМ ЧИСЛЕ НДС (10%) 224,55 руб."
    pattern05 = r'(?:В\s+ТОМ\s+ЧИСЛЕ|В\s+Т\.?\s*Ч\.?)\s+НДС\s*\((\d+)%\)\s*([\d\s\.,\-]+)(?:РУБ|РУБЛЕЙ)?'
    match = re.search(pattern05, text_upper)
    if match:
        rate_str = match.group(1)
        amount_str = match.group(2).replace(' ', '').replace('-', '.').replace(',', '.')
        # Удаляем множественные точки (если есть)
        parts = amount_str.split('.')
        if len(parts) > 2:
            amount_str = ''.join(parts[:-1]) + '.' + parts[-1]
        try:
            vat_rate = Decimal(rate_str)
            vat_amount = Decimal(amount_str)
            return vat_amount, vat_rate
        except (ValueError, Exception):
            pass

    # Паттерн 1: "НДС 20% - 3344,56" или "НДС 10% 1000.00"
    # Ставка и сумма с опциональным дефисом между ними
    pattern1 = r'НДС\s+(\d+)\s*%\s*-?\s*([\d\s\.,]+)(?:РУБ|РУБЛЕЙ)?'
    match = re.search(pattern1, text_upper)
    if match:
        rate_str = match.group(1)
        amount_str = match.group(2).replace(' ', '').replace(',', '.')
        # Удаляем множественные точки (если есть)
        parts = amount_str.split('.')
        if len(parts) > 2:
            amount_str = ''.join(parts[:-1]) + '.' + parts[-1]
        try:
            vat_rate = Decimal(rate_str)
            vat_amount = Decimal(amount_str)
            return vat_amount, vat_rate
        except (ValueError, Exception):
            pass

    # Паттерн 2: "В ТОМ ЧИСЛЕ НДС - 32971.00" или "В Т.Ч. НДС 5953-49"
    # Различные варианты "в том числе" + сумма
    pattern2 = r'(?:В\s+ТОМ\s+ЧИСЛЕ|В\s+Т\.?\s*Ч\.?)\s+НДС\s*-?\s*([\d\s\.,\-]+)(?:РУБ|РУБЛЕЙ)?'
    match = re.search(pattern2, text_upper)
    if match:
        vat_str = match.group(1).replace(' ', '').replace('-', '.').replace(',', '.')
        # Удаляем множественные точки
        parts = vat_str.split('.')
        if len(parts) > 2:
            vat_str = ''.join(parts[:-1]) + '.' + parts[-1]
        try:
            vat_amount = Decimal(vat_str)
            return vat_amount, None
        except (ValueError, Exception):
            pass

    # Паттерн 3: Просто "НДС - 1000.00" или "НДС 1000"
    pattern3 = r'(?<![А-Я])НДС\s*-?\s*([\d\s\.,]+)(?:РУБ|РУБЛЕЙ)?(?!\s*%)'
    match = re.search(pattern3, text_upper)
    if match:
        # Проверяем что это не "НДС 20%" (не ставка)
        amount_str = match.group(1).replace(' ', '').replace(',', '.')
        parts = amount_str.split('.')
        if len(parts) > 2:
            amount_str = ''.join(parts[:-1]) + '.' + parts[-1]
        try:
            vat_amount = Decimal(amount_str)
            # Игнорируем если это похоже на ставку (< 100)
            if vat_amount >= 100:
                return vat_amount, None
        except (ValueError, Exception):
            pass

    # Паттерн 4: Только ставка "НДС 20%"
    pattern4 = r'НДС\s+(\d+)\s*%'
    match = re.search(pattern4, text_upper)
    if match:
        rate_str = match.group(1)
        try:
            vat_rate = Decimal(rate_str)
            return None, vat_rate
        except (ValueError, Exception):
            pass

    return None, None


# Тестовые случаи из реальных данных
test_cases = [
    {
        'text': 'Оплата по УПД 317398 от 21.11.2025. В том числе НДС - 32971.00 рублей.',
        'expected_amount': Decimal('32971.00'),
        'expected_rate': None,
        'description': 'Первый кейс со скриншота'
    },
    {
        'text': 'Оплата за стом.материалы по сч.166105 от 23.12.25 г. НДС 10% - 3344,56руб',
        'expected_amount': Decimal('3344.56'),
        'expected_rate': Decimal('10'),
        'description': 'Второй кейс со скриншота'
    },
    {
        'text': 'ОПЛАТА ПО СЧЕТУ № 141086 ОТ 5 НОЯБРЯ 2025 Г. СТОМ. МАТЕРИАЛЫ СУММА 60571-00 В Т.Ч. НДС 5953-49',
        'expected_amount': Decimal('5953.49'),
        'expected_rate': None,
        'description': 'Старый пример с "В Т.Ч."'
    },
    {
        'text': 'Оплата НДС 20% 2000.00',
        'expected_amount': Decimal('2000.00'),
        'expected_rate': Decimal('20'),
        'description': 'Ставка и сумма через пробел'
    },
    {
        'text': 'Оплата НДС 20%',
        'expected_amount': None,
        'expected_rate': Decimal('20'),
        'description': 'Только ставка'
    },
    {
        'text': 'Возврат денежных средств по акту сверки взаиморасчетов. В т.ч. НДС (20%) 900,00 руб.',
        'expected_amount': Decimal('900.00'),
        'expected_rate': Decimal('20'),
        'description': 'НДС с процентом в скобках (20%)'
    },
    {
        'text': 'Возврат денежных средств по акту сверки взаиморасчетов. В т.ч. НДС (10%) 224,55 руб.',
        'expected_amount': Decimal('224.55'),
        'expected_rate': Decimal('10'),
        'description': 'НДС с процентом в скобках (10%)'
    },
    {
        'text': 'СЧЕТ 166227 ОТ 23.12.2025. НДС НЕ ОБЛАГАЕТСЯ',
        'expected_amount': None,
        'expected_rate': Decimal('0'),
        'description': 'НДС не облагается (0%)'
    },
    {
        'text': 'Зачисление средств по операциям эквайринга. Мерчант №551000454440. Комиссия 747,50. Возврат покупки 0.00/0.00.НДС не облагается.',
        'expected_amount': None,
        'expected_rate': Decimal('0'),
        'description': 'НДС не облагается в конце текста'
    },
]


def run_tests():
    print("🧪 Тестирование парсинга НДС\n")
    print("=" * 80)

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n📝 Тест {i}: {test['description']}")
        print(f"Текст: {test['text'][:70]}...")

        vat_amount, vat_rate = extract_vat_from_text(test['text'])

        expected_amount = test['expected_amount']
        expected_rate = test['expected_rate']

        amount_match = vat_amount == expected_amount
        rate_match = vat_rate == expected_rate

        if amount_match and rate_match:
            print(f"✅ PASSED")
            print(f"   Сумма НДС: {vat_amount} (ожидалось: {expected_amount})")
            print(f"   Ставка НДС: {vat_rate}% (ожидалось: {expected_rate}%)")
            passed += 1
        else:
            print(f"❌ FAILED")
            print(f"   Сумма НДС: {vat_amount} (ожидалось: {expected_amount}) {'✅' if amount_match else '❌'}")
            print(f"   Ставка НДС: {vat_rate}% (ожидалось: {expected_rate}%) {'✅' if rate_match else '❌'}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"\n📊 Результаты: {passed} пройдено, {failed} не пройдено из {len(test_cases)} тестов")

    if failed == 0:
        print("🎉 Все тесты пройдены успешно!")
    else:
        print(f"⚠️ Некоторые тесты не прошли. Необходимо доработать regex паттерны.")

    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
