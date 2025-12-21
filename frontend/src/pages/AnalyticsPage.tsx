import { useState } from 'react'
import {
  Card,
  Row,
  Col,
  Statistic,
  Typography,
  DatePicker,
  Select,
  Space,
  Spin,
  Tag,
  Table,
  Progress,
  Empty,
} from 'antd'
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  BankOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  RobotOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { getAnalytics, AnalyticsFilters } from '../api/bankTransactions'
import { getCategories } from '../api/categories'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

const COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16']

const statusLabels: Record<string, string> = {
  NEW: 'Новые',
  CATEGORIZED: 'Категоризированы',
  APPROVED: 'Утверждены',
  NEEDS_REVIEW: 'На проверке',
  IGNORED: 'Игнорированы',
}

const formatAmount = (value: number) => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(0)}K`
  }
  return value.toFixed(0)
}

const formatFullAmount = (value: number) => {
  return Number(value).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₽'
}

export default function AnalyticsPage() {
  const [filters, setFilters] = useState<AnalyticsFilters>({
    compare_previous_period: true,
  })

  // Fetch analytics
  const { data: analytics, isLoading } = useQuery({
    queryKey: ['bank-transactions-analytics', filters],
    queryFn: () => getAnalytics(filters),
  })

  // Fetch categories for filter
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => getCategories({ is_active: true }),
  })

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!analytics) {
    return <Empty description="Нет данных для отображения" />
  }

  const { kpis, monthly_flow, top_categories, top_counterparties, processing_funnel, ai_performance, low_confidence_items } = analytics

  // Prepare category pie data
  const categoryPieData = top_categories.slice(0, 6).map((cat, index) => ({
    name: cat.category_name,
    value: Number(cat.total_amount),
    count: cat.transaction_count,
    fill: COLORS[index % COLORS.length],
  }))

  // Prepare monthly flow data for chart
  const monthlyChartData = monthly_flow.map(m => ({
    name: m.month_name,
    'Расход': Number(m.debit_amount),
    'Приход': Number(m.credit_amount),
    'Нетто': Number(m.net_flow),
    transactions: m.transaction_count,
  }))

  // AI confidence distribution
  const confidenceData = ai_performance.confidence_distribution.map(b => ({
    name: b.bracket,
    count: b.count,
    amount: Number(b.total_amount),
  }))

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <BankOutlined style={{ marginRight: 8 }} />
            Аналитика банковских операций
          </Title>
        </Col>
        <Col>
          <Space wrap>
            <RangePicker
              onChange={(dates) => {
                setFilters(prev => ({
                  ...prev,
                  date_from: dates?.[0]?.format('YYYY-MM-DD'),
                  date_to: dates?.[1]?.format('YYYY-MM-DD'),
                }))
              }}
              placeholder={['Дата с', 'Дата по']}
            />
            <Select
              placeholder="Категория"
              style={{ width: 200 }}
              allowClear
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              onChange={(value) => setFilters(prev => ({ ...prev, category_id: value }))}
              options={categories.map(cat => ({ value: cat.id, label: cat.name }))}
            />
            <Select
              placeholder="Тип операции"
              style={{ width: 150 }}
              allowClear
              onChange={(value) => setFilters(prev => ({ ...prev, transaction_type: value }))}
              options={[
                { value: 'DEBIT', label: 'Расход' },
                { value: 'CREDIT', label: 'Приход' },
              ]}
            />
          </Space>
        </Col>
      </Row>

      {/* KPI Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Всего операций"
              value={kpis.total_transactions}
              prefix={<BankOutlined />}
              suffix={
                kpis.transactions_change !== undefined && (
                  <Tag color={kpis.transactions_change >= 0 ? 'green' : 'red'} style={{ marginLeft: 8 }}>
                    {kpis.transactions_change >= 0 ? '+' : ''}{kpis.transactions_change}
                  </Tag>
                )
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Расход"
              value={Number(kpis.total_debit_amount)}
              precision={0}
              prefix={<ArrowDownOutlined style={{ color: '#cf1322' }} />}
              suffix="₽"
              valueStyle={{ color: '#cf1322' }}
            />
            {kpis.debit_change_percent !== undefined && (
              <Text type={kpis.debit_change_percent <= 0 ? 'success' : 'danger'}>
                {kpis.debit_change_percent >= 0 ? '+' : ''}{kpis.debit_change_percent.toFixed(1)}% vs пред. период
              </Text>
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Приход"
              value={Number(kpis.total_credit_amount)}
              precision={0}
              prefix={<ArrowUpOutlined style={{ color: '#3f8600' }} />}
              suffix="₽"
              valueStyle={{ color: '#3f8600' }}
            />
            {kpis.credit_change_percent !== undefined && (
              <Text type={kpis.credit_change_percent >= 0 ? 'success' : 'danger'}>
                {kpis.credit_change_percent >= 0 ? '+' : ''}{kpis.credit_change_percent.toFixed(1)}% vs пред. период
              </Text>
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Нетто"
              value={Number(kpis.net_flow)}
              precision={0}
              prefix={Number(kpis.net_flow) >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              suffix="₽"
              valueStyle={{ color: Number(kpis.net_flow) >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Status & AI Metrics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small">
            <Statistic
              title="Новые"
              value={kpis.new_count}
              prefix={<ClockCircleOutlined style={{ color: '#1890ff' }} />}
              suffix={<Text type="secondary" style={{ fontSize: 12 }}>{kpis.new_percent.toFixed(0)}%</Text>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small">
            <Statistic
              title="Категоризированы"
              value={kpis.categorized_count}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              suffix={<Text type="secondary" style={{ fontSize: 12 }}>{kpis.categorized_percent.toFixed(0)}%</Text>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small">
            <Statistic
              title="Требуют проверки"
              value={kpis.needs_review_count}
              prefix={<ExclamationCircleOutlined style={{ color: '#faad14' }} />}
              suffix={<Text type="secondary" style={{ fontSize: 12 }}>{kpis.needs_review_percent.toFixed(0)}%</Text>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small">
            <Statistic
              title="Авто-категоризация AI"
              value={kpis.auto_categorized_count}
              prefix={<RobotOutlined style={{ color: '#722ed1' }} />}
              suffix={<Text type="secondary" style={{ fontSize: 12 }}>{kpis.auto_categorized_percent.toFixed(0)}%</Text>}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Row 1 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {/* Cash Flow Chart */}
        <Col xs={24} lg={16}>
          <Card title="Денежный поток по месяцам" size="small">
            {monthlyChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={monthlyChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={formatAmount} />
                  <Tooltip formatter={(value) => formatFullAmount(Number(value))} />
                  <Legend />
                  <Bar dataKey="Расход" fill="#cf1322" />
                  <Bar dataKey="Приход" fill="#3f8600" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="Нет данных" />
            )}
          </Card>
        </Col>

        {/* Category Breakdown Pie */}
        <Col xs={24} lg={8}>
          <Card title="Топ категорий" size="small">
            {categoryPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={categoryPieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {categoryPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatFullAmount(Number(value))} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="Нет категоризированных операций" />
            )}
          </Card>
        </Col>
      </Row>

      {/* Charts Row 2 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {/* Processing Funnel */}
        <Col xs={24} lg={12}>
          <Card title="Воронка обработки" size="small" extra={
            <Text type="secondary">
              Конверсия в утверждённые: {processing_funnel.conversion_rate_to_approved.toFixed(1)}%
            </Text>
          }>
            <Row gutter={[8, 8]}>
              {processing_funnel.stages.map((stage, index) => (
                <Col span={24} key={stage.status}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 120 }}>
                      <Tag color={['blue', 'green', 'cyan', 'orange', 'default'][index]}>
                        {statusLabels[stage.status] || stage.status}
                      </Tag>
                    </div>
                    <Progress
                      percent={stage.percent_of_total}
                      size="small"
                      style={{ flex: 1 }}
                      format={() => `${stage.count} (${stage.percent_of_total.toFixed(0)}%)`}
                    />
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>

        {/* AI Performance */}
        <Col xs={24} lg={12}>
          <Card title="Производительность AI" size="small" extra={
            <Text type="secondary">
              Средняя уверенность: {(ai_performance.avg_confidence * 100).toFixed(0)}%
            </Text>
          }>
            {confidenceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={confidenceData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#722ed1" name="Кол-во" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="Нет данных" />
            )}
            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={12}>
                <Statistic
                  title="Высокая уверенность (≥90%)"
                  value={ai_performance.high_confidence_count}
                  valueStyle={{ color: '#52c41a', fontSize: 20 }}
                  suffix={<Text type="secondary" style={{ fontSize: 12 }}>{ai_performance.high_confidence_percent.toFixed(0)}%</Text>}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Низкая уверенность (<70%)"
                  value={ai_performance.low_confidence_count}
                  valueStyle={{ color: '#faad14', fontSize: 20 }}
                  suffix={<Text type="secondary" style={{ fontSize: 12 }}>{ai_performance.low_confidence_percent.toFixed(0)}%</Text>}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Top Counterparties & Categories Tables */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="Топ контрагентов" size="small">
            <Table
              dataSource={top_counterparties.slice(0, 10)}
              rowKey="counterparty_inn"
              size="small"
              pagination={false}
              columns={[
                {
                  title: 'Контрагент',
                  dataIndex: 'counterparty_name',
                  ellipsis: true,
                },
                {
                  title: 'Операций',
                  dataIndex: 'transaction_count',
                  width: 80,
                  align: 'center',
                },
                {
                  title: 'Сумма',
                  dataIndex: 'total_amount',
                  width: 120,
                  align: 'right',
                  render: (val) => formatFullAmount(Number(val)),
                },
                {
                  title: '',
                  dataIndex: 'is_regular',
                  width: 30,
                  render: (isRegular) => isRegular ? <SyncOutlined style={{ color: '#722ed1' }} title="Регулярный" /> : null,
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Категории по сумме" size="small">
            <Table
              dataSource={top_categories}
              rowKey="category_id"
              size="small"
              pagination={false}
              columns={[
                {
                  title: 'Категория',
                  dataIndex: 'category_name',
                  ellipsis: true,
                },
                {
                  title: 'Тип',
                  dataIndex: 'category_type',
                  width: 70,
                  render: (type) => type ? <Tag color={type === 'OPEX' ? 'blue' : 'purple'}>{type}</Tag> : '-',
                },
                {
                  title: 'Операций',
                  dataIndex: 'transaction_count',
                  width: 80,
                  align: 'center',
                },
                {
                  title: 'Сумма',
                  dataIndex: 'total_amount',
                  width: 120,
                  align: 'right',
                  render: (val) => formatFullAmount(Number(val)),
                },
                {
                  title: '%',
                  dataIndex: 'percent_of_total',
                  width: 60,
                  align: 'right',
                  render: (val) => `${val.toFixed(0)}%`,
                },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {/* Low Confidence Items */}
      {low_confidence_items.length > 0 && (
        <Card title="Операции с низкой уверенностью AI (требуют проверки)" size="small">
          <Table
            dataSource={low_confidence_items}
            rowKey="transaction_id"
            size="small"
            pagination={{ pageSize: 10 }}
            columns={[
              {
                title: 'Дата',
                dataIndex: 'transaction_date',
                width: 100,
                render: (date) => dayjs(date).format('DD.MM.YYYY'),
              },
              {
                title: 'Контрагент',
                dataIndex: 'counterparty_name',
                width: 200,
                ellipsis: true,
              },
              {
                title: 'Сумма',
                dataIndex: 'amount',
                width: 120,
                align: 'right',
                render: (val) => formatFullAmount(Number(val)),
              },
              {
                title: 'Назначение',
                dataIndex: 'payment_purpose',
                ellipsis: true,
              },
              {
                title: 'Предложение AI',
                dataIndex: 'suggested_category_name',
                width: 150,
                render: (name) => name ? <Tag color="orange">{name}</Tag> : '-',
              },
              {
                title: 'Уверенность',
                dataIndex: 'category_confidence',
                width: 100,
                render: (val) => (
                  <Progress
                    percent={Math.round(val * 100)}
                    size="small"
                    strokeColor={val >= 0.5 ? '#faad14' : '#f5222d'}
                  />
                ),
              },
            ]}
          />
        </Card>
      )}
    </div>
  )
}
