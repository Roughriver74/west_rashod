"""
Pydantic schemas for Fin module API request/response validation
Imported and adapted from west_fin project
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============== Bank Account Schemas ==============

class FinBankAccountBase(BaseModel):
    """Base schema for fin bank account"""
    account_number: str
    bank_name: Optional[str] = None
    is_active: bool = True


class FinBankAccount(FinBankAccountBase):
    """Schema for fin bank account with database fields"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinBankAccountList(BaseModel):
    """Schema for fin bank account list"""
    items: List[FinBankAccount]


# ============== Contract Schemas ==============

class FinContractBase(BaseModel):
    """Base schema for contract"""
    contract_number: str
    contract_date: Optional[date] = None
    contract_type: Optional[str] = None
    counterparty: Optional[str] = None
    is_active: bool = True


class FinContract(FinContractBase):
    """Schema for contract with database fields"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinContractList(BaseModel):
    """Schema for contract list"""
    items: List[FinContract]


# ============== Payer Schemas ==============

class FinPayer(BaseModel):
    """Schema for payer"""
    name: str


class FinPayerList(BaseModel):
    """Schema for payer list"""
    items: List[FinPayer]


# ============== Excluded Payers Preferences ==============

class FinExcludedPayersUpdate(BaseModel):
    """Payload to persist excluded payers"""
    payers: List[str] = []


class FinExcludedPayersResponse(BaseModel):
    """Persisted excluded payers"""
    items: List[str] = []


# ============== Receipt Schemas ==============

class FinReceiptBase(BaseModel):
    """Base schema for receipt"""
    operation_id: str
    organization: str
    operation_type: Optional[str] = None
    bank_account: Optional[str] = None
    accounting_account: Optional[str] = None
    document_number: Optional[str] = None
    document_date: Optional[date] = None
    payer: Optional[str] = None
    payer_account: Optional[str] = None
    settlement_account: Optional[str] = None
    contract_number: Optional[str] = None
    contract_date: Optional[date] = None
    currency: Optional[str] = None
    amount: Decimal
    commission: Optional[Decimal] = None
    payment_purpose: Optional[str] = None
    responsible_person: Optional[str] = None
    comment: Optional[str] = None


class FinReceipt(FinReceiptBase):
    """Schema for receipt with database fields"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinReceiptList(BaseModel):
    """Schema for paginated receipt list"""
    total: int
    items: List[FinReceipt]


# ============== Expense Schemas ==============

class FinExpenseBase(BaseModel):
    """Base schema for expense"""
    operation_id: str
    organization: str
    operation_type: Optional[str] = None
    bank_account: Optional[str] = None
    accounting_account: Optional[str] = None
    document_number: Optional[str] = None
    document_date: Optional[date] = None
    recipient: Optional[str] = None
    recipient_account: Optional[str] = None
    debit_account: Optional[str] = None
    contract_number: Optional[str] = None
    contract_date: Optional[date] = None
    currency: Optional[str] = None
    amount: Decimal
    expense_article: Optional[str] = None
    payment_purpose: Optional[str] = None
    responsible_person: Optional[str] = None
    comment: Optional[str] = None
    tax_period: Optional[str] = None
    unconfirmed_by_bank: bool = False


