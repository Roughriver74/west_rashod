"""Bank transaction schemas."""
from typing import Optional, List, Any, Dict
from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal

from app.db.models import (
    BankTransactionTypeEnum,
    BankTransactionStatusEnum,
    PaymentSourceEnum,
    RegionEnum,
    DocumentTypeEnum,
)


class BankTransactionBase(BaseModel):
    """Base bank transaction schema."""
    transaction_date: datetime
    amount: Decimal
    transaction_type: BankTransactionTypeEnum = BankTransactionTypeEnum.DEBIT

    # VAT (НДС)
    vat_amount: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None

    # Counterparty
    counterparty_name: Optional[str] = None
    counterparty_inn: Optional[str] = None
    counterparty_kpp: Optional[str] = None
    counterparty_account: Optional[str] = None
    counterparty_bank: Optional[str] = None
    counterparty_bik: Optional[str] = None

    # Payment details
    payment_purpose: Optional[str] = None
    business_operation: Optional[str] = None
    payment_source: PaymentSourceEnum = PaymentSourceEnum.BANK

    # Our organization
    organization_id: Optional[int] = None
    account_number: Optional[str] = None

    # Document
    document_number: Optional[str] = None
    document_date: Optional[datetime] = None

    # Classification
    category_id: Optional[int] = None

    # Status
    status: BankTransactionStatusEnum = BankTransactionStatusEnum.NEW

    # Additional
    notes: Optional[str] = None
    region: Optional[RegionEnum] = None
    exhibition: Optional[str] = None
    document_type: Optional[DocumentTypeEnum] = None

    # Currency breakdown
    amount_rub_credit: Optional[Decimal] = None
    amount_eur_credit: Optional[Decimal] = None
    amount_rub_debit: Optional[Decimal] = None
    amount_eur_debit: Optional[Decimal] = None

    # Time periods
    transaction_month: Optional[int] = None
    transaction_year: Optional[int] = None
    expense_acceptance_month: Optional[int] = None
    expense_acceptance_year: Optional[int] = None


class BankTransactionCreate(BankTransactionBase):
    """Create bank transaction schema."""
    pass


class BankTransactionUpdate(BaseModel):
    """Update bank transaction schema."""
    transaction_date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    transaction_type: Optional[BankTransactionTypeEnum] = None
    vat_amount: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    counterparty_name: Optional[str] = None
    counterparty_inn: Optional[str] = None
    counterparty_kpp: Optional[str] = None
    counterparty_account: Optional[str] = None
    counterparty_bank: Optional[str] = None
    counterparty_bik: Optional[str] = None
    payment_purpose: Optional[str] = None
    business_operation: Optional[str] = None
    payment_source: Optional[PaymentSourceEnum] = None
    organization_id: Optional[int] = None
    account_number: Optional[str] = None
    document_number: Optional[str] = None
    document_date: Optional[datetime] = None
    category_id: Optional[int] = None
    status: Optional[BankTransactionStatusEnum] = None
    notes: Optional[str] = None
    region: Optional[RegionEnum] = None
    exhibition: Optional[str] = None
    document_type: Optional[DocumentTypeEnum] = None
    amount_rub_credit: Optional[Decimal] = None
    amount_eur_credit: Optional[Decimal] = None
    amount_rub_debit: Optional[Decimal] = None
    amount_eur_debit: Optional[Decimal] = None
    transaction_month: Optional[int] = None
    transaction_year: Optional[int] = None
    expense_acceptance_month: Optional[int] = None
    expense_acceptance_year: Optional[int] = None
    is_active: Optional[bool] = None


class BankTransactionCategorize(BaseModel):
    """Categorize transaction schema."""
    category_id: int
    notes: Optional[str] = None


class BankTransactionBulkCategorize(BaseModel):
    """Bulk categorize transactions schema."""
    transaction_ids: List[int]
    category_id: int


class BankTransactionBulkStatusUpdate(BaseModel):
    """Bulk status update schema."""
    transaction_ids: List[int]
    status: BankTransactionStatusEnum


class BankTransactionInDB(BankTransactionBase):
    """Bank transaction in database."""
    id: int
    category_confidence: Optional[float] = None
    suggested_category_id: Optional[int] = None
    is_regular_payment: bool = False
    regular_payment_pattern_id: Optional[int] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    import_source: Optional[str] = None
    import_file_name: Optional[str] = None
    imported_at: Optional[datetime] = None
    external_id_1c: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BankTransactionResponse(BankTransactionInDB):
    """Bank transaction response with related data."""
    category_name: Optional[str] = None
    organization_name: Optional[str] = None
    suggested_category_name: Optional[str] = None


class BankTransactionStats(BaseModel):
    """Bank transaction statistics."""
    total: int = 0
    new: int = 0
    categorized: int = 0
    approved: int = 0
    needs_review: int = 0
    ignored: int = 0
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")


class BankTransactionImportResult(BaseModel):
    """Import result schema."""
    success: bool
    imported: int = 0
    skipped: int = 0
    total_rows: int = 0
    errors: List[Dict[str, Any]] = []
    error: Optional[str] = None


