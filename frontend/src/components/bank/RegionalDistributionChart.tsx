import React from 'react'
import { Card, Empty, Spin, Row, Col } from 'antd'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'
import type { RegionalData, SourceDistribution } from '../../types/bankTransaction'

interface Props {
  regionalData: RegionalData[]
  sourceData: SourceDistribution[]
  loading?: boolean
}

const RegionalDistributionChart: React.FC<Props> = ({
  regionalData,
  sourceData,
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

  const REGION_NAMES: Record<string, string> = {
    MOSCOW: 'Москва',
    SPB: 'Санкт-Петербург',
    REGIONS: 'Регионы',
    FOREIGN: 'Заграница',
  }

  const REGION_COLORS: Record<string, string> = {
    MOSCOW: '#1890ff',
    SPB: '#52c41a',
    REGIONS: '#faad14',
    FOREIGN: '#722ed1',
  }

  const SOURCE_COLORS: Record<string, string> = {
    BANK: '#1890ff',
    CASH: '#52c41a',
  }

  if (loading) {
    return (
      <Card title="География и источники платежей">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!regionalData || regionalData.length === 0) {
    return (
      <Card title="География и источники платежей">
        <Empty description="Нет данных для отображения" />
      </Card>
    )
  }

  // Prepare regional data
  const regionalChartData = regionalData.map((item) => ({
    name: REGION_NAMES[item.region] || item.region,
    region: item.region,
    value: Number(item.total_amount),
    count: item.transaction_count,
    percent: item.percent_of_total,
  }))

  // Prepare source distribution by month
  const sourceByMonth: Record<string, any> = {}
  sourceData.forEach((item) => {
    const key = item.month_name
    if (!sourceByMonth[key]) {
      sourceByMonth[key] = {
        month: key,
        BANK: 0,
        CASH: 0,
      }
    }
    sourceByMonth[key][item.payment_source] = Number(item.total_amount)
  })
  const sourceChartData = Object.values(sourceByMonth)

  return (
    <Card title="География и источники платежей">
      <Row gutter={[24, 24]}>
        {/* Regional Distribution Pie Chart */}
        <Col xs={24} lg={12}>
          <h4 style={{ marginBottom: 16 }}>Распределение по регионам</h4>
          {regionalChartData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={regionalChartData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    label={({ name, percent }) => `${name}: ${percent.toFixed(1)}%`}
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {regionalChartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={REGION_COLORS[entry.region] || '#d9d9d9'}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                  />
                </PieChart>
              </ResponsiveContainer>

              {/* Regional Legend with details */}
              <div style={{ marginTop: 16 }}>
                {regionalChartData.map((item, index) => (
                  <div
                    key={index}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '8px 0',
                      borderBottom: '1px solid #f0f0f0',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <div
                        style={{
                          width: 12,
                          height: 12,
                          backgroundColor: REGION_COLORS[item.region] || '#d9d9d9',
                          marginRight: 8,
                          borderRadius: 2,
                        }}
                      />
                      <span style={{ fontSize: 13, fontWeight: 500 }}>{item.name}</span>
                    </div>
                    <div style={{ fontSize: 13 }}>
                      <span style={{ color: '#1890ff', fontWeight: 'bold' }}>
                        {formatCurrency(item.value)}
                      </span>
                      <span style={{ color: '#8c8c8c', marginLeft: 8 }}>
                        ({item.count} транзакций)
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <Empty description="Нет региональных данных" />
          )}
        </Col>

        {/* Payment Source Distribution by Month */}
        <Col xs={24} lg={12}>
          <h4 style={{ marginBottom: 16 }}>Банк vs Касса по месяцам</h4>
          {sourceChartData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart
                  data={sourceChartData}
                  margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 11 }}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis tickFormatter={formatCurrency} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  <Legend wrapperStyle={{ paddingTop: 20 }} />
                  <Bar dataKey="BANK" name="Банк" fill={SOURCE_COLORS.BANK} stackId="a" />
                  <Bar dataKey="CASH" name="Касса" fill={SOURCE_COLORS.CASH} stackId="a" />
                </BarChart>
              </ResponsiveContainer>

              {/* Source Summary */}
              <div style={{ marginTop: 16, display: 'flex', gap: 16, justifyContent: 'center' }}>
                <div style={{ textAlign: 'center', padding: 12, background: '#f0f5ff', borderRadius: 8, flex: 1 }}>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>Банк</div>
                  <div style={{ fontSize: 18, fontWeight: 'bold', color: SOURCE_COLORS.BANK }}>
                    {formatCurrency(
                      sourceData
                        .filter(s => s.payment_source === 'BANK')
                        .reduce((sum, s) => sum + Number(s.total_amount), 0)
                    )}
                  </div>
                  <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                    {sourceData
                      .filter(s => s.payment_source === 'BANK')
                      .reduce((sum, s) => sum + s.transaction_count, 0).toLocaleString('ru-RU')} транзакций
                  </div>
                </div>
                <div style={{ textAlign: 'center', padding: 12, background: '#f6ffed', borderRadius: 8, flex: 1 }}>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>Касса</div>
                  <div style={{ fontSize: 18, fontWeight: 'bold', color: SOURCE_COLORS.CASH }}>
                    {formatCurrency(
                      sourceData
                        .filter(s => s.payment_source === 'CASH')
                        .reduce((sum, s) => sum + Number(s.total_amount), 0)
                    )}
                  </div>
                  <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                    {sourceData
                      .filter(s => s.payment_source === 'CASH')
                      .reduce((sum, s) => sum + s.transaction_count, 0).toLocaleString('ru-RU')} транзакций
                  </div>
                </div>
              </div>
            </>
          ) : (
            <Empty description="Нет данных по источникам" />
          )}
        </Col>
      </Row>
    </Card>
  )
}

export default RegionalDistributionChart
