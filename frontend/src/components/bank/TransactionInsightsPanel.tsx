import React from 'react'
import { Card, Col, Empty, Row, Tag } from 'antd'
import type {
  MonthlyFlowData,
  CategoryBreakdown,
  CounterpartyBreakdown,
} from '../../types/bankTransaction'

interface TransactionInsightsPanelProps {
  monthlyFlow?: MonthlyFlowData[]
  topCategories?: CategoryBreakdown[]
  topCounterparties?: CounterpartyBreakdown[]
  loading?: boolean
}

type InsightItem = {
  key: string
  title: string
  icon: string
  main: string
  description: string
  extra?: string
  color?: string
}

const TransactionInsightsPanel: React.FC<TransactionInsightsPanelProps> = ({
  monthlyFlow = [],
  topCategories = [],
  topCounterparties = [],
  loading,
}) => {
  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0,
    }).format(value)

  const totalTransactions = monthlyFlow.reduce(
    (sum, item) => sum + (item.transaction_count || 0),
    0
  )

  const busiestMonth = monthlyFlow.reduce<MonthlyFlowData | undefined>(
    (best, item) =>
      !best || item.transaction_count > (best.transaction_count || 0) ? item : best,
    undefined
  )

  const maxDebitMonth = monthlyFlow.reduce<MonthlyFlowData | undefined>(
    (best, item) => (!best || item.debit_amount > best.debit_amount ? item : best),
    undefined
  )

  const maxCreditMonth = monthlyFlow.reduce<MonthlyFlowData | undefined>(
    (best, item) => (!best || item.credit_amount > best.credit_amount ? item : best),
    undefined
  )

  const topCategory = topCategories[0]
  const regularCounterparty =
    topCounterparties.find((item) => item.is_regular) || topCounterparties[0]

  const insights: InsightItem[] = [
    busiestMonth && {
      key: 'busiest-month',
      title: 'Самый активный месяц',
      icon: '📆',
      main: busiestMonth.month_name,
      description: `${busiestMonth.transaction_count.toLocaleString('ru-RU')} операций`,
      extra:
        totalTransactions > 0
          ? `Доля ${((busiestMonth.transaction_count / totalTransactions) * 100).toFixed(1)}%`
          : undefined,
      color: '#1890ff',
    },
    maxDebitMonth && {
      key: 'max-debit',
      title: 'Пиковый расход',
      icon: '💸',
      main: formatCurrency(maxDebitMonth.debit_amount),
      description: `Месяц: ${maxDebitMonth.month_name}`,
      extra: `Чистый поток ${formatCurrency(maxDebitMonth.net_flow)}`,
      color: '#cf1322',
    },
    maxCreditMonth && {
      key: 'max-credit',
      title: 'Пиковый приход',
      icon: '💰',
      main: formatCurrency(maxCreditMonth.credit_amount),
      description: `Месяц: ${maxCreditMonth.month_name}`,
      extra: `Чистый поток ${formatCurrency(maxCreditMonth.net_flow)}`,
      color: '#3f8600',
    },
    topCategory && {
      key: 'top-category',
      title: 'Лидирующая категория',
      icon: '🏷️',
      main: topCategory.category_name,
      description: formatCurrency(topCategory.total_amount),
      extra: `Средний чек ${formatCurrency(topCategory.avg_amount)}`,
      color: '#722ed1',
    },
    regularCounterparty && {
      key: 'top-counterparty',
      title: 'Ключевой контрагент',
      icon: '🤝',
      main: regularCounterparty.counterparty_name,
      description: `${regularCounterparty.transaction_count.toLocaleString('ru-RU')} операций`,
      extra: `Оборот ${formatCurrency(regularCounterparty.total_amount)}`,
      color: '#fa8c16',
    },
  ].filter(Boolean) as InsightItem[]

  const hasInsights = insights.length > 0

  return (
    <Card title="Ключевые инсайты" loading={loading}>
      {hasInsights ? (
        <Row gutter={[16, 16]}>
          {insights.map((item) => (
            <Col key={item.key} xs={24} sm={12} xl={6}>
              <div
                style={{
                  border: '1px solid #f0f0f0',
                  borderRadius: 12,
                  padding: 16,
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: '#8c8c8c' }}>
                    {item.icon} {item.title}
                  </span>
                  {item.extra && (
                    <Tag color={item.color || 'blue'}>{item.extra}</Tag>
                  )}
                </div>
                <div
                  style={{
                    fontSize: 20,
                    fontWeight: 600,
                    color: item.color || '#1f1f1f',
                  }}
                >
                  {item.main}
                </div>
                <div style={{ fontSize: 13, color: '#595959' }}>{item.description}</div>
              </div>
            </Col>
          ))}
        </Row>
      ) : (
        <Empty description="Недостаточно данных для расчёта инсайтов" />
      )}
    </Card>
  )
}

export default TransactionInsightsPanel
