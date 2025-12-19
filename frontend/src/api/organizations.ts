import apiClient from './client'

export interface Organization {
  id: number
  name: string
  inn: string | null
  kpp: string | null
  is_active: boolean
}

export const getOrganizations = async (params?: { is_active?: boolean; search?: string }): Promise<Organization[]> => {
  const response = await apiClient.get('/organizations', { params })
  return response.data
}

export const createOrganization = async (data: Partial<Organization>): Promise<Organization> => {
  const response = await apiClient.post('/organizations', data)
  return response.data
}

export const updateOrganization = async (id: number, data: Partial<Organization>): Promise<Organization> => {
  const response = await apiClient.put(`/organizations/${id}`, data)
  return response.data
}

export const deleteOrganization = async (id: number): Promise<void> => {
  await apiClient.delete(`/organizations/${id}`)
}
