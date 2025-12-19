import apiClient from './client'

export interface Department {
  id: number
  name: string
  code: string
  description: string | null
  is_active: boolean
}

export const getDepartments = async (): Promise<Department[]> => {
  const response = await apiClient.get('/departments', { params: { is_active: true } })
  return response.data
}

export const getDepartment = async (id: number): Promise<Department> => {
  const response = await apiClient.get(`/departments/${id}`)
  return response.data
}
