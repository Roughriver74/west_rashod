import { useState, useMemo } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Input,
  Select,
  DatePicker,
  Row,
  Col,
  Statistic,
  Modal,
  Form,
  InputNumber,
  message,
  Drawer,
  Descriptions,
  Popconfirm,
  Progress,
  Tooltip,
} from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SendOutlined,
  DeleteOutlined,
  EyeOutlined,
  EditOutlined,
  LinkOutlined,
  ReloadOutlined,
  DollarOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import type { ColumnsType } from 'antd/es/table'
import {
  getExpenses,
  getExpenseStats,
  createExpense,
  updateExpense,
  deleteExpense,
  submitExpenseForApproval,
  approveExpense,
  exportExpenses,
  bulkDeleteExpenses,
  Expense,
  ExpenseFilters,
  ExpenseCreate,
  ExpenseStatus,
  ExpensePriority,
  ExpenseList,
} from '../api/expenses'
import { getCategories } from '../api/categories'
import { getOrganizations } from '../api/organizations'
import { syncExpenses } from '../api/sync1c'
import { getTaskStatus, TaskInfo } from '../api/tasks'

const { Title, Text } = Typography
const { RangePicker } = DatePicker
const { TextArea } = Input

const statusColors: Record<ExpenseStatus, string> = {
  DRAFT: 'default',
  PENDING: 'processing',
  APPROVED: 'success',
  REJECTED: 'error',
  PAID: 'cyan',
  PARTIALLY_PAID: 'orange',
  CANCELLED: 'default',
}

const statusLabels: Record<ExpenseStatus, string> = {
  DRAFT: 'Черновик',
  PENDING: 'На согласовании',
  APPROVED: 'Согласовано',
  REJECTED: 'Отклонено',
  PAID: 'Оплачено',
  PARTIALLY_PAID: 'Частично оплачено',
  CANCELLED: 'Отменено',
}

const priorityColors: Record<ExpensePriority, string> = {
  LOW: 'default',
  NORMAL: 'blue',
  HIGH: 'orange',
  URGENT: 'red',
}

const priorityLabels: Record<ExpensePriority, string> = {
  LOW: 'Низкий',
  NORMAL: 'Обычный',
  HIGH: 'Высокий',
  URGENT: 'Срочный',
}

const formatAmount = (value: number) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

