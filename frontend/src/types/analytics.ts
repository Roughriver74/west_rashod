/**
 * TypeScript типы для аналитики и календаря оплат
 */

import { Expense } from './expense'

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
