/**
 * Types for Bank Transactions
 */

export enum BankTransactionType {
  DEBIT = 'DEBIT',
  CREDIT = 'CREDIT',
}

export enum BankTransactionStatus {
  NEW = 'NEW',
  CATEGORIZED = 'CATEGORIZED',
  MATCHED = 'MATCHED',
  APPROVED = 'APPROVED',
  NEEDS_REVIEW = 'NEEDS_REVIEW',
  IGNORED = 'IGNORED',
}

export interface BankTransaction {
  id: number
  transaction_date: string
  amount: number
  transaction_type: BankTransactionType
  payment_source?: 'BANK' | 'CASH'
  counterparty_name?: string
  counterparty_inn?: string
  counterparty_kpp?: string
  counterparty_account?: string
  counterparty_bank?: string
  counterparty_bik?: string
  payment_purpose?: string
  organization_id?: number
  account_number?: string
  document_number?: string
  document_date?: string
  category_id?: number
  category_confidence?: number
  suggested_category_id?: number
  expense_id?: number
  matching_score?: number
  suggested_expense_id?: number
  status: BankTransactionStatus
  notes?: string
  is_regular_payment: boolean
  regular_payment_pattern_id?: number
  reviewed_by?: number
  reviewed_at?: string
  department_id: number
  import_source?: string
  import_file_name?: string
  imported_at?: string
  external_id_1c?: string
  is_active: boolean
  created_at: string
  updated_at?: string
  // Relations
  category_name?: string
  suggested_category_name?: string
  expense_number?: string
  suggested_expense_number?: string
  organization_name?: string
  reviewed_by_name?: string
  department_name?: string
}

export interface BankTransactionCreate {
  transaction_date: string
  amount: number
  transaction_type: BankTransactionType
  counterparty_name?: string
  counterparty_inn?: string
  counterparty_kpp?: string
  counterparty_account?: string
  counterparty_bank?: string
  counterparty_bik?: string
  payment_purpose?: string
  organization_id?: number
  account_number?: string
  document_number?: string
  document_date?: string
  notes?: string
  department_id: number
}

export interface BankTransactionUpdate {
  category_id?: number
  expense_id?: number
  status?: BankTransactionStatus
  notes?: string
  is_regular_payment?: boolean
}

export interface BankTransactionCategorize {
  category_id: number
  notes?: string
}

export interface BankTransactionLink {
  expense_id: number
  notes?: string
}

export interface BankTransactionList {
  total: number
  items: BankTransaction[]
  page: number
  page_size: number
  pages: number
}

export interface BankTransactionStats {
  total_transactions: number
  total_amount: number // Deprecated: use total_credit_amount and total_debit_amount
  total_credit_amount: number // Sum of CREDIT (приход) transactions
  total_debit_amount: number // Sum of DEBIT (расход) transactions
  new_count: number
  categorized_count: number
  matched_count: number
  approved_count: number
  needs_review_count: number
  avg_category_confidence?: number
  avg_matching_score?: number
}

export interface BankTransactionImportResult {
  total_rows: number
  imported: number
  skipped: number
  errors: Array<{ row: number; error: string }>
  warnings: Array<{ row: number; warning: string }>
}

export interface MatchingSuggestion {
  expense_id: number
  expense_number: string
  expense_amount: number
  expense_date: string
  expense_category_id?: number
  expense_contractor_name?: string
  matching_score: number
  match_reasons: string[]
}

export interface CategorySuggestion {
  category_id: number
  category_name: string
  confidence: number
  reasoning: string[]
}

export interface RegularPaymentPattern {
  id: number
  counterparty_inn?: string
  counterparty_name?: string
  category_id: number
  category_name: string
  avg_amount: number
  frequency_days: number
  last_payment_date: string
  transaction_count: number
}

export interface BulkCategorizeRequest {
  transaction_ids: number[]
  category_id: number
  notes?: string
}

export interface BulkLinkRequest {
  links: Array<{ transaction_id: number; expense_id: number }>
}

export interface BulkStatusUpdateRequest {
  transaction_ids: number[]
  status: BankTransactionStatus
}

// ===================================================================
// Analytics Types
// ===================================================================

export interface BankTransactionKPIs {
  // Financial metrics
  total_debit_amount: number
  total_credit_amount: number
  net_flow: number
  total_transactions: number

  // Comparison with previous period
  debit_change_percent?: number
  credit_change_percent?: number
  net_flow_change_percent?: number
  transactions_change?: number

  // Status distribution
  new_count: number
  categorized_count: number
  matched_count: number
  approved_count: number
  needs_review_count: number
  ignored_count: number

