import { Layout, Menu, Typography, Avatar, Dropdown, Space, Button } from 'antd'
import {
  BankOutlined,
  CalendarOutlined,
  DashboardOutlined,
  TagsOutlined,
  TeamOutlined,
  SyncOutlined,
  LogoutOutlined,
  UserOutlined,
  FileTextOutlined,
  LineChartOutlined,
  RobotOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ClockCircleOutlined,
  CloudDownloadOutlined,
  FundOutlined,
  DollarOutlined,
  BarChartOutlined,
  TableOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { ReactNode, useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'

const { Header, Sider, Content } = Layout
const { Text } = Typography

interface AppLayoutProps {
  children: ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebarCollapsed')
    return saved ? JSON.parse(saved) : false
  })

  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', JSON.stringify(collapsed))
  }, [collapsed])

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Дашборд',
    },
    {
      key: '/bank-transactions',
      icon: <BankOutlined />,
      label: 'Банковские операции',
    },
    {
      key: '/bank-transactions-analytics',
      icon: <LineChartOutlined />,
      label: 'Аналитика',
    },
    {
      key: '/expenses',
      icon: <FileTextOutlined />,
      label: 'Заявки на расходы',
    },
    {
      key: '/payment-calendar',
      icon: <CalendarOutlined />,
      label: 'Календарь оплат',
    },
    {
      key: '/categories',
      icon: <TagsOutlined />,
      label: 'Категории',
    },
    {
      key: '/organizations',
      icon: <TeamOutlined />,
      label: 'Организации',
    },
    {
      key: '/categorization-rules',
      icon: <RobotOutlined />,
      label: 'Правила категоризации',
    },
    
    {
      key: '/sync-1c',
      icon: <SyncOutlined />,
      label: 'Синхронизация 1С',
    },
    {
      key: '/sync-settings',
      icon: <ClockCircleOutlined />,
      label: 'Настройки синхронизации',
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'fin-group',
      type: 'group' as const,
      label: 'Финансовый модуль',
      children: [
        {
          key: '/fin',
          icon: <FundOutlined />,
          label: 'Фин. дашборд',
        },
        {
          key: '/fin/analytics',
          icon: <LineChartOutlined />,
          label: 'Фин. аналитика',
        },
        {
          key: '/fin/cashflow',
          icon: <DollarOutlined />,
          label: 'Cash Flow',
        },
    
        {
          key: '/fin/contracts',
          icon: <FileTextOutlined />,
          label: 'Договоры',
        },
        {
          key: '/fin/kpi',
          icon: <BarChartOutlined />,
          label: 'KPI',
        },
        {
          key: '/fin/calendar',
          icon: <CalendarOutlined />,
          label: 'Фин. календарь',
        },
        {
          key: '/fin/turnover-balance',
          icon: <TableOutlined />,
          label: 'ОСВ',
        },
        {
          key: '/fin/import',
          icon: <CloudDownloadOutlined />,
          label: 'FTP импорт',
        },
      ],
    },
  ]

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выйти',
      onClick: () => {
        logout()
        navigate('/login')
      },
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={240}
        theme="dark"
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
      >
        <div style={{ padding: '16px', textAlign: 'center' }}>
          {!collapsed && (
            <Text style={{ color: 'white', fontSize: '18px', fontWeight: 'bold' }}>
              West Поток
            </Text>
          )}
          {collapsed && (
            <Text style={{ color: 'white', fontSize: '18px', fontWeight: 'bold' }}>
              WP
            </Text>
          )}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{
              fontSize: '16px',
              width: 64,
              height: 64,
            }}
          />
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} />
              <Text>{user?.full_name || user?.username}</Text>
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ padding: '24px', background: '#f5f5f5' }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}
