import apiClient from './client'

export type RuleType = 'COUNTERPARTY_INN' | 'COUNTERPARTY_NAME' | 'BUSINESS_OPERATION' | 'KEYWORD'

export interface CategorizationRule {
  id: number
  rule_type: RuleType
  counterparty_inn: string | null
  counterparty_name: string | null
  business_operation: string | null
  keyword: string | null
  category_id: number
  category_name: string | null
  priority: number
  confidence: number
  is_active: boolean
  notes: string | null
  created_at: string
  updated_at: string
  created_by: number | null
}

export interface CategorizationRuleCreate {
  rule_type: RuleType
  counterparty_inn?: string | null
  counterparty_name?: string | null
  business_operation?: string | null
  keyword?: string | null
  category_id: number
  priority?: number
  confidence?: number
  is_active?: boolean
  notes?: string | null
}

export interface CategorizationRuleUpdate {
  rule_type?: RuleType
  counterparty_inn?: string | null
  counterparty_name?: string | null
  business_operation?: string | null
  keyword?: string | null
  category_id?: number
  priority?: number
  confidence?: number
  is_active?: boolean
  notes?: string | null
}

export const getCategorizationRules = async (params?: {
  rule_type?: RuleType
  is_active?: boolean
  limit?: number
}): Promise<CategorizationRule[]> => {
  const response = await apiClient.get('/categorization-patterns/rules', { params })
  return response.data
}

export const createCategorizationRule = async (
  data: CategorizationRuleCreate
): Promise<CategorizationRule> => {
  const response = await apiClient.post('/categorization-patterns/rules', data)
  return response.data
}

export const updateCategorizationRule = async (
  id: number,
  data: CategorizationRuleUpdate
): Promise<CategorizationRule> => {
  const response = await apiClient.put(`/categorization-patterns/rules/${id}`, data)
  return response.data
}

export const deleteCategorizationRule = async (id: number): Promise<void> => {
  await apiClient.delete(`/categorization-patterns/rules/${id}`)
}

export const bulkActivateRules = async (rule_ids: number[]): Promise<void> => {
  await apiClient.post('/categorization-patterns/rules/bulk-activate', rule_ids)
}

export const bulkDeactivateRules = async (rule_ids: number[]): Promise<void> => {
  await apiClient.post('/categorization-patterns/rules/bulk-deactivate', rule_ids)
}
