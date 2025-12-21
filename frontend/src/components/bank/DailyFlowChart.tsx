import React, { useMemo } from 'react'
import { Card, Empty, Spin } from 'antd'
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type { DailyFlowData } from '../../types/bankTransaction'
import dayjs from 'dayjs'

interface Props {
  data: DailyFlowData[]
  loading?: boolean
  title?: string
}

const DailyFlowChart: React.FC<Props> = ({ data, loading, title = 'Ежедневный денежный поток' }) => {
  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0,
      notation: 'compact',
      compactDisplay: 'short',
    }).format(value)

  const chartData = useMemo(
    () =>
      data.map((item) => ({
        date: dayjs(item.date).format('DD.MM'),
        fullDate: dayjs(item.date).format('DD MMMM YYYY'),
        debit: Number(item.debit_amount),
        credit: Number(item.credit_amount),
        net: Number(item.net_flow),
        count: item.transaction_count,
      })),
    [data]
  )

  if (loading) {
    return (
      <Card title={title}>
        <div style={{ minHeight: 320, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card title={title}>
        <Empty description="Нет данных для выбранного периода" />
      </Card>
    )
  }

  return (
    <Card title={title}>
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={formatCurrency} tick={{ fontSize: 11 }} />
          <YAxis
            orientation="right"
            yAxisId={1}
            tick={{ fontSize: 11 }}
            tickFormatter={(value) => `${value}`}
            allowDecimals={false}
          />
          <Tooltip
            formatter={(value: number | undefined, name: string | undefined) => {
              if (value === undefined) return ''
              if (name === 'Транзакций') {
                return value
              }
              return formatCurrency(Number(value))
            }}
            labelFormatter={(label, payload) => payload?.[0]?.payload?.fullDate || label}
          />
          <Legend />
          <Bar dataKey="debit" name="Расход" fill="#ff7875" stackId="flow" />
          <Bar dataKey="credit" name="Приход" fill="#73d13d" stackId="flow" />
          <Line
            type="monotone"
            dataKey="net"
            name="Чистый поток"
            stroke="#1890ff"
            strokeWidth={3}
            dot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="count"
            name="Транзакций"
            stroke="#faad14"
            strokeDasharray="3 3"
            yAxisId={1}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </Card>
  )
}

export default DailyFlowChart
