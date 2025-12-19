import apiClient from './client'

export interface Category {
  id: number
  name: string
  type: 'OPEX' | 'CAPEX'
  description: string | null
  parent_id: number | null
  is_active: boolean
}

export const getCategories = async (params?: { department_id?: number; is_active?: boolean }): Promise<Category[]> => {
  const response = await apiClient.get('/categories', { params })
  return response.data
}

export const getCategoryTree = async (params?: { department_id?: number; type?: string }): Promise<Category[]> => {
  const response = await apiClient.get('/categories/tree', { params })
  return response.data
}

export const createCategory = async (data: Partial<Category>): Promise<Category> => {
  const response = await apiClient.post('/categories', data)
  return response.data
}

export const updateCategory = async (id: number, data: Partial<Category>): Promise<Category> => {
  const response = await apiClient.put(`/categories/${id}`, data)
  return response.data
}

export const deleteCategory = async (id: number): Promise<void> => {
  await apiClient.delete(`/categories/${id}`)
}
