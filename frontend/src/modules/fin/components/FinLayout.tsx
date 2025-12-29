import { useState, useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Layout, Menu, Typography, Avatar, Dropdown, Space, Button, theme } from 'antd'
import {
  DashboardOutlined,
  BarChartOutlined,
  FileTextOutlined,
  LineChartOutlined,
  CalendarOutlined,
  RiseOutlined,
  TableOutlined,
  EditOutlined,
  CloudDownloadOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  ArrowLeftOutlined,
  DollarOutlined,
  BankOutlined,
  TagsOutlined,
  ApartmentOutlined,
  SlidersOutlined,
  SyncOutlined,
  SettingOutlined,
  DollarCircleOutlined,
} from '@ant-design/icons'
import { useAuth } from '../../../contexts/AuthContext'
import FinFilters from './FinFilters'
import '../styles/fin-theme.css'

const { Header, Sider, Content } = Layout
const { Text } = Typography

export default function FinLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem('finSidebarCollapsed')
    return saved ? JSON.parse(saved) : true
  })
  const [openKeys, setOpenKeys] = useState<string[]>(() => {
    const saved = localStorage.getItem('finSidebarCollapsed')
    const isCollapsed = saved ? JSON.parse(saved) : true
    return isCollapsed ? [] : ['main-group', 'fin-group']
  })
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { token } = theme.useToken()

  const mainNavItems = [
    { key: '/', icon: <DashboardOutlined />, label: 'Дашборд' },
    { key: '/bank-transactions', icon: <BankOutlined />, label: 'Банковские операции' },
    { key: '/analytics', icon: <BarChartOutlined />, label: 'Аналитика' },
    { key: '/regular-payments', icon: <DollarCircleOutlined />, label: 'Заявки на расходы' },
    { key: '/payment-calendar', icon: <CalendarOutlined />, label: 'Календарь оплат' },
    { key: '/categories', icon: <TagsOutlined />, label: 'Категории' },
    { key: '/organizations', icon: <ApartmentOutlined />, label: 'Организации' },
    { key: '/categorization-rules', icon: <SlidersOutlined />, label: 'Правила категоризации' },
    { key: '/sync-1c', icon: <SyncOutlined />, label: 'Синхронизация 1С' },
    { key: '/sync-settings', icon: <SettingOutlined />, label: 'Настройки синхронизации' },
  ]

  const finNavItems = [
    { key: '/fin', icon: <DashboardOutlined />, label: 'Фин. дашборд' },
    { key: '/fin/analytics', icon: <BarChartOutlined />, label: 'Фин. аналитика' },
    { key: '/fin/cashflow', icon: <LineChartOutlined />, label: 'Cash Flow' },
    { key: '/fin/contracts', icon: <FileTextOutlined />, label: 'Договоры' },
    { key: '/fin/kpi', icon: <RiseOutlined />, label: 'KPI' },
    { key: '/fin/calendar', icon: <CalendarOutlined />, label: 'Фин. календарь' },
    { key: '/fin/turnover-balance', icon: <TableOutlined />, label: 'ОСВ' },
    { key: '/fin/adjustments', icon: <EditOutlined />, label: 'Корректировки' },
    { key: '/fin/import', icon: <CloudDownloadOutlined />, label: 'FTP импорт' },
  ]

  const menuItems = [
    {
      key: 'main-group',
      label: <span className="fin-nav-group">Транзакции</span>,
      children: mainNavItems,
    },
    {
      key: 'fin-group',
      label: <span className="fin-nav-group">Кредиды</span>,
      children: finNavItems,
    },
  ]

  useEffect(() => {
    localStorage.setItem('finSidebarCollapsed', JSON.stringify(collapsed))
    if (collapsed) {
      setOpenKeys([])
    } else {
      setOpenKeys(['main-group', 'fin-group'])
    }
  }, [collapsed])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const userMenuItems = [
    {
      key: 'main-app',
      icon: <ArrowLeftOutlined />,
      label: 'Главное приложение',
      onClick: () => navigate('/'),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выйти',
      danger: true,
      onClick: handleLogout,
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={260}
        collapsedWidth={80}
        theme="dark"
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        className="fin-sider"
        style={{
          background: 'linear-gradient(180deg, #0b1f3a 0%, #051327 100%)',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
        }}
      >
        {/* Logo */}
        <div
          className="fin-sider__brand"
        >
          <Space direction="vertical" size={0}>
            <DollarOutlined style={{ fontSize: 28, color: '#1890ff' }} />
            {!collapsed && (
              <>
                <Text className="fin-sider__title">West Поток</Text>
                <Text className="fin-sider__subtitle">Финансовый модуль</Text>
              </>
            )}
          </Space>
        </div>

        {/* Navigation */}
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          openKeys={openKeys}
          onOpenChange={(keys) => setOpenKeys(keys as string[])}
          inlineCollapsed={collapsed}
          onClick={({ key }) => navigate(key)}
          style={{ flex: 1, borderRight: 0, paddingTop: 8 }}
        />

        {/* Footer */}
        {!collapsed && (
          <div
            style={{
              padding: '16px',
              textAlign: 'center',
              borderTop: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <Text style={{ color: 'rgba(255, 255, 255, 0.45)', fontSize: '11px' }}>
              West Finance Module v1.0.0
            </Text>
          </div>
        )}
      </Sider>

      {/* Main Content */}
      <Layout style={{ marginLeft: collapsed ? 80 : 260, transition: 'margin-left 0.2s' }}>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
            position: 'sticky',
            top: 0,
            zIndex: 99,
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{
              fontSize: '16px',
              width: 48,
              height: 48,
            }}
          />

          <Space size="middle">
            {/* Status indicator */}
            <Space size="small">
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  backgroundColor: token.colorSuccess,
                }}
              />
              <Text type="secondary" style={{ fontSize: 13 }}>
                Система работает
              </Text>
            </Space>

            {/* User Menu */}
            {user && (
              <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                <Space style={{ cursor: 'pointer' }}>
                  <Avatar
                    style={{ backgroundColor: token.colorPrimary }}
                    icon={<UserOutlined />}
                  >
                    {(user.full_name || user.username || 'U').charAt(0).toUpperCase()}
                  </Avatar>
                  <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
                    <Text style={{ fontSize: 14, fontWeight: 500 }}>
                      {user.full_name || user.username}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {user.role === 'admin' ? 'Администратор' : 'Пользователь'}
                    </Text>
                  </div>
                </Space>
              </Dropdown>
            )}
          </Space>
        </Header>

        {/* Filters */}
        <div style={{ padding: '16px 24px 0 24px' }}>
          <div className="fin-shell">
            <FinFilters />
          </div>
        </div>

        {/* Page Content */}
        <Content style={{ padding: '24px 24px 32px', background: '#f3f6fb', minHeight: 'calc(100vh - 180px)' }}>
          <div className="fin-shell">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}
