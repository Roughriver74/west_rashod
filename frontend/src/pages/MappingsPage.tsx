import { useState } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Input,
  Select,
  message,
  Typography,
  Modal,
  Form,
  Switch,
  Popconfirm,
  InputNumber,
  Progress,
  Row,
  Col,
  Statistic,
} from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnsType } from 'antd/es/table'
import apiClient from '../api/client'
import { getCategories, Category } from '../api/categories'
import { useDepartment } from '../contexts/DepartmentContext'

const { Title } = Typography

interface BusinessOperationMapping {
  id: number
  operation_name: string
  category_id: number
  category_name?: string
  priority: number
  confidence: number
  is_active: boolean
  department_id: number
}

const getMappings = async (params?: { department_id?: number }) => {
  const response = await apiClient.get('/business-operation-mappings', { params })
  return response.data as BusinessOperationMapping[]
}

const createMapping = async (data: Partial<BusinessOperationMapping>) => {
  const response = await apiClient.post('/business-operation-mappings', data)
  return response.data
}

const updateMapping = async (id: number, data: Partial<BusinessOperationMapping>) => {
  const response = await apiClient.put(`/business-operation-mappings/${id}`, data)
  return response.data
}

const deleteMapping = async (id: number) => {
  await apiClient.delete(`/business-operation-mappings/${id}`)
}

const bulkActivate = async (ids: number[]) => {
  await apiClient.post('/business-operation-mappings/bulk-activate', { ids })
}

const bulkDeactivate = async (ids: number[]) => {
  await apiClient.post('/business-operation-mappings/bulk-deactivate', { ids })
}