export default function ExpensesPage() {
  const queryClient = useQueryClient()
  const [form] = Form.useForm()

  // State
  const [filters, setFilters] = useState<ExpenseFilters>({ skip: 0, limit: 50 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null)
  const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [rejectModalOpen, setRejectModalOpen] = useState(false)
  const [rejectingExpenseId, setRejectingExpenseId] = useState<number | null>(null)
  const [rejectionReason, setRejectionReason] = useState('')
  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false)
  const [syncTaskId, setSyncTaskId] = useState<string | null>(null)
  const [syncProgress, setSyncProgress] = useState<TaskInfo | null>(null)

  // Queries
  const { data: expenseList, isLoading } = useQuery({
    queryKey: ['expenses', filters],
    queryFn: () => getExpenses(filters),
  })

  const expenses = expenseList?.items || []
  const totalExpenses = expenseList?.total || 0
  const currentPage = expenseList?.page || 1
  const pageSize = expenseList?.page_size || 50

  const { data: stats } = useQuery({
    queryKey: ['expense-stats'],
    queryFn: () => getExpenseStats(),
  })

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => getCategories({ is_active: true }),
  })

  const { data: organizations = [] } = useQuery({
    queryKey: ['organizations'],
    queryFn: () => getOrganizations({ is_active: true }),
  })

  // Получить уникальные подразделения из всех загруженных заявок
  const uniqueSubdivisions = useMemo(() => {
    const subdivisions = new Set<string>()
    expenses.forEach(exp => {
      if (exp.subdivision) {
        subdivisions.add(exp.subdivision)
      }
    })
    return Array.from(subdivisions).sort()
  }, [expenses])

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: ExpenseCreate) => createExpense(data),
    onSuccess: () => {
      message.success('Заявка создана')
      setIsModalOpen(false)
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      queryClient.invalidateQueries({ queryKey: ['expense-stats'] })
    },
    onError: () => message.error('Ошибка при создании заявки'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ExpenseCreate> }) => updateExpense(id, data),
    onSuccess: () => {
      message.success('Заявка обновлена')
      setIsModalOpen(false)
      setEditingExpense(null)
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      queryClient.invalidateQueries({ queryKey: ['expense-stats'] })
    },
    onError: () => message.error('Ошибка при обновлении заявки'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteExpense(id),
    onSuccess: () => {
      message.success('Заявка удалена')
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      queryClient.invalidateQueries({ queryKey: ['expense-stats'] })
    },
    onError: () => message.error('Ошибка при удалении заявки'),
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: (filters: ExpenseFilters) => bulkDeleteExpenses(filters),
    onSuccess: (data) => {
      message.success(`Удалено заявок: ${data.count}`)
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      queryClient.invalidateQueries({ queryKey: ['expense-stats'] })
    },
    onError: () => message.error('Ошибка при массовом удалении'),
  })

  const submitMutation = useMutation({
    mutationFn: (id: number) => submitExpenseForApproval(id),
    onSuccess: () => {
      message.success('Заявка отправлена на согласование')
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      queryClient.invalidateQueries({ queryKey: ['expense-stats'] })
    },
    onError: () => message.error('Ошибка при отправке заявки'),
  })

  const approveMutation = useMutation({
    mutationFn: ({ id, action, reason }: { id: number; action: 'approve' | 'reject'; reason?: string }) =>
      approveExpense(id, action, reason),
    onSuccess: (_, variables) => {
      message.success(variables.action === 'approve' ? 'Заявка согласована' : 'Заявка отклонена')
      setRejectModalOpen(false)
      setRejectingExpenseId(null)
      setRejectionReason('')
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      queryClient.invalidateQueries({ queryKey: ['expense-stats'] })
    },
    onError: () => message.error('Ошибка при обработке заявки'),
  })

  const handleCreate = () => {
    setEditingExpense(null)
    form.resetFields()
    form.setFieldsValue({
      request_date: dayjs(),
      priority: 'NORMAL',
      currency: 'RUB',
    })
    setIsModalOpen(true)
  }

  const handleEdit = (expense: Expense) => {
    setEditingExpense(expense)
    form.setFieldsValue({
      ...expense,
      request_date: dayjs(expense.request_date),
      due_date: expense.due_date ? dayjs(expense.due_date) : null,
      invoice_date: expense.invoice_date ? dayjs(expense.invoice_date) : null,
    })
    setIsModalOpen(true)
  }

  const handleSubmit = (values: ExpenseCreate & { request_date: dayjs.Dayjs; due_date?: dayjs.Dayjs; invoice_date?: dayjs.Dayjs }) => {
    const data = {
      ...values,
      request_date: values.request_date.format('YYYY-MM-DD'),
      due_date: values.due_date?.format('YYYY-MM-DD'),
      invoice_date: values.invoice_date?.format('YYYY-MM-DD'),
    }

    if (editingExpense) {
      updateMutation.mutate({ id: editingExpense.id, data })
    } else {
      createMutation.mutate(data as ExpenseCreate)
    }
  }

  const handleReject = () => {
    if (rejectingExpenseId) {
      approveMutation.mutate({
        id: rejectingExpenseId,
        action: 'reject',
        reason: rejectionReason,
      })
    }
  }

  const handleSync = async (dateFrom: string, dateTo: string) => {
    try {
      const result = await syncExpenses({ date_from: dateFrom, date_to: dateTo })
      setSyncTaskId(result.task_id)
      message.success('Синхронизация запущена')

      // Poll task status
      const pollInterval = setInterval(async () => {
        try {
          const task = await getTaskStatus(result.task_id)
          setSyncProgress(task)

          if (task.status === 'completed') {
            clearInterval(pollInterval)
            message.success('Синхронизация завершена')
            queryClient.invalidateQueries({ queryKey: ['expenses'] })
            queryClient.invalidateQueries({ queryKey: ['expense-stats'] })
            setTimeout(() => {
              setIsSyncModalOpen(false)
              setSyncTaskId(null)
              setSyncProgress(null)
            }, 2000)
          } else if (task.status === 'failed') {
            clearInterval(pollInterval)
            message.error('Ошибка синхронизации')
          }
        } catch (err) {
          clearInterval(pollInterval)
          message.error('Ошибка получения статуса задачи')
        }
      }, 1000)
    } catch (error) {
      message.error('Ошибка запуска синхронизации')
    }
  }

  const handleExport = async () => {
    try {
      const blob = await exportExpenses(filters)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `expenses_${dayjs().format('YYYY-MM-DD')}.xlsx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      message.success('Экспорт выполнен')
    } catch (error) {
      message.error('Ошибка экспорта')
    }
  }

  const handleBulkDelete = () => {
    const filterDesc = []
    if (filters.status) filterDesc.push(`статус: ${statusLabels[filters.status as ExpenseStatus]}`)
    if (filters.date_from && filters.date_to) filterDesc.push(`период: ${filters.date_from} - ${filters.date_to}`)
    if (filters.search) filterDesc.push(`поиск: "${filters.search}"`)
    if (filters.category_id) filterDesc.push('категория выбрана')
    if (filters.organization_id) filterDesc.push('организация выбрана')
    if (filters.contractor_id) filterDesc.push('контрагент выбран')
    if (filters.subdivision) filterDesc.push(`подразделение: ${filters.subdivision}`)

    const description = filterDesc.length > 0
      ? `Фильтры: ${filterDesc.join(', ')}`
      : 'Все заявки (без фильтров)'

    Modal.confirm({
      title: 'Массовое удаление заявок',
      icon: <DeleteOutlined style={{ color: '#ff4d4f' }} />,
      content: (
        <div>
          <p><strong>ВНИМАНИЕ!</strong> Эта операция необратима!</p>
          <p>{description}</p>
          <p>Вы уверены, что хотите удалить все заявки, соответствующие выбранным фильтрам?</p>
        </div>
      ),
      okText: 'Да, удалить',
      okType: 'danger',
      cancelText: 'Отмена',
      onOk: () => {
        // Отправить только поддерживаемые backend параметры
        const deleteFilters: Partial<ExpenseFilters> = {}
        if (filters.status) deleteFilters.status = filters.status
        if (filters.date_from) deleteFilters.date_from = filters.date_from
        if (filters.date_to) deleteFilters.date_to = filters.date_to
        if (filters.category_id) deleteFilters.category_id = filters.category_id
        if (filters.organization_id) deleteFilters.organization_id = filters.organization_id
        if (filters.contractor_id) deleteFilters.contractor_id = filters.contractor_id
        if (filters.subdivision) deleteFilters.subdivision = filters.subdivision
        if (filters.search) deleteFilters.search = filters.search

        bulkDeleteMutation.mutate(deleteFilters)
      },
    })
  }

  const handlePageChange = (page: number, pageSize?: number) => {
    const newSkip = (page - 1) * (pageSize || filters.limit || 50)
    setFilters({ ...filters, skip: newSkip, limit: pageSize || filters.limit })
  }

  const columns: ColumnsType<Expense> = [
    {
      title: 'Номер',
      dataIndex: 'number',
      key: 'number',
      width: 120,
      fixed: 'left',
      render: (value, record) => (
        <Button type="link" onClick={() => { setSelectedExpense(record); setIsDrawerOpen(true) }}>
          {value}
        </Button>
      ),
    },
    {
      title: 'Дата',
      dataIndex: 'request_date',
      key: 'request_date',
      width: 100,
      render: (date) => dayjs(date).format('DD.MM.YYYY'),
      sorter: (a, b) => dayjs(a.request_date).unix() - dayjs(b.request_date).unix(),
    },
    {
      title: 'Название / Описание',
      key: 'title_description',
      width: 280,
      ellipsis: true,
      render: (_, record) => (
        <Space direction="vertical" size={2} style={{ width: '100%' }}>
          <Text strong ellipsis style={{ maxWidth: 260 }}>{record.title}</Text>
          {record.description && (
            <Text type="secondary" ellipsis style={{ fontSize: 12, maxWidth: 260 }}>
              {record.description}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Контрагент',
      dataIndex: 'contractor_name',
      key: 'contractor',
      width: 180,
      ellipsis: true,
      render: (value) => value ? (
        <Tooltip title={value}>
          <Text ellipsis strong style={{ fontSize: 13 }}>{value}</Text>
        </Tooltip>
      ) : <Text type="secondary">-</Text>,
    },
    {
      title: 'Сумма',
      key: 'amount',
      width: 140,
      align: 'right',
      render: (_, record) => (
        <Space direction="vertical" size={0} style={{ textAlign: 'right' }}>
          <Text strong>{formatAmount(record.amount)}</Text>
          {record.amount_paid > 0 && (
            <Text type="success" style={{ fontSize: 12 }}>
              Оплачено: {formatAmount(record.amount_paid)}
            </Text>
          )}
        </Space>
      ),
      sorter: (a, b) => a.amount - b.amount,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status: ExpenseStatus) => (
        <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>
      ),
      filters: Object.entries(statusLabels).map(([value, text]) => ({ text, value })),
      onFilter: (value, record) => record.status === value,
    },
    {
      title: 'Приоритет',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: ExpensePriority) => (
        <Tag color={priorityColors[priority]}>{priorityLabels[priority]}</Tag>
      ),
    },
    {
      title: 'Категория',
      dataIndex: 'category_name',
      key: 'category_name',
      width: 160,
      ellipsis: true,
      render: (value) => value ? <Tag color="blue">{value}</Tag> : <Text type="secondary">-</Text>,
    },
    {
      title: 'Подразделение',
      dataIndex: 'subdivision',
      key: 'subdivision',
      width: 140,
      ellipsis: true,
      render: (value, record) => value ? (
        <Tooltip title={`${value}${record.subdivision_code ? ` (${record.subdivision_code})` : ''}`}>
          <Text ellipsis style={{ fontSize: 12 }}>{value}</Text>
        </Tooltip>
      ) : <Text type="secondary">-</Text>,
    },
    {
      title: 'Заметки',
      dataIndex: 'notes',
      key: 'notes',
      width: 80,
      align: 'center',
      render: (value) => (
        value ? (
          <Tooltip title={value}>
            <Tag color="orange" icon={<FileTextOutlined />} />
          </Tooltip>
        ) : '-'
      ),
    },
    {
      title: 'Связи',
      key: 'linked',
      width: 80,
      align: 'center',
      render: (_, record) => (
        record.linked_transactions_count > 0 ? (
          <Tooltip title={`Привязано: ${formatAmount(record.linked_transactions_amount)}`}>
            <Tag color="green" icon={<LinkOutlined />}>
              {record.linked_transactions_count}
            </Tag>
          </Tooltip>
        ) : <Text type="secondary">-</Text>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 130,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Просмотр">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => { setSelectedExpense(record); setIsDrawerOpen(true) }}
            />
          </Tooltip>

          {record.status === 'DRAFT' && (
            <Tooltip title="Редактировать">
              <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
            </Tooltip>
          )}

          {['DRAFT', 'REJECTED', 'CANCELLED'].includes(record.status) && (
            <Popconfirm title="Удалить заявку?" onConfirm={() => deleteMutation.mutate(record.id)}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 0 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={2} style={{ margin: 0 }}>
            <FileTextOutlined /> Заявки на расходы
          </Title>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => queryClient.invalidateQueries({ queryKey: ['expenses'] })}
            >
              Обновить
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => setIsSyncModalOpen(true)}
            >
              Синхронизация из 1С
            </Button>
            <Button
              icon={<FileTextOutlined />}
              onClick={handleExport}
            >
              Экспорт в Excel
            </Button>
            <Popconfirm
              title="Удалить все заявки по текущему фильтру?"
              description="Это действие необратимо!"
              onConfirm={handleBulkDelete}
              okText="Удалить"
              cancelText="Отмена"
              okButtonProps={{ danger: true }}
            >
              <Button
                danger
                icon={<DeleteOutlined />}
                loading={bulkDeleteMutation.isPending}
              >
                Удалить по фильтру
              </Button>
            </Popconfirm>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Новая заявка
            </Button>
          </Space>
        </div>

        {/* Stats */}
        {stats && (
          <Row gutter={16}>
            <Col xs={12} sm={8} md={4}>
              <Card size="small">
                <Statistic title="Всего" value={stats.total} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Card size="small">
                <Statistic title="На согласовании" value={stats.pending} valueStyle={{ color: '#1890ff' }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Card size="small">
                <Statistic title="Согласовано" value={stats.approved} valueStyle={{ color: '#52c41a' }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Card size="small">
                <Statistic title="Оплачено" value={stats.paid} valueStyle={{ color: '#13c2c2' }} />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Card size="small">
                <Statistic
                  title="К оплате"
                  value={stats.total_pending}
                  prefix={<DollarOutlined />}
                  formatter={(value) => formatAmount(Number(value))}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={4}>
              <Card size="small">
                <Statistic
                  title="Оплачено всего"
                  value={stats.total_paid}
                  valueStyle={{ color: '#52c41a' }}
                  formatter={(value) => formatAmount(Number(value))}
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* Filters */}
        <Card size="small">
          <Space wrap>
            <Input
              placeholder="Поиск..."
              prefix={<SearchOutlined />}
              style={{ width: 200 }}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              allowClear
            />
            <Select
              placeholder="Статус"
              style={{ width: 150 }}
              allowClear
              onChange={(value) => setFilters({ ...filters, status: value })}
              options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))}
            />
            <Select
              placeholder="Категория"
              style={{ width: 180 }}
              allowClear
              showSearch
              optionFilterProp="label"
              onChange={(value) => setFilters({ ...filters, category_id: value })}
              options={categories.map((c) => ({ value: c.id, label: c.name }))}
            />
            <Select
              placeholder="Подразделение"
              style={{ width: 200 }}
              allowClear
              showSearch
              optionFilterProp="label"
              onChange={(value) => setFilters({ ...filters, subdivision: value })}
              value={filters.subdivision}
              options={uniqueSubdivisions.map((s) => ({ value: s, label: s }))}
            />
            <RangePicker
              placeholder={['С', 'По']}
              format="DD.MM.YYYY"
              onChange={(dates) => {
                if (dates) {
                  setFilters({
                    ...filters,
                    date_from: dates[0]?.format('YYYY-MM-DD'),
                    date_to: dates[1]?.format('YYYY-MM-DD'),
                  })
                } else {
                  setFilters({ ...filters, date_from: undefined, date_to: undefined })
                }
              }}
            />
          </Space>
        </Card>

        {/* Table */}
        <Card>
          <Table
            columns={columns}
            dataSource={expenses}
            rowKey="id"
            loading={isLoading}
            pagination={{
              current: currentPage,
              pageSize: pageSize,
              total: totalExpenses,
              showSizeChanger: true,
              showTotal: (total) => `Всего ${total} заявок`,
              onChange: handlePageChange,
              pageSizeOptions: ['10', '25', '50', '100'],
            }}
            scroll={{ x: 1500 }}
            size="small"
          />
        </Card>
      </Space>

      {/* Create/Edit Modal */}
      <Modal
        title={editingExpense ? 'Редактировать заявку' : 'Новая заявка на расход'}
        open={isModalOpen}
        onCancel={() => { setIsModalOpen(false); setEditingExpense(null); form.resetFields() }}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item name="title" label="Название" rules={[{ required: true }]}>
                <Input placeholder="Краткое описание расхода" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="priority" label="Приоритет">
                <Select options={Object.entries(priorityLabels).map(([v, l]) => ({ value: v, label: l }))} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="amount" label="Сумма" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="request_date" label="Дата заявки" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="due_date" label="Срок оплаты">
                <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category_id" label="Категория">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  options={categories.map((c) => ({ value: c.id, label: c.name }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="organization_id" label="Организация">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  options={organizations.map((o) => ({ value: o.id, label: o.name }))}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="contractor_name" label="Контрагент">
                <Input placeholder="Название контрагента" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="contractor_inn" label="ИНН контрагента">
                <Input placeholder="ИНН" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="payment_purpose" label="Назначение платежа">
            <TextArea rows={2} placeholder="Назначение платежа для банка" />
          </Form.Item>

          <Form.Item name="notes" label="Примечания">
            <TextArea rows={2} placeholder="Дополнительные примечания" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => { setIsModalOpen(false); setEditingExpense(null) }}>
                Отмена
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={createMutation.isPending || updateMutation.isPending}
              >
                {editingExpense ? 'Сохранить' : 'Создать'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Reject Modal */}
      <Modal
        title="Отклонить заявку"
        open={rejectModalOpen}
        onCancel={() => { setRejectModalOpen(false); setRejectingExpenseId(null); setRejectionReason('') }}
        onOk={handleReject}
        okText="Отклонить"
        okButtonProps={{ danger: true, loading: approveMutation.isPending }}
      >
        <Form.Item label="Причина отклонения">
          <TextArea
            rows={3}
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            placeholder="Укажите причину отклонения заявки"
          />
        </Form.Item>
      </Modal>

      {/* Detail Drawer */}
      <Drawer
        title={`Заявка ${selectedExpense?.number}`}
        open={isDrawerOpen}
        onClose={() => { setIsDrawerOpen(false); setSelectedExpense(null) }}
        width="100%"
        styles={{
          body: {
            padding: '12px',
            overflowX: 'hidden'
          }
        }}
      >
        {selectedExpense && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="Номер">{selectedExpense.number}</Descriptions.Item>
              <Descriptions.Item label="Статус">
                <Tag color={statusColors[selectedExpense.status]}>
                  {statusLabels[selectedExpense.status]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Название" span={2}>
                <Text strong>{selectedExpense.title}</Text>
              </Descriptions.Item>
              {selectedExpense.description && selectedExpense.description !== selectedExpense.title && (
                <Descriptions.Item label="Описание" span={2}>
                  <Text>{selectedExpense.description}</Text>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="Сумма">{formatAmount(selectedExpense.amount)}</Descriptions.Item>
              <Descriptions.Item label="Оплачено">{formatAmount(selectedExpense.amount_paid)}</Descriptions.Item>
              <Descriptions.Item label="Дата заявки">
                {dayjs(selectedExpense.request_date).format('DD.MM.YYYY')}
              </Descriptions.Item>
              <Descriptions.Item label="Срок оплаты">
                {selectedExpense.due_date ? dayjs(selectedExpense.due_date).format('DD.MM.YYYY') : '-'}
              </Descriptions.Item>
              {selectedExpense.payment_date && (
                <Descriptions.Item label="Дата оплаты" span={2}>
                  {dayjs(selectedExpense.payment_date).format('DD.MM.YYYY')}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="Контрагент" span={2}>
                {selectedExpense.contractor_name || '-'}
                {selectedExpense.contractor_inn && ` (ИНН: ${selectedExpense.contractor_inn})`}
              </Descriptions.Item>
              <Descriptions.Item label="Организация" span={2}>
                {selectedExpense.organization_name || '-'}
              </Descriptions.Item>
              {selectedExpense.subdivision && (
                <Descriptions.Item label="Подразделение" span={2}>
                  {selectedExpense.subdivision}
                  {selectedExpense.subdivision_code && <Text type="secondary"> ({selectedExpense.subdivision_code})</Text>}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="Категория">{selectedExpense.category_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="Приоритет">
                <Tag color={priorityColors[selectedExpense.priority]}>
                  {priorityLabels[selectedExpense.priority]}
                </Tag>
              </Descriptions.Item>
              {selectedExpense.payment_purpose &&
               selectedExpense.payment_purpose !== selectedExpense.title &&
               selectedExpense.payment_purpose !== selectedExpense.description && (
                <Descriptions.Item label="Назначение платежа" span={2}>
                  {selectedExpense.payment_purpose}
                </Descriptions.Item>
              )}
              {selectedExpense.comment && (
                <Descriptions.Item label="Комментарий 1С" span={2}>
                  <Text type="secondary">{selectedExpense.comment}</Text>
                </Descriptions.Item>
              )}
              {selectedExpense.notes && (
                <Descriptions.Item label="Примечания" span={2}>
                  <Text style={{ whiteSpace: 'pre-wrap' }}>{selectedExpense.notes}</Text>
                </Descriptions.Item>
              )}
              {selectedExpense.rejection_reason && (
                <Descriptions.Item label="Причина отклонения" span={2}>
                  <Text type="danger">{selectedExpense.rejection_reason}</Text>
                </Descriptions.Item>
              )}
              {selectedExpense.imported_from_1c && (
                <Descriptions.Item label="Импорт из 1С" span={2}>
                  <Tag color="cyan">Синхронизировано из 1С</Tag>
                  {selectedExpense.synced_at && (
                    <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                      {dayjs(selectedExpense.synced_at).format('DD.MM.YYYY HH:mm')}
                    </Text>
                  )}
                </Descriptions.Item>
              )}
            </Descriptions>

            {/* Payment Progress */}
            {selectedExpense.amount > 0 && (
              <Card title="Прогресс оплаты" size="small">
                <Progress
                  percent={Math.round((selectedExpense.amount_paid / selectedExpense.amount) * 100)}
                  status={selectedExpense.amount_paid >= selectedExpense.amount ? 'success' : 'active'}
                  format={(percent) => `${percent}%`}
                />
                <Row gutter={16} style={{ marginTop: 16 }}>
                  <Col span={8}>
                    <Statistic title="К оплате" value={selectedExpense.amount} formatter={(v) => formatAmount(Number(v))} />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Оплачено"
                      value={selectedExpense.amount_paid}
                      valueStyle={{ color: '#52c41a' }}
                      formatter={(v) => formatAmount(Number(v))}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Остаток"
                      value={selectedExpense.remaining_amount || 0}
                      valueStyle={{ color: '#cf1322' }}
                      formatter={(v) => formatAmount(Number(v))}
                    />
                  </Col>
                </Row>
              </Card>
            )}

            {/* Linked Transactions */}
            {selectedExpense.linked_transactions_count > 0 && (
              <Card title={`Привязанные транзакции (${selectedExpense.linked_transactions_count})`} size="small">
                <Statistic
                  value={selectedExpense.linked_transactions_amount}
                  formatter={(v) => formatAmount(Number(v))}
                  prefix={<LinkOutlined />}
                />
              </Card>
            )}
          </Space>
        )}
      </Drawer>

      {/* Sync Modal */}
      <Modal
        title="Синхронизация заявок из 1С"
        open={isSyncModalOpen}
        onCancel={() => {
          setIsSyncModalOpen(false)
          setSyncTaskId(null)
          setSyncProgress(null)
        }}
        footer={null}
        width={600}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Form
            layout="vertical"
            onFinish={(values) => {
              const dateFrom = values.dateRange[0].format('YYYY-MM-DD')
              const dateTo = values.dateRange[1].format('YYYY-MM-DD')
              handleSync(dateFrom, dateTo)
            }}
            initialValues={{
              dateRange: [dayjs().subtract(30, 'days'), dayjs()],
            }}
          >
            <Form.Item
              label="Период"
              name="dateRange"
              rules={[{ required: true, message: 'Выберите период' }]}
            >
              <RangePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={!!syncTaskId} block>
                Запустить синхронизацию
              </Button>
            </Form.Item>
          </Form>

          {syncProgress && (
            <Card size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text>Статус:</Text>
                  <Tag color={syncProgress.status === 'completed' ? 'success' : 'processing'}>
                    {syncProgress.status === 'running' && 'Выполняется'}
                    {syncProgress.status === 'completed' && 'Завершено'}
                    {syncProgress.status === 'failed' && 'Ошибка'}
                    {syncProgress.status === 'pending' && 'Ожидание'}
                  </Tag>
                </div>
                <Progress percent={syncProgress.progress || 0} status="active" />
                {syncProgress.message && <Text type="secondary">{syncProgress.message}</Text>}
                {syncProgress.result && (
                  <div>
                    <Text>Получено из 1С: {syncProgress.result.total_fetched || 0}</Text>
                    <br />
                    <Text>Создано: {syncProgress.result.total_created || 0}</Text>
                    <br />
                    <Text>Обновлено: {syncProgress.result.total_updated || 0}</Text>
                    <br />
                    <Text>Пропущено: {syncProgress.result.total_skipped || 0}</Text>
                  </div>
                )}
              </Space>
            </Card>
          )}
        </Space>
      </Modal>
    </div>
  )
}
