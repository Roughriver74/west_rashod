"""
Service for importing bank transactions from Excel files
Support for various bank statement formats
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, date
import pandas as pd
import io
from sqlalchemy.orm import Session

from app.core import constants
from app.db.models import (
    BankTransaction,
    BankTransactionTypeEnum,
    BankTransactionStatusEnum,
    RegionEnum,
    DocumentTypeEnum,
)
from app.services.transaction_classifier import TransactionClassifier


class BankTransactionImporter:
    """
    Import bank transactions from Excel files
    Supports common bank statement formats
    """

    def __init__(self, db: Session):
        self.db = db
        self.classifier = TransactionClassifier(db)

    def preview_import(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Preview Excel file for import
        Returns:
        - Available columns
        - Auto-detected column mapping
        - First 5 rows as sample data
        """
        try:
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file_content))

            # Normalize column names
            df.columns = df.columns.str.strip()

            # Auto-detect columns
            detected_mapping = self._detect_columns(df.columns)

            # Get sample data (first 5 rows)
            sample_data = []
            for idx, row in df.head(5).iterrows():
                sample_row = {}
                for col in df.columns:
                    value = row[col]
                    # Convert to JSON-serializable format
                    if pd.isna(value):
                        sample_row[col] = None
                    elif isinstance(value, (date, datetime)):
                        sample_row[col] = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float, Decimal)):
                        sample_row[col] = float(value)
                    else:
                        sample_row[col] = str(value)
                sample_data.append(sample_row)

            return {
                'success': True,
                'columns': list(df.columns),
                'detected_mapping': detected_mapping,
                'sample_data': sample_data,
                'total_rows': len(df),
                'required_fields': {
                    'date': 'Дата (обязательно)',
                    'payer': 'Кто (наша организация)',
                    'counterparty': 'Кому (контрагент)',
                    'payment_purpose': 'За что',
                    'category': 'Статья расходов',
                    'region': 'Регион',
                    'exhibition': 'Выставка/мероприятие',
                    'amount_rub_credit': 'Приход руб',
                    'amount_eur_credit': 'Приход EUR',
                    'amount_rub_debit': 'Расход руб',
                    'amount_eur_debit': 'Расход EUR',
                    'document_type': 'Вид документа',
                    'notes': 'Примечание',
                    'status': 'Статус согласования',
                    'transaction_month': 'МЕС',
                    'expense_acceptance_month': 'Мес принятия к расходу',
                    'department': 'Отдел',
                    'inn': 'ИНН контрагента',
                    'document_number': 'Номер документа'
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def import_from_excel(
        self,
        file_content: bytes,
        filename: str,
        user_id: int,
        column_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Import bank transactions from Excel file

        Expected columns (flexible mapping):
        - Дата операции / Дата / Date
        - Сумма / Amount
        - Контрагент / Counterparty / Плательщик/Получатель
        - ИНН контрагента / INN
        - Назначение платежа / Payment Purpose / Описание
        - Номер документа / Document Number
        - Дебет/Кредит / Type (optional)
        """
        try:
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file_content))

            # Normalize column names
            df.columns = df.columns.str.strip()

            # Map columns to our schema
            if not column_mapping:
                column_mapping = self._detect_columns(df.columns)

            # Check required fields: date is required, amount OR extended amount fields
            has_date = column_mapping.get('date')
            has_amount = (
                column_mapping.get('amount') or
                column_mapping.get('amount_rub_credit') or
                column_mapping.get('amount_rub_debit') or
                column_mapping.get('amount_eur_credit') or
                column_mapping.get('amount_eur_debit')
            )

            if not has_date or not has_amount:
                return {
                    'success': False,
                    'error': 'Required columns not found. Need at least: Date and Amount (or Приход руб/Расход руб)',
                    'imported': 0,
                    'skipped': 0,
                    'errors': []
                }

            imported = 0
            skipped = 0
            errors = []

            for idx, row in df.iterrows():
                try:
                    # Parse date
                    transaction_date = self._parse_date(row[column_mapping['date']])
                    if not transaction_date:
                        errors.append({
                            'row': idx + 2,  # Excel row number (1-indexed + header)
                            'error': 'Invalid date format'
                        })
                        skipped += 1
                        continue

                    # Parse amount (support both single 'amount' column and extended split columns)
                    amount = None
                    transaction_type = None
                    amount_rub_credit = None
                    amount_eur_credit = None
                    amount_rub_debit = None
                    amount_eur_debit = None

                    # If we have extended fields (Приход/Расход), use them
                    if column_mapping.get('amount_rub_credit') or column_mapping.get('amount_rub_debit'):
                        # Parse extended amount fields
                        if column_mapping.get('amount_rub_credit'):
                            amount_rub_credit = self._parse_amount(row.get(column_mapping['amount_rub_credit']))
                        if column_mapping.get('amount_eur_credit'):
                            amount_eur_credit = self._parse_amount(row.get(column_mapping['amount_eur_credit']))
                        if column_mapping.get('amount_rub_debit'):
                            amount_rub_debit = self._parse_amount(row.get(column_mapping['amount_rub_debit']))
                        if column_mapping.get('amount_eur_debit'):
                            amount_eur_debit = self._parse_amount(row.get(column_mapping['amount_eur_debit']))

                        # Determine main amount and type based on which field has value
                        if amount_rub_credit and amount_rub_credit > 0:
                            amount = amount_rub_credit
                            transaction_type = BankTransactionTypeEnum.CREDIT
                        elif amount_rub_debit and amount_rub_debit > 0:
                            amount = amount_rub_debit
                            transaction_type = BankTransactionTypeEnum.DEBIT
                        elif amount_eur_credit and amount_eur_credit > 0:
                            amount = amount_eur_credit
                            transaction_type = BankTransactionTypeEnum.CREDIT
                        elif amount_eur_debit and amount_eur_debit > 0:
                            amount = amount_eur_debit
                            transaction_type = BankTransactionTypeEnum.DEBIT

                    # Fallback to single 'amount' column if no extended fields or they're empty
                    if amount is None and column_mapping.get('amount'):
                        amount = self._parse_amount(row[column_mapping['amount']])
                        # Determine type from 'type' column or amount sign
                        transaction_type = BankTransactionTypeEnum.DEBIT  # Default to debit (expense)
                        if column_mapping.get('type'):
                            type_value = str(row[column_mapping['type']]).strip().lower()
                            if 'кредит' in type_value or 'credit' in type_value or 'приход' in type_value:
                                transaction_type = BankTransactionTypeEnum.CREDIT
                            elif 'дебет' in type_value or 'debit' in type_value or 'расход' in type_value:
                                transaction_type = BankTransactionTypeEnum.DEBIT
                        # If amount is negative, it's a debit
                        if amount and amount < 0:
                            transaction_type = BankTransactionTypeEnum.DEBIT
                            amount = abs(amount)

                    # Validate we have amount
                    if amount is None or amount == 0:
                        errors.append({
                            'row': idx + 2,
                            'error': 'Invalid amount'
                        })
                        skipped += 1
                        continue

                    # Ensure transaction_type is set
                    if transaction_type is None:
                        transaction_type = BankTransactionTypeEnum.DEBIT

                    # Extract other fields
                    counterparty_name = self._get_value(row, column_mapping.get('counterparty'))
                    counterparty_inn = self._get_value(row, column_mapping.get('inn'))
                    payment_purpose = self._get_value(row, column_mapping.get('payment_purpose'))
                    document_number = self._get_value(row, column_mapping.get('document_number'))

                    # Check if transaction already exists (by date, amount, and counterparty)
                    existing = self.db.query(BankTransaction).filter(
                        BankTransaction.transaction_date == transaction_date,
                        BankTransaction.amount == amount,
                        BankTransaction.counterparty_inn == counterparty_inn,
                        BankTransaction.is_active == True
                    ).first()

                    if existing:
                        skipped += 1
                        continue

                    # Extract additional extended fields if available
                    region_raw = self._get_value(row, column_mapping.get('region'))
                    region = self._map_region(region_raw)  # Map Cyrillic to Latin enum
                    exhibition = self._get_value(row, column_mapping.get('exhibition'))
                    document_type_raw = self._get_value(row, column_mapping.get('document_type'))
                    document_type = self._map_document_type(document_type_raw)  # Map to valid enum or None
                    notes = self._get_value(row, column_mapping.get('notes'))
                    transaction_month = self._parse_int(self._get_value(row, column_mapping.get('transaction_month')))
                    expense_acceptance_month = self._parse_int(self._get_value(row, column_mapping.get('expense_acceptance_month')))

                    # Create new transaction
                    transaction = BankTransaction(
                        transaction_date=transaction_date,
                        amount=amount,
                        transaction_type=transaction_type,
                        counterparty_name=counterparty_name,
                        counterparty_inn=counterparty_inn,
                        payment_purpose=payment_purpose,
                        document_number=document_number,
                        # Extended fields
                        amount_rub_credit=amount_rub_credit,
                        amount_eur_credit=amount_eur_credit,
                        amount_rub_debit=amount_rub_debit,
                        amount_eur_debit=amount_eur_debit,
                        region=region,
                        exhibition=exhibition,
                        document_type=document_type,
                        notes=notes,
                        transaction_month=transaction_month,
                        expense_acceptance_month=expense_acceptance_month,
                        # System fields
                        status=BankTransactionStatusEnum.NEW,
                        import_source='MANUAL_UPLOAD',
                        import_file_name=filename,
                        imported_at=datetime.utcnow(),
                    )

                    # Classification: RULES auto-apply, AI only suggests
                    try:
                        category_id, confidence, reasoning, is_rule_based = self.classifier.classify(
                            payment_purpose=payment_purpose,
                            counterparty_name=counterparty_name,
                            counterparty_inn=counterparty_inn,
                            amount=amount,
                            transaction_type=transaction_type.value  # Pass transaction type for better classification
                        )

                        if category_id:
                            transaction.category_confidence = float(confidence)

                            if is_rule_based:
                                # RULE: auto-apply category
                                transaction.category_id = category_id
                                transaction.status = BankTransactionStatusEnum.CATEGORIZED
                            else:
                                # AI HEURISTIC: only suggest
                                transaction.suggested_category_id = category_id
                                transaction.status = BankTransactionStatusEnum.NEEDS_REVIEW

                    except Exception as e:
                        # If classification fails, just continue without it
                        pass

                    self.db.add(transaction)
                    imported += 1

                except Exception as e:
                    errors.append({
                        'row': idx + 2,
                        'error': str(e)
                    })
                    skipped += 1

            self.db.commit()

            return {
                'success': True,
                'imported': imported,
                'skipped': skipped,
                'total_rows': len(df),
                'errors': errors
            }

        except Exception as e:
            self.db.rollback()
            return {
                'success': False,
                'error': f'Failed to process file: {str(e)}',
                'imported': 0,
                'skipped': 0,
                'errors': []
            }

    def _detect_columns(self, columns: List[str]) -> Dict[str, str]:
        """
        Auto-detect column names
        """
        mapping = {}

        # Normalize column names
        normalized = {col: col.strip().lower() for col in columns}

        # Date column
        date_keywords = ['дата', 'date', 'дата операции', 'transaction date']
        for col, norm in normalized.items():
            if any(kw in norm for kw in date_keywords):
                mapping['date'] = col
                break

        # Amount column
        amount_keywords = ['сумма', 'amount', 'sum', 'значение']
        for col, norm in normalized.items():
            if any(kw in norm for kw in amount_keywords):
                mapping['amount'] = col
                break

        # Counterparty
        counterparty_keywords = ['контрагент', 'counterparty', 'плательщик', 'получатель', 'payer', 'recipient']
        for col, norm in normalized.items():
            if any(kw in norm for kw in counterparty_keywords):
                mapping['counterparty'] = col
                break

        # INN
        inn_keywords = ['инн', 'inn']
        for col, norm in normalized.items():
            if any(kw in norm for kw in inn_keywords):
                mapping['inn'] = col
                break

        # Payment purpose
        purpose_keywords = ['назначение', 'purpose', 'описание', 'description', 'комментарий', 'comment']
        for col, norm in normalized.items():
            if any(kw in norm for kw in purpose_keywords):
                mapping['payment_purpose'] = col
                break

        # Document number
        doc_keywords = ['номер', 'number', 'документ', 'document']
        for col, norm in normalized.items():
            if any(kw in norm for kw in doc_keywords):
                mapping['document_number'] = col
                break

        # Transaction type
        type_keywords = ['тип', 'type', 'дебет', 'debit', 'кредит', 'credit']
        for col, norm in normalized.items():
            if any(kw in norm for kw in type_keywords) and 'документ' not in norm:
                mapping['type'] = col
                break

        # Payer (Кто)
        payer_keywords = ['кто']
        for col, norm in normalized.items():
            if norm in payer_keywords:
                mapping['payer'] = col
                break

        # Category (статья)
        category_keywords = ['статья', 'category']
        for col, norm in normalized.items():
            if any(kw in norm for kw in category_keywords):
                mapping['category'] = col
                break

        # Region
        region_keywords = ['регион', 'region']
        for col, norm in normalized.items():
            if any(kw in norm for kw in region_keywords):
                mapping['region'] = col
                break

        # Exhibition
        exhibition_keywords = ['выставка', 'exhibition']
        for col, norm in normalized.items():
            if any(kw in norm for kw in exhibition_keywords):
                mapping['exhibition'] = col
                break

        # Income RUB
        for col, norm in normalized.items():
            if 'приход' in norm and 'руб' in norm:
                mapping['amount_rub_credit'] = col
                break

        # Income EUR
        for col, norm in normalized.items():
            if 'приход' in norm and 'eur' in norm:
                mapping['amount_eur_credit'] = col
                break

        # Expense RUB
        for col, norm in normalized.items():
            if 'расход' in norm and 'руб' in norm:
                mapping['amount_rub_debit'] = col
                break

        # Expense EUR
        for col, norm in normalized.items():
            if 'расход' in norm and 'eur' in norm:
                mapping['amount_eur_debit'] = col
                break

        # Document type (вид)
        for col, norm in normalized.items():
            if norm == 'вид' or (norm == 'вид документа'):
                mapping['document_type'] = col
                break

        # Month (МЕС)
        for col, norm in normalized.items():
            if norm == 'мес' or norm == 'месяц':
                mapping['transaction_month'] = col
                break

        # Expense acceptance month
        for col, norm in normalized.items():
            if 'мес принятия' in norm or 'месяц принятия' in norm:
                mapping['expense_acceptance_month'] = col
                break

        # Department
        department_keywords = ['отдел', 'department']
        for col, norm in normalized.items():
            if any(kw in norm for kw in department_keywords):
                mapping['department'] = col
                break

        # Notes (Примечание)
        notes_keywords = ['примечание', 'note']
        for col, norm in normalized.items():
            if any(kw in norm for kw in notes_keywords):
                mapping['notes'] = col
                break

        # Status
        for col, norm in normalized.items():
            if 'статус согласования' in norm or 'статус' in norm:
                mapping['status'] = col
                break

        return mapping

    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse date from various formats"""
        if pd.isna(value):
            return None

        if isinstance(value, (date, datetime)):
            return value if isinstance(value, date) else value.date()

        # Try parsing string
        if isinstance(value, str):
            try:
                return pd.to_datetime(value, dayfirst=True).date()
            except:
                return None

        return None

    def _parse_amount(self, value: Any) -> Optional[Decimal]:
        """Parse amount from various formats"""
        if pd.isna(value):
            return None

        try:
            # Remove spaces and replace comma with dot
            if isinstance(value, str):
                value = value.replace(' ', '').replace(',', '.')

            return Decimal(str(value))
        except:
            return None

    def _get_value(self, row: pd.Series, column: Optional[str]) -> Optional[str]:
        """Get value from row by column name"""
        if not column or column not in row.index:
            return None

        value = row[column]
        if pd.isna(value):
            return None

        return str(value).strip() if value else None

    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Parse integer from string value"""
        if not value:
            return None

        try:
            # Remove spaces and convert to int
            if isinstance(value, str):
                value = value.replace(' ', '')
            return int(float(value))  # Convert via float to handle decimals like "8.0"
        except:
            return None

    def _map_region(self, value: Optional[str]) -> Optional[RegionEnum]:
        """Map region value to enum (convert Cyrillic to Latin)"""
        if not value:
            return None

        # Normalize value
        normalized = value.strip().upper()

        # Mapping dictionary (Cyrillic -> Enum)
        region_mapping = {
            'СПБ': RegionEnum.SPB,
            'САНКТ-ПЕТЕРБУРГ': RegionEnum.SPB,
            'ПЕТЕРБУРГ': RegionEnum.SPB,
            'SPB': RegionEnum.SPB,
            'MOSCOW': RegionEnum.MOSCOW,
            'МОСКВА': RegionEnum.MOSCOW,
            'МСК': RegionEnum.MOSCOW,
            'РЕГИОНЫ': RegionEnum.REGIONS,
            'REGIONS': RegionEnum.REGIONS,
            'ЗАРУБЕЖ': RegionEnum.FOREIGN,
            'FOREIGN': RegionEnum.FOREIGN,
        }

        # Return mapped value or None if not found
        return region_mapping.get(normalized)

    def _map_document_type(self, value: Optional[str]) -> Optional[DocumentTypeEnum]:
        """Map document type value to enum"""
        if not value:
            return None

        # Normalize value
        normalized = value.strip().upper()

        # Mapping dictionary
        doc_type_mapping = {
            'ПЛАТЕЖНОЕ ПОРУЧЕНИЕ': DocumentTypeEnum.PAYMENT_ORDER,
            'ПЛАТЕЖКА': DocumentTypeEnum.PAYMENT_ORDER,
            'ПП': DocumentTypeEnum.PAYMENT_ORDER,
            'PAYMENT_ORDER': DocumentTypeEnum.PAYMENT_ORDER,
            'КАССОВЫЙ ОРДЕР': DocumentTypeEnum.CASH_ORDER,
            'КО': DocumentTypeEnum.CASH_ORDER,
            'CASH_ORDER': DocumentTypeEnum.CASH_ORDER,
            'СЧЕТ': DocumentTypeEnum.INVOICE,
            'INVOICE': DocumentTypeEnum.INVOICE,
            'АКТ': DocumentTypeEnum.ACT,
            'ACT': DocumentTypeEnum.ACT,
            'ДОГОВОР': DocumentTypeEnum.CONTRACT,
            'CONTRACT': DocumentTypeEnum.CONTRACT,
            'ДРУГОЕ': DocumentTypeEnum.OTHER,
            'OTHER': DocumentTypeEnum.OTHER,
        }

        # Return mapped value or None if not a valid document type
        return doc_type_mapping.get(normalized)
