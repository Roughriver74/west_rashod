import apiClient from './client'

export interface Sync1CResult {
  success: boolean
  message?: string
  total_processed: number
  created: number
  updated: number
  skipped: number
  errors: string[]
}

export const testConnection = async () => {
  const response = await apiClient.get('/sync-1c/test-connection')
  return response.data
}

export const syncTransactions = async (data: {
  department_id: number
  date_from?: string
  date_to?: string
  auto_classify?: boolean
}): Promise<Sync1CResult> => {
  const response = await apiClient.post('/sync-1c/bank-transactions/sync', data)
  return response.data
}

export const syncOrganizations = async (data: {
  department_id: number
}): Promise<Sync1CResult> => {
  const response = await apiClient.post(`/sync-1c/organizations/sync?department_id=${data.department_id}`)
  return response.data
}

export const syncCategories = async (data: {
  department_id: number
}): Promise<Sync1CResult> => {
  const response = await apiClient.post(`/sync-1c/categories/sync?department_id=${data.department_id}`)
  return response.data
}
