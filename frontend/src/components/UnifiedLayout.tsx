import { useEffect, useMemo, useState } from 'react'
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
  AppstoreOutlined,
  ClusterOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  DollarOutlined,
  BankOutlined,
  TagsOutlined,
  ApartmentOutlined,
  SlidersOutlined,
  SyncOutlined,
  SettingOutlined,
  DollarCircleOutlined,
} from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'
import FinFilters from '../modules/fin/components/FinFilters'
import '../modules/fin/styles/fin-theme.css'

const { Header, Sider, Content } = Layout
const { Text } = Typography

export default function UnifiedLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { token } = theme.useToken()

  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem('unifiedSidebarCollapsed')
    return saved ? JSON.parse(saved) : true
  })

  const [openKeys, setOpenKeys] = useState<string[]>(() => {
    const saved = localStorage.getItem('unifiedSidebarCollapsed')
    const isCollapsed = saved ? JSON.parse(saved) : true
    return isCollapsed ? [] : ['main-group', 'fin-group']
  })

  useEffect(() => {
    localStorage.setItem('unifiedSidebarCollapsed', JSON.stringify(collapsed))
    if (collapsed) {
      setOpenKeys([])
    } else {
      setOpenKeys(['main-group', 'fin-group'])
    }
  }, [collapsed])

  const mainNavItems = [
    { key: '/', icon: <DashboardOutlined />, label: 'Дашборд' },
    { key: '/bank-transactions', icon: <BankOutlined />, label: 'Банковские операции' },
    { key: '/bank-transactions-analytics', icon: <BarChartOutlined />, label: 'Аналитика' },
    { key: '/expenses', icon: <FileTextOutlined />, label: 'Заявки на расходы' },
    { key: '/regular-payments', icon: <DollarCircleOutlined />, label: 'Регулярные платежи' },
    { key: '/payment-calendar', icon: <CalendarOutlined />, label: 'Календарь оплат' },
    { key: '/categories', icon: <TagsOutlined />, label: 'Категории' },
    { key: '/organizations', icon: <ApartmentOutlined />, label: 'Организации' },
    { key: '/categorization-rules', icon: <SlidersOutlined />, label: 'Правила категоризации' },
  
    { key: '/contractors', icon: <UserOutlined />, label: 'Контрагенты' },
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

  const menuItems = useMemo(
    () => [
      {
        key: 'main-group',
        icon: <AppstoreOutlined />,
        label: <span className="fin-nav-group">West Поток</span>,
        children: mainNavItems,
      },
      {
        key: 'fin-group',
        icon: <ClusterOutlined />,
        label: <span className="fin-nav-group">Финансовый модуль</span>,
        children: finNavItems,
      },
    ],
    []
  )

  const allMenuKeys = useMemo(
    () => [...mainNavItems, ...finNavItems].map(item => item.key),
    [mainNavItems, finNavItems]
  )

  const selectedKey = useMemo(() => {
    const matched = allMenuKeys.reduce<string | undefined>((best, key) => {
      const isMatch = location.pathname === key || location.pathname.startsWith(`${key}/`)
      if (!isMatch) return best

      if (!best || key.length > best.length) {
        return key
      }

      return best
    }, undefined)

    return matched || location.pathname
  }, [allMenuKeys, location.pathname])

  const isFinRoute = location.pathname.startsWith('/fin')

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выйти',
      danger: true,
      onClick: () => {
        logout()
        navigate('/login')
      },
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
        <div className="fin-sider__brand">
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

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          openKeys={openKeys}
          onOpenChange={(keys) => setOpenKeys(keys as string[])}
          inlineCollapsed={collapsed}
          onClick={({ key }) => navigate(key)}
          style={{ flex: 1, borderRight: 0, paddingTop: 8 }}
        />

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

        {isFinRoute && (
          <div style={{ padding: '16px 24px 0 24px' }}>
            <div className="fin-shell">
              <FinFilters />
            </div>
          </div>
        )}

        <Content style={{ padding: '24px 24px 32px', background: '#f3f6fb', minHeight: 'calc(100vh - 180px)' }}>
          <div className="fin-shell">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}
