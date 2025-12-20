import apiClient from './client'

export interface Sync1CResult {
  success: boolean
  message?: string
  statistics: {
    total?: number
    total_fetched?: number
    total_created?: number
    total_updated?: number
    total_skipped?: number
    created?: number
    updated?: number
    skipped?: number
    receipts_created?: number
    payments_created?: number
    cash_receipts_created?: number
    cash_payments_created?: number
  }
  errors: string[]
}

// Helper to get stats from result
export function getResultStats(result: Sync1CResult) {
  const stats = result.statistics || {}
  return {
    total_processed: stats.total ?? stats.total_fetched ?? 0,
    created: stats.created ?? stats.total_created ?? 0,
    updated: stats.updated ?? stats.total_updated ?? 0,
    skipped: stats.skipped ?? stats.total_skipped ?? 0,
  }
}

export const testConnection = async () => {
  const response = await apiClient.get('/sync-1c/test-connection')
  return response.data
}

export const syncTransactions = async (data: {
  date_from?: string
  date_to?: string
  auto_classify?: boolean
}): Promise<Sync1CResult> => {
  const response = await apiClient.post('/sync-1c/bank-transactions/sync', data)
  return response.data
}

export const syncOrganizations = async (_data: object = {}): Promise<Sync1CResult> => {
  const response = await apiClient.post('/sync-1c/organizations/sync')
  return response.data
}

export const syncCategories = async (_data: object = {}): Promise<Sync1CResult> => {
  const response = await apiClient.post('/sync-1c/categories/sync')
  return response.data
}
