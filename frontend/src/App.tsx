import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import { Spin } from 'antd'

import LoginPage from './pages/LoginPage'
import AppLayout from './components/AppLayout'
import DashboardPage from './pages/DashboardPage'
import BankTransactionsPage from './pages/BankTransactionsPage'
import CategoriesPage from './pages/CategoriesPage'
import OrganizationsPage from './pages/OrganizationsPage'
import MappingsPage from './pages/MappingsPage'
import Sync1CPage from './pages/Sync1CPage'

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
                <Route path="/categories" element={<CategoriesPage />} />
                <Route path="/organizations" element={<OrganizationsPage />} />
                <Route path="/mappings" element={<MappingsPage />} />
                <Route path="/sync-1c" element={<Sync1CPage />} />
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
