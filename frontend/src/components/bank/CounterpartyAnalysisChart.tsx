import React from 'react'
import { Card, Empty, Spin, Table, Tag, Tooltip } from 'antd'
import { ClockCircleOutlined } from '@ant-design/icons'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { CounterpartyBreakdown } from '../../types/bankTransaction'

interface Props {
  data: CounterpartyBreakdown[]
  loading?: boolean
  title?: string
}

const CounterpartyAnalysisChart: React.FC<Props> = ({
  data,
  loading,
  title = 'Анализ контрагентов'
}) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0,
      notation: 'compact',
      compactDisplay: 'short',
    }).format(value)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU')
  }

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1', '#d084d1']

  if (loading) {
    return (
      <Card title={title}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card title={title}>
        <Empty description="Нет данных для отображения" />
      </Card>
    )
  }

  // Prepare data for bar chart (top 10)
  const chartData = data.slice(0, 10).map((item) => ({
    name: item.counterparty_name.length > 30
      ? item.counterparty_name.substring(0, 30) + '...'
      : item.counterparty_name,
    fullName: item.counterparty_name,
    'Сумма': Number(item.total_amount),
    'Количество': item.transaction_count,
    isRegular: item.is_regular,
  }))

  const columns = [
    {
      title: '№',
      key: 'index',
      width: 50,
      render: (_: any, __: any, index: number) => index + 1,
    },
    {
      title: 'Контрагент',
      dataIndex: 'counterparty_name',
      key: 'counterparty_name',
      width: '25%',
      render: (text: string, record: CounterpartyBreakdown) => (
        <>
          {text}
          {record.is_regular && (
            <Tooltip title="Регулярный контрагент">
              <Tag color="blue" icon={<ClockCircleOutlined />} style={{ marginLeft: 8 }}>
                Регулярный
              </Tag>
            </Tooltip>
          )}
        </>
      ),
    },
    {
      title: 'ИНН',
      dataIndex: 'counterparty_inn',
      key: 'counterparty_inn',
      width: '12%',
      render: (inn: string | undefined) => inn || '-',
    },
    {
      title: 'Количество транзакций',
      dataIndex: 'transaction_count',
      key: 'transaction_count',
      align: 'right' as const,
      width: '12%',
      render: (value: number) => value.toLocaleString('ru-RU'),
      sorter: (a: CounterpartyBreakdown, b: CounterpartyBreakdown) =>
        a.transaction_count - b.transaction_count,
    },
    {
      title: 'Общая сумма',
      dataIndex: 'total_amount',
      key: 'total_amount',
      align: 'right' as const,
      width: '13%',
      render: (value: number) => (
        <strong style={{ color: '#1890ff' }}>{formatCurrency(value)}</strong>
      ),
      sorter: (a: CounterpartyBreakdown, b: CounterpartyBreakdown) =>
        Number(a.total_amount) - Number(b.total_amount),
      defaultSortOrder: 'descend' as const,
    },
    {
      title: 'Средняя сумма',
      dataIndex: 'avg_amount',
      key: 'avg_amount',
      align: 'right' as const,
      width: '13%',
      render: (value: number) => formatCurrency(value),
      sorter: (a: CounterpartyBreakdown, b: CounterpartyBreakdown) =>
        Number(a.avg_amount) - Number(b.avg_amount),
    },
    {
      title: 'Период',
      key: 'period',
      width: '15%',
      render: (_: any, record: CounterpartyBreakdown) => (
        <div style={{ fontSize: 12 }}>
          <div>с {formatDate(record.first_transaction_date)}</div>
          <div style={{ color: '#8c8c8c' }}>
            по {formatDate(record.last_transaction_date)}
          </div>
        </div>
      ),
    },
  ]

  return (
    <Card title={title}>
      {/* Bar Chart - Top 10 Counterparties */}
      <div style={{ marginBottom: 32 }}>
        <h4 style={{ marginBottom: 16 }}>Топ-10 контрагентов по объему операций</h4>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 150, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" tickFormatter={formatCurrency} tick={{ fontSize: 11 }} />
            <YAxis
              dataKey="name"
              type="category"
              tick={{ fontSize: 11 }}
              width={145}
            />
            <RechartsTooltip
              formatter={(value: number | undefined, name: string | undefined) => {
                if (value === undefined) return ''
                if (name === 'Сумма') return formatCurrency(value)
                return value
              }}
              labelFormatter={(label: string) => {
                const item = chartData.find(d => d.name === label)
                return item?.fullName || label
              }}
            />
            <Legend />
            <Bar dataKey="Сумма" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.isRegular ? '#1890ff' : COLORS[index % COLORS.length]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Cards */}
      <div style={{ display: 'flex', gap: 24, marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{
          padding: 16,
          background: '#f0f5ff',
          borderRadius: 8,
          flex: '1 1 200px'
        }}>
          <div style={{ fontSize: 12, color: '#8c8c8c' }}>Всего контрагентов</div>
          <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
            {data.length}
          </div>
        </div>
        <div style={{
          padding: 16,
          background: '#f6ffed',
          borderRadius: 8,
          flex: '1 1 200px'
        }}>
          <div style={{ fontSize: 12, color: '#8c8c8c' }}>Регулярных контрагентов</div>
          <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
            {data.filter(c => c.is_regular).length}
            <span style={{ fontSize: 14, marginLeft: 8, color: '#8c8c8c' }}>
              ({((data.filter(c => c.is_regular).length / data.length) * 100).toFixed(1)}%)
            </span>
          </div>
        </div>
        <div style={{
          padding: 16,
          background: '#fff7e6',
          borderRadius: 8,
          flex: '1 1 200px'
        }}>
          <div style={{ fontSize: 12, color: '#8c8c8c' }}>Средняя сумма на контрагента</div>
          <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>
            {formatCurrency(
              data.reduce((sum, c) => sum + Number(c.total_amount), 0) / data.length
            )}
          </div>
        </div>
      </div>

      {/* Detailed Table */}
      <div>
        <h4 style={{ marginBottom: 16 }}>Полный список контрагентов</h4>
        <Table
          columns={columns}
          dataSource={data}
          rowKey={(record) => record.counterparty_inn || record.counterparty_name}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Всего: ${total} контрагентов`,
          }}
          size="small"
          scroll={{ x: 1000 }}
        />
      </div>
    </Card>
  )
}

export default CounterpartyAnalysisChart
