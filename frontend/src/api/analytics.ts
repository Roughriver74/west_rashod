/**
 * API клиент для аналитики и календаря оплат
 */

import apiClient from './client'
import { Expense } from './expenses'

export interface PaymentCalendarDay {
  date: string
  total_amount: number
  payment_count: number
  planned_amount: number
  planned_count: number
}

export interface PaymentsByDay {
  date: string
  paid: Expense[]
  planned: Expense[]
  total_paid_amount: number
  total_planned_amount: number
}

export interface PaymentCalendarFilters {
  year: number
  month: number
  category_id?: number
  organization_id?: number
}

// API Functions

export const getPaymentCalendar = async (filters: PaymentCalendarFilters): Promise<PaymentCalendarDay[]> => {
  const response = await apiClient.get('/analytics/payment-calendar', {
    params: filters
  })
  return response.data
}

export const getPaymentsByDay = async (
  date: string,
  filters?: {
    category_id?: number
    organization_id?: number
  }
): Promise<PaymentsByDay> => {
  const response = await apiClient.get(`/analytics/payment-calendar/${date}`, {
    params: filters
  })
  return response.data
}
