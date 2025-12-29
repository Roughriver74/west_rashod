import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import { Spin } from 'antd'

import LoginPage from './pages/LoginPage'
import UnifiedLayout from './components/UnifiedLayout'
import DashboardPage from './pages/DashboardPage'
import BankTransactionsPage from './pages/BankTransactionsPage'
import BankTransactionsAnalyticsPage from './pages/BankTransactionsAnalyticsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import RegularPaymentsPage from './pages/RegularPaymentsPage'
import ExpensesPage from './pages/ExpensesPage'
import PaymentCalendarPage from './pages/PaymentCalendarPage'
import CategoriesPage from './pages/CategoriesPage'
import CategorizationRulesPage from './pages/CategorizationRulesPage'
import OrganizationsPage from './pages/OrganizationsPage'
import ContractorsPage from './pages/ContractorsPage'
import MappingsPage from './pages/MappingsPage'
import Sync1CPage from './pages/Sync1CPage'
import SyncSettingsPage from './pages/SyncSettingsPage'

// Fin Module Pages
import FinDashboardPage from './modules/fin/pages/FinDashboardPage'
import FinContractsPage from './modules/fin/pages/FinContractsPage'
import FinImportPage from './modules/fin/pages/FinImportPage'
import FinAnalyticsPage from './modules/fin/pages/FinAnalyticsPage'
import FinCashFlowPage from './modules/fin/pages/FinCashFlowPage'
import FinReceiptsPage from './modules/fin/pages/FinReceiptsPage'
import FinExpensesPage from './modules/fin/pages/FinExpensesPage'
import FinKPIPage from './modules/fin/pages/FinKPIPage'
import FinCalendarPage from './modules/fin/pages/FinCalendarPage'
import FinTurnoverBalancePage from './modules/fin/pages/FinTurnoverBalancePage'
import FinAdjustmentsPage from './modules/fin/pages/FinAdjustmentsPage'
import FinContractOperationsPage from './modules/fin/pages/FinContractOperationsPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* All routes under one unified layout */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <UnifiedLayout />
          </ProtectedRoute>
        }
      >
        {/* Main App Routes */}
        <Route index element={<DashboardPage />} />
        <Route path="bank-transactions" element={<BankTransactionsPage />} />
        <Route path="bank-transactions-analytics" element={<BankTransactionsAnalyticsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="regular-payments" element={<RegularPaymentsPage />} />
        <Route path="expenses" element={<ExpensesPage />} />
        <Route path="payment-calendar" element={<PaymentCalendarPage />} />
        <Route path="categories" element={<CategoriesPage />} />
        <Route path="categorization-rules" element={<CategorizationRulesPage />} />
        <Route path="organizations" element={<OrganizationsPage />} />
        <Route path="contractors" element={<ContractorsPage />} />
        <Route path="mappings" element={<MappingsPage />} />
        <Route path="sync-1c" element={<Sync1CPage />} />
        <Route path="sync-settings" element={<SyncSettingsPage />} />

        {/* Fin Module Routes */}
        <Route path="fin">
          <Route index element={<FinDashboardPage />} />
          <Route path="analytics" element={<FinAnalyticsPage />} />
          <Route path="contracts" element={<FinContractsPage />} />
          <Route path="contract-operations" element={<FinContractOperationsPage />} />
          <Route path="cashflow" element={<FinCashFlowPage />} />
          <Route path="receipts" element={<FinReceiptsPage />} />
          <Route path="expenses" element={<FinExpensesPage />} />
          <Route path="kpi" element={<FinKPIPage />} />
          <Route path="calendar" element={<FinCalendarPage />} />
          <Route path="turnover-balance" element={<FinTurnoverBalancePage />} />
          <Route path="osv" element={<FinTurnoverBalancePage />} />
          <Route path="adjustments" element={<FinAdjustmentsPage />} />
          <Route path="import" element={<FinImportPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default App
