import apiClient from './client'

export interface Contractor {
  id: number
  name: string
  short_name: string | null
  inn: string | null
  kpp: string | null
  ogrn: string | null
  address: string | null
  phone: string | null
  email: string | null
  contact_person: string | null
  bank_account: string | null
  bank_name: string | null
  bank_bik: string | null
  is_active: boolean
  guid_1c: string | null
  created_at: string
  updated_at: string | null
}

export interface ContractorFilters {
  skip?: number
  limit?: number
  is_active?: boolean
  search?: string
}

export const getContractors = async (filters: ContractorFilters = {}): Promise<Contractor[]> => {
  const response = await apiClient.get('/contractors', { params: filters })
  return response.data
}

export const getContractor = async (id: number): Promise<Contractor> => {
  const response = await apiClient.get(`/contractors/${id}`)
  return response.data
}

export const createContractor = async (data: Partial<Contractor>): Promise<Contractor> => {
  const response = await apiClient.post('/contractors', data)
  return response.data
}

export const updateContractor = async (id: number, data: Partial<Contractor>): Promise<Contractor> => {
  const response = await apiClient.put(`/contractors/${id}`, data)
  return response.data
}

export const deleteContractor = async (id: number): Promise<void> => {
  await apiClient.delete(`/contractors/${id}`)
}
