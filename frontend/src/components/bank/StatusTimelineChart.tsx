import React from 'react'
import { Card, Empty, Spin } from 'antd'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import dayjs from 'dayjs'
import type { StatusTimelinePoint } from '../../types/bankTransaction'

interface Props {
  data: StatusTimelinePoint[]
  loading?: boolean
}

const StatusTimelineChart: React.FC<Props> = ({ data, loading }) => {
  const chartData = data.map((item) => ({
    date: dayjs(item.date).format('DD.MM'),
    fullDate: dayjs(item.date).format('DD MMMM YYYY'),
    NEW: item.new_count,
    CATEGORIZED: item.categorized_count,
    MATCHED: item.matched_count,
    APPROVED: item.approved_count,
    NEEDS_REVIEW: item.needs_review_count,
    IGNORED: item.ignored_count,
  }))

  if (loading) {
    return (
      <Card title="Динамика статусов">
        <div style={{ minHeight: 320, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card title="Динамика статусов">
        <Empty description="Нет данных по статусам" />
      </Card>
    )
  }

  return (
    <Card title="Динамика статусов по дням">
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
          <Tooltip labelFormatter={(label, payload) => payload?.[0]?.payload?.fullDate || label} />
          <Legend />
          <Line dataKey="NEW" name="NEW" stroke="#1890ff" strokeWidth={2} dot={false} />
          <Line dataKey="CATEGORIZED" name="CATEGORIZED" stroke="#52c41a" strokeWidth={2} dot={false} />
          <Line dataKey="MATCHED" name="MATCHED" stroke="#722ed1" strokeWidth={2} dot={false} />
          <Line dataKey="APPROVED" name="APPROVED" stroke="#389e0d" strokeWidth={2} dot={false} />
          <Line dataKey="NEEDS_REVIEW" name="NEEDS_REVIEW" stroke="#fa8c16" strokeWidth={2} dot={false} />
          <Line dataKey="IGNORED" name="IGNORED" stroke="#bfbfbf" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}

export default StatusTimelineChart
