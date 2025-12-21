import React, { useMemo } from 'react'
import { Card, Col, Empty, Row, Statistic, Tag } from 'antd'
import { ResponsiveTable } from '../common/ResponsiveTable'
import { CalendarOutlined, FieldTimeOutlined, FundOutlined } from '@ant-design/icons'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis} from 'recharts'
import dayjs from 'dayjs'
import type { RegularPaymentSummary } from '../../types/bankTransaction'

interface RegularPaymentsInsightsProps {
  data?: RegularPaymentSummary[]
  loading?: boolean
}

const RegularPaymentsInsights: React.FC<RegularPaymentsInsightsProps> = ({ data = [], loading }) => {
  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0}).format(value)

  const hasData = data.length > 0

  const summary = useMemo(() => {
    if (!hasData) {
      return {
        count: 0,
        avgAmount: 0,
        avgInterval: 0,
        avgPayments: 0}
    }

    const totalAmount = data.reduce((sum, item) => sum + Number(item.avg_amount), 0)
    const totalInterval = data.reduce((sum, item) => sum + (item.avg_days_between || 0), 0)
    const totalPayments = data.reduce((sum, item) => sum + (item.payment_count || 0), 0)

    return {
      count: data.length,
      avgAmount: totalAmount / data.length,
      avgInterval: totalInterval / data.length,
      avgPayments: totalPayments / data.length}
  }, [data, hasData])

  const chartData = useMemo(() => {
    return data
      .slice()
      .sort((a, b) => Number(b.avg_amount) - Number(a.avg_amount))
      .slice(0, 6)
      .map((item) => ({
        name: item.counterparty_name.length > 20
          ? `${item.counterparty_name.slice(0, 17)}...`
          : item.counterparty_name,
        fullName: item.counterparty_name,
        amount: Number(item.avg_amount),
        payments: item.payment_count}))
  }, [data])

  const columns = [
    {
      title: 'Контрагент',
      dataIndex: 'counterparty_name',
      key: 'counterparty_name',
      width: '20%',
      render: (text: string, record: RegularPaymentSummary) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          {record.counterparty_inn && (
            <Tag color="blue" style={{ marginTop: 4 }}>
              ИНН {record.counterparty_inn}
            </Tag>
          )}
        </div>
      )},
    {
      title: 'Категория',
      dataIndex: 'category_name',
      key: 'category_name',
      width: '18%'},
    {
      title: 'Avg сумма',
      dataIndex: 'avg_amount',
      key: 'avg_amount',
      align: 'right' as const,
      render: (value: number) => formatCurrency(value)},
    {
      title: 'Кол-во платежей',
      dataIndex: 'payment_count',
      key: 'payment_count',
      align: 'right' as const,
      render: (value: number) => value.toLocaleString('ru-RU')},
    {
      title: 'Интервал',
      dataIndex: 'avg_days_between',
      key: 'avg_days_between',
      align: 'right' as const,
      render: (value?: number) => (value ? `~${value.toFixed(0)} дней` : '—')},
    {
      title: 'Последний платёж',
      dataIndex: 'last_payment_date',
      key: 'last_payment_date',
      align: 'right' as const,
      render: (value: string) => dayjs(value).format('DD.MM.YYYY')},
    {
      title: 'Следующий ожидается',
      dataIndex: 'next_expected_date',
      key: 'next_expected_date',
      align: 'right' as const,
      render: (value?: string) => {
        if (!value) return '—'
        const diff = dayjs(value).diff(dayjs(), 'day')
        let color: string = 'default'
        if (diff < 0) color = 'red'
        else if (diff <= 7) color = 'orange'
        else color = 'green'
        return (
          <Tag color={color}>
            {dayjs(value).format('DD.MM.YYYY')}
          </Tag>
        )
      }},
  ]

  return (
    <Card title="Регулярные платежи" loading={loading}>
      {hasData ? (
        <>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col xs={24} md={8}>
              <Statistic
                title="Количество шаблонов"
                value={summary.count}
                prefix={<FundOutlined />}
              />
            </Col>
            <Col xs={24} md={8}>
              <Statistic
                title="Средний чек"
                value={summary.avgAmount}
                formatter={(value) => formatCurrency(Number(value))}
                prefix={<CalendarOutlined />}
              />
            </Col>
            <Col xs={24} md={8}>
              <Statistic
                title="Средний интервал"
                value={
                  summary.avgInterval
                    ? `${summary.avgInterval.toFixed(0)} дней`
                    : '—'
                }
                prefix={<FieldTimeOutlined />}
              />
            </Col>
          </Row>

          <Row gutter={[24, 24]}>
            <Col xs={24} lg={10}>
              <h4 style={{ marginBottom: 12 }}>ТОП-6 по среднему чеку</h4>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={chartData}
                    layout="vertical"
                    margin={{ top: 10, right: 20, left: 20, bottom: 10 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" tickFormatter={(value) => formatCurrency(Number(value))} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 12 }}
                      width={120}
                    />
                    <RechartsTooltip
                      formatter={(value: number, _name: string, props: any) => [
                        formatCurrency(Number(value)),
                        props.payload.fullName,
                      ]}
                    />
                    <Bar dataKey="amount" fill="#1890ff" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Empty description="Нет данных для диаграммы" />
              )}
            </Col>

            <Col xs={24} lg={14}>
              <h4 style={{ marginBottom: 12 }}>Детализация по контрагентам</h4>
              <ResponsiveTable
                columns={columns}
                dataSource={data}
                rowKey={(record) => `${record.counterparty_name}-${record.category_name}`}
                pagination={{
                  pageSize: 8,
                  showSizeChanger: false}}
                size="small"
                scroll={{ x: 900 }}
              />
            </Col>
          </Row>
        </>
      ) : (
        <Empty description="Регулярные платежи не найдены" />
      )}
    </Card>
  )
}

export default RegularPaymentsInsights
