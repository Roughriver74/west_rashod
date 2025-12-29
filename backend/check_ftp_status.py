from app.db.session import SessionLocal
from app.db.models import SyncSettings
from app.modules.fin.models import FinImportLog
from sqlalchemy import desc

db = SessionLocal()

# Проверка настроек FTP
settings = db.query(SyncSettings).first()
if settings:
    print("\n=== НАСТРОЙКИ FTP СИНХРОНИЗАЦИИ ===")
    print(f"FTP импорт включен: {settings.ftp_import_enabled}")
    print(f"Интервал импорта: {settings.ftp_import_interval_hours} часов")
    print(f"Очистка данных перед импортом: {settings.ftp_import_clear_existing}")
    print(f"Последний запуск: {settings.last_ftp_import_started_at}")
    print(f"Последнее завершение: {settings.last_ftp_import_completed_at}")
    print(f"Статус: {settings.last_ftp_import_status}")
    print(f"Сообщение: {settings.last_ftp_import_message}")

# Последние 5 импортов
print("\n=== ПОСЛЕДНИЕ ИМПОРТЫ ===")
imports = db.query(FinImportLog).order_by(desc(FinImportLog.import_date)).limit(5).all()
for imp in imports:
    print(f"\n{imp.import_date.strftime('%Y-%m-%d %H:%M:%S')} - {imp.source_file}")
    print(f"  Таблица: {imp.table_name}")
    print(f"  Статус: {imp.status}")
    print(f"  Вставлено: {imp.rows_inserted}, Обновлено: {imp.rows_updated}, Ошибок: {imp.rows_failed}")
    print(f"  Время выполнения: {imp.processing_time_seconds} сек")
    if imp.error_message:
        print(f"  Ошибка: {imp.error_message}")

db.close()
