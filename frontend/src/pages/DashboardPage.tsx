import { Card, Row, Col, Statistic, Typography } from 'antd'
import {
  BankOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { getTransactionStats } from '../api/bankTransactions'

const { Title } = Typography

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['transaction-stats'],
    queryFn: () => getTransactionStats({}),
  })

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        Дашборд
      </Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={isLoading}>
            <Statistic
              title="Всего операций"
              value={stats?.total || 0}
              prefix={<BankOutlined />}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card loading={isLoading}>
            <Statistic
              title="Новые"
              value={stats?.new || 0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card loading={isLoading}>
            <Statistic
              title="Категоризированы"
              value={stats?.categorized || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card loading={isLoading}>
            <Statistic
              title="Требуют проверки"
              value={stats?.needs_review || 0}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12}>
          <Card loading={isLoading}>
            <Statistic
              title="Расходы (DEBIT)"
              value={stats?.total_debit || 0}
              prefix={<ArrowDownOutlined />}
              precision={2}
              suffix="₽"
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12}>
          <Card loading={isLoading}>
            <Statistic
              title="Поступления (CREDIT)"
              value={stats?.total_credit || 0}
              prefix={<ArrowUpOutlined />}
              precision={2}
              suffix="₽"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
