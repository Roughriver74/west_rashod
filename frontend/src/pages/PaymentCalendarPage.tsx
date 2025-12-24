import { useState } from 'react'
import {
  Card,
  Calendar,
  Badge,
  Modal,
  Table,
  Tag,
  Typography,
  Select,
  Row,
  Col,
  Statistic,
  Space,
  Collapse,
  Button,
} from 'antd'
import {
  DollarOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import dayjs, { Dayjs } from 'dayjs'
import type { TableColumnsType } from 'antd'
import { getPaymentCalendar, getPaymentsByDay } from '../api/analytics'
import { Expense, ExpenseStatus } from '../api/expenses'
import { getCategories } from '../api/categories'
import { getOrganizations } from '../api/organizations'

const { Title, Text } = Typography
const { Panel } = Collapse

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

const formatAmount = (value: number) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

export default function PaymentCalendarPage() {
  const queryClient = useQueryClient()

  // State
  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs())
  const [currentMonth, setCurrentMonth] = useState<Dayjs>(dayjs())
  const [categoryFilter, setCategoryFilter] = useState<number | undefined>()
  const [organizationFilter, setOrganizationFilter] = useState<number | undefined>()
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Queries
  const { data: calendarData = [] } = useQuery({
    queryKey: [
      'payment-calendar',
      currentMonth.year(),
      currentMonth.month() + 1,
      categoryFilter,
      organizationFilter,
    ],
    queryFn: () =>
      getPaymentCalendar({
        year: currentMonth.year(),
        month: currentMonth.month() + 1,
        category_id: categoryFilter,
        organization_id: organizationFilter,
      }),
  })

  const { data: dayDetails } = useQuery({
    queryKey: ['payments-by-day', selectedDate.format('YYYY-MM-DD'), categoryFilter, organizationFilter],
    queryFn: () =>
      getPaymentsByDay(selectedDate.format('YYYY-MM-DD'), {
        category_id: categoryFilter,
        organization_id: organizationFilter,
      }),
    enabled: isModalOpen,
  })

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => getCategories({ is_active: true }),
  })

  const { data: organizations = [] } = useQuery({
    queryKey: ['organizations'],
    queryFn: () => getOrganizations({ is_active: true }),
  })

  // Calculate statistics
  const stats = calendarData.reduce(
    (acc, day) => {
      acc.totalPaid += day.total_amount
      acc.totalPlanned += day.planned_amount
      acc.paidCount += day.payment_count
      acc.plannedCount += day.planned_count
      if (day.payment_count > 0 || day.planned_count > 0) {
        acc.daysWithPayments++
      }
      return acc
    },
    { totalPaid: 0, totalPlanned: 0, paidCount: 0, plannedCount: 0, daysWithPayments: 0 }
  )

  // Cell renderer for calendar
  const dateCellRender = (value: Dayjs) => {
    const dateStr = value.format('YYYY-MM-DD')
    const dayData = calendarData.find((d) => d.date === dateStr)

    if (!dayData || (dayData.payment_count === 0 && dayData.planned_count === 0)) {
      return null
    }

    return (
      <div>
        {dayData.payment_count > 0 && (
          <Badge
            status="success"
            text={
              <Text style={{ fontSize: 11 }}>
                {formatAmount(dayData.total_amount)} ({dayData.payment_count})
              </Text>
            }
          />
        )}
        {dayData.planned_count > 0 && (
          <Badge
            status="warning"
            text={
              <Text style={{ fontSize: 11 }}>
                {formatAmount(dayData.planned_amount)} ({dayData.planned_count})
              </Text>
            }
          />
        )}
      </div>
    )
  }

  const handleSelect = (date: Dayjs) => {
    setSelectedDate(date)
    setIsModalOpen(true)
  }

  const expenseColumns: TableColumnsType<Expense> = [
    {
      title: 'Номер',
      dataIndex: 'number',
      key: 'number',
      width: 120,
    },
    {
      title: 'Название',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          {record.contractor_name && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.contractor_name}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      key: 'amount',
      width: 130,
      align: 'right',
      render: (value) => <Text strong>{formatAmount(value)}</Text>,
    },
    {
      title: 'Категория',
      dataIndex: 'category_name',
      key: 'category_name',
      width: 150,
      render: (value) => (value ? <Tag>{value}</Tag> : '-'),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (status: ExpenseStatus) => <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>,
    },
  ]

  return (
    <div style={{ padding: 0 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={2} style={{ margin: 0 }}>
            <CalendarOutlined /> Календарь оплат
          </Title>
          <Button icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: ['payment-calendar'] })}>
            Обновить
          </Button>
        </div>

        {/* Stats */}
        <Row gutter={16}>
          <Col xs={12} sm={8} md={6}>
            <Card size="small">
              <Statistic
                title="Оплачено в месяце"
                value={stats.totalPaid}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
                formatter={(value) => formatAmount(Number(value))}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Card size="small">
              <Statistic
                title="Запланировано"
                value={stats.totalPlanned}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#faad14' }}
                formatter={(value) => formatAmount(Number(value))}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Card size="small">
              <Statistic title="Оплаченных заявок" value={stats.paidCount} prefix={<DollarOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Card size="small">
              <Statistic title="Дней с платежами" value={stats.daysWithPayments} prefix={<CalendarOutlined />} />
            </Card>
          </Col>
        </Row>

        {/* Filters */}
        <Card size="small">
          <Space wrap>
            <Select
              placeholder="Категория"
              style={{ width: 200 }}
              allowClear
              onChange={setCategoryFilter}
              value={categoryFilter}
              options={categories.map((c) => ({ value: c.id, label: c.name }))}
            />
            <Select
              placeholder="Организация"
              style={{ width: 200 }}
              allowClear
              onChange={setOrganizationFilter}
              value={organizationFilter}
              options={organizations.map((o) => ({ value: o.id, label: o.name }))}
            />
          </Space>
        </Card>

        {/* Calendar */}
        <Card>
          <Calendar
            dateCellRender={dateCellRender}
            onSelect={handleSelect}
            value={currentMonth}
            onPanelChange={(date) => setCurrentMonth(date)}
          />
          <div style={{ marginTop: 16, padding: 8, background: '#f5f5f5', borderRadius: 4 }}>
            <Space size="large">
              <Space>
                <Badge status="success" />
                <Text>Оплаченные заявки (PAID)</Text>
              </Space>
              <Space>
                <Badge status="warning" />
                <Text>Запланированные заявки (PENDING)</Text>
              </Space>
            </Space>
          </div>
        </Card>
      </Space>

      {/* Day Details Modal */}
      <Modal
        title={`Платежи на ${selectedDate.format('DD.MM.YYYY')}`}
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        width={1000}
      >
        {dayDetails && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Row gutter={16}>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="Оплачено"
                    value={dayDetails.total_paid_amount}
                    valueStyle={{ color: '#52c41a' }}
                    prefix={<CheckCircleOutlined />}
                    formatter={(value) => formatAmount(Number(value))}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="Запланировано"
                    value={dayDetails.total_planned_amount}
                    valueStyle={{ color: '#faad14' }}
                    prefix={<ClockCircleOutlined />}
                    formatter={(value) => formatAmount(Number(value))}
                  />
                </Card>
              </Col>
            </Row>

            <Collapse defaultActiveKey={['paid', 'planned']}>
              <Panel
                header={`Оплаченные (${dayDetails.paid.length} шт, ${formatAmount(dayDetails.total_paid_amount)})`}
                key="paid"
              >
                <Table columns={expenseColumns} dataSource={dayDetails.paid} rowKey="id" pagination={false} size="small" />
              </Panel>
              <Panel
                header={`Запланированные (${dayDetails.planned.length} шт, ${formatAmount(dayDetails.total_planned_amount)})`}
                key="planned"
              >
                <Table columns={expenseColumns} dataSource={dayDetails.planned} rowKey="id" pagination={false} size="small" />
              </Panel>
            </Collapse>
          </Space>
        )}
      </Modal>
    </div>
  )
}
