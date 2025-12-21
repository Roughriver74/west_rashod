import React from 'react'
import { Card, Empty, Spin, Row, Col, Table, Tag, Progress } from 'antd'
import {
  FunnelChart,
  Funnel,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import type { ProcessingFunnelData, AIPerformanceData, LowConfidenceItem } from '../../types/bankTransaction'

interface Props {
  processingFunnel: ProcessingFunnelData
  aiPerformance: AIPerformanceData
  lowConfidenceItems: LowConfidenceItem[]
  loading?: boolean
}

const ProcessingEfficiencyChart: React.FC<Props> = ({
  processingFunnel,
  aiPerformance,
  lowConfidenceItems,
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU')
  }

  const STATUS_NAMES: Record<string, string> = {
    NEW: 'Новые',
    CATEGORIZED: 'Категоризированные',
    MATCHED: 'Связанные',
    APPROVED: 'Утверждённые',
    NEEDS_REVIEW: 'Требуют проверки',
    IGNORED: 'Проигнорированные',
  }

  const STATUS_COLORS: Record<string, string> = {
    NEW: '#1890ff',
    CATEGORIZED: '#52c41a',
    MATCHED: '#722ed1',
    APPROVED: '#389e0d',
    NEEDS_REVIEW: '#fa8c16',
    IGNORED: '#d9d9d9',
  }

  const CONFIDENCE_COLORS = ['#52c41a', '#1890ff', '#faad14', '#ff4d4f']

  if (loading) {
    return (
      <Card title="Эффективность обработки">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  // Prepare funnel data
  const funnelData = processingFunnel.stages
    .filter(stage => stage.count > 0)
    .map(stage => ({
      name: STATUS_NAMES[stage.status] || stage.status,
      value: stage.count,
      amount: Number(stage.amount),
      percent: stage.percent_of_total,
      fill: STATUS_COLORS[stage.status] || '#d9d9d9',
    }))

  // Prepare AI confidence distribution
  const confidenceData = aiPerformance.confidence_distribution.map((bracket, index) => ({
    name: bracket.bracket,
    value: bracket.count,
    amount: Number(bracket.total_amount),
    percent: bracket.percent_of_total,
    fill: CONFIDENCE_COLORS[index] || '#d9d9d9',
  }))

  // Low confidence table columns
  const lowConfidenceColumns = [
    {
      title: 'Дата',
      dataIndex: 'transaction_date',
      key: 'transaction_date',
      width: '10%',
      render: (date: string) => formatDate(date),
    },
    {
      title: 'Контрагент',
      dataIndex: 'counterparty_name',
      key: 'counterparty_name',
      width: '20%',
    },
    {
      title: 'Назначение платежа',
      dataIndex: 'payment_purpose',
      key: 'payment_purpose',
      width: '30%',
      render: (text: string | undefined) => text || '-',
      ellipsis: true,
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      key: 'amount',
      align: 'right' as const,
      width: '12%',
      render: (value: number) => formatCurrency(value),
    },
    {
      title: 'Предложенная категория',
      dataIndex: 'suggested_category_name',
      key: 'suggested_category_name',
      width: '15%',
      render: (text: string | undefined) => text || '-',
    },
    {
      title: 'Уверенность',
      dataIndex: 'category_confidence',
      key: 'category_confidence',
      align: 'center' as const,
      width: '13%',
      render: (value: number) => (
        <div>
          <Progress
            percent={value * 100}
            size="small"
            strokeColor={value >= 0.7 ? '#52c41a' : value >= 0.5 ? '#faad14' : '#ff4d4f'}
            format={(percent) => `${percent?.toFixed(0)}%`}
          />
        </div>
      ),
    },
  ]

  return (
    <Card title="Эффективность обработки и AI">
      <Row gutter={[24, 24]}>
        {/* Processing Funnel */}
        <Col xs={24} lg={12}>
          <h4 style={{ marginBottom: 16 }}>Воронка обработки транзакций</h4>
          <ResponsiveContainer width="100%" height={400}>
            <FunnelChart>
              <Tooltip
                formatter={(value: number, name: string, props: any) => {
                  return [
                    `${value.toLocaleString('ru-RU')} транзакций (${props.payload.percent.toFixed(1)}%)`,
                    name
                  ]
                }}
              />
              <Funnel
                dataKey="value"
                data={funnelData}
                isAnimationActive
              >
                <LabelList
                  position="right"
                  fill="#000"
                  stroke="none"
                  dataKey="name"
                />
              </Funnel>
            </FunnelChart>
          </ResponsiveContainer>

          {/* Funnel Summary */}
          <div style={{ marginTop: 16, padding: 16, background: '#f0f5ff', borderRadius: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>Конверсия в APPROVED</div>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#389e0d' }}>
                  {processingFunnel.conversion_rate_to_approved.toFixed(1)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>Всего транзакций</div>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                  {processingFunnel.total_count.toLocaleString('ru-RU')}
                </div>
              </div>
            </div>
          </div>
        </Col>

        {/* AI Performance */}
        <Col xs={24} lg={12}>
          <h4 style={{ marginBottom: 16 }}>Распределение уверенности AI</h4>
          <ResponsiveContainer width="100%" height={400}>
            <PieChart>
              <Pie
                data={confidenceData}
                cx="50%"
                cy="50%"
                labelLine={true}
                label={({ name, percent }) => `${name}: ${percent.toFixed(1)}%`}
                outerRadius={120}
                fill="#8884d8"
                dataKey="value"
              >
                {confidenceData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => `${value.toLocaleString('ru-RU')} транзакций`}
              />
            </PieChart>
          </ResponsiveContainer>

          {/* AI Summary */}
          <div style={{ marginTop: 16 }}>
            <Row gutter={16}>
              <Col span={12}>
                <div style={{ padding: 16, background: '#f6ffed', borderRadius: 8, textAlign: 'center' }}>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>Средняя уверенность</div>
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                    {(aiPerformance.avg_confidence * 100).toFixed(1)}%
                  </div>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ padding: 16, background: '#fff7e6', borderRadius: 8, textAlign: 'center' }}>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>Высокая уверенность</div>
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>
                    {aiPerformance.high_confidence_percent.toFixed(1)}%
                  </div>
                  <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                    {aiPerformance.high_confidence_count} транзакций
                  </div>
                </div>
              </Col>
            </Row>
          </div>
        </Col>

        {/* Low Confidence Items Table */}
        <Col xs={24}>
          <h4 style={{ marginTop: 24, marginBottom: 16 }}>
            Транзакции с низкой уверенностью ({'<'}70%)
            <Tag color="orange" style={{ marginLeft: 8 }}>
              {lowConfidenceItems.length} требуют проверки
            </Tag>
          </h4>
          {lowConfidenceItems.length > 0 ? (
            <Table
              columns={lowConfidenceColumns}
              dataSource={lowConfidenceItems}
              rowKey="transaction_id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `Всего: ${total}`,
              }}
              size="small"
              scroll={{ x: 1200 }}
            />
          ) : (
            <Empty description="Нет транзакций с низкой уверенностью" />
          )}
        </Col>
      </Row>
    </Card>
  )
}

export default ProcessingEfficiencyChart
