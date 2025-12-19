import apiClient from './client'

export interface BankTransaction {
  id: number
  transaction_date: string
  amount: number
  transaction_type: 'DEBIT' | 'CREDIT'
  counterparty_name: string | null
  counterparty_inn: string | null
  payment_purpose: string | null
  category_id: number | null
  category_name: string | null
  organization_id: number | null
  organization_name: string | null
  status: string
  created_at: string
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
