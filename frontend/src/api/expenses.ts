import apiClient from './client'

export type ExpenseStatus = 'DRAFT' | 'PENDING' | 'APPROVED' | 'REJECTED' | 'PAID' | 'PARTIALLY_PAID' | 'CANCELLED'
export type ExpensePriority = 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT'
export type ExpenseType = 'OPEX' | 'CAPEX'

export interface Expense {
  id: number
  number: string
  title: string
  description: string | null
  amount: number
  amount_paid: number
  currency: string
  request_date: string
  due_date: string | null
  payment_date: string | null
  category_id: number | null
  category_name: string | null
  expense_type: ExpenseType | null
  contractor_id: number | null
  contractor_name: string | null
  contractor_inn: string | null
  organization_id: number | null
  organization_name: string | null
  subdivision: string | null
  subdivision_code: string | null
  status: ExpenseStatus
  priority: ExpensePriority
  requested_by: number | null
  requested_by_name: string | null
  approved_by: number | null
  approved_by_name: string | null
  approved_at: string | null
  rejection_reason: string | null
  invoice_number: string | null
  invoice_date: string | null
  contract_number: string | null
  notes: string | null
  payment_purpose: string | null
  external_id_1c: string | null
  remaining_amount: number | null
  linked_transactions_count: number
  linked_transactions_amount: number
  // New fields from 1C sync
  comment: string | null
  requester: string | null
  is_paid: boolean
  is_closed: boolean
  imported_from_1c: boolean
  needs_review: boolean
  synced_at: string | null
  // Meta
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface ExpenseStats {
  total: number
  draft: number
  pending: number
  approved: number
  rejected: number
  paid: number
  partially_paid: number
  cancelled: number
  total_amount: number
  total_paid: number
  total_pending: number
}

export interface ExpenseFilters {
  status?: ExpenseStatus
  priority?: ExpensePriority
  date_from?: string
  date_to?: string
  search?: string
  category_id?: number
  organization_id?: number
  contractor_id?: number
  subdivision?: string
  skip?: number
  limit?: number
}

export interface ExpenseList {
  total: number
  items: Expense[]
  page: number
  page_size: number
  pages: number
}

export interface ExpenseCreate {
  title: string
  description?: string
  amount: number
  currency?: string
  request_date: string
  due_date?: string
  category_id?: number
  expense_type?: ExpenseType
  contractor_id?: number
  contractor_name?: string
  contractor_inn?: string
  organization_id?: number
  priority?: ExpensePriority
  invoice_number?: string
  invoice_date?: string
  contract_number?: string
  notes?: string
  payment_purpose?: string
}

export interface ExpenseUpdate {
  title?: string
  description?: string
  amount?: number
  currency?: string
  request_date?: string
  due_date?: string
  payment_date?: string
  category_id?: number
  expense_type?: ExpenseType
  contractor_id?: number
  contractor_name?: string
  contractor_inn?: string
  organization_id?: number
  status?: ExpenseStatus
  priority?: ExpensePriority
  invoice_number?: string
  invoice_date?: string
  contract_number?: string
  notes?: string
  payment_purpose?: string
}

export interface MatchingSuggestion {
  expense_id: number
  expense_number: string
  expense_title: string
  expense_amount: number
  expense_date: string
  expense_category_id: number | null
  expense_category_name: string | null
  expense_contractor_name: string | null
  expense_contractor_inn: string | null
  expense_status: string
  remaining_amount: number
  matching_score: number
  match_reasons: string[]
}

// API Functions

export const getExpenses = async (filters: ExpenseFilters = {}): Promise<ExpenseList> => {
  const response = await apiClient.get('/expenses', { params: filters })
  return response.data
}

export const getExpenseStats = async (params: { date_from?: string; date_to?: string } = {}): Promise<ExpenseStats> => {
  const response = await apiClient.get('/expenses/stats', { params })
  return response.data
}

export const getExpense = async (id: number): Promise<Expense> => {
  const response = await apiClient.get(`/expenses/${id}`)
  return response.data
}

export const createExpense = async (data: ExpenseCreate): Promise<Expense> => {
  const response = await apiClient.post('/expenses', data)
  return response.data
}

export const updateExpense = async (id: number, data: ExpenseUpdate): Promise<Expense> => {
  const response = await apiClient.put(`/expenses/${id}`, data)
  return response.data
}

export const deleteExpense = async (id: number): Promise<void> => {
  await apiClient.delete(`/expenses/${id}`)
}

export const submitExpenseForApproval = async (id: number): Promise<{ message: string }> => {
  const response = await apiClient.post(`/expenses/${id}/submit`)
  return response.data
}

export const approveExpense = async (id: number, action: 'approve' | 'reject', rejection_reason?: string): Promise<Expense> => {
  const response = await apiClient.post(`/expenses/${id}/approve`, {
    action,
    rejection_reason
  })
  return response.data
}

export const getExpenseTransactions = async (id: number): Promise<unknown[]> => {
  const response = await apiClient.get(`/expenses/${id}/transactions`)
  return response.data
}

export const unlinkTransactionFromExpense = async (expenseId: number, transactionId: number): Promise<{ message: string }> => {
  const response = await apiClient.post(`/expenses/${expenseId}/unlink/${transactionId}`)
  return response.data
}

// Bank transaction linking
export const getMatchingExpenses = async (transactionId: number, threshold: number = 30): Promise<MatchingSuggestion[]> => {
  const response = await apiClient.get(`/bank-transactions/${transactionId}/matching-expenses`, {
    params: { threshold }
  })
  return response.data
}

export const linkTransactionToExpense = async (transactionId: number, expenseId: number, notes?: string): Promise<{ message: string }> => {
  const response = await apiClient.put(`/bank-transactions/${transactionId}/link`, null, {
    params: { expense_id: expenseId, notes }
  })
  return response.data
}

export const unlinkTransactionFromExpenseByTx = async (transactionId: number): Promise<{ message: string }> => {
  const response = await apiClient.put(`/bank-transactions/${transactionId}/unlink`)
  return response.data
}

export const autoMatchTransactions = async (threshold: number = 70, limit: number = 100): Promise<{
  message: string
  matched_count: number
  matches: Array<{
    transaction_id: number
    expense_id: number
    expense_number: string
    score: number
    reasons: string[]
  }>
}> => {
  const response = await apiClient.post('/bank-transactions/auto-match', null, {
    params: { threshold, limit }
  })
  return response.data
}

// New API methods

export const updateExpenseStatus = async (id: number, status: ExpenseStatus): Promise<Expense> => {
  const response = await apiClient.patch(`/expenses/${id}/status`, null, {
    params: { new_status: status }
  })
  return response.data
}

export const exportExpenses = async (filters: ExpenseFilters = {}): Promise<Blob> => {
  const response = await apiClient.get('/expenses/export', {
    params: filters,
    responseType: 'blob'
  })
  return response.data
}

export const bulkDeleteExpenses = async (filters: ExpenseFilters = {}): Promise<{ message: string; count: number }> => {
  const response = await apiClient.post('/expenses/bulk-delete', null, {
    params: filters
  })
  return response.data
}
