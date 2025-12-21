import React from 'react'
import { Card, Empty, Spin } from 'antd'
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { MonthlyFlowData } from '../../types/bankTransaction'

interface Props {
  data: MonthlyFlowData[]
  loading?: boolean
  title?: string
}

const CashFlowChart: React.FC<Props> = ({ data, loading, title = 'Помесячный денежный поток' }) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0,
      notation: 'compact',
      compactDisplay: 'short',
    }).format(value)
  }

  // Transform data for chart
  const chartData = data.map((item) => ({
    month: item.month_name,
    'Расход (DEBIT)': Number(item.debit_amount),
    'Приход (CREDIT)': Number(item.credit_amount),
    'Чистый поток': Number(item.net_flow),
  }))

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

  return (
    <Card title={title}>
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12 }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={formatCurrency}
          />
          <Tooltip
            formatter={(value: number | undefined) => value !== undefined ? formatCurrency(value) : ''}
            contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)' }}
          />
          <Legend
            wrapperStyle={{ paddingTop: 20 }}
            iconType="square"
          />
          <Bar
            dataKey="Расход (DEBIT)"
            fill="#ff4d4f"
            name="Расход"
            radius={[4, 4, 0, 0]}
          />
          <Bar
            dataKey="Приход (CREDIT)"
            fill="#52c41a"
            name="Приход"
            radius={[4, 4, 0, 0]}
          />
          <Line
            type="monotone"
            dataKey="Чистый поток"
            stroke="#1890ff"
            strokeWidth={3}
            name="Чистый поток"
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Summary statistics below chart */}
      <div style={{ marginTop: 24, display: 'flex', gap: 32, justifyContent: 'center', flexWrap: 'wrap' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: '#8c8c8c' }}>Всего транзакций</div>
          <div style={{ fontSize: 16, fontWeight: 'bold' }}>
            {data.reduce((sum, item) => sum + item.transaction_count, 0).toLocaleString('ru-RU')}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 12, color: '#8c8c8c' }}>Средняя уверенность AI</div>
          <div style={{ fontSize: 16, fontWeight: 'bold' }}>
            {data.filter(item => item.avg_confidence).length > 0
              ? ((data.reduce((sum, item) => sum + (item.avg_confidence || 0), 0) /
                  data.filter(item => item.avg_confidence).length) * 100).toFixed(1) + '%'
              : 'N/A'}
          </div>
        </div>
      </div>
    </Card>
  )
}

export default CashFlowChart
