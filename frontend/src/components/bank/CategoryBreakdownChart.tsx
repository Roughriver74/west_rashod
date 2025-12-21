import React from 'react'
import { Card, Empty, Spin, Row, Col, Table, Tag } from 'antd'
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { CategoryBreakdown } from '../../types/bankTransaction'

interface Props {
  topCategories: CategoryBreakdown[]
  categoryTypeDistribution: CategoryBreakdown[]
  loading?: boolean
}

const CategoryBreakdownChart: React.FC<Props> = ({
  topCategories,
  categoryTypeDistribution,
  loading,
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

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1', '#d084d1']
  const TYPE_COLORS: Record<string, string> = {
    OPEX: '#1890ff',
    CAPEX: '#52c41a',
    TAX: '#faad14',
    OTHER: '#d9d9d9',
  }

  if (loading) {
    return (
      <Card title="Breakdown по категориям">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!topCategories || topCategories.length === 0) {
    return (
      <Card title="Breakdown по категориям">
        <Empty description="Нет данных для отображения" />
      </Card>
    )
  }

  const barChartData = topCategories.map((item) => ({
    name: item.category_name.length > 25 ? item.category_name.substring(0, 25) + '...' : item.category_name,
    fullName: item.category_name,
    'Сумма': Number(item.total_amount),
    'Количество': item.transaction_count,
  }))

  const pieChartData = categoryTypeDistribution.map((item) => ({
    name: item.category_name,
    value: Number(item.total_amount),
    count: item.transaction_count,
    percent: item.percent_of_total,
  }))

  const columns = [
    {
      title: 'Категория',
      dataIndex: 'category_name',
      key: 'category_name',
      width: '30%',
      render: (text: string, record: CategoryBreakdown) => (
        <>
          {text}
          {record.category_type && (
            <Tag
              color={TYPE_COLORS[record.category_type] || 'default'}
              style={{ marginLeft: 8 }}
            >
              {record.category_type}
            </Tag>
          )}
        </>
      ),
    },
    {
      title: 'Количество',
      dataIndex: 'transaction_count',
      key: 'transaction_count',
      align: 'right' as const,
      render: (value: number) => value.toLocaleString('ru-RU'),
    },
    {
      title: 'Сумма',
      dataIndex: 'total_amount',
      key: 'total_amount',
      align: 'right' as const,
      render: (value: number) => formatCurrency(value),
    },
    {
      title: 'Средняя сумма',
      dataIndex: 'avg_amount',
      key: 'avg_amount',
      align: 'right' as const,
      render: (value: number) => formatCurrency(value),
    },
    {
      title: 'AI уверенность',
      dataIndex: 'avg_confidence',
      key: 'avg_confidence',
      align: 'right' as const,
      render: (value: number | undefined) =>
        value !== null && value !== undefined ? `${(value * 100).toFixed(1)}%` : 'N/A',
    },
    {
      title: '% от общей суммы',
      dataIndex: 'percent_of_total',
      key: 'percent_of_total',
      align: 'right' as const,
      render: (value: number) => `${value.toFixed(1)}%`,
    },
  ]

  return (
    <Card title="Breakdown по категориям">
      <Row gutter={[24, 24]}>
        {/* Top 10 Categories Bar Chart */}
        <Col xs={24} lg={14}>
          <h4 style={{ marginBottom: 16 }}>Топ-10 категорий по объему</h4>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              data={barChartData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={formatCurrency} tick={{ fontSize: 11 }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={95} />
              <Tooltip
                formatter={(value: number, name: string) => {
                  if (name === 'Сумма') return formatCurrency(value)
                  return value
                }}
                labelFormatter={(label: string) => {
                  const item = barChartData.find(d => d.name === label)
                  return item?.fullName || label
                }}
              />
              <Legend />
              <Bar dataKey="Сумма" fill="#1890ff" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Col>

        {/* Category Type Distribution Pie Chart */}
        <Col xs={24} lg={10}>
          <h4 style={{ marginBottom: 16 }}>Распределение по типам категорий</h4>
          <ResponsiveContainer width="100%" height={400}>
            <PieChart>
              <Pie
                data={pieChartData}
                cx="50%"
                cy="50%"
                labelLine={true}
                label={({ name, percent }) => `${name}: ${(percent).toFixed(1)}%`}
                outerRadius={120}
                fill="#8884d8"
                dataKey="value"
              >
                {pieChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={TYPE_COLORS[entry.name] || COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => formatCurrency(value)}
              />
            </PieChart>
          </ResponsiveContainer>

          {/* Legend with counts */}
          <div style={{ marginTop: 16 }}>
            {pieChartData.map((item, index) => (
              <div
                key={index}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '4px 0',
                  borderBottom: '1px solid #f0f0f0',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <div
                    style={{
                      width: 12,
                      height: 12,
                      backgroundColor: TYPE_COLORS[item.name] || COLORS[index % COLORS.length],
                      marginRight: 8,
                      borderRadius: 2,
                    }}
                  />
                  <span style={{ fontSize: 13 }}>{item.name}</span>
                </div>
                <div style={{ fontSize: 13, color: '#8c8c8c' }}>
                  {item.count} транзакций
                </div>
              </div>
            ))}
          </div>
        </Col>

        {/* Detailed Table */}
        <Col xs={24}>
          <h4 style={{ marginTop: 16, marginBottom: 16 }}>Детальная информация</h4>
          <Table
            columns={columns}
            dataSource={topCategories}
            rowKey="category_id"
            pagination={false}
            size="small"
            scroll={{ x: 800 }}
          />
        </Col>
      </Row>
    </Card>
  )
}

export default CategoryBreakdownChart
