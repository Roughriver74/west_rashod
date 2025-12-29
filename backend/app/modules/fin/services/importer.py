"""
Data importer with UPSERT logic for loading parsed XLSX data into PostgreSQL
Adapted from west_fin project for fin module
"""
import logging
from typing import List, Dict, Tuple
from datetime import datetime
from pathlib import Path
import time

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.modules.fin.models import (
    FinReceipt, FinExpense, FinExpenseDetail, FinImportLog,
    FinBankAccount, FinContract
)
from app.db.models import Organization
from app.modules.fin.services.xlsx_parser import FinXLSXParser

logger = logging.getLogger(__name__)


class FinDataImporter:
    """Importer for financial data with UPSERT capabilities - fin module"""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.parser = FinXLSXParser()
        # Cache for reference data to avoid repeated DB queries
        self._org_cache = {}
        self._bank_cache = {}
        self._contract_cache = {}

    def clear_existing_data(self) -> None:
        """
        Очистить основные таблицы fin модуля перед полным импортом.
        Используется для обеспечения актуальности данных при загрузке из FTP.

        ВАЖНО: Таблица fin_manual_adjustments НЕ очищается!
        Ручные корректировки сохраняются между импортами.
        """
        logger.info("Очистка таблиц fin модуля: fin_expense_details, fin_expenses, fin_receipts")
        logger.info("ПРИМЕЧАНИЕ: Таблица fin_manual_adjustments НЕ очищается")
        try:
            # One truncate with CASCADE to respect FK на operation_id
            self.db.execute(text("TRUNCATE TABLE fin_expense_details, fin_expenses, fin_receipts RESTART IDENTITY CASCADE"))
            self.db.commit()
            # Очистить кеши
            self._org_cache.clear()
            self._bank_cache.clear()
            self._contract_cache.clear()
            logger.info("Очистка завершена")
        except SQLAlchemyError as e:
            logger.error(f"Не удалось очистить таблицы: {e}")
            self.db.rollback()
            raise

    def get_or_create_organization(self, org_name: str) -> int:
        """Get or create organization and return its ID (uses main organizations table)"""
        if not org_name:
            return None

        if org_name in self._org_cache:
            return self._org_cache[org_name]

        org = self.db.query(Organization).filter(Organization.name == org_name).first()
        if not org:
            org = Organization(name=org_name, is_active=True)
            self.db.add(org)
            self.db.flush()
            logger.info(f"Created new organization: {org_name}")

        self._org_cache[org_name] = org.id
        return org.id

    def get_or_create_bank_account(self, account_number: str, org_name: str = None) -> int:
        """Get or create fin bank account and return its ID"""
        if not account_number:
            return None

        if account_number in self._bank_cache:
            return self._bank_cache[account_number]

        bank = self.db.query(FinBankAccount).filter(FinBankAccount.account_number == account_number).first()
        if not bank:
            bank = FinBankAccount(
                account_number=account_number,
                is_active=True
            )
            self.db.add(bank)
            self.db.flush()
            logger.info(f"Created new fin bank account: {account_number}")

        self._bank_cache[account_number] = bank.id
        return bank.id

    def get_or_create_contract(self, contract_number: str, contract_date: datetime = None, org_name: str = None) -> int:
        """Get or create fin contract and return its ID"""
        if not contract_number:
            return None

        if contract_number in self._contract_cache:
            return self._contract_cache[contract_number]

        contract = self.db.query(FinContract).filter(FinContract.contract_number == contract_number).first()
        if not contract:
            contract = FinContract(
                contract_number=contract_number,
                contract_date=contract_date,
                is_active=True
            )
            self.db.add(contract)
            self.db.flush()
            logger.info(f"Created new fin contract: {contract_number}")

        self._contract_cache[contract_number] = contract.id
        return contract.id

    def upsert_receipts(self, records: List[Dict]) -> Tuple[int, int, int]:
        """
        Insert or update fin receipt records

        Args:
            records: List of receipt dictionaries

        Returns:
            Tuple[int, int, int]: (inserted, updated, failed)
        """
        inserted = 0
        updated = 0
        failed = 0

        for record in records:
            try:
                # Auto-create organization and bank account
                org_name = record.get('organization')
                bank_account = record.get('bank_account')

                if org_name:
                    record['organization_id'] = self.get_or_create_organization(org_name)

                if bank_account:
                    record['bank_account_id'] = self.get_or_create_bank_account(bank_account, org_name)

                contract_number = record.get('contract_number')
                contract_date = record.get('contract_date')
                if contract_number:
                    record['contract_id'] = self.get_or_create_contract(
                        contract_number,
                        contract_date,
                        org_name
                    )

                # Remove denormalized fields
                record.pop('organization', None)
                record.pop('bank_account', None)
                record.pop('contract_number', None)

                # Check if record exists before UPSERT
                existing = self.db.query(FinReceipt).filter(
                    FinReceipt.operation_id == record.get('operation_id')
                ).first()

                stmt = insert(FinReceipt).values(**record)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['operation_id'],
                    set_={
                        key: value
                        for key, value in record.items()
                        if key != 'operation_id'
                    }
                )

                result = self.db.execute(stmt)

                if result.rowcount > 0:
                    if existing:
                        updated += 1
                    else:
                        inserted += 1
                # rowcount = 0 with ON CONFLICT DO UPDATE is rare, don't count as failure

            except Exception as e:
                logger.error(f"Error upserting fin receipt {record.get('operation_id')}: {e}")
                failed += 1

        try:
            self.db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error committing fin receipts: {e}")
            self.db.rollback()
            return 0, 0, len(records)

        logger.info(f"Fin Receipts: {inserted} inserted, {updated} updated, {failed} failed")
        return inserted, updated, failed

    def upsert_expenses(self, records: List[Dict]) -> Tuple[int, int, int]:
        """
        Insert or update fin expense records

        Args:
            records: List of expense dictionaries

        Returns:
            Tuple[int, int, int]: (inserted, updated, failed)
        """
        inserted = 0
        updated = 0
        failed = 0

        for record in records:
            try:
                # Auto-create organization, bank account, and contract
                org_name = record.get('organization')
                bank_account = record.get('bank_account')
                contract_number = record.get('contract_number')
                contract_date = record.get('contract_date')

                if org_name:
                    record['organization_id'] = self.get_or_create_organization(org_name)

                if bank_account:
                    record['bank_account_id'] = self.get_or_create_bank_account(bank_account, org_name)

                if contract_number:
                    record['contract_id'] = self.get_or_create_contract(contract_number, contract_date, org_name)

                # Remove denormalized fields
                record.pop('organization', None)
                record.pop('bank_account', None)
                record.pop('contract_number', None)

                # Check if record exists before UPSERT
                existing = self.db.query(FinExpense).filter(
                    FinExpense.operation_id == record.get('operation_id')
                ).first()

                stmt = insert(FinExpense).values(**record)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['operation_id'],
                    set_={
                        key: value
                        for key, value in record.items()
                        if key != 'operation_id'
                    }
                )

                result = self.db.execute(stmt)

                if result.rowcount > 0:
                    if existing:
                        updated += 1
                    else:
                        inserted += 1
                # rowcount = 0 with ON CONFLICT DO UPDATE is rare, don't count as failure

            except Exception as e:
                logger.error(f"Error upserting fin expense {record.get('operation_id')}: {e}")
                failed += 1

        try:
            self.db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error committing fin expenses: {e}")
            self.db.rollback()
            return 0, 0, len(records)

        logger.info(f"Fin Expenses: {inserted} inserted, {updated} updated, {failed} failed")
        return inserted, updated, failed

    def upsert_expense_details(self, records: List[Dict], source_file: str = None) -> Tuple[int, int, int]:
        """
        Insert or update fin expense detail records using UPSERT

        Args:
            records: List of expense detail dictionaries
            source_file: Optional source file name

        Returns:
            Tuple[int, int, int]: (inserted, updated, failed)
        """
        inserted = 0
        updated = 0
        failed = 0
        skipped = 0

        # Get all existing expense operation IDs
        existing_expense_ids = set(
            row[0] for row in self.db.query(FinExpense.operation_id).all()
        )

        for record in records:
            expense_op_id = record.get('expense_operation_id')
            if expense_op_id not in existing_expense_ids:
                logger.warning(
                    f"Skipping detail: expense_operation_id '{expense_op_id}' "
                    f"not found in fin_expenses table"
                )
                skipped += 1
                failed += 1
                continue

            try:
                # Check if record exists before UPSERT
                from sqlalchemy import and_, func
                existing = self.db.query(FinExpenseDetail).filter(
                    and_(
                        FinExpenseDetail.expense_operation_id == record.get('expense_operation_id'),
                        func.coalesce(FinExpenseDetail.contract_number, '') == func.coalesce(record.get('contract_number'), ''),
                        func.coalesce(FinExpenseDetail.payment_type, '') == func.coalesce(record.get('payment_type'), ''),
                        func.coalesce(FinExpenseDetail.payment_amount, 0) == func.coalesce(record.get('payment_amount'), 0),
                        func.coalesce(FinExpenseDetail.settlement_account, '') == func.coalesce(record.get('settlement_account'), '')
                    )
                ).first()

                # Используем PostgreSQL ON CONFLICT DO UPDATE
                stmt = insert(FinExpenseDetail).values(**record)

                # Создаем индекс для ON CONFLICT (используем те же поля что и в уникальном индексе)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[
                        'expense_operation_id',
                        text('COALESCE(contract_number, \'\')'),
                        text('COALESCE(payment_type, \'\')'),
                        text('COALESCE(payment_amount, 0)'),
                        text('COALESCE(settlement_account, \'\')')
                    ],
                    set_={
                        key: value
                        for key, value in record.items()
                        if key not in ['id', 'created_at']  # Не обновляем id и created_at
                    }
                )

                result = self.db.execute(stmt)

                if result.rowcount > 0:
                    if existing:
                        updated += 1
                    else:
                        inserted += 1

            except Exception as e:
                logger.error(
                    f"Error upserting fin detail for "
                    f"{record.get('expense_operation_id')}: {e}"
                )
                failed += 1

        try:
            self.db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error committing fin expense details: {e}")
            self.db.rollback()
            return 0, 0, len(records)

        logger.info(
            f"Fin Expense details: {inserted} inserted, {updated} updated, {failed} failed "
            f"({skipped} skipped)"
        )
        return inserted, updated, failed

    def log_import(
        self,
        source_file: str,
        table_name: str,
        rows_inserted: int,
        rows_updated: int,
        rows_failed: int,
        status: str,
        error_message: str = None,
        processing_time: float = 0.0
    ):
        """Log import operation to database"""
        try:
            log = FinImportLog(
                source_file=source_file,
                table_name=table_name,
                rows_inserted=rows_inserted,
                rows_updated=rows_updated,
                rows_failed=rows_failed,
                status=status,
                error_message=error_message,
                processed_by="fin_importer",
                processing_time_seconds=round(processing_time, 2)
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error logging fin import: {e}")
            self.db.rollback()

    def import_file(self, file_path: str) -> bool:
        """
        Import a single XLSX file

        Args:
            file_path: Path to XLSX file

        Returns:
            bool: True if import successful
        """
        filename = Path(file_path).name
        start_time = time.time()

        logger.info(f"Starting fin import of: {filename}")

        try:
            file_type, records = self.parser.parse_file(file_path)

            if file_type is None or not records:
                logger.warning(f"No records parsed from {filename}")
                self.log_import(
                    filename, "unknown", 0, 0, 0,
                    "failed", "No records parsed",
                    time.time() - start_time
                )
                return False

            if file_type == "receipt":
                inserted, updated, failed = self.upsert_receipts(records)
                table_name = "fin_receipts"

            elif file_type == "expense":
                inserted, updated, failed = self.upsert_expenses(records)
                table_name = "fin_expenses"

            elif file_type == "detail":
                inserted, updated, failed = self.upsert_expense_details(records, source_file=filename)
                table_name = "fin_expense_details"

            else:
                logger.error(f"Unknown file type: {file_type}")
                return False

            if failed == 0:
                status = "success"
            elif inserted + updated > 0:
                status = "partial"
            else:
                status = "failed"

            self.log_import(
                filename, table_name,
                inserted, updated, failed,
                status, None,
                time.time() - start_time
            )

            logger.info(
                f"Fin import completed: {filename} "
                f"({inserted} inserted, {updated} updated, {failed} failed)"
            )

            return status in ["success", "partial"]

        except Exception as e:
            logger.error(f"Error importing {filename}: {e}")
            self.log_import(
                filename, "unknown", 0, 0, 0,
                "failed", str(e),
                time.time() - start_time
            )
            return False

    def import_files(self, file_paths: List[str], clear_existing: bool = True) -> Dict[str, int]:
        """
        Import multiple XLSX files

        Args:
            file_paths: List of file paths
            clear_existing: Whether to clear existing data before import

        Returns:
            Dict[str, int]: Summary of import results
        """
        summary = {
            "total": len(file_paths),
            "success": 0,
            "failed": 0
        }

        if clear_existing:
            self.clear_existing_data()

        for file_path in file_paths:
            if self.import_file(file_path):
                summary["success"] += 1
            else:
                summary["failed"] += 1

        logger.info(
            f"Fin import summary: {summary['success']}/{summary['total']} files imported"
        )

        return summary
