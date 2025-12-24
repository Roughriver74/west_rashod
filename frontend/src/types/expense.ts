/**
 * TypeScript типы для работы с заявками на расход (Expenses)
 */

export enum ExpenseStatus {
  DRAFT = 'DRAFT',
  PENDING = 'PENDING',
  PAID = 'PAID',
  REJECTED = 'REJECTED',
  CANCELLED = 'CANCELLED',
  CLOSED = 'CLOSED' // deprecated, use PAID
}

export enum ExpensePriority {
  LOW = 'LOW',
  NORMAL = 'NORMAL',
  HIGH = 'HIGH',
  URGENT = 'URGENT'
}

export enum ExpenseType {
  ONE_TIME = 'ONE_TIME',
  RECURRING = 'RECURRING'
}

export interface Expense {
  id: number
  number: string
  title: string
  description?: string
  amount: number
  currency: string
  request_date: string
  due_date?: string
  payment_date?: string

  // Classification
  category_id?: number
  category_name?: string
  expense_type?: ExpenseType

  // Counterparty
  contractor_id?: number
  contractor_name?: string
  contractor_inn?: string

  // Organization
  organization_id?: number
  organization_name?: string

  // Status and priority
  status: ExpenseStatus
  priority: ExpensePriority

  // Payment tracking
  amount_paid: number
  remaining_amount?: number

  // Approval workflow
  requested_by?: number
  requested_by_name?: string
  approved_by?: number
  approved_by_name?: string
  approved_at?: string
  rejection_reason?: string

  // Documents
  invoice_number?: string
  invoice_date?: string
  contract_number?: string

  // Additional info
  notes?: string
  payment_purpose?: string

  // New fields from 1C sync
  comment?: string
  requester?: string
  is_paid: boolean
  is_closed: boolean
  imported_from_1c: boolean
  needs_review: boolean
  synced_at?: string

  // Integration
  external_id_1c?: string

  // Linked transactions
  linked_transactions_count?: number
  linked_transactions_amount?: number

  // Meta
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ExpenseFilters {
  skip?: number
  limit?: number
  status?: ExpenseStatus
  priority?: ExpensePriority
  date_from?: string
  date_to?: string
  search?: string
  category_id?: number
  organization_id?: number
  contractor_id?: number
}

export interface ExpenseList {
  total: number
  items: Expense[]
  page: number
  page_size: number
  pages: number
}

export interface ExpenseStats {
  total: number
  draft: number
  pending: number
  approved: number
  rejected: number
  paid: number
  partially_paid: number
  cancelled: number
  total_amount: number
  total_paid: number
  total_pending: number
}

export interface ExpenseCreate {
  title: string
  description?: string
  amount: number
  currency?: string
  request_date: string
  due_date?: string
  category_id?: number
  expense_type?: ExpenseType
  contractor_id?: number
  contractor_name?: string
  contractor_inn?: string
  organization_id?: number
  priority?: ExpensePriority
  invoice_number?: string
  invoice_date?: string
  contract_number?: string
  notes?: string
  payment_purpose?: string
}

export interface ExpenseUpdate {
  title?: string
  description?: string
  amount?: number
  currency?: string
  request_date?: string
  due_date?: string
  payment_date?: string
  category_id?: number
  expense_type?: ExpenseType
  contractor_id?: number
  contractor_name?: string
  contractor_inn?: string
  organization_id?: number
  status?: ExpenseStatus
  priority?: ExpensePriority
  invoice_number?: string
  invoice_date?: string
  contract_number?: string
  notes?: string
  payment_purpose?: string
}
