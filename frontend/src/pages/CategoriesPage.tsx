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
} from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnsType } from 'antd/es/table'
import {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  Category,
} from '../api/categories'

const { Title } = Typography

export default function CategoriesPage() {
  const queryClient = useQueryClient()
  const [searchText, setSearchText] = useState('')
  const [typeFilter, setTypeFilter] = useState<string | undefined>()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [form] = Form.useForm()

  // Fetch categories
  const { data: categories = [], isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: () => getCategories({}),
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => {
      message.success('Категория создана')
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      setIsModalOpen(false)
      form.resetFields()
    },
    onError: () => {
      message.error('Ошибка создания категории')
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Category> }) =>
      updateCategory(id, data),
    onSuccess: () => {
      message.success('Категория обновлена')
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      setIsModalOpen(false)
      setEditingCategory(null)
      form.resetFields()
    },
    onError: () => {
      message.error('Ошибка обновления категории')
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => {
      message.success('Категория удалена')
      queryClient.invalidateQueries({ queryKey: ['categories'] })
    },
    onError: () => {
      message.error('Ошибка удаления категории')
    },
  })

  const handleSubmit = (values: unknown) => {
    if (editingCategory) {
      updateMutation.mutate({ id: editingCategory.id, data: values as Partial<Category> })
    } else {
      createMutation.mutate(values as Category)
    }
  }

  const handleEdit = (record: Category) => {
    setEditingCategory(record)
    form.setFieldsValue(record)
    setIsModalOpen(true)
  }

  const handleAdd = () => {
    setEditingCategory(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true, type: 'OPEX' })
    setIsModalOpen(true)
  }

  const filteredCategories = categories.filter((cat) => {
    const matchesSearch =
      !searchText ||
      cat.name.toLowerCase().includes(searchText.toLowerCase()) ||
      cat.description?.toLowerCase().includes(searchText.toLowerCase())
    const matchesType = !typeFilter || cat.type === typeFilter
    return matchesSearch && matchesType
  })

  const columns: ColumnsType<Category> = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'Тип',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type) => (
        <Tag color={type === 'OPEX' ? 'blue' : 'green'}>{type}</Tag>
      ),
    },
    {
      title: 'Описание',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text) => text || '-',
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
            title="Удалить категорию?"
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
        Категории расходов
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input
            placeholder="Поиск..."
            prefix={<SearchOutlined />}
            style={{ width: 250 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <Select
            placeholder="Тип"
            style={{ width: 120 }}
            allowClear
            value={typeFilter}
            onChange={setTypeFilter}
            options={[
              { value: 'OPEX', label: 'OPEX' },
              { value: 'CAPEX', label: 'CAPEX' },
            ]}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            Добавить
          </Button>
        </Space>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={filteredCategories}
          loading={isLoading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Всего: ${total}`,
          }}
        />
      </Card>

      <Modal
        title={editingCategory ? 'Редактировать категорию' : 'Новая категория'}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false)
          setEditingCategory(null)
          form.resetFields()
        }}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label="Название"
            rules={[{ required: true, message: 'Введите название' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="type"
            label="Тип"
            rules={[{ required: true, message: 'Выберите тип' }]}
          >
            <Select
              options={[
                { value: 'OPEX', label: 'OPEX (Операционные расходы)' },
                { value: 'CAPEX', label: 'CAPEX (Капитальные расходы)' },
              ]}
            />
          </Form.Item>

          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={3} />
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
                {editingCategory ? 'Сохранить' : 'Создать'}
              </Button>
              <Button
                onClick={() => {
                  setIsModalOpen(false)
                  setEditingCategory(null)
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
