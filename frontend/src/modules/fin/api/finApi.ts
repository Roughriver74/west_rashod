/**
 * API client for Fin module
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8005';

// Create axios instance with auth
const finApi = axios.create({
  baseURL: `${API_BASE}/api/v1/fin`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth interceptor
finApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Types
export interface FinReceipt {
  id: number;
  operation_id: string;
  organization: string | null;
  organization_id: number | null;
  operation_type: string | null;
  bank_account: string | null;
  bank_account_id: number | null;
  accounting_account: string | null;
  document_number: string | null;
  document_date: string | null;
  payer: string | null;
  payer_account: string | null;
  settlement_account: string | null;
  contract_number: string | null;
  contract_id: number | null;
  contract_date: string | null;
  currency: string | null;
  amount: number;
  commission: number;
  payment_purpose: string | null;
  responsible_person: string | null;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinExpense {
  id: number;
  operation_id: string;
  organization: string | null;
  organization_id: number | null;
  operation_type: string | null;
  bank_account: string | null;
  bank_account_id: number | null;
  accounting_account: string | null;
  document_number: string | null;
  document_date: string | null;
  recipient: string | null;
  recipient_account: string | null;
  debit_account: string | null;
  contract_number: string | null;
  contract_id: number | null;
  contract_date: string | null;
  currency: string | null;
  amount: number;
  expense_article: string | null;
  payment_purpose: string | null;
  responsible_person: string | null;
  comment: string | null;
  tax_period: string | null;
  unconfirmed_by_bank: boolean;
  created_at: string;
  updated_at: string;
}

export interface FinContract {
  id: number;
  contract_number: string;
  contract_date: string | null;
  contract_type: string | null;
  counterparty: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FTPImportTask {
  task_id: string;
  status: string;
  progress: number;
  message: string;
  result?: Record<string, unknown>;
}

export interface ListResponse<T> {
  total: number;
  items: T[];
}

// Receipts API
export const getReceipts = async (params: {
  skip?: number;
  limit?: number;
  organizations?: string;
  payers?: string;
  date_from?: string;
  date_to?: string;
  contracts?: string;
}): Promise<ListResponse<FinReceipt>> => {
  const response = await finApi.get('/receipts/', { params });
  return response.data;
};

export const getReceiptsSummary = async (params: {
  organizations?: string;
  date_from?: string;
  date_to?: string;
}): Promise<{ total_records: number; total_amount: number }> => {
  const response = await finApi.get('/receipts/summary', { params });
  return response.data;
};

// Expenses API
export const getExpenses = async (params: {
  skip?: number;
  limit?: number;
  organizations?: string;
  recipients?: string;
  date_from?: string;
  date_to?: string;
  contracts?: string;
}): Promise<ListResponse<FinExpense>> => {
  const response = await finApi.get('/expenses/', { params });
  return response.data;
};

export const getExpensesSummary = async (params: {
  organizations?: string;
  date_from?: string;
  date_to?: string;
}): Promise<{ total_records: number; total_amount: number }> => {
  const response = await finApi.get('/expenses/summary', { params });
  return response.data;
};

export const getExpenseDetails = async (expenseId: number): Promise<FinExpense & { details: unknown[] }> => {
  const response = await finApi.get(`/expenses/${expenseId}`);
  return response.data;
};

// Contracts API
export const getContracts = async (params: {
  skip?: number;
  limit?: number;
  is_active?: boolean;
  contract_type?: string;
  search?: string;
}): Promise<ListResponse<FinContract>> => {
  const response = await finApi.get('/references/contracts', { params });
  return response.data;
};

// FTP Import API
export const triggerFTPImport = async (clearExisting: boolean = true): Promise<{ task_id: string; status: string; message: string }> => {
  const response = await finApi.post('/import/ftp', { clear_existing: clearExisting });
  return response.data;
};

export const getFTPImportStatus = async (taskId: string): Promise<FTPImportTask> => {
  const response = await finApi.get(`/import/ftp/status/${taskId}`);
  return response.data;
};

export const cancelFTPImport = async (taskId: string): Promise<{ task_id: string; status: string; message: string }> => {
  const response = await finApi.post(`/import/ftp/cancel/${taskId}`);
  return response.data;
};

export const getImportLogs = async (params?: {
  skip?: number;
  limit?: number;
  status?: string;
}): Promise<ListResponse<{
  id: number;
  import_date: string;
  source_file: string;
  table_name: string;
  rows_inserted: number;
  rows_updated: number;
  rows_failed: number;
  status: string;
  error_message: string | null;
  processing_time_seconds: number;
}>> => {
  const response = await finApi.get('/import/logs', { params });
  return response.data;
};

// References API
export const getBankAccounts = async (params?: {
  skip?: number;
  limit?: number;
  is_active?: boolean;
}): Promise<ListResponse<{ id: number; account_number: string; bank_name: string | null; is_active: boolean }>> => {
  const response = await finApi.get('/references/bank-accounts', { params });
  return response.data;
};

export const getOrganizations = async (params?: {
  is_active?: boolean;
  search?: string;
}): Promise<ListResponse<{ id: number; name: string; is_active: boolean }>> => {
  const response = await finApi.get('/references/organizations', { params });
  return response.data;
};

export const getUniquePayers = async (params?: {
  search?: string;
  limit?: number;
}): Promise<{ total: number; items: string[] }> => {
  const response = await finApi.get('/references/payers', { params });
  return response.data;
};

export const getUniqueRecipients = async (params?: {
  search?: string;
  limit?: number;
}): Promise<{ total: number; items: string[] }> => {
  const response = await finApi.get('/references/recipients', { params });
  return response.data;
};

// Excluded Payers API
export const getExcludedPayers = async (): Promise<ListResponse<{ id: number; payer_name: string; created_at: string }>> => {
  const response = await finApi.get('/references/excluded-payers');
  return response.data;
};

export const addExcludedPayer = async (payerName: string): Promise<{ id: number; payer_name: string }> => {
  const response = await finApi.post('/references/excluded-payers', { payer_name: payerName });
  return response.data;
};

export const removeExcludedPayer = async (payerId: number): Promise<void> => {
  await finApi.delete(`/references/excluded-payers/${payerId}`);
};

// Analytics API
export interface FinSummary {
  total_receipts: number;
  total_expenses: number;
  balance: number;
  receipts_count: number;
  expenses_count: number;
  contracts_count: number;
  period_start: string | null;
  period_end: string | null;
}

export interface MonthlyCashFlow {
  month: string;
  inflow: number;
  outflow: number;
  net: number;
  cumulative: number;
}

export interface OrganizationStats {
  organization_id: number;
  organization_name: string;
  total_receipts: number;
  total_expenses: number;
  balance: number;
  receipts_count: number;
  expenses_count: number;
}

export const getFinSummary = async (params?: {
  date_from?: string;
  date_to?: string;
  organization_id?: number;
}): Promise<FinSummary> => {
  const response = await finApi.get('/analytics/summary', { params });
  return response.data;
};

export const getMonthlyCashFlow = async (params?: {
  date_from?: string;
  date_to?: string;
  organization_id?: number;
}): Promise<MonthlyCashFlow[]> => {
  const response = await finApi.get('/analytics/monthly-cashflow', { params });
  return response.data;
};

export const getStatsByOrganization = async (params?: {
  date_from?: string;
  date_to?: string;
}): Promise<OrganizationStats[]> => {
  const response = await finApi.get('/analytics/by-organization', { params });
  return response.data;
};

export const getTopPayers = async (params?: {
  limit?: number;
  date_from?: string;
  date_to?: string;
}): Promise<Array<{ payer: string; total: number; count: number }>> => {
  const response = await finApi.get('/analytics/top-payers', { params });
  return response.data;
};

export const getTopRecipients = async (params?: {
  limit?: number;
  date_from?: string;
  date_to?: string;
}): Promise<Array<{ recipient: string; total: number; count: number }>> => {
  const response = await finApi.get('/analytics/top-recipients', { params });
  return response.data;
};

// KPI API
export interface KPIMetrics {
  repaymentVelocity: number;
  paymentEfficiency: number;
  avgInterestRate: number;
  debtRatio: number;
  activeContracts: number;
  totalContracts: number;
  totalReceived: number;
  totalExpenses: number;
  principalPaid: number;
  interestPaid: number;
}

export interface OrgEfficiencyMetric {
  id: number;
  name: string;
  totalPaid: number;
  principal: number;
  interest: number;
  received: number;
  efficiency: number;
  debtRatio: number;
  operationsCount: number;
}

export interface MonthlyEfficiency {
  month: string;
  principal: number;
  interest: number;
  total: number;
  efficiency: number;
}

export const getKPIMetrics = async (params?: {
  date_from?: string;
  date_to?: string;
  organizations?: string;
}): Promise<KPIMetrics> => {
  const response = await finApi.get('/analytics/kpi', { params });
  return response.data;
};

export const getOrgEfficiency = async (params?: {
  date_from?: string;
  date_to?: string;
  organizations?: string;
  payers?: string;
  excluded_payers?: string;
  contracts?: string;
}): Promise<OrgEfficiencyMetric[]> => {
  const response = await finApi.get('/analytics/org-efficiency', { params });
  return response.data;
};

export const getMonthlyEfficiency = async (params?: {
  date_from?: string;
  date_to?: string;
  year?: number;
  organizations?: string;
  payers?: string;
  excluded_payers?: string;
  contracts?: string;
}): Promise<MonthlyEfficiency[]> => {
  const response = await finApi.get('/analytics/monthly-efficiency', { params });
  return response.data;
};

// Contracts Summary API
export interface ContractsSummaryRecord {
  contractId: number;
  contractNumber: string;
  organization: string;
  payer: string;
  totalPaid: number;
  principal: number;
  interest: number;
  totalReceived: number;
  balance: number;
  openingBalance: number;
  paidPercent: number;
  operationsCount: number;
  lastPayment: string | null;
  firstReceipt: string | null;
}

export interface ContractsSummaryPagination {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface ContractsSummaryResponse {
  data: ContractsSummaryRecord[];
  pagination: ContractsSummaryPagination;
}

export const getContractsSummary = async (params?: {
  date_from?: string;
  date_to?: string;
  organizations?: string;
  payers?: string;
  excluded_payers?: string;
  contracts?: string;
  page?: number;
  limit?: number;
  search?: string;
}): Promise<ContractsSummaryResponse> => {
  const response = await finApi.get('/analytics/contracts-summary', { params });
  return response.data;
};

// Turnover Balance API
export interface TurnoverBalanceRow {
  account: string;
  counterparty?: string;
  parentCounterparty?: string;
  inn?: string;
  contract?: string;
  balanceStartDebit: number;
  balanceStartCredit: number;
  turnoverDebit: number;
  turnoverCredit: number;
  balanceEndDebit: number;
  balanceEndCredit: number;
  level: number;
}

export const getTurnoverBalance = async (params?: {
  date_from?: string;
  date_to?: string;
  organizations?: string;
  payers?: string;
  excluded_payers?: string;
  contracts?: string;
  account_number?: string;
}): Promise<TurnoverBalanceRow[]> => {
  const response = await finApi.get('/analytics/turnover-balance', { params });
  return response.data;
};

// Calendar API - payments by date
export const getPaymentsByDate = async (params: {
  date_from: string;
  date_to: string;
  organizations?: string;
}): Promise<Array<{
  date: string;
  count: number;
  total: number;
  expenses: Array<{ id: number; document_date: string; amount: number; organization: string; contract_number?: string }>;
}>> => {
  const response = await finApi.get('/analytics/payments-by-date', { params });
  return response.data;
};

// Adjustments API
export interface ManualAdjustment {
  id: number;
  adjustment_date: string;
  counterparty: string | null;
  contract_number: string | null;
  adjustment_type: 'receipt' | 'expense';  // receipt = поступление, expense = списание
  payment_type: string | null;  // For expense: 'Погашение долга', 'Уплата процентов'
  amount: number;  // Can be positive (increase) or negative (reversal/decrease)
  description: string | null;
  created_by: string | null;
  created_at: string;
}

export const getAdjustments = async (params?: {
  skip?: number;
  limit?: number;
  date_from?: string;
  date_to?: string;
  adjustment_type?: string;
}): Promise<ListResponse<ManualAdjustment>> => {
  const response = await finApi.get('/adjustments/', { params });
  return response.data;
};

export const createAdjustment = async (data: {
  adjustment_date: string;
  counterparty?: string;
  contract_number?: string;
  adjustment_type: 'receipt' | 'expense';  // receipt = поступление, expense = списание
  payment_type?: string;  // Required for expense: 'Погашение долга' or 'Уплата процентов'
  amount: number;  // Can be positive (increase) or negative (reversal/decrease)
  description?: string;
}): Promise<ManualAdjustment> => {
  const response = await finApi.post('/adjustments/', data);
  return response.data;
};

export const deleteAdjustment = async (id: number): Promise<void> => {
  await finApi.delete(`/adjustments/${id}`);
};

// Expense Details API - for real principal/interest calculations
export interface FinExpenseDetailItem {
  id: number;
  expense_operation_id: string;
  contract_number: string | null;
  repayment_type: string | null;
  settlement_account: string | null;
  advance_account: string | null;
  payment_type: string | null; // 'Погашение долга' or 'Уплата процентов'
  payment_amount: number;
  settlement_rate: number;
  settlement_amount: number;
  vat_amount: number;
  expense_amount: number;
  vat_in_expense: number;
}

export const getAllExpenseDetails = async (params?: {
  skip?: number;
  limit?: number;
  date_from?: string;
  date_to?: string;
  organizations?: string;
}): Promise<ListResponse<FinExpenseDetailItem>> => {
  const response = await finApi.get('/expenses/details/all', { params });
  return response.data;
};

// Credit Balances - for Dashboard KPIs
export interface CreditBalances {
  openingBalance: number;
  periodReceived: number;
  periodPrincipalPaid: number;
  periodInterestPaid: number;
  closingBalance: number;
  totalDebt: number;
}

export const getCreditBalances = async (params?: {
  date_from?: string;
  date_to?: string;
  organizations?: string;
  payers?: string;
  excluded_payers?: string;
  contracts?: string;
}): Promise<CreditBalances> => {
  // Use backend endpoint for correct opening balance calculation
  const response = await finApi.get('/analytics/credit-balances', { params });
  const data = response.data;

  return {
    openingBalance: data.opening_balance || 0,
    periodReceived: data.period_received || 0,
    periodPrincipalPaid: data.period_principal_paid || 0,
    periodInterestPaid: data.period_interest_paid || 0,
    closingBalance: data.closing_balance || 0,
    totalDebt: data.total_debt || 0
  };
};

// Contract Operations - for Contract Details Page
export interface ContractOperation {
  id: number;
  type: 'receipt' | 'expense';
  operation_id?: string;
  document_date: string | null;
  document_number: string | null;
  amount: number;
  principal: number;
  interest: number;
  payer?: string;
  recipient?: string;
  payment_purpose: string | null;
  organization: string | null;
  is_adjustment?: boolean;
}

export interface ContractOperationsResponse {
  contract_number: string;
  organization: string | null;
  summary: {
    opening_balance: number;
    total_received: number;
    total_paid: number;
    principal_paid: number;
    interest_paid: number;
    closing_balance: number;
  };
  statistics: {
    receipts_count: number;
    expenses_count: number;
    total_operations: number;
  };
  operations: ContractOperation[];
}

export const getContractOperations = async (
  contractNumber: string,
  params?: {
    date_from?: string;
    date_to?: string;
  }
): Promise<ContractOperationsResponse> => {
  const response = await finApi.get(
    `/analytics/contract-operations/${encodeURIComponent(contractNumber)}`,
    { params }
  );
  return response.data;
};

export const getContractOperationsById = async (
  contractId: number,
  params?: {
    date_from?: string;
    date_to?: string;
  }
): Promise<ContractOperationsResponse> => {
  // Use the new endpoint that accepts contract_id as query parameter
  const response = await finApi.get('/analytics/contract-operations-by-id', {
    params: {
      contract_id: contractId,
      ...params,
    },
  });
  return response.data;
};

export default finApi;
