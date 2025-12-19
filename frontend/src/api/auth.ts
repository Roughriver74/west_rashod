import apiClient from './client'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  role: string
  department_id: number | null
  is_active: boolean
}

export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  const formData = new URLSearchParams()
  formData.append('username', data.username)
  formData.append('password', data.password)

  const response = await apiClient.post<LoginResponse>('/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  })
  return response.data
}

export const getCurrentUser = async (): Promise<User> => {
  const response = await apiClient.get<User>('/auth/me')
  return response.data
}
