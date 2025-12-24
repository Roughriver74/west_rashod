import { Card, Row, Col, Statistic, Typography, DatePicker, Spin, Empty, Segmented } from 'antd'
import {
  BankOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { getAnalytics } from '../api/bankTransactions'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import dayjs, { Dayjs } from 'dayjs'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, AreaChart, Area
} from 'recharts'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16']

export default function DashboardPage() {
  const navigate = useNavigate()
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null]>([
    dayjs().startOf('month'),
    dayjs().endOf('month')
  ])
  const [chartType, setChartType] = useState<string>('bar')

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', dateRange[0]?.format('YYYY-MM-DD'), dateRange[1]?.format('YYYY-MM-DD')],
    queryFn: () => getAnalytics({
      date_from: dateRange[0]?.format('YYYY-MM-DD'),
      date_to: dateRange[1]?.format('YYYY-MM-DD'),
      compare_previous_period: true
    }),
  })

  // Функция для перехода на страницу операций с фильтрами
  const navigateToTransactions = (filters: Record<string, string>) => {
    const searchParams = new URLSearchParams()

    // Добавляем период из дашборда
    if (dateRange[0]) searchParams.set('date_from', dateRange[0].format('YYYY-MM-DD'))
    if (dateRange[1]) searchParams.set('date_to', dateRange[1].format('YYYY-MM-DD'))

    // Добавляем дополнительные фильтры
    Object.entries(filters).forEach(([key, value]) => {
      if (value) searchParams.set(key, value)
    })

    navigate(`/bank-transactions?${searchParams.toString()}`)
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0
    }).format(value)
  }

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('ru-RU').format(value)
  }

  const renderChangeIndicator = (change: number | null | undefined, suffix = '%') => {
    if (change === null || change === undefined) return null
    const isPositive = change > 0
    const color = isPositive ? '#52c41a' : '#f5222d'
    const Icon = isPositive ? RiseOutlined : FallOutlined
    return (
      <Text style={{ color, fontSize: 12, marginLeft: 8 }}>
        <Icon /> {isPositive ? '+' : ''}{change.toFixed(1)}{suffix}
      </Text>
    )
  }

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <Spin size="large" />
      </div>
    )
  }

  const kpis = analytics?.kpis

  // Prepare chart data
  const monthlyData = analytics?.monthly_flow?.map(item => ({
    name: item.month_name,
    'Расходы': Number(item.debit_amount),
    'Поступления': Number(item.credit_amount),
    'Чистый поток': Number(item.net_flow),
    'Операций': item.transaction_count
  })) || []

  const categoryData = analytics?.top_categories?.map(item => ({
    name: item.category_name || 'Без категории',
    value: Number(item.total_amount),
    count: item.transaction_count,
    percent: item.percent_of_total
  })) || []

  const statusData = analytics?.processing_funnel?.stages?.map(stage => ({
    name: getStatusLabel(stage.status),
    value: stage.count,
    amount: Number(stage.amount),
    percent: stage.percent_of_total
  })) || []

  function getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      'new': 'Новые',
      'categorized': 'Категоризированы',
      'approved': 'Одобрены',
      'needs_review': 'На проверке',
      'ignored': 'Игнорированы'
    }
    return labels[status] || status
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ background: '#fff', padding: 12, border: '1px solid #ddd', borderRadius: 4 }}>
          <Text strong>{label}</Text>
          {payload.map((entry: any, index: number) => (
            <div key={index} style={{ color: entry.color }}>
              {entry.name}: {formatCurrency(entry.value)}
            </div>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>Дашборд</Title>
        </Col>
        <Col>
          <RangePicker
            value={dateRange}
            onChange={(dates) => setDateRange(dates || [null, null])}
            format="DD.MM.YYYY"
          />
        </Col>
      </Row>

      {/* KPI Cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            onClick={() => navigateToTransactions({})}
            style={{ cursor: 'pointer' }}
          >
            <Statistic
              title="Всего операций"
              value={kpis?.total_transactions || 0}
              prefix={<BankOutlined />}
              suffix={
                kpis?.transactions_change !== null && kpis?.transactions_change !== undefined
                  ? renderChangeIndicator(kpis.transactions_change, '')
                  : null
              }
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            onClick={() => navigateToTransactions({ status: 'NEW' })}
            style={{ cursor: 'pointer' }}
          >
            <Statistic
              title="Новые"
              value={kpis?.new_count || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
              suffix={<Text type="secondary" style={{ fontSize: 12 }}>({kpis?.new_percent?.toFixed(1)}%)</Text>}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            onClick={() => navigateToTransactions({ status: 'CATEGORIZED' })}
            style={{ cursor: 'pointer' }}
          >
            <Statistic
              title="Категоризированы"
              value={kpis?.categorized_count || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
              suffix={<Text type="secondary" style={{ fontSize: 12 }}>({kpis?.categorized_percent?.toFixed(1)}%)</Text>}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            onClick={() => navigateToTransactions({ only_unprocessed: 'true' })}
            style={{ cursor: 'pointer' }}
          >
            <Statistic
              title="Требуют проверки"
              value={kpis?.needs_review_count || 0}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
              suffix={<Text type="secondary" style={{ fontSize: 12 }}>({kpis?.needs_review_percent?.toFixed(1)}%)</Text>}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12}>
          <Card
            hoverable
            onClick={() => navigateToTransactions({ transaction_type: 'DEBIT' })}
            style={{ cursor: 'pointer' }}
          >
            <Statistic
              title="Расходы (DEBIT)"
              value={kpis?.total_debit_amount || 0}
              prefix={<ArrowDownOutlined />}
              precision={0}
              suffix="₽"
              valueStyle={{ color: '#cf1322' }}
              formatter={(value) => formatNumber(Number(value))}
            />
            {renderChangeIndicator(kpis?.debit_change_percent)}
          </Card>
        </Col>

        <Col xs={24} sm={12}>
          <Card
            hoverable
            onClick={() => navigateToTransactions({ transaction_type: 'CREDIT' })}
            style={{ cursor: 'pointer' }}
          >
            <Statistic
              title="Поступления (CREDIT)"
              value={kpis?.total_credit_amount || 0}
              prefix={<ArrowUpOutlined />}
              precision={0}
              suffix="₽"
              valueStyle={{ color: '#3f8600' }}
              formatter={(value) => formatNumber(Number(value))}
            />
            {renderChangeIndicator(kpis?.credit_change_percent)}
          </Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        {/* Monthly Flow Chart */}
        <Col xs={24} lg={16}>
          <Card
            title="Денежный поток по месяцам"
            extra={
              <Segmented
                value={chartType}
                onChange={(value) => setChartType(value as string)}
                options={[
                  { label: 'Столбцы', value: 'bar' },
                  { label: 'Линии', value: 'line' },
                  { label: 'Область', value: 'area' },
                ]}
              />
            }
          >
            {monthlyData.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                {chartType === 'bar' ? (
                  <BarChart data={monthlyData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis tickFormatter={(value) => `${(value / 1000000).toFixed(1)}М`} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar dataKey="Расходы" fill="#f5222d" />
                    <Bar dataKey="Поступления" fill="#52c41a" />
                  </BarChart>
                ) : chartType === 'line' ? (
                  <LineChart data={monthlyData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis tickFormatter={(value) => `${(value / 1000000).toFixed(1)}М`} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Line type="monotone" dataKey="Расходы" stroke="#f5222d" strokeWidth={2} />
                    <Line type="monotone" dataKey="Поступления" stroke="#52c41a" strokeWidth={2} />
                  </LineChart>
                ) : (
                  <AreaChart data={monthlyData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis tickFormatter={(value) => `${(value / 1000000).toFixed(1)}М`} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Area type="monotone" dataKey="Расходы" fill="#f5222d" fillOpacity={0.3} stroke="#f5222d" />
                    <Area type="monotone" dataKey="Поступления" fill="#52c41a" fillOpacity={0.3} stroke="#52c41a" />
                  </AreaChart>
                )}
              </ResponsiveContainer>
            ) : (
              <Empty description="Нет данных за выбранный период" />
            )}
          </Card>
        </Col>

        {/* Category Pie Chart */}
        <Col xs={24} lg={8}>
          <Card title="Топ категорий по расходам">
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, percent }) => `${(name || '').slice(0, 15)}${(name || '').length > 15 ? '...' : ''} (${(percent || 0).toFixed(0)}%)`}
                    labelLine={false}
                    onClick={(data) => {
                      if (data && data.name) {
                        // Находим ID категории из данных
                        const categoryItem = analytics?.top_categories?.find(c => c.category_name === data.name)
                        if (categoryItem) {
                          navigateToTransactions({ category_id: categoryItem.category_id.toString() })
                        }
                      }
                    }}
                    cursor="pointer"
                  >
                    {categoryData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => formatCurrency(Number(value || 0))}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="Нет категоризированных операций" />
            )}
          </Card>
        </Col>
      </Row>

      {/* Status Distribution & AI Performance */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="Статусы обработки">
            {statusData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={statusData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="name" width={120} />
                  <Tooltip formatter={(value) => formatNumber(Number(value || 0))} />
                  <Bar
                    dataKey="value"
                    fill="#1890ff"
                    onClick={(data: any) => {
                      // Маппинг русских названий на статусы
                      const statusMap: Record<string, string> = {
                        'Новые': 'NEW',
                        'Категоризированы': 'CATEGORIZED',
                        'Одобрены': 'APPROVED',
                        'На проверке': 'NEEDS_REVIEW',
                        'Игнорированы': 'IGNORED'
                      }
                      const status = statusMap[data.name]
                      if (status) {
                        navigateToTransactions({ status })
                      }
                    }}
                    cursor="pointer"
                  >
                    {statusData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="Нет данных" />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Производительность AI классификации">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="Средняя уверенность"
                  value={(analytics?.ai_performance?.avg_confidence || 0) * 100}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Авто-категоризировано"
                  value={kpis?.auto_categorized_count || 0}
                  suffix={<Text type="secondary" style={{ fontSize: 12 }}>({kpis?.auto_categorized_percent?.toFixed(1)}%)</Text>}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Высокая уверенность (≥90%)"
                  value={analytics?.ai_performance?.high_confidence_count || 0}
                  suffix={<Text type="secondary" style={{ fontSize: 12 }}>({analytics?.ai_performance?.high_confidence_percent?.toFixed(1)}%)</Text>}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Низкая уверенность (&lt;70%)"
                  value={analytics?.ai_performance?.low_confidence_count || 0}
                  suffix={<Text type="secondary" style={{ fontSize: 12 }}>({analytics?.ai_performance?.low_confidence_percent?.toFixed(1)}%)</Text>}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Top Counterparties */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24}>
          <Card title="Топ-10 контрагентов по сумме">
            {analytics?.top_counterparties && analytics.top_counterparties.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={analytics.top_counterparties.slice(0, 10).map(cp => ({
                    name: cp.counterparty_name?.slice(0, 25) + (cp.counterparty_name?.length > 25 ? '...' : ''),
                    amount: Number(cp.total_amount),
                    count: cp.transaction_count
                  }))}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" tickFormatter={(value) => `${(value / 1000000).toFixed(1)}М`} />
                  <YAxis type="category" dataKey="name" width={200} />
                  <Tooltip formatter={(value) => formatCurrency(Number(value || 0))} />
                  <Bar dataKey="amount" fill="#722ed1" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="Нет данных о контрагентах" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
