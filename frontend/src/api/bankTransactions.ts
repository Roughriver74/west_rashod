import apiClient from './client'

export interface BankTransaction {
  id: number
  transaction_date: string
  amount: number
  transaction_type: 'DEBIT' | 'CREDIT'
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
  date_from?: string
  date_to?: string
  search?: string
  category_id?: number
  only_unprocessed?: boolean
  skip?: number
  limit?: number
}

export const getBankTransactions = async (filters: TransactionFilters): Promise<BankTransaction[]> => {
  const response = await apiClient.get('/bank-transactions', { params: filters })
  return response.data
}

export const getTransactionStats = async (params: object = {}): Promise<BankTransactionStats> => {
  const response = await apiClient.get('/bank-transactions/stats', { params })
  return response.data
}

export const categorizeTransaction = async (id: number, data: { category_id: number; notes?: string }) => {
  const response = await apiClient.put(`/bank-transactions/${id}/categorize`, data)
  return response.data
}

export const bulkCategorize = async (data: { transaction_ids: number[]; category_id: number }) => {
  const response = await apiClient.post('/bank-transactions/bulk-categorize', data)
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
  debit_change_percent: number | null
  credit_change_percent: number | null
  net_flow_change_percent: number | null
  transactions_change: number | null
  new_count: number
  categorized_count: number
  approved_count: number
  needs_review_count: number
  ignored_count: number
  new_percent: number
  categorized_percent: number
  approved_percent: number
  needs_review_percent: number
  ignored_percent: number
  avg_category_confidence: number | null
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
  avg_confidence: number | null
}

export interface CategoryBreakdown {
  category_id: number
  category_name: string
  category_type: string | null
  transaction_count: number
  total_amount: number
  avg_amount: number
  avg_confidence: number | null
  percent_of_total: number
}

export interface CounterpartyBreakdown {
  counterparty_inn: string | null
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
    confidence_distribution: { bracket: string; count: number; total_amount: number; percent_of_total: number }[]
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
    payment_purpose: string | null
    suggested_category_name: string | null
    category_confidence: number
    status: string
  }[]
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

export const updateTransaction = async (id: number, data: Partial<BankTransaction>) => {
  const response = await apiClient.put(`/bank-transactions/${id}`, data)
  return response.data
}
