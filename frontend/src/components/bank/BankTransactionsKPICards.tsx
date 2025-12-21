import React from 'react'
import { Row, Col, Card, Statistic, Progress, Typography } from 'antd'
import {
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  TransactionOutlined,
  RobotOutlined,
  SyncOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import type { BankTransactionKPIs } from '../../types/bankTransaction'

const { Text } = Typography

interface Props {
  kpis: BankTransactionKPIs
  loading?: boolean
}

const BankTransactionsKPICards: React.FC<Props> = ({ kpis, loading }) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatPercent = (value: number | undefined) => {
    if (value === undefined || value === null) return null
    const isPositive = value >= 0
    const icon = isPositive ? <RiseOutlined /> : <FallOutlined />
    const color = isPositive ? '#3f8600' : '#cf1322'
    return (
      <Text style={{ fontSize: 12, color }}>
        {icon} {Math.abs(value).toFixed(1)}%
      </Text>
    )
  }

  return (
    <>
      {/* Financial Metrics Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="💰 Общий расход (DEBIT)"
              value={kpis.total_debit_amount}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={<DollarOutlined style={{ color: '#cf1322' }} />}
              valueStyle={{ color: '#cf1322' }}
            />
            {kpis.debit_change_percent !== undefined && (
              <div style={{ marginTop: 8 }}>
                {formatPercent(kpis.debit_change_percent)} vs предыдущий период
              </div>
            )}
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="💵 Общий приход (CREDIT)"
              value={kpis.total_credit_amount}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={<DollarOutlined style={{ color: '#3f8600' }} />}
              valueStyle={{ color: '#3f8600' }}
            />
            {kpis.credit_change_percent !== undefined && (
              <div style={{ marginTop: 8 }}>
                {formatPercent(kpis.credit_change_percent)} vs предыдущий период
              </div>
            )}
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="📊 Чистый поток"
              value={kpis.net_flow}
              formatter={(value) => formatCurrency(Number(value))}
              valueStyle={{ color: kpis.net_flow >= 0 ? '#3f8600' : '#cf1322' }}
            />
            {kpis.net_flow_change_percent !== undefined && (
              <div style={{ marginTop: 8 }}>
                {formatPercent(kpis.net_flow_change_percent)} vs предыдущий период
              </div>
            )}
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="📈 Количество транзакций"
              value={kpis.total_transactions}
              prefix={<TransactionOutlined />}
            />
            {kpis.transactions_change !== undefined && (
              <div style={{ marginTop: 8 }}>
                <Text style={{ fontSize: 12 }}>
                  {kpis.transactions_change > 0 ? '+' : ''}
                  {kpis.transactions_change} vs предыдущий период
                </Text>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Status Distribution Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} lg={4}>
          <Card loading={loading} size="small">
            <Statistic
              title="🆕 NEW"
              value={kpis.new_count}
              suffix={<Text type="secondary">({(kpis.new_percent ?? 0).toFixed(1)}%)</Text>}
              valueStyle={{ fontSize: 20 }}
            />
            <Progress
              percent={kpis.new_percent ?? 0}
              showInfo={false}
              strokeColor="#1890ff"
              size="small"
            />
          </Card>
        </Col>

        <Col xs={12} sm={8} lg={4}>
          <Card loading={loading} size="small">
            <Statistic
              title="📋 CATEGORIZED"
              value={kpis.categorized_count}
              suffix={<Text type="secondary">({(kpis.categorized_percent ?? 0).toFixed(1)}%)</Text>}
              valueStyle={{ fontSize: 20 }}
            />
            <Progress
              percent={kpis.categorized_percent ?? 0}
              showInfo={false}
              strokeColor="#52c41a"
              size="small"
            />
          </Card>
        </Col>

        <Col xs={12} sm={8} lg={4}>
          <Card loading={loading} size="small">
            <Statistic
              title="🔗 MATCHED"
              value={kpis.matched_count}
              suffix={<Text type="secondary">({(kpis.matched_percent ?? 0).toFixed(1)}%)</Text>}
              valueStyle={{ fontSize: 20 }}
            />
            <Progress
              percent={kpis.matched_percent ?? 0}
              showInfo={false}
              strokeColor="#722ed1"
              size="small"
            />
          </Card>
        </Col>

        <Col xs={12} sm={8} lg={4}>
          <Card loading={loading} size="small">
            <Statistic
              title="✅ APPROVED"
              value={kpis.approved_count}
              suffix={<Text type="secondary">({(kpis.approved_percent ?? 0).toFixed(1)}%)</Text>}
              valueStyle={{ fontSize: 20 }}
            />
            <Progress
              percent={kpis.approved_percent ?? 0}
              showInfo={false}
              strokeColor="#389e0d"
              size="small"
            />
          </Card>
        </Col>

        <Col xs={12} sm={8} lg={4}>
          <Card loading={loading} size="small">
            <Statistic
              title="⚠️ NEEDS_REVIEW"
              value={kpis.needs_review_count}
              suffix={<Text type="secondary">({(kpis.needs_review_percent ?? 0).toFixed(1)}%)</Text>}
              valueStyle={{ fontSize: 20 }}
            />
            <Progress
              percent={kpis.needs_review_percent ?? 0}
              showInfo={false}
              strokeColor="#fa8c16"
              size="small"
            />
          </Card>
        </Col>

        <Col xs={12} sm={8} lg={4}>
          <Card loading={loading} size="small">
            <Statistic
              title="🚫 IGNORED"
              value={kpis.ignored_count}
              suffix={<Text type="secondary">({(kpis.ignored_percent ?? 0).toFixed(1)}%)</Text>}
              valueStyle={{ fontSize: 20 }}
            />
            <Progress
              percent={kpis.ignored_percent ?? 0}
              showInfo={false}
              strokeColor="#d9d9d9"
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* AI Performance Row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card loading={loading}>
            <Statistic
              title="🤖 Средняя уверенность AI"
              value={kpis.avg_category_confidence ? (kpis.avg_category_confidence * 100).toFixed(1) : 0}
              suffix="%"
              prefix={<RobotOutlined />}
              valueStyle={{ color: kpis.avg_category_confidence && kpis.avg_category_confidence >= 0.9 ? '#3f8600' : '#faad14' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={8}>
          <Card loading={loading}>
            <Statistic
              title="🎯 Авто-категоризированные"
              value={kpis.auto_categorized_count}
              suffix={<Text type="secondary">({(kpis.auto_categorized_percent ?? 0).toFixed(1)}%)</Text>}
              prefix={<CheckCircleOutlined />}
            />
            <Progress
              percent={kpis.auto_categorized_percent ?? 0}
              showInfo={false}
              strokeColor="#52c41a"
            />
          </Card>
        </Col>

        <Col xs={24} sm={8}>
          <Card loading={loading}>
            <Statistic
              title="🔄 Регулярные платежи"
              value={kpis.regular_payments_count}
              suffix={<Text type="secondary">({(kpis.regular_payments_percent ?? 0).toFixed(1)}%)</Text>}
              prefix={<SyncOutlined />}
            />
            <Progress
              percent={kpis.regular_payments_percent ?? 0}
              showInfo={false}
              strokeColor="#1890ff"
            />
          </Card>
        </Col>
      </Row>
    </>
  )
}

export default BankTransactionsKPICards
