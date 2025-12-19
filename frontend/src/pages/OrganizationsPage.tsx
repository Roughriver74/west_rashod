import { useState } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Input,
  message,
  Typography,
  Modal,
  Form,
  Switch,
  Popconfirm,
  Tooltip,
} from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnsType } from 'antd/es/table'
import apiClient from '../api/client'

const { Title } = Typography

interface Organization {
  id: number
  short_name: string
  full_name: string | null
  inn: string | null
  kpp: string | null
  legal_address: string | null
  is_active: boolean
  external_id_1c: string | null
  synced_at: string | null
  department_id: number
}

const getOrganizations = async (params?: { department_id?: number }) => {
  const response = await apiClient.get('/organizations', { params })
  return response.data as Organization[]
}

const createOrganization = async (data: Partial<Organization>) => {
  const response = await apiClient.post('/organizations', data)
  return response.data
}

const updateOrganization = async (id: number, data: Partial<Organization>) => {
  const response = await apiClient.put(`/organizations/${id}`, data)
  return response.data
}

const deleteOrganization = async (id: number) => {
  await apiClient.delete(`/organizations/${id}`)
}

export default function OrganizationsPage() {
  const queryClient = useQueryClient()
  const [searchText, setSearchText] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingOrg, setEditingOrg] = useState<Organization | null>(null)
  const [form] = Form.useForm()

  // Fetch organizations
  const { data: organizations = [], isLoading } = useQuery({
    queryKey: ['organizations'],
    queryFn: () => getOrganizations({ department_id: undefined }),
    
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: createOrganization,
    onSuccess: () => {
      message.success('Организация создана')
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
      setIsModalOpen(false)
      form.resetFields()
    },
    onError: () => {
      message.error('Ошибка создания организации')
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Organization> }) =>
      updateOrganization(id, data),
    onSuccess: () => {
      message.success('Организация обновлена')
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
      setIsModalOpen(false)
      setEditingOrg(null)
      form.resetFields()
    },
    onError: () => {
      message.error('Ошибка обновления организации')
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteOrganization,
    onSuccess: () => {
      message.success('Организация удалена')
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
    },
    onError: () => {
      message.error('Ошибка удаления организации')
    },
  })

  const handleSubmit = (values: any) => {
    const data = {
      ...values,
      
    }

    if (editingOrg) {
      updateMutation.mutate({ id: editingOrg.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleEdit = (record: Organization) => {
    setEditingOrg(record)
    form.setFieldsValue(record)
    setIsModalOpen(true)
  }

  const handleAdd = () => {
    setEditingOrg(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true })
    setIsModalOpen(true)
  }

  const filteredOrganizations = organizations.filter((org) => {
    if (!searchText) return true
    const search = searchText.toLowerCase()
    return (
      org.short_name.toLowerCase().includes(search) ||
      org.full_name?.toLowerCase().includes(search) ||
      org.inn?.includes(search)
    )
  })

  const columns: ColumnsType<Organization> = [
    {
      title: 'Краткое название',
      dataIndex: 'short_name',
      key: 'short_name',
      sorter: (a, b) => a.short_name.localeCompare(b.short_name),
    },
    {
      title: 'ИНН',
      dataIndex: 'inn',
      key: 'inn',
      width: 130,
      render: (inn) => inn || '-',
    },
    {
      title: 'КПП',
      dataIndex: 'kpp',
      key: 'kpp',
      width: 110,
      render: (kpp) => kpp || '-',
    },
    {
      title: 'Полное название',
      dataIndex: 'full_name',
      key: 'full_name',
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <span>{text || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: '1С',
      dataIndex: 'external_id_1c',
      key: 'external_id_1c',
      width: 60,
      render: (id) =>
        id ? (
          <Tooltip title={`Синхронизировано: ${id.substring(0, 8)}...`}>
            <SyncOutlined style={{ color: '#52c41a' }} />
          </Tooltip>
        ) : (
          <Tag color="warning">Нет</Tag>
        ),
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? 'Активна' : 'Неактивна'}
        </Tag>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="Удалить организацию?"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="Да"
            cancelText="Нет"
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        Организации
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input
            placeholder="Поиск по названию или ИНН..."
            prefix={<SearchOutlined />}
            style={{ width: 300 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            Добавить
          </Button>
        </Space>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={filteredOrganizations}
          loading={isLoading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Всего: ${total}`,
          }}
        />
      </Card>

      <Modal
        title={editingOrg ? 'Редактировать организацию' : 'Новая организация'}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false)
          setEditingOrg(null)
          form.resetFields()
        }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="short_name"
            label="Краткое название"
            rules={[{ required: true, message: 'Введите краткое название' }]}
          >
            <Input placeholder="ООО Компания" />
          </Form.Item>

          <Form.Item name="full_name" label="Полное название">
            <Input placeholder="Общество с ограниченной ответственностью «Компания»" />
          </Form.Item>

          <Space style={{ width: '100%' }}>
            <Form.Item
              name="inn"
              label="ИНН"
              style={{ width: '50%' }}
              rules={[
                {
                  pattern: /^\d{10}$|^\d{12}$/,
                  message: 'ИНН должен содержать 10 или 12 цифр',
                },
              ]}
            >
              <Input placeholder="1234567890" maxLength={12} />
            </Form.Item>

            <Form.Item
              name="kpp"
              label="КПП"
              style={{ width: '50%' }}
              rules={[
                {
                  pattern: /^\d{9}$/,
                  message: 'КПП должен содержать 9 цифр',
                },
              ]}
            >
              <Input placeholder="123456789" maxLength={9} />
            </Form.Item>
          </Space>

          <Form.Item name="legal_address" label="Юридический адрес">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item name="is_active" label="Активна" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={createMutation.isPending || updateMutation.isPending}
              >
                {editingOrg ? 'Сохранить' : 'Создать'}
              </Button>
              <Button
                onClick={() => {
                  setIsModalOpen(false)
                  setEditingOrg(null)
                  form.resetFields()
                }}
              >
                Отмена
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