export default function MappingsPage() {
  const { selectedDepartment } = useDepartment()
  const queryClient = useQueryClient()
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<boolean | undefined>()
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingMapping, setEditingMapping] = useState<BusinessOperationMapping | null>(null)
  const [form] = Form.useForm()

  // Fetch mappings
  const { data: mappings = [], isLoading } = useQuery({
    queryKey: ['business-operation-mappings', selectedDepartment?.id],
    queryFn: () => getMappings({ department_id: selectedDepartment?.id }),
    enabled: !!selectedDepartment,
  })

  // Fetch categories for dropdown
  const { data: categories = [] } = useQuery({
    queryKey: ['categories', selectedDepartment?.id],
    queryFn: () => getCategories({ department_id: selectedDepartment?.id, is_active: true }),
    enabled: !!selectedDepartment,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: createMapping,
    onSuccess: () => {
      message.success('Маппинг создан')
      queryClient.invalidateQueries({ queryKey: ['business-operation-mappings'] })
      setIsModalOpen(false)
      form.resetFields()
    },
    onError: () => {
      message.error('Ошибка создания маппинга')
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<BusinessOperationMapping> }) =>
      updateMapping(id, data),
    onSuccess: () => {
      message.success('Маппинг обновлен')
      queryClient.invalidateQueries({ queryKey: ['business-operation-mappings'] })
      setIsModalOpen(false)
      setEditingMapping(null)
      form.resetFields()
    },
    onError: () => {
      message.error('Ошибка обновления маппинга')
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteMapping,
    onSuccess: () => {
      message.success('Маппинг удален')
      queryClient.invalidateQueries({ queryKey: ['business-operation-mappings'] })
    },
    onError: () => {
      message.error('Ошибка удаления маппинга')
    },
  })

  // Bulk activate mutation
  const bulkActivateMutation = useMutation({
    mutationFn: bulkActivate,
    onSuccess: () => {
      message.success('Маппинги активированы')
      queryClient.invalidateQueries({ queryKey: ['business-operation-mappings'] })
      setSelectedRowKeys([])
    },
  })

  // Bulk deactivate mutation
  const bulkDeactivateMutation = useMutation({
    mutationFn: bulkDeactivate,
    onSuccess: () => {
      message.success('Маппинги деактивированы')
      queryClient.invalidateQueries({ queryKey: ['business-operation-mappings'] })
      setSelectedRowKeys([])
    },
  })

  const handleSubmit = (values: any) => {
    const data = {
      ...values,
      department_id: selectedDepartment?.id,
    }

    if (editingMapping) {
      updateMutation.mutate({ id: editingMapping.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleEdit = (record: BusinessOperationMapping) => {
    setEditingMapping(record)
    form.setFieldsValue(record)
    setIsModalOpen(true)
  }

  const handleAdd = () => {
    setEditingMapping(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true, priority: 50, confidence: 0.9 })
    setIsModalOpen(true)
  }

  const filteredMappings = mappings.filter((m) => {
    const matchesSearch =
      !searchText ||
      m.operation_name.toLowerCase().includes(searchText.toLowerCase()) ||
      m.category_name?.toLowerCase().includes(searchText.toLowerCase())
    const matchesStatus = statusFilter === undefined || m.is_active === statusFilter
    return matchesSearch && matchesStatus
  })

  // Statistics
  const activeCount = mappings.filter((m) => m.is_active).length
  const inactiveCount = mappings.filter((m) => !m.is_active).length

  const columns: ColumnsType<BusinessOperationMapping> = [
    {
      title: 'Хозяйственная операция',
      dataIndex: 'operation_name',
      key: 'operation_name',
      sorter: (a, b) => a.operation_name.localeCompare(b.operation_name),
    },
    {
      title: 'Категория',
      dataIndex: 'category_name',
      key: 'category_name',
      render: (name) => name || '-',
    },
    {
      title: 'Приоритет',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      sorter: (a, b) => a.priority - b.priority,
    },
    {
      title: 'Уверенность',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 150,
      render: (conf) => (
        <Progress
          percent={Math.round(conf * 100)}
          size="small"
          status={conf >= 0.9 ? 'success' : conf >= 0.7 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? 'Активен' : 'Неактивен'}
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
            title="Удалить маппинг?"
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

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys as number[]),
  }

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        Маппинг операций
      </Title>

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic title="Всего маппингов" value={mappings.length} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Активных"
              value={activeCount}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Неактивных"
              value={inactiveCount}
              valueStyle={{ color: '#8c8c8c' }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input
            placeholder="Поиск..."
            prefix={<SearchOutlined />}
            style={{ width: 250 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <Select
            placeholder="Статус"
            style={{ width: 140 }}
            allowClear
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { value: true, label: 'Активные' },
              { value: false, label: 'Неактивные' },
            ]}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            Добавить
          </Button>
          {selectedRowKeys.length > 0 && (
            <>
              <Button
                onClick={() => bulkActivateMutation.mutate(selectedRowKeys)}
                loading={bulkActivateMutation.isPending}
              >
                Активировать ({selectedRowKeys.length})
              </Button>
              <Button
                onClick={() => bulkDeactivateMutation.mutate(selectedRowKeys)}
                loading={bulkDeactivateMutation.isPending}
              >
                Деактивировать ({selectedRowKeys.length})
              </Button>
            </>
          )}
        </Space>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={filteredMappings}
          loading={isLoading}
          rowSelection={rowSelection}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Всего: ${total}`,
          }}
        />
      </Card>

      <Modal
        title={editingMapping ? 'Редактировать маппинг' : 'Новый маппинг'}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false)
          setEditingMapping(null)
          form.resetFields()
        }}
        footer={null}
        width={500}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="operation_name"
            label="Хозяйственная операция"
            rules={[{ required: true, message: 'Введите название операции' }]}
          >
            <Input placeholder="ОплатаПоставщику" />
          </Form.Item>

          <Form.Item
            name="category_id"
            label="Категория"
            rules={[{ required: true, message: 'Выберите категорию' }]}
          >
            <Select
              showSearch
              placeholder="Выберите категорию"
              optionFilterProp="children"
              options={categories.map((cat: Category) => ({
                value: cat.id,
                label: `${cat.name} (${cat.type})`,
              }))}
            />
          </Form.Item>

          <Space style={{ width: '100%' }}>
            <Form.Item
              name="priority"
              label="Приоритет (0-100)"
              style={{ width: '50%' }}
              rules={[{ required: true, message: 'Введите приоритет' }]}
            >
              <InputNumber min={0} max={100} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item
              name="confidence"
              label="Уверенность (0-1)"
              style={{ width: '50%' }}
              rules={[{ required: true, message: 'Введите уверенность' }]}
            >
              <InputNumber
                min={0}
                max={1}
                step={0.05}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Space>

          <Form.Item name="is_active" label="Активен" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={createMutation.isPending || updateMutation.isPending}
              >
                {editingMapping ? 'Сохранить' : 'Создать'}
              </Button>
              <Button
                onClick={() => {
                  setIsModalOpen(false)
                  setEditingMapping(null)
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
