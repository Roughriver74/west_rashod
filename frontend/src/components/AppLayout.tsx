import { Layout, Menu, Select, Typography, Avatar, Dropdown, Space } from 'antd'
import {
  BankOutlined,
  DashboardOutlined,
  TagsOutlined,
  TeamOutlined,
  SyncOutlined,
  SettingOutlined,
  LogoutOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { ReactNode } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useDepartment } from '../contexts/DepartmentContext'

const { Header, Sider, Content } = Layout
const { Text } = Typography

interface AppLayoutProps {
  children: ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const { departments, selectedDepartment, setSelectedDepartment } = useDepartment()

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
      key: '/mappings',
      icon: <SettingOutlined />,
      label: 'Маппинг операций',
    },
    {
      key: '/sync-1c',
      icon: <SyncOutlined />,
      label: 'Синхронизация 1С',
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
      <Sider width={240} theme="dark">
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <Text style={{ color: 'white', fontSize: '18px', fontWeight: 'bold' }}>
            West Rashod
          </Text>
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
          <Select
            style={{ width: 250 }}
            placeholder="Выберите отдел"
            value={selectedDepartment?.id}
            onChange={(value) => {
              const dept = departments.find((d) => d.id === value)
              setSelectedDepartment(dept || null)
            }}
            options={departments.map((d) => ({
              value: d.id,
              label: d.name,
            }))}
          />
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} />
              <Text>{user?.full_name || user?.username}</Text>
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ margin: '24px', background: '#f5f5f5' }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}
