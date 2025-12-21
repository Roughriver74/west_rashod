import apiClient from './client'

export interface CounterpartyPattern {
  counterparty_inn: string | null
  counterparty_name: string | null
  category_id: number
  category_name: string
  transaction_count: number
  avg_amount: number
  confidence_estimate: number
}

export interface BusinessOperationPattern {
  business_operation: string
  category_id: number
  category_name: string
  transaction_count: number
  confidence_estimate: number
}

export interface CategorizationStats {
  total_transactions: number
  auto_categorized: number
  needs_review: number
  manual_categorized: number
  avg_confidence: number | null
  high_confidence_count: number
  medium_confidence_count: number
  low_confidence_count: number
}

export const getCounterpartyPatterns = async (params?: {
  limit?: number
  min_transactions?: number
}): Promise<CounterpartyPattern[]> => {
  const response = await apiClient.get('/categorization-patterns/counterparties', { params })
  return response.data
}

export const getBusinessOperationPatterns = async (params?: {
  limit?: number
  min_transactions?: number
}): Promise<BusinessOperationPattern[]> => {
  const response = await apiClient.get('/categorization-patterns/business-operations', { params })
  return response.data
}

export const getCategorizationStats = async (): Promise<CategorizationStats> => {
  const response = await apiClient.get('/categorization-patterns/stats')
  return response.data
}
