import { useState } from 'react'
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
  Expense,
  ExpenseFilters,
  ExpenseCreate,
  ExpenseStatus,
  ExpensePriority,
} from '../api/expenses'
import { getCategories } from '../api/categories'
import { getOrganizations } from '../api/organizations'

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
  const [filters, setFilters] = useState<ExpenseFilters>({ limit: 100 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null)
  const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [rejectModalOpen, setRejectModalOpen] = useState(false)
  const [rejectingExpenseId, setRejectingExpenseId] = useState<number | null>(null)
  const [rejectionReason, setRejectionReason] = useState('')

  // Queries
  const { data: expenses = [], isLoading } = useQuery({
    queryKey: ['expenses', filters],
    queryFn: () => getExpenses(filters),
  })

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

  const columns: ColumnsType<Expense> = [
    {
      title: 'Номер',
      dataIndex: 'number',
      key: 'number',
      width: 130,
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
      title: 'Название',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong ellipsis style={{ maxWidth: 300 }}>{value}</Text>
          {record.contractor_name && (
            <Text type="secondary" style={{ fontSize: 12 }}>{record.contractor_name}</Text>
          )}
        </Space>
      ),
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
      width: 150,
      render: (value) => value ? <Tag>{value}</Tag> : '-',
    },
    {
      title: 'Транзакции',
      key: 'linked',
      width: 100,
      align: 'center',
      render: (_, record) => (
        record.linked_transactions_count > 0 ? (
          <Tooltip title={`Привязано: ${formatAmount(record.linked_transactions_amount)}`}>
            <Tag color="blue" icon={<LinkOutlined />}>
              {record.linked_transactions_count}
            </Tag>
          </Tooltip>
        ) : '-'
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 180,
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
            <>
              <Tooltip title="Редактировать">
                <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
              </Tooltip>
              <Tooltip title="На согласование">
                <Button
                  size="small"
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={() => submitMutation.mutate(record.id)}
                  loading={submitMutation.isPending}
                />
              </Tooltip>
            </>
          )}

          {record.status === 'PENDING' && (
            <>
              <Tooltip title="Согласовать">
                <Button
                  size="small"
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={() => approveMutation.mutate({ id: record.id, action: 'approve' })}
                  style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
                />
              </Tooltip>
              <Tooltip title="Отклонить">
                <Button
                  size="small"
                  danger
                  icon={<CloseCircleOutlined />}
                  onClick={() => { setRejectingExpenseId(record.id); setRejectModalOpen(true) }}
                />
              </Tooltip>
            </>
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
            pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `Всего ${total}` }}
            scroll={{ x: 1200 }}
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
        width={600}
      >
        {selectedExpense && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="Номер">{selectedExpense.number}</Descriptions.Item>
              <Descriptions.Item label="Статус">
                <Tag color={statusColors[selectedExpense.status]}>
                  {statusLabels[selectedExpense.status]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Название" span={2}>{selectedExpense.title}</Descriptions.Item>
              <Descriptions.Item label="Сумма">{formatAmount(selectedExpense.amount)}</Descriptions.Item>
              <Descriptions.Item label="Оплачено">{formatAmount(selectedExpense.amount_paid)}</Descriptions.Item>
              <Descriptions.Item label="Дата заявки">
                {dayjs(selectedExpense.request_date).format('DD.MM.YYYY')}
              </Descriptions.Item>
              <Descriptions.Item label="Срок оплаты">
                {selectedExpense.due_date ? dayjs(selectedExpense.due_date).format('DD.MM.YYYY') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Контрагент" span={2}>
                {selectedExpense.contractor_name || '-'}
                {selectedExpense.contractor_inn && ` (ИНН: ${selectedExpense.contractor_inn})`}
              </Descriptions.Item>
              <Descriptions.Item label="Категория">{selectedExpense.category_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="Приоритет">
                <Tag color={priorityColors[selectedExpense.priority]}>
                  {priorityLabels[selectedExpense.priority]}
                </Tag>
              </Descriptions.Item>
              {selectedExpense.payment_purpose && (
                <Descriptions.Item label="Назначение" span={2}>{selectedExpense.payment_purpose}</Descriptions.Item>
              )}
              {selectedExpense.notes && (
                <Descriptions.Item label="Примечания" span={2}>{selectedExpense.notes}</Descriptions.Item>
              )}
              {selectedExpense.rejection_reason && (
                <Descriptions.Item label="Причина отклонения" span={2}>
                  <Text type="danger">{selectedExpense.rejection_reason}</Text>
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
    </div>
  )
}
