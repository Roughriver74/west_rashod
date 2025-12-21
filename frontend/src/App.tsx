import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import { Spin } from 'antd'

import LoginPage from './pages/LoginPage'
import AppLayout from './components/AppLayout'
import DashboardPage from './pages/DashboardPage'
import BankTransactionsPage from './pages/BankTransactionsPage'
import BankTransactionsAnalyticsPage from './pages/BankTransactionsAnalyticsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import RegularPaymentsPage from './pages/RegularPaymentsPage'
import ExpensesPage from './pages/ExpensesPage'
import CategoriesPage from './pages/CategoriesPage'
import CategorizationRulesPage from './pages/CategorizationRulesPage'
import OrganizationsPage from './pages/OrganizationsPage'
import ContractorsPage from './pages/ContractorsPage'
import MappingsPage from './pages/MappingsPage'
import Sync1CPage from './pages/Sync1CPage'
import SyncSettingsPage from './pages/SyncSettingsPage'

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
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/bank-transactions" element={<BankTransactionsPage />} />
                <Route path="/bank-transactions-analytics" element={<BankTransactionsAnalyticsPage />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
                <Route path="/regular-payments" element={<RegularPaymentsPage />} />
                <Route path="/expenses" element={<ExpensesPage />} />
                <Route path="/categories" element={<CategoriesPage />} />
                <Route path="/categorization-rules" element={<CategorizationRulesPage />} />
                <Route path="/organizations" element={<OrganizationsPage />} />
                <Route path="/contractors" element={<ContractorsPage />} />
                <Route path="/mappings" element={<MappingsPage />} />
                <Route path="/sync-1c" element={<Sync1CPage />} />
                <Route path="/sync-settings" element={<SyncSettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App
