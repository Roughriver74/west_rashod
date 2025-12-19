import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import dayjs from 'dayjs'
import 'dayjs/locale/ru'

import App from './App'
import { AuthProvider } from './contexts/AuthContext'
import { DepartmentProvider } from './contexts/DepartmentContext'

import './index.css'

dayjs.locale('ru')

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider locale={ruRU}>
          <AuthProvider>
            <DepartmentProvider>
              <App />
            </DepartmentProvider>
          </AuthProvider>
        </ConfigProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
)
