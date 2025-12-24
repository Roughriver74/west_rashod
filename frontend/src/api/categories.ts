import apiClient from './client'

export interface Category {
  id: number
  name: string
  type: 'OPEX' | 'CAPEX'
  description: string | null
  parent_id: number | null
  is_folder: boolean
  code_1c: string | null
  external_id_1c: string | null
  order_index: number | null
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface CategoryTreeNode extends Category {
  children: CategoryTreeNode[]
}

export const getCategories = async (params?: { type?: string; is_active?: boolean; search?: string }): Promise<Category[]> => {
  const response = await apiClient.get('/categories', { params })
  return response.data
}

export const getCategoryTree = async (params?: { type?: string }): Promise<CategoryTreeNode[]> => {
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
