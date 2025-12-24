import apiClient from './client'
import type {
  CategorizationWithSuggestionsResponse,
  BulkCategorizationWithSuggestionsResponse,
  CreateRuleFromSuggestionRequest,
  RuleSuggestionsResponse
} from '../types/bankTransaction'

export interface BankTransaction {
  id: number
  transaction_date: string
  amount: number
  transaction_type: 'DEBIT' | 'CREDIT'
  vat_amount?: number | null
  vat_rate?: number | null
  counterparty_name: string | null
  counterparty_inn: string | null
  counterparty_kpp: string | null
  counterparty_account: string | null
  counterparty_bank: string | null
  counterparty_bik: string | null
  payment_purpose: string | null
  business_operation: string | null
  category_id: number | null
  category_name: string | null
  suggested_category_id: number | null
  suggested_category_name: string | null
  category_confidence: number | null
  organization_id: number | null
  organization_name: string | null
  account_number: string | null
  document_number: string | null
  document_date: string | null
  status: string
  notes: string | null
  is_regular_payment: boolean
  payment_source: 'BANK' | 'CASH'
  created_at: string
  updated_at: string | null
}

export interface BankTransactionStats {
  total: number
  new: number
  categorized: number
  approved: number
  needs_review: number
  ignored: number
  total_debit: number
  total_credit: number
}

export interface TransactionFilters {
  status?: string
  transaction_type?: string
  payment_source?: string
  date_from?: string
  date_to?: string
  search?: string
  category_id?: number
  account_number?: string
  organization_id?: number
  only_unprocessed?: boolean
  skip?: number
  limit?: number
  offset?: number
}

export interface PaginatedBankTransactions {
  items: BankTransaction[]
  total: number
}

export const getBankTransactions = async (filters: TransactionFilters): Promise<PaginatedBankTransactions> => {
  // Remove undefined/null values from params
  const cleanParams = Object.entries(filters).reduce((acc, [key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      acc[key] = value
    }
    return acc
  }, {} as Record<string, any>)

  // Use skip instead of offset if offset is provided
  if (cleanParams.offset !== undefined) {
    cleanParams.skip = cleanParams.offset
    delete cleanParams.offset
  }

  const response = await apiClient.get('/bank-transactions', { params: cleanParams })
  return response.data
}

export const getTransactionStats = async (params: object = {}): Promise<BankTransactionStats> => {
  const response = await apiClient.get('/bank-transactions/stats', { params })
  return response.data
}

export const categorizeTransaction = async (
  id: number,
  data: { category_id: number; notes?: string }
): Promise<CategorizationWithSuggestionsResponse> => {
  const response = await apiClient.put(`/bank-transactions/${id}/categorize`, data)
  return response.data
}

export const bulkCategorize = async (
  data: { transaction_ids: number[]; category_id: number }
): Promise<BulkCategorizationWithSuggestionsResponse> => {
  const response = await apiClient.post('/bank-transactions/bulk-categorize', data)
  return response.data
}

export const createRuleFromSuggestion = async (
  data: CreateRuleFromSuggestionRequest
): Promise<{ success: boolean; message: string; rule_id: number; applied_count?: number }> => {
  const response = await apiClient.post('/bank-transactions/create-rule-from-suggestion', data)
  return response.data
}

export const bulkStatusUpdate = async (data: { transaction_ids: number[]; status: string }) => {
  const response = await apiClient.post('/bank-transactions/bulk-status-update', data)
  return response.data
}

export const getCategorySuggestions = async (id: number) => {
  const response = await apiClient.get(`/bank-transactions/${id}/category-suggestions`)
  return response.data
}

