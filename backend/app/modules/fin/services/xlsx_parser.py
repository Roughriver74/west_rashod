"""
XLSX parser for processing financial files
Handles three types of files: Receipts, Expenses, and Expense Details
Adapted from west_fin project for fin module
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


class FinXLSXParser:
    """Parser for XLSX financial files - fin module"""

    # Mapping between XLSX column names and model fields
    RECEIPT_COLUMNS = {
        "Поступление на расчетный счет": "operation_id",
        "Организация": "organization",
        "Вид операции": "operation_type",
        "Банковский счет": "bank_account",
        "Счет учета": "accounting_account",
        "Номер входящего документа": "document_number",
        "Дата входящего документа": "document_date",
        "Плательщик": "payer",
        "Счет плательщика": "payer_account",
        "Счет расчетов": "settlement_account",
        "Договор": "contract_number",
        "Дата договора": "contract_date",
        "Валюта": "currency",
        "Сумма": "amount",
        "Комиссия": "commission",
        "Назначение платежа": "payment_purpose",
        "Ответственный": "responsible_person",
        "Комментарий": "comment",
    }

    EXPENSE_COLUMNS = {
        "Списание с расчетного счета": "operation_id",
        "Организация": "organization",
        "Вид операции": "operation_type",
        "Банковский счет": "bank_account",
        "Счет учета": "accounting_account",
        "Вх. номер": "document_number",
        "Вх. дата": "document_date",
        "Получатель": "recipient",
        "Счет получателя": "recipient_account",
        "Счет дебета": "debit_account",
        "Договор": "contract_number",
        "Дата договора": "contract_date",
        "Валюта": "currency",
        "Сумма": "amount",
        "Статья расходов": "expense_article",
        "Назначение платежа": "payment_purpose",
        "Ответственный": "responsible_person",
        "Комментарий": "comment",
        "Налоговый период": "tax_period",
        "Не подтверждено банком": "unconfirmed_by_bank",
    }

    DETAIL_COLUMNS = {
        "Списание с расчетного счета": "expense_operation_id",
        "Договор": "contract_number",
        "Погашение задолженности": "repayment_type",
        "Счет расчетов": "settlement_account",
        "Счет авансов": "advance_account",
        "Вид платежа по кредитам займам": "payment_type",
        "Сумма платежа": "payment_amount",
        "Курс расчетов": "settlement_rate",
        "Сумма расчетов": "settlement_amount",
        "Сумма НДС": "vat_amount",
        "Сумма расходов": "expense_amount",
        "в т.ч. НДС": "vat_in_expense",
    }

    @staticmethod
    def detect_file_type(filename: str) -> Optional[str]:
        """
        Detect file type based on filename

        Args:
            filename: Name of the file

        Returns:
            str: 'receipt', 'expense', or 'detail', or None if unknown
        """
        filename_lower = filename.lower()

        if "postuplenie" in filename_lower or "поступление" in filename_lower:
            return "receipt"
        elif "rasshifrovka" in filename_lower or "расшифровка" in filename_lower:
            return "detail"
        elif "spisanie" in filename_lower or "списание" in filename_lower:
            # Check if it's not rasshifrovka
            if "rasshifrovka" not in filename_lower and "расшифровка" not in filename_lower:
                return "expense"

        logger.warning(f"Unknown file type for: {filename}")
        return None

    @staticmethod
    def clean_value(value) -> Optional[str]:
        """Clean and normalize cell value"""
        if pd.isna(value) or value is None or value == "":
            return None

        # Convert to string and strip whitespace
        str_value = str(value).strip()

        # Return None for empty strings
        if str_value == "" or str_value == "None":
            return None

        return str_value

    @staticmethod
    def parse_date(value) -> Optional[str]:
        """Parse date value to YYYY-MM-DD format"""
        if pd.isna(value) or value is None:
            return None

        try:
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d")
            elif isinstance(value, str):
                # Try multiple date formats
                for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.strftime("%Y-%m-%d")
                    except ValueError:
                        continue
        except Exception as e:
            logger.debug(f"Date parse error: {e}")

        return None

    @staticmethod
    def parse_numeric(value) -> Optional[float]:
        """Parse numeric value"""
        if pd.isna(value) or value is None:
            return None

        try:
            # Handle comma as decimal separator
            if isinstance(value, str):
                value = value.replace(",", ".").replace(" ", "")

            return float(value)
        except (ValueError, TypeError):
            return None

    def parse_receipt_file(self, file_path: str) -> List[Dict]:
        """
        Parse receipt (поступление) XLSX file

        Args:
            file_path: Path to XLSX file

        Returns:
            List[Dict]: List of receipt records
        """
        try:
            df = pd.read_excel(file_path, sheet_name=0)
            records = []

            for idx, row in df.iterrows():
                record = {}

                for xlsx_col, model_field in self.RECEIPT_COLUMNS.items():
                    if xlsx_col not in df.columns:
                        continue

                    value = row[xlsx_col]

                    # Handle specific field types
                    if model_field in ["document_date", "contract_date"]:
                        record[model_field] = self.parse_date(value)
                    elif model_field in ["amount", "commission"]:
                        record[model_field] = self.parse_numeric(value)
                    else:
                        record[model_field] = self.clean_value(value)

                # Skip rows without operation_id or amount
                if not record.get("operation_id") or not record.get("amount"):
                    continue

                # Skip summary/total rows (like "Итого")
                operation_id = str(record.get("operation_id", "")).strip().lower()
                if operation_id in ["итого", "total", "всего", "sum"]:
                    continue

                records.append(record)

            logger.info(f"Parsed {len(records)} receipt records from {Path(file_path).name}")
            return records

        except Exception as e:
            logger.error(f"Error parsing receipt file {file_path}: {e}")
            return []

    def parse_expense_file(self, file_path: str) -> List[Dict]:
        """
        Parse expense (списание) XLSX file

        Args:
            file_path: Path to XLSX file

        Returns:
            List[Dict]: List of expense records
        """
        try:
            df = pd.read_excel(file_path, sheet_name=0)
            records = []

            for idx, row in df.iterrows():
                record = {}

                for xlsx_col, model_field in self.EXPENSE_COLUMNS.items():
                    if xlsx_col not in df.columns:
                        continue

                    value = row[xlsx_col]

                    # Handle specific field types
                    if model_field in ["document_date", "contract_date"]:
                        record[model_field] = self.parse_date(value)
                    elif model_field == "amount":
                        record[model_field] = self.parse_numeric(value)
                    elif model_field == "unconfirmed_by_bank":
                        record[model_field] = bool(value) if value else False
                    else:
                        record[model_field] = self.clean_value(value)

                # Skip rows without operation_id or amount
                if not record.get("operation_id") or not record.get("amount"):
                    continue

                # Skip summary/total rows (like "Итого")
                operation_id = str(record.get("operation_id", "")).strip().lower()
                if operation_id in ["итого", "total", "всего", "sum"]:
                    continue

                records.append(record)

            logger.info(f"Parsed {len(records)} expense records from {Path(file_path).name}")
            return records

        except Exception as e:
            logger.error(f"Error parsing expense file {file_path}: {e}")
            return []

    def parse_detail_file(self, file_path: str) -> List[Dict]:
        """
        Parse expense detail (расшифровка) XLSX file

        Args:
            file_path: Path to XLSX file

        Returns:
            List[Dict]: List of expense detail records
        """
        try:
            df = pd.read_excel(file_path, sheet_name=0)
            records = []

            for idx, row in df.iterrows():
                record = {}

                for xlsx_col, model_field in self.DETAIL_COLUMNS.items():
                    if xlsx_col not in df.columns:
                        continue

                    value = row[xlsx_col]

                    # Handle specific field types
                    if model_field in [
                        "payment_amount", "settlement_rate", "settlement_amount",
                        "vat_amount", "expense_amount", "vat_in_expense"
                    ]:
                        record[model_field] = self.parse_numeric(value)
                    else:
                        record[model_field] = self.clean_value(value)

                # Skip rows without expense_operation_id
                if not record.get("expense_operation_id"):
                    continue

                records.append(record)

            logger.info(f"Parsed {len(records)} detail records from {Path(file_path).name}")
            return records

        except Exception as e:
            logger.error(f"Error parsing detail file {file_path}: {e}")
            return []

    def parse_file(self, file_path: str) -> Tuple[Optional[str], List[Dict]]:
        """
        Parse XLSX file based on detected type

        Args:
            file_path: Path to XLSX file

        Returns:
            Tuple[Optional[str], List[Dict]]: (file_type, records)
        """
        filename = Path(file_path).name
        file_type = self.detect_file_type(filename)

        if file_type is None:
            logger.error(f"Cannot determine file type for: {filename}")
            return None, []

        if file_type == "receipt":
            records = self.parse_receipt_file(file_path)
        elif file_type == "expense":
            records = self.parse_expense_file(file_path)
        elif file_type == "detail":
            records = self.parse_detail_file(file_path)
        else:
            return None, []

        return file_type, records
