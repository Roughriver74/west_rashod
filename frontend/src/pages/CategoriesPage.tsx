import { useState, useMemo } from 'react'
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
  TreeSelect,
} from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  FolderOutlined,
  FileOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnsType } from 'antd/es/table'
import {
  getCategoryTree,
  createCategory,
  updateCategory,
  deleteCategory,
  Category,
  CategoryTreeNode,
} from '../api/categories'
import apiClient from '../api/client'

const { Title, Text } = Typography

// Конвертируем дерево для TreeSelect
const convertToTreeSelectData = (nodes: CategoryTreeNode[]): any[] => {
  return nodes.map(node => ({
    value: node.id,
    title: node.name,
    disabled: false,
    children: node.children?.length > 0 ? convertToTreeSelectData(node.children) : undefined,
  }))
}

// Фильтруем дерево по поисковому запросу
const filterTree = (nodes: CategoryTreeNode[], search: string, typeFilter?: string): CategoryTreeNode[] => {
  const result: CategoryTreeNode[] = []

  for (const node of nodes) {
    const matchesSearch = !search || node.name.toLowerCase().includes(search.toLowerCase())
    const matchesType = !typeFilter || node.type === typeFilter
    const filteredChildren = node.children?.length > 0 ? filterTree(node.children, search, typeFilter) : []

    if ((matchesSearch && matchesType) || filteredChildren.length > 0) {
      result.push({
        ...node,
        children: filteredChildren,
      })
    }
  }

  return result
}

export default function CategoriesPage() {
  const queryClient = useQueryClient()
  const [searchText, setSearchText] = useState('')
  const [typeFilter, setTypeFilter] = useState<string | undefined>()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [form] = Form.useForm()
  const [expandedRowKeys, setExpandedRowKeys] = useState<React.Key[]>([])

  // Fetch category tree
  const { data: categoryTree = [], isLoading } = useQuery({
    queryKey: ['categoryTree'],
    queryFn: () => getCategoryTree({}),
  })

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: () => apiClient.post('/sync-1c/categories/sync'),
    onSuccess: (response) => {
      const data = response.data
      if (data.success) {
        message.success(data.message)
      } else {
        message.error(data.message)
      }
      queryClient.invalidateQueries({ queryKey: ['categoryTree'] })
      queryClient.invalidateQueries({ queryKey: ['categories'] })
    },
    onError: () => {
      message.error('Ошибка синхронизации категорий')
    },
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => {
      message.success('Категория создана')
      queryClient.invalidateQueries({ queryKey: ['categoryTree'] })
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
      queryClient.invalidateQueries({ queryKey: ['categoryTree'] })
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
      queryClient.invalidateQueries({ queryKey: ['categoryTree'] })
      queryClient.invalidateQueries({ queryKey: ['categories'] })
    },
    onError: () => {
      message.error('Ошибка удаления категории')
    },
  })

  const handleSubmit = (values: any) => {
    const data = {
      ...values,
      parent_id: values.parent_id || null,
    }
    if (editingCategory) {
      updateMutation.mutate({ id: editingCategory.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleEdit = (record: Category) => {
    setEditingCategory(record)
    form.setFieldsValue({
      ...record,
      parent_id: record.parent_id || undefined,
    })
    setIsModalOpen(true)
  }

  const handleAdd = (parentId?: number) => {
    setEditingCategory(null)
    form.resetFields()
    form.setFieldsValue({
      is_active: true,
      type: 'OPEX',
      is_folder: false,
      parent_id: parentId || undefined,
    })
    setIsModalOpen(true)
  }

  // Фильтрованное дерево
  const filteredTree = useMemo(() => {
    return filterTree(categoryTree, searchText, typeFilter)
  }, [categoryTree, searchText, typeFilter])

  // TreeSelect data для выбора родителя
  const parentTreeData = useMemo(() => {
    return convertToTreeSelectData(categoryTree)
  }, [categoryTree])

  // Раскрыть всё при поиске
  const allKeys = useMemo(() => {
    const keys: number[] = []
    const extractKeys = (nodes: CategoryTreeNode[]) => {
      for (const node of nodes) {
        if (node.children?.length > 0) {
          keys.push(node.id)
          extractKeys(node.children)
        }
      }
    }
    extractKeys(categoryTree)
    return keys
  }, [categoryTree])

  // При поиске раскрываем все
  const effectiveExpandedKeys = searchText ? allKeys : expandedRowKeys

  const columns: ColumnsType<CategoryTreeNode> = [
    {
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          {record.is_folder ? (
            <FolderOutlined style={{ color: '#faad14' }} />
          ) : (
            <FileOutlined style={{ color: '#1890ff' }} />
          )}
          <span style={{ fontWeight: record.is_folder ? 600 : 400 }}>{name}</span>
          {record.code_1c && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              [{record.code_1c}]
            </Text>
          )}
        </Space>
      ),
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
      width: 250,
      ellipsis: true,
      render: (text) => text || <Text type="secondary">—</Text>,
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
      width: 150,
      render: (_, record) => (
        <Space size="small">
          {record.is_folder && (
            <Button
              type="link"
              size="small"
              icon={<PlusOutlined />}
              onClick={() => handleAdd(record.id)}
              title="Добавить подкатегорию"
            />
          )}
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="Удалить категорию?"
            description={record.children?.length > 0 ? "У категории есть подкатегории!" : undefined}
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="Да"
            cancelText="Нет"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
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
            allowClear
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
          <Button type="primary" icon={<PlusOutlined />} onClick={() => handleAdd()}>
            Добавить
          </Button>
          <Button
            icon={<SyncOutlined spin={syncMutation.isPending} />}
            onClick={() => syncMutation.mutate()}
            loading={syncMutation.isPending}
          >
            Синхронизировать из 1С
          </Button>
        </Space>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={filteredTree}
          loading={isLoading}
          expandable={{
            expandedRowKeys: effectiveExpandedKeys as number[],
            onExpandedRowsChange: (keys) => setExpandedRowKeys(keys as React.Key[]),
            indentSize: 24,
          }}
          pagination={false}
          size="middle"
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
        width={500}
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
            name="parent_id"
            label="Родительская категория"
          >
            <TreeSelect
              placeholder="Выберите родителя (опционально)"
              allowClear
              treeDefaultExpandAll
              treeData={parentTreeData}
              showSearch
              treeNodeFilterProp="title"
            />
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

          <Space style={{ width: '100%' }} size="large">
            <Form.Item name="is_folder" label="Это папка (группа)" valuePropName="checked">
              <Switch />
            </Form.Item>

            <Form.Item name="is_active" label="Активна" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>

          <Form.Item style={{ marginBottom: 0, marginTop: 16 }}>
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
