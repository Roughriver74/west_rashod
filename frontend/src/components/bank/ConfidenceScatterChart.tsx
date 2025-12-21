import React, { useMemo } from 'react'
import { Card, Empty, Spin, Table, Tag } from 'antd'
import {
  ResponsiveContainer,
  ScatterChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Scatter,
  Legend,
} from 'recharts'
import type { ConfidenceScatterPoint } from '../../types/bankTransaction'
import { BankTransactionType } from '../../types/bankTransaction'
import dayjs from 'dayjs'

interface Props {
  data: ConfidenceScatterPoint[]
  loading?: boolean
}

const ConfidenceScatterChart: React.FC<Props> = ({ data, loading }) => {
  const [debitPoints, creditPoints] = useMemo(() => {
    const debit: ConfidenceScatterPoint[] = []
    const credit: ConfidenceScatterPoint[] = []
    data.forEach((point) => {
      if (point.transaction_type === BankTransactionType.DEBIT) {
        debit.push(point)
      } else {
        credit.push(point)
      }
    })
    return [debit, credit]
  }, [data])

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0,
      notation: 'compact',
      compactDisplay: 'short',
    }).format(value)

  const columns = [
    {
      title: 'Дата',
      dataIndex: 'transaction_date',
      key: 'transaction_date',
      render: (value: string) => dayjs(value).format('DD.MM.YYYY'),
    },
    {
      title: 'Контрагент',
      dataIndex: 'counterparty_name',
      key: 'counterparty_name',
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      key: 'amount',
      align: 'right' as const,
      render: (value: number) => formatCurrency(value),
    },
    {
      title: 'Уверенность',
      dataIndex: 'category_confidence',
      key: 'category_confidence',
      align: 'right' as const,
      render: (value?: number) =>
        value !== undefined ? `${(value * 100).toFixed(1)}%` : '—',
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (value: string) => <Tag>{value}</Tag>,
    },
  ]

  if (loading) {
    return (
      <Card title="Связь суммы и уверенности AI">
        <div style={{ minHeight: 320, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card title="Связь суммы и уверенности AI">
        <Empty description="Нет транзакций с уверенностью AI" />
      </Card>
    )
  }

  return (
    <Card title="Связь суммы и уверенности AI">
      <ResponsiveContainer width="100%" height={360}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
          <CartesianGrid />
          <XAxis
            type="number"
            dataKey="amount"
            name="Сумма"
            tickFormatter={(value) => formatCurrency(value)}
          />
          <YAxis
            type="number"
            dataKey="category_confidence"
            name="Уверенность"
            domain={[0, 1]}
            tickFormatter={(value) => `${Math.round(value * 100)}%`}
          />
          <Tooltip
            formatter={(value: any, name: string) => {
              if (name === 'Уверенность') {
                return [`${(value * 100).toFixed(1)}%`, name]
              }
              return [formatCurrency(Number(value)), name]
            }}
            labelFormatter={() => ''}
          />
          <Legend />
          <Scatter
            name="Расходы"
            data={debitPoints}
            fill="#ff7875"
            shape="circle"
            line={{ strokeDasharray: '3 3' }}
          />
          <Scatter name="Приходы" data={creditPoints} fill="#52c41a" shape="triangle" />
        </ScatterChart>
      </ResponsiveContainer>
      <div style={{ marginTop: 24 }}>
        <Table
          columns={columns}
          dataSource={data.slice(0, 20)}
          rowKey={(record) => record.transaction_id}
          size="small"
          pagination={false}
        />
      </div>
    </Card>
  )
}

export default ConfidenceScatterChart