class FinExpense(FinExpenseBase):
    """Schema for expense with database fields"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinExpenseList(BaseModel):
    """Schema for paginated expense list"""
    total: int
    items: List[FinExpense]


# ============== Expense Detail Schemas ==============

class FinExpenseDetailBase(BaseModel):
    """Base schema for expense detail"""
    expense_operation_id: str
    contract_number: Optional[str] = None
    repayment_type: Optional[str] = None
    settlement_account: Optional[str] = None
    advance_account: Optional[str] = None
    payment_type: Optional[str] = None
    payment_amount: Optional[Decimal] = None
    settlement_rate: Optional[Decimal] = None
    settlement_amount: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = None
    expense_amount: Optional[Decimal] = None
    vat_in_expense: Optional[Decimal] = None


class FinExpenseDetail(FinExpenseDetailBase):
    """Schema for expense detail with database fields"""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinExpenseDetailList(BaseModel):
    """Schema for paginated expense detail list"""
    total: int
    items: List[FinExpenseDetail]


# ============== Import Log Schemas ==============

class FinImportLog(BaseModel):
    """Schema for import log"""
    id: int
    import_date: datetime
    source_file: str
    table_name: str
    rows_inserted: int
    rows_updated: int
    rows_failed: int
    status: str
    error_message: Optional[str] = None
    processed_by: Optional[str] = None
    processing_time_seconds: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class FinImportLogList(BaseModel):
    """Schema for paginated import log list"""
    total: int
    items: List[FinImportLog]


# ============== Credit Balance Schemas ==============

class FinCreditBalances(BaseModel):
    """Aggregated balances for credit dashboard"""
    openingBalance: float = 0.0
    closingBalance: float = 0.0
    periodReceived: float = 0.0
    periodPrincipalPaid: float = 0.0
    periodInterestPaid: float = 0.0


class FinCreditBalancesResponse(BaseModel):
    """Wrapper for credit balance response"""
    data: FinCreditBalances


# ============== Turnover Balance Sheet Schemas ==============

class FinTurnoverBalanceRow(BaseModel):
    """Schema for a single row in turnover balance sheet"""
    account: Optional[str] = None
    counterparty: Optional[str] = None
    inn: Optional[str] = None
    contract: Optional[str] = None
    document_number: Optional[str] = None
    document_date: Optional[str] = None
    balanceStartDebit: float = 0.0
    balanceStartCredit: float = 0.0
    turnoverDebit: float = 0.0
    turnoverCredit: float = 0.0
    balanceEndDebit: float = 0.0
    balanceEndCredit: float = 0.0
    level: int = 0  # 0 = loan type, 1 = counterparty, 2 = contract, 3 = document
    parentAccount: Optional[str] = None
    parentCounterparty: Optional[str] = None


class FinTurnoverBalanceResponse(BaseModel):
    """Schema for turnover balance sheet response"""
    data: List[FinTurnoverBalanceRow]


# ============== Manual Adjustment Schemas ==============

class FinManualAdjustmentBase(BaseModel):
    """Base schema for manual adjustment"""
    contract_id: Optional[int] = None
    contract_number: Optional[str] = None
    adjustment_type: Literal['receipt', 'expense']
    payment_type: Optional[str] = None
    amount: Decimal
    document_date: date
    document_number: Optional[str] = None
    counterparty: Optional[str] = None
    organization_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    accounting_account: Optional[str] = None
    description: Optional[str] = None
    comment: Optional[str] = None

    @field_validator('payment_type')
    @classmethod
    def validate_payment_type(cls, v, info):
        """Payment type is required for expense adjustments"""
        if info.data.get('adjustment_type') == 'expense' and not v:
            raise ValueError('payment_type is required for expense adjustments')
        return v


class FinManualAdjustmentCreate(FinManualAdjustmentBase):
    """Schema for creating manual adjustment"""
    pass


class FinManualAdjustmentUpdate(BaseModel):
    """Schema for updating manual adjustment"""
    contract_id: Optional[int] = None
    contract_number: Optional[str] = None
    adjustment_type: Optional[Literal['receipt', 'expense']] = None
    payment_type: Optional[str] = None
    amount: Optional[Decimal] = None
    document_date: Optional[date] = None
    document_number: Optional[str] = None
    counterparty: Optional[str] = None
    organization_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    accounting_account: Optional[str] = None
    description: Optional[str] = None
    comment: Optional[str] = None


class FinManualAdjustment(FinManualAdjustmentBase):
    """Schema for manual adjustment with database fields"""
    id: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinManualAdjustmentList(BaseModel):
    """Schema for paginated manual adjustment list"""
    total: int
    items: List[FinManualAdjustment]


# ============== FTP Import Schemas ==============

class FinFTPImportRequest(BaseModel):
    """Schema for FTP import request"""
    clear_existing: bool = True


class FinFTPImportResponse(BaseModel):
    """Schema for FTP import response"""
    task_id: str
    message: str


class FinImportTriggerResponse(BaseModel):
    """Schema for manual import trigger response"""
    message: str
    timestamp: datetime


# ============== Analytics Schemas ==============

class FinCashFlowItem(BaseModel):
    """Cash flow item for analytics"""
    period: str
    receipts: float = 0.0
    expenses: float = 0.0
    net_flow: float = 0.0


class FinCashFlowResponse(BaseModel):
    """Cash flow analytics response"""
    data: List[FinCashFlowItem]


class FinKPIMetrics(BaseModel):
    """KPI metrics for dashboard"""
    total_receipts: float = 0.0
    total_expenses: float = 0.0
    net_cash_flow: float = 0.0
    principal_paid: float = 0.0
    interest_paid: float = 0.0
    average_daily_receipts: float = 0.0
    average_daily_expenses: float = 0.0
    receipts_count: int = 0
    expenses_count: int = 0


class FinKPIResponse(BaseModel):
    """KPI analytics response"""
    data: FinKPIMetrics


# ============== Contracts Summary Schemas ==============

class FinContractsSummaryRecord(BaseModel):
    """Contract summary record"""
    contractId: int
    contractNumber: str
    organization: str
    payer: str
    totalPaid: float
    principal: float
    interest: float
    totalReceived: float
    balance: float
    paidPercent: float
    operationsCount: int
    lastPayment: Optional[str] = None
    firstReceipt: Optional[str] = None


class FinContractsSummaryPagination(BaseModel):
    """Pagination info for contracts summary"""
    page: int
    limit: int
    total: int
    pages: int


class FinContractsSummaryResponse(BaseModel):
    """Contracts summary response"""
    data: List[FinContractsSummaryRecord]
    pagination: FinContractsSummaryPagination