export const importFromExcel = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post('/bank-transactions/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

// Analytics types
export interface BankTransactionKPIs {
  total_debit_amount: number
  total_credit_amount: number
  net_flow: number
  total_transactions: number
  debit_change_percent?: number
  credit_change_percent?: number
  net_flow_change_percent?: number
  transactions_change?: number
  new_count: number
  categorized_count: number
  matched_count: number
  approved_count: number
  needs_review_count: number
  ignored_count: number
  new_percent: number
  categorized_percent: number
  matched_percent: number
  approved_percent: number
  needs_review_percent: number
  ignored_percent: number
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

export interface BankTransactionAnalytics {
  kpis: BankTransactionKPIs
  monthly_flow: MonthlyFlowData[]
  daily_flow: { date: string; debit_amount: number; credit_amount: number; net_flow: number; transaction_count: number }[]
  top_categories: CategoryBreakdown[]
  category_type_distribution: CategoryBreakdown[]
  top_counterparties: CounterpartyBreakdown[]
  processing_funnel: {
    stages: { status: string; count: number; amount: number; percent_of_total: number }[]
    total_count: number
    conversion_rate_to_approved: number
  }
  ai_performance: {
    confidence_distribution: { bracket: string; min_confidence: number; max_confidence: number; count: number; total_amount: number; percent_of_total: number }[]
    avg_confidence: number
    high_confidence_count: number
    high_confidence_percent: number
    low_confidence_count: number
    low_confidence_percent: number
  }
  low_confidence_items: {
    transaction_id: number
    transaction_date: string
    counterparty_name: string
    amount: number
    payment_purpose?: string
    suggested_category_name?: string
    category_confidence: number
    status: string
  }[]
  activity_heatmap: { day_of_week: number; hour: number; transaction_count: number; total_amount: number; avg_amount: number }[]
  status_timeline: { date: string; new_count: number; categorized_count: number; matched_count: number; approved_count: number; needs_review_count: number; ignored_count: number }[]
  confidence_scatter: { transaction_id: number; transaction_date: string; counterparty_name?: string; amount: number; category_confidence?: number; status: string; transaction_type: 'DEBIT' | 'CREDIT'; is_regular_payment: boolean }[]
  regular_payments: { counterparty_inn?: string; counterparty_name: string; category_name: string; avg_amount: number; amount_variance: number; payment_count: number; avg_days_between?: number; last_payment_date: string; next_expected_date?: string }[]
  exhibitions: { transaction_id: number; transaction_date: string; exhibition: string; counterparty_name: string; amount: number; category_name?: string }[]
  regional_distribution: { region: string; transaction_count: number; total_amount: number; percent_of_total: number }[]
  source_distribution: { payment_source: string; year: number; month: number; month_name: string; transaction_count: number; total_amount: number }[]
}

export interface AnalyticsFilters {
  date_from?: string
  date_to?: string
  year?: number
  month?: number
  transaction_type?: string
  category_id?: number
  compare_previous_period?: boolean
}

export const getAnalytics = async (filters: AnalyticsFilters = {}): Promise<BankTransactionAnalytics> => {
  const response = await apiClient.get('/bank-transactions/analytics', { params: filters })
  return response.data
}

export const bulkDelete = async (transaction_ids: number[]) => {
  const response = await apiClient.post('/bank-transactions/bulk-delete', transaction_ids)
  return response.data
}

export const deleteByFilter = async (filters: TransactionFilters) => {
  const cleanParams = Object.entries(filters).reduce((acc, [key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      acc[key] = value
    }
    return acc
  }, {} as Record<string, any>)

  const response = await apiClient.post('/bank-transactions/delete-by-filter', null, {
    params: cleanParams
  })
  return response.data
}

export const updateTransaction = async (id: number, data: Partial<BankTransaction>) => {
  const response = await apiClient.put(`/bank-transactions/${id}`, data)
  return response.data
}

// Regular Payment Patterns
export interface RegularPaymentPattern {
  counterparty_inn: string | null
  counterparty_name: string | null
  category_id: number | null
  category_name: string | null
  avg_amount: number
  frequency_days: number
  last_payment_date: string
  transaction_count: number
  is_monthly: boolean
  is_quarterly: boolean
}

export interface RegularPaymentPatternList {
  patterns: RegularPaymentPattern[]
  total_count: number
  monthly_count: number
  quarterly_count: number
  other_count: number
}

export const getRegularPatterns = async (): Promise<RegularPaymentPatternList> => {
  const response = await apiClient.get('/bank-transactions/regular-patterns')
  return response.data
}

export const markRegularPayments = async (): Promise<{ message: string; marked_count: number }> => {
  const response = await apiClient.post('/bank-transactions/mark-regular-payments')
  return response.data
}

// Similar transactions
export const getSimilarTransactions = async (
  transactionId: number,
  similarityThreshold: number = 0.5,
  limit: number = 1000
): Promise<BankTransaction[]> => {
  const response = await apiClient.get(`/bank-transactions/${transactionId}/similar`, {
    params: { similarity_threshold: similarityThreshold, limit }
  })
  return response.data
}

export const applyCategoryToSimilar = async (
  transactionId: number,
  categoryId: number,
  applyToTransactionIds?: number[]
): Promise<{
  message: string
  updated_count: number
  category_id: number
  category_name: string
  rule_suggestions: RuleSuggestionsResponse
}> => {
  const response = await apiClient.post(`/bank-transactions/${transactionId}/apply-category-to-similar`, {
    category_id: categoryId,
    apply_to_transaction_ids: applyToTransactionIds || null
  })
  return response.data
}

// Account Grouping
export interface AccountGrouping {
  account_number: string
  organization_id: number | null
  organization_name: string | null
  our_bank_name: string | null
  our_bank_bik: string | null
  total_count: number
  credit_count: number
  debit_count: number
  total_credit_amount: number
  total_debit_amount: number
  balance: number
  needs_processing_count: number
  approved_count: number
  last_transaction_date: string | null
}

export interface AccountGroupingList {
  accounts: AccountGrouping[]
  total_accounts: number
}

export const getAccountGrouping = async (filters: {
  date_from?: string
  date_to?: string
  transaction_type?: string
  status?: string
}): Promise<AccountGroupingList> => {
  // Фильтруем undefined параметры, чтобы избежать 422 ошибки
  const cleanParams = Object.fromEntries(
    Object.entries(filters).filter(([_, value]) => value !== undefined && value !== '')
  )
  const response = await apiClient.get('/bank-transactions/account-grouping', { params: cleanParams })
  return response.data
}