  // Status percentages
  new_percent: number
  categorized_percent: number
  matched_percent: number
  approved_percent: number
  needs_review_percent: number
  ignored_percent: number

  // AI metrics
  avg_category_confidence?: number
  auto_categorized_count: number
  auto_categorized_percent: number
  regular_payments_count: number
  regular_payments_percent: number
}

export interface MonthlyFlowData {
  year: number
  month: number
  month_name: string
  debit_amount: number
  credit_amount: number
  net_flow: number
  transaction_count: number
  avg_confidence?: number
}

export interface CategoryBreakdown {
  category_id: number
  category_name: string
  category_type?: string
  transaction_count: number
  total_amount: number
  avg_amount: number
  avg_confidence?: number
  percent_of_total: number
}

export interface CounterpartyBreakdown {
  counterparty_inn?: string
  counterparty_name: string
  transaction_count: number
  total_amount: number
  avg_amount: number
  first_transaction_date: string
  last_transaction_date: string
  is_regular: boolean
}

export interface RegionalData {
  region: string
  transaction_count: number
  total_amount: number
  percent_of_total: number
}

export interface SourceDistribution {
  payment_source: string
  year: number
  month: number
  month_name: string
  transaction_count: number
  total_amount: number
}

export interface ProcessingFunnelStage {
  status: string
  count: number
  amount: number
  percent_of_total: number
  avg_processing_hours?: number
}

export interface ProcessingFunnelData {
  stages: ProcessingFunnelStage[]
  total_count: number
  conversion_rate_to_approved: number
}

export interface ConfidenceBracket {
  bracket: string
  min_confidence: number
  max_confidence: number
  count: number
  total_amount: number
  percent_of_total: number
}

export interface AIPerformanceData {
  confidence_distribution: ConfidenceBracket[]
  avg_confidence: number
  high_confidence_count: number
  high_confidence_percent: number
  low_confidence_count: number
  low_confidence_percent: number
}

export interface ExhibitionData {
  transaction_id: number
  transaction_date: string
  exhibition: string
  counterparty_name: string
  amount: number
  category_name?: string
}

export interface LowConfidenceItem {
  transaction_id: number
  transaction_date: string
  counterparty_name: string
  amount: number
  payment_purpose?: string
  suggested_category_name?: string
  category_confidence: number
  status: string
}

export interface RegularPaymentSummary {
  counterparty_inn?: string
  counterparty_name: string
  category_name: string
  avg_amount: number
  amount_variance: number
  payment_count: number
  avg_days_between?: number
  last_payment_date: string
  next_expected_date?: string
}

export interface DailyFlowData {
  date: string
  debit_amount: number
  credit_amount: number
  net_flow: number
  transaction_count: number
}

export interface ActivityHeatmapPoint {
  day_of_week: number
  hour: number
  transaction_count: number
  total_amount: number
  avg_amount: number
}

export interface StatusTimelinePoint {
  date: string
  new_count: number
  categorized_count: number
  matched_count: number
  approved_count: number
  needs_review_count: number
  ignored_count: number
}

export interface ConfidenceScatterPoint {
  transaction_id: number
  transaction_date: string
  counterparty_name?: string
  amount: number
  category_confidence?: number
  status: string
  transaction_type: BankTransactionType
  is_regular_payment: boolean
}

export interface BankTransactionAnalytics {
  kpis: BankTransactionKPIs
  monthly_flow: MonthlyFlowData[]
  daily_flow: DailyFlowData[]
  top_categories: CategoryBreakdown[]
  category_type_distribution: CategoryBreakdown[]
  top_counterparties: CounterpartyBreakdown[]
  regional_distribution: RegionalData[]
  source_distribution: SourceDistribution[]
  processing_funnel: ProcessingFunnelData
  ai_performance: AIPerformanceData
  low_confidence_items: LowConfidenceItem[]
  activity_heatmap: ActivityHeatmapPoint[]
  status_timeline: StatusTimelinePoint[]
  confidence_scatter: ConfidenceScatterPoint[]
  regular_payments: RegularPaymentSummary[]
  exhibitions: ExhibitionData[]
}

export interface BankTransactionAnalyticsParams {
  date_from?: string
  date_to?: string
  year?: number
  month?: number
  quarter?: number
  transaction_type?: BankTransactionType
  payment_source?: 'BANK' | 'CASH'
  status?: BankTransactionStatus
  region?: string
  category_id?: number
  department_id?: number
  compare_previous_period?: boolean
}
