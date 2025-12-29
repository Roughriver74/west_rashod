#!/usr/bin/env python3
"""Test UPSERT performance (without clearing data)"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import SessionLocal
from app.modules.fin.services.importer import FinDataImporter

db = SessionLocal()
importer = FinDataImporter(db)

files = [
    "/Users/evgenijsikunov/projects/west/west_fin/west-west_fin/xls/Vest - spisanie(rasshifrovka) XLSX.xlsx"
]

print("\n=== ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ UPSERT (UPDATE) ===\n")

for file_path in files:
    filename = Path(file_path).name
    print(f"Файл: {filename}")

    start = time.time()
    success = importer.import_file(file_path)
    elapsed = time.time() - start

    print(f"Результат: {'✓ Успешно' if success else '✗ Ошибка'}")
    print(f"Время выполнения: {elapsed:.2f} сек\n")

db.close()