class BankTransactionImportPreview(BaseModel):
    """Import preview schema."""
    success: bool
    columns: List[str] = []
    detected_mapping: Dict[str, str] = {}
    sample_data: List[Dict[str, Any]] = []
    total_rows: int = 0
    required_fields: Dict[str, str] = {}
    error: Optional[str] = None


class CategorySuggestion(BaseModel):
    """Category suggestion from AI."""
    category_id: int
    category_name: str
    confidence: float
    reasoning: Optional[str] = None


# ==================== Categorization Rule Suggestions ====================

class RuleSuggestion(BaseModel):
    """Предложение создать правило категоризации."""
    rule_type: str  # "COUNTERPARTY_INN", "COUNTERPARTY_NAME", "BUSINESS_OPERATION"
    match_value: str  # Значение для поиска (ИНН, название, операция)
    transaction_count: int  # Сколько транзакций подходят
    description: str  # Человекочитаемое описание
    can_create: bool  # Можно ли создать (нет дубликатов)
    matching_existing_count: int = 0  # Сколько существующих транзакций без категории будут затронуты


class RuleSuggestionsResponse(BaseModel):
    """Ответ с предложениями создания правил."""
    suggestions: List[RuleSuggestion]
    total_transactions: int
    category_id: int
    category_name: str


class CategorizationWithSuggestionsResponse(BaseModel):
    """Ответ после категоризации с предложениями правил."""
    transaction: BankTransactionResponse
    rule_suggestions: RuleSuggestionsResponse


class BulkCategorizationWithSuggestionsResponse(BaseModel):
    """Ответ после массовой категоризации с предложениями правил."""
    updated_count: int
    message: str
    rule_suggestions: RuleSuggestionsResponse


class CreateRuleFromSuggestionRequest(BaseModel):
    """Запрос на создание правила из предложения."""
    rule_type: str  # "COUNTERPARTY_INN", "COUNTERPARTY_NAME", "BUSINESS_OPERATION", "KEYWORD"
    match_value: str
    category_id: int
    priority: int = 10
    confidence: float = 0.95
    notes: Optional[str] = None
    apply_to_existing: bool = False  # Применить правило к существующим транзакциям


# ==================== Pagination ====================

class BankTransactionList(BaseModel):
    """List of bank transactions with pagination."""
    total: int
    items: List[BankTransactionResponse]
    page: int
    page_size: int
    pages: int


# ==================== Analytics Schemas ====================

class BankTransactionKPIs(BaseModel):
    """Key Performance Indicators for bank transactions."""
    # Financial metrics
    total_debit_amount: Decimal
    total_credit_amount: Decimal
    net_flow: Decimal
    total_transactions: int

    # Comparison with previous period
    debit_change_percent: Optional[float] = None
    credit_change_percent: Optional[float] = None
    net_flow_change_percent: Optional[float] = None
    transactions_change: Optional[int] = None

    # Status distribution
    new_count: int = 0
    categorized_count: int = 0
    approved_count: int = 0
    needs_review_count: int = 0
    ignored_count: int = 0

    # Status percentages
    new_percent: float = 0.0
    categorized_percent: float = 0.0
    approved_percent: float = 0.0
    needs_review_percent: float = 0.0
    ignored_percent: float = 0.0

    # AI metrics
    avg_category_confidence: Optional[float] = None
    auto_categorized_count: int = 0
    auto_categorized_percent: float = 0.0
    regular_payments_count: int = 0
    regular_payments_percent: float = 0.0


class MonthlyFlowData(BaseModel):
    """Monthly cash flow data for time series chart."""
    year: int
    month: int
    month_name: str
    debit_amount: Decimal
    credit_amount: Decimal
    net_flow: Decimal
    transaction_count: int
    avg_confidence: Optional[float] = None


class DailyFlowData(BaseModel):
    """Daily cash flow details."""
    date: date
    debit_amount: Decimal
    credit_amount: Decimal
    net_flow: Decimal
    transaction_count: int


class CategoryBreakdown(BaseModel):
    """Breakdown by category."""
    category_id: int
    category_name: str
    category_type: Optional[str] = None
    transaction_count: int
    total_amount: Decimal
    avg_amount: Decimal
    avg_confidence: Optional[float] = None
    percent_of_total: float = 0.0


class CounterpartyBreakdown(BaseModel):
    """Breakdown by counterparty."""
    counterparty_inn: Optional[str] = None
    counterparty_name: str
    transaction_count: int
    total_amount: Decimal
    avg_amount: Decimal
    first_transaction_date: datetime
    last_transaction_date: datetime
    is_regular: bool = False


class ProcessingFunnelStage(BaseModel):
    """One stage in processing funnel."""
    status: str
    count: int
    amount: Decimal
    percent_of_total: float = 0.0


class ProcessingFunnelData(BaseModel):
    """Processing funnel data."""
    stages: List[ProcessingFunnelStage]
    total_count: int
    conversion_rate_to_approved: float = 0.0


