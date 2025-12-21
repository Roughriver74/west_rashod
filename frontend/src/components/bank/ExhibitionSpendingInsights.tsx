import React, { useMemo } from 'react'
import { Card, Col, Empty, List, Row, Statistic, Tag, Typography } from 'antd'
import { CalendarOutlined, EnvironmentOutlined } from '@ant-design/icons'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from 'recharts'
import dayjs from 'dayjs'
import type { ExhibitionData } from '../../types/bankTransaction'

const { Text } = Typography

interface ExhibitionSpendingInsightsProps {
  data?: ExhibitionData[]
  loading?: boolean
}

const ExhibitionSpendingInsights: React.FC<ExhibitionSpendingInsightsProps> = ({
  data = [],
  loading,
}) => {
  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0,
    }).format(value)

  const hasData = data.length > 0

  const aggregated = useMemo(() => {
    const map = new Map<
      string,
      { exhibition: string; total: number; count: number; latest: string }
    >()
    data.forEach((item) => {
      const current = map.get(item.exhibition)
      if (current) {
        current.total += Number(item.amount)
        current.count += 1
        if (dayjs(item.transaction_date).isAfter(dayjs(current.latest))) {
          current.latest = item.transaction_date
        }
      } else {
        map.set(item.exhibition, {
          exhibition: item.exhibition,
          total: Number(item.amount),
          count: 1,
          latest: item.transaction_date,
        })
      }
    })
    return Array.from(map.values()).sort((a, b) => b.total - a.total)
  }, [data])

  const chartData = aggregated.slice(0, 6).map((item) => ({
    name: item.exhibition.length > 28 ? `${item.exhibition.slice(0, 25)}...` : item.exhibition,
    fullName: item.exhibition,
    amount: item.total,
    latest: item.latest,
  }))

  const timelineItems = useMemo(() => {
    return data
      .slice()
      .sort(
        (a, b) =>
          dayjs(b.transaction_date).valueOf() - dayjs(a.transaction_date).valueOf()
      )
      .slice(0, 8)
  }, [data])

  const totalSpend = aggregated.reduce((sum, item) => sum + item.total, 0)

  return (
    <Card title="Активность по выставкам" loading={loading}>
      {hasData ? (
        <>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col xs={24} md={8}>
              <Statistic
                title="Всего выставок"
                value={aggregated.length}
                prefix={<EnvironmentOutlined />}
              />
            </Col>
            <Col xs={24} md={8}>
              <Statistic
                title="Совокупные затраты"
                value={totalSpend}
                formatter={(value) => formatCurrency(Number(value))}
                prefix={<CalendarOutlined />}
              />
            </Col>
            <Col xs={24} md={8}>
              <Statistic
                title="Последняя активность"
                value={
                  timelineItems[0]
                    ? dayjs(timelineItems[0].transaction_date).format('DD.MM.YYYY')
                    : '—'
                }
              />
            </Col>
          </Row>

          <Row gutter={[24, 24]}>
            <Col xs={24} lg={12}>
              <h4 style={{ marginBottom: 12 }}>ТОП-6 выставок по объему</h4>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart
                    data={chartData}
                    margin={{ top: 10, right: 20, left: 20, bottom: 10 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-20} />
                    <YAxis tickFormatter={(value) => formatCurrency(Number(value))} />
                    <RechartsTooltip
                      formatter={(value: number | undefined) =>
                        value !== undefined ? formatCurrency(Number(value)) : ''
                      }
                      labelFormatter={(label: string, payload) => {
                        const source = payload?.[0]?.payload
                        return `${source?.fullName || label} (последнее: ${dayjs(source?.latest).format(
                          'DD.MM.YYYY'
                        )})`
                      }}
                    />
                    <Bar dataKey="amount" fill="#13c2c2" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Empty description="Недостаточно данных для графика" />
              )}
            </Col>

            <Col xs={24} lg={12}>
              <h4 style={{ marginBottom: 12 }}>Недавние транзакции</h4>
              <List
                dataSource={timelineItems}
                renderItem={(item) => (
                  <List.Item key={item.transaction_id}>
                    <List.Item.Meta
                      title={
                        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap' }}>
                          <div>
                            <Text strong>{item.exhibition}</Text>
                            {item.category_name && (
                              <Tag color="purple" style={{ marginLeft: 8 }}>
                                {item.category_name}
                              </Tag>
                            )}
                          </div>
                          <Text style={{ color: '#8c8c8c' }}>
                            {dayjs(item.transaction_date).format('DD.MM.YYYY')}
                          </Text>
                        </div>
                      }
                      description={
                        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                          <div>
                            <Text style={{ color: '#595959' }}>{item.counterparty_name}</Text>
                          </div>
                          <Text strong>{formatCurrency(Number(item.amount))}</Text>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            </Col>
          </Row>
        </>
      ) : (
        <Empty description="Нет транзакций, связанных с выставками" />
      )}
    </Card>
  )
}

export default ExhibitionSpendingInsights
