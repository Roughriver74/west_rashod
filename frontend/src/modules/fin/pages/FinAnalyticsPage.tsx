/**
 * Fin Analytics Page - Detailed analytics with KPI and efficiency metrics
 * Rewritten with Ant Design
 */
import { useMemo } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import {
  Row,
  Col,
  Card,
  Statistic,
  Table,
  Spin,
  Typography,
  Space,
  Button,
  Tag,
  Empty,
  Alert,
} from 'antd'
import {
  PercentageOutlined,
  RiseOutlined,
  FileTextOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ComposedChart, Cell
} from 'recharts'
import { formatAmount, formatAxisAmount, formatTooltipAmount } from '../utils/formatters'
import { useFinFilterValues } from '../stores/finFilterStore'
import { useDebounce } from '../hooks/usePerformance'
import { buildFilterPayload } from '../utils/filterParams'
import { getKPIMetrics, getMonthlyEfficiency, getOrgEfficiency } from '../api/finApi'
import type { KPIMetrics, MonthlyEfficiency, OrgEfficiencyMetric } from '../api/finApi'

const { Title, Text } = Typography

export default function FinAnalyticsPage() {
  const filters = useFinFilterValues()
  const debouncedFilters = useDebounce(filters, 500)
  const filterPayload = useMemo(
    () => buildFilterPayload(debouncedFilters, { includeDefaultDateTo: true }),
    [debouncedFilters]
  )

  const metricsQuery = useQuery({
    queryKey: ['fin', 'analytics', 'kpi-metrics', filterPayload],
    queryFn: () => getKPIMetrics(filterPayload),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  })

  const monthlyEfficiencyQuery = useQuery({
    queryKey: ['fin', 'analytics', 'monthly-efficiency', filterPayload],
    queryFn: () => getMonthlyEfficiency(filterPayload),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  })

  const orgEfficiencyQuery = useQuery({
    queryKey: ['fin', 'analytics', 'org-efficiency', filterPayload],
    queryFn: () => getOrgEfficiency(filterPayload),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  })

  const kpiMetrics = metricsQuery.data as KPIMetrics | undefined
  const monthlyEfficiency = (monthlyEfficiencyQuery.data ?? []) as MonthlyEfficiency[]
  const orgEfficiency = (orgEfficiencyQuery.data ?? []) as OrgEfficiencyMetric[]

  const isInitialLoading = (
    (metricsQuery.isLoading && !metricsQuery.data) ||
    (monthlyEfficiencyQuery.isLoading && !monthlyEfficiencyQuery.data) ||
    (orgEfficiencyQuery.isLoading && !orgEfficiencyQuery.data)
  )

  const handleRefresh = () => {
    metricsQuery.refetch()
    monthlyEfficiencyQuery.refetch()
    orgEfficiencyQuery.refetch()
  }

  if (metricsQuery.isError || monthlyEfficiencyQuery.isError || orgEfficiencyQuery.isError) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: 16 }}>
        <Alert
          type="error"
          message="Ошибка загрузки"
          description="Не удалось загрузить аналитику. Попробуйте еще раз."
          showIcon
        />
        <Button type="primary" icon={<ReloadOutlined />} onClick={handleRefresh}>
          Обновить
        </Button>
      </div>
    )
  }

  if (isInitialLoading || !kpiMetrics) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <Space direction="vertical" align="center">
          <Spin size="large" />
          <Text type="secondary">Загрузка аналитики...</Text>
        </Space>
      </div>
    )
  }

  const avgInterestRate = kpiMetrics.avgInterestRate?.toFixed(2) || '0.00'
  const paymentVelocity = kpiMetrics.repaymentVelocity?.toFixed(1) || '0.0'
  const activeContracts = kpiMetrics.activeContracts || 0

  const dateTickFormatter = (value: string) => {
    if (!value) return ''
    const [year, month] = value.split('-')
    const months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
    return `${months[parseInt(month) - 1]} '${year.slice(-2)}`
  }

  // Table columns for organization efficiency
  const columns = [
    {
      title: 'Организация',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text ellipsis style={{ maxWidth: 200 }}>{text}</Text>,
    },
    {
      title: 'Получено',
      dataIndex: 'received',
      key: 'received',
      align: 'right' as const,
      render: (value: number) => <Text style={{ fontFamily: 'monospace' }}>{formatAmount(value)}</Text>,
    },
    {
      title: 'Погашено',
      dataIndex: 'principal',
      key: 'principal',
      align: 'right' as const,
      render: (value: number) => <Text style={{ fontFamily: 'monospace' }}>{formatAmount(value)}</Text>,
    },
    {
      title: 'Эффективность',
      dataIndex: 'efficiency',
      key: 'efficiency',
      align: 'center' as const,
      render: (value: number) => (
        <Tag color={value > 70 ? 'success' : value > 50 ? 'warning' : 'error'}>
          {value.toFixed(1)}%
        </Tag>
      ),
    },
  ]

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ marginBottom: 4 }}>Детальная аналитика</Title>
        <Text type="secondary">Глубокий анализ эффективности и трендов</Text>
      </div>

      {/* Key Metrics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card
            style={{
              background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
              borderRadius: 12,
            }}
            bodyStyle={{ padding: 20 }}
          >
            <Statistic
              title={<span style={{ color: 'rgba(255,255,255,0.85)' }}>Средняя ставка</span>}
              value={avgInterestRate}
              suffix="%"
              prefix={<PercentageOutlined />}
              valueStyle={{ color: 'white', fontSize: 28 }}
            />
            <Text style={{ color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>
              Процентная нагрузка
            </Text>
            <div style={{ marginTop: 8, fontSize: 11, color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>
              Расчет: (Уплачено процентов / Получено кредитов) × 100%
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={8}>
          <Card
            style={{
              background: 'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)',
              borderRadius: 12,
            }}
            bodyStyle={{ padding: 20 }}
          >
            <Statistic
              title={<span style={{ color: 'rgba(255,255,255,0.85)' }}>Скорость погашения</span>}
              value={paymentVelocity}
              suffix="%"
              prefix={<RiseOutlined />}
              valueStyle={{ color: 'white', fontSize: 28 }}
            />
            <Text style={{ color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>
              Погашено от полученного
            </Text>
            <div style={{ marginTop: 8, fontSize: 11, color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>
              Расчет: (Погашено тела / Получено кредитов) × 100%
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={8}>
          <Card
            style={{
              background: 'linear-gradient(135deg, #fa8c16 0%, #d46b08 100%)',
              borderRadius: 12,
            }}
            bodyStyle={{ padding: 20 }}
          >
            <Statistic
              title={<span style={{ color: 'rgba(255,255,255,0.85)' }}>Активных договоров</span>}
              value={activeContracts}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: 'white', fontSize: 28 }}
            />
            <Text style={{ color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>
              Уникальных кредитов
            </Text>
            <div style={{ marginTop: 8, fontSize: 11, color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>
              Договоры с остатком долга более 100 руб
            </div>
          </Card>
        </Col>
      </Row>

      {/* Monthly Efficiency Chart */}
      <Card
        title="Эффективность погашения по месяцам"
        extra={<Text type="secondary">Соотношение тела долга к процентам</Text>}
        style={{ marginBottom: 24 }}
      >
        <div style={{ height: 350 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={monthlyEfficiency}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="month"
                tickFormatter={dateTickFormatter}
                tick={{ fontSize: 11 }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis
                yAxisId="left"
                tickFormatter={formatAxisAmount}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11 }}
                domain={[0, 100]}
              />
              <Tooltip
                formatter={(value, name) => {
                  const v = typeof value === 'number' ? value : 0
                  if (name === 'Эффективность') return `${v.toFixed(1)}%`
                  return formatTooltipAmount(v)
                }}
                labelFormatter={dateTickFormatter}
              />
              <Legend />
              <Bar yAxisId="left" dataKey="principal" name="Тело" fill="#52c41a" />
              <Bar yAxisId="left" dataKey="interest" name="Проценты" fill="#faad14" />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="efficiency"
                name="Эффективность"
                stroke="#1890ff"
                strokeWidth={3}
                dot={{ r: 4 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Organization Efficiency Chart */}
      <Card
        title="Эффективность по организациям"
        extra={<Text type="secondary">Доля погашения тела в общих платежах</Text>}
        style={{ marginBottom: 24 }}
      >
        <div style={{ height: 400 }}>
          {orgEfficiency.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={orgEfficiency} layout="vertical" margin={{ left: 20, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={150}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip
                  formatter={(value, name) => {
                    const v = typeof value === 'number' ? value : 0
                    if (name === 'Эффективность') return `${v.toFixed(1)}%`
                    return formatTooltipAmount(v)
                  }}
                />
                <Legend />
                <Bar dataKey="efficiency" name="Эффективность" fill="#1890ff">
                  {orgEfficiency.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.efficiency > 50 ? '#52c41a' : '#faad14'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Empty description="Нет данных" />
          )}
        </div>
      </Card>

      {/* Charts Row */}
      <Row gutter={[16, 16]}>
        {/* Debt Ratio Chart */}
        <Col xs={24} lg={12}>
          <Card
            title="Долговая нагрузка"
            extra={<Text type="secondary">Остаток долга к полученному</Text>}
          >
            <div style={{ height: 350 }}>
              {orgEfficiency.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={orgEfficiency}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 10 }}
                      angle={-45}
                      textAnchor="end"
                      height={100}
                    />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(value: number | undefined) => `${(value ?? 0).toFixed(1)}%`} />
                    <Bar dataKey="debtRatio" name="Долговая нагрузка">
                      {orgEfficiency.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.debtRatio < 30 ? '#52c41a' : entry.debtRatio < 60 ? '#faad14' : '#ff4d4f'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Empty description="Нет данных" />
              )}
            </div>
          </Card>
        </Col>

        {/* Summary Table */}
        <Col xs={24} lg={12}>
          <Card
            title="Сводка по организациям"
            extra={<Text type="secondary">Детальные показатели</Text>}
          >
            <Table
              columns={columns}
              dataSource={orgEfficiency.slice(0, 10)}
              rowKey="name"
              pagination={false}
              size="small"
              locale={{ emptyText: <Empty description="Нет данных" /> }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