class ConfidenceBracket(BaseModel):
    """AI confidence bracket."""
    bracket: str
    min_confidence: float
    max_confidence: float
    count: int
    total_amount: Decimal
    percent_of_total: float = 0.0


class AIPerformanceData(BaseModel):
    """AI performance metrics."""
    confidence_distribution: List[ConfidenceBracket]
    avg_confidence: float = 0.0
    high_confidence_count: int = 0
    high_confidence_percent: float = 0.0
    low_confidence_count: int = 0
    low_confidence_percent: float = 0.0


class LowConfidenceItem(BaseModel):
    """Transaction with low AI confidence."""
    transaction_id: int
    transaction_date: datetime
    counterparty_name: str
    amount: Decimal
    payment_purpose: Optional[str] = None
    suggested_category_name: Optional[str] = None
    category_confidence: float
    status: str


class ActivityHeatmapPoint(BaseModel):
    """Activity heatmap data point (day of week × hour)."""
    day_of_week: int  # 0-6 (Monday-Sunday)
    hour: int  # 0-23
    transaction_count: int
    total_amount: Decimal
    avg_amount: Decimal


class StatusTimelinePoint(BaseModel):
    """Status distribution over time."""
    date: date
    new_count: int = 0
    categorized_count: int = 0
    matched_count: int = 0
    approved_count: int = 0
    needs_review_count: int = 0
    ignored_count: int = 0


class ConfidenceScatterPoint(BaseModel):
    """Scatter plot point for confidence analysis."""
    transaction_id: int
    transaction_date: datetime
    counterparty_name: Optional[str] = None
    amount: Decimal
    category_confidence: Optional[float] = None
    status: str
    transaction_type: str
    is_regular_payment: bool = False


class RegionalData(BaseModel):
    """Regional distribution data."""
    region: str
    transaction_count: int
    total_amount: Decimal
    avg_amount: Decimal
    percent_of_total: float = 0.0


class SourceDistribution(BaseModel):
    """Payment source distribution."""
    source: str
    transaction_count: int
    total_amount: Decimal
    percent_of_total: float = 0.0


class RegularPaymentSummary(BaseModel):
    """Summary of regular payment pattern."""
    counterparty_inn: Optional[str] = None
    counterparty_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    avg_amount: Decimal
    frequency_days: int
    last_payment_date: date
    transaction_count: int
    is_monthly: bool = False
    is_quarterly: bool = False


class ExhibitionData(BaseModel):
    """Exhibition spending data."""
    exhibition: str
    transaction_count: int
    total_amount: Decimal
    avg_amount: Decimal
    first_transaction_date: datetime
    last_transaction_date: datetime


class BankTransactionAnalytics(BaseModel):
    """Complete analytics data for bank transactions."""
    kpis: BankTransactionKPIs
    monthly_flow: List[MonthlyFlowData]
    daily_flow: List[DailyFlowData]
    top_categories: List[CategoryBreakdown]
    category_type_distribution: List[CategoryBreakdown]
    top_counterparties: List[CounterpartyBreakdown]
    regional_distribution: List[RegionalData]
    source_distribution: List[SourceDistribution]
    processing_funnel: ProcessingFunnelData
    ai_performance: AIPerformanceData
    low_confidence_items: List[LowConfidenceItem]
    activity_heatmap: List[ActivityHeatmapPoint]
    status_timeline: List[StatusTimelinePoint]
    confidence_scatter: List[ConfidenceScatterPoint]
    regular_payments: List[RegularPaymentSummary]
    exhibitions: List[ExhibitionData]


# ==================== Regular Payment Patterns ====================

class RegularPaymentPattern(BaseModel):
    """Detected regular payment pattern."""
    counterparty_inn: Optional[str] = None
    counterparty_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    avg_amount: float
    frequency_days: int
    last_payment_date: str
    transaction_count: int
    is_monthly: bool = False
    is_quarterly: bool = False

    @property
    def frequency_label(self) -> str:
        """Human-readable frequency label."""
        if self.is_monthly:
            return "Ежемесячно"
        elif self.is_quarterly:
            return "Ежеквартально"
        elif self.frequency_days <= 7:
            return "Еженедельно"
        elif self.frequency_days <= 14:
            return "Раз в 2 недели"
        else:
            return f"Каждые {self.frequency_days} дней"


class RegularPaymentPatternList(BaseModel):
    """List of regular payment patterns."""
    patterns: List[RegularPaymentPattern]
    total_count: int
    monthly_count: int
    quarterly_count: int
    other_count: int


# ==================== Account Grouping ====================

class AccountGrouping(BaseModel):
    """Grouping of transactions by account number."""
    account_number: str
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    our_bank_name: Optional[str] = None
    our_bank_bik: Optional[str] = None
    total_count: int
    credit_count: int
    debit_count: int
    total_credit_amount: Decimal
    total_debit_amount: Decimal
    balance: Decimal
    needs_processing_count: int
    approved_count: int
    last_transaction_date: Optional[datetime] = None


class AccountGroupingList(BaseModel):
    """List of account groupings."""
    accounts: List[AccountGrouping]
    total_accounts: int
