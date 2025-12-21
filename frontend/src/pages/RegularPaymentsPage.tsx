import { useState } from 'react'
import {
  Card,
  Table,
  Typography,
  Space,
  Tag,
  Button,
  Statistic,
  Row,
  Col,
  message,
  Tooltip,
  Progress,
} from 'antd'
import {
  SyncOutlined,
  CalendarOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnsType } from 'antd/es/table'
import {
  getRegularPatterns,
  markRegularPayments,
  RegularPaymentPattern,
} from '../api/bankTransactions'

const { Title, Text } = Typography

const formatAmount = (value: number) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

const getFrequencyLabel = (pattern: RegularPaymentPattern): string => {
  if (pattern.is_monthly) return 'Ежемесячно'
  if (pattern.is_quarterly) return 'Ежеквартально'
  if (pattern.frequency_days <= 7) return 'Еженедельно'
  if (pattern.frequency_days <= 14) return 'Раз в 2 недели'
  return `Каждые ${pattern.frequency_days} дней`
}

const getFrequencyColor = (pattern: RegularPaymentPattern): string => {
  if (pattern.is_monthly) return 'blue'
  if (pattern.is_quarterly) return 'purple'
  if (pattern.frequency_days <= 7) return 'green'
  if (pattern.frequency_days <= 14) return 'cyan'
  return 'default'
}

export default function RegularPaymentsPage() {
  const queryClient = useQueryClient()
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['regular-patterns'],
    queryFn: getRegularPatterns,
  })

  const markMutation = useMutation({
    mutationFn: markRegularPayments,
    onSuccess: (result) => {
      message.success(result.message)
      queryClient.invalidateQueries({ queryKey: ['regular-patterns'] })
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
    },
    onError: () => {
      message.error('Ошибка при маркировке регулярных платежей')
    },
  })

  const columns: ColumnsType<RegularPaymentPattern> = [
    {
      title: 'Контрагент',
      key: 'counterparty',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.counterparty_name || 'Без названия'}</Text>
          {record.counterparty_inn && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              ИНН: {record.counterparty_inn}
            </Text>
          )}
        </Space>
      ),
      sorter: (a, b) => (a.counterparty_name || '').localeCompare(b.counterparty_name || ''),
    },
    {
      title: 'Категория',
      dataIndex: 'category_name',
      key: 'category_name',
      render: (value) => value ? <Tag color="blue">{value}</Tag> : <Tag>Без категории</Tag>,
    },
    {
      title: 'Средняя сумма',
      dataIndex: 'avg_amount',
      key: 'avg_amount',
      align: 'right',
      render: (value) => (
        <Text strong style={{ color: '#cf1322' }}>
          {formatAmount(value)}
        </Text>
      ),
      sorter: (a, b) => a.avg_amount - b.avg_amount,
    },
    {
      title: 'Периодичность',
      key: 'frequency',
      align: 'center',
      render: (_, record) => (
        <Tag color={getFrequencyColor(record)} icon={<CalendarOutlined />}>
          {getFrequencyLabel(record)}
        </Tag>
      ),
      filters: [
        { text: 'Ежемесячно', value: 'monthly' },
        { text: 'Ежеквартально', value: 'quarterly' },
        { text: 'Другое', value: 'other' },
      ],
      onFilter: (value, record) => {
        if (value === 'monthly') return record.is_monthly
        if (value === 'quarterly') return record.is_quarterly
        return !record.is_monthly && !record.is_quarterly
      },
    },
    {
      title: 'Интервал (дней)',
      dataIndex: 'frequency_days',
      key: 'frequency_days',
      align: 'center',
      render: (value) => <Text>{value}</Text>,
      sorter: (a, b) => a.frequency_days - b.frequency_days,
    },
    {
      title: 'Транзакций',
      dataIndex: 'transaction_count',
      key: 'transaction_count',
      align: 'center',
      render: (value) => (
        <Tooltip title={`Всего ${value} транзакций в паттерне`}>
          <Tag color="geekblue">{value}</Tag>
        </Tooltip>
      ),
      sorter: (a, b) => a.transaction_count - b.transaction_count,
    },
    {
      title: 'Последний платеж',
      dataIndex: 'last_payment_date',
      key: 'last_payment_date',
      render: (value) => {
        const date = new Date(value)
        return date.toLocaleDateString('ru-RU')
      },
      sorter: (a, b) => new Date(a.last_payment_date).getTime() - new Date(b.last_payment_date).getTime(),
    },
  ]

  const patterns = data?.patterns || []
  const totalMonthlyAmount = patterns
    .filter((p) => p.is_monthly)
    .reduce((sum, p) => sum + p.avg_amount, 0)

  const totalQuarterlyAmount = patterns
    .filter((p) => p.is_quarterly)
    .reduce((sum, p) => sum + p.avg_amount, 0)

  return (
    <div style={{ padding: 0 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={2} style={{ margin: 0 }}>
            <SyncOutlined /> Регулярные платежи
          </Title>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              Обновить
            </Button>
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => markMutation.mutate()}
              loading={markMutation.isPending}
            >
              Отметить транзакции
            </Button>
          </Space>
        </div>

        {/* Stats Cards */}
        <Row gutter={16}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Всего паттернов"
                value={data?.total_count || 0}
                prefix={<SyncOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Ежемесячных"
                value={data?.monthly_count || 0}
                valueStyle={{ color: '#1890ff' }}
                suffix={
                  <Text type="secondary" style={{ fontSize: 14 }}>
                    ({formatAmount(totalMonthlyAmount)}/мес)
                  </Text>
                }
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Ежеквартальных"
                value={data?.quarterly_count || 0}
                valueStyle={{ color: '#722ed1' }}
                suffix={
                  <Text type="secondary" style={{ fontSize: 14 }}>
                    ({formatAmount(totalQuarterlyAmount)}/кв)
                  </Text>
                }
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Других"
                value={data?.other_count || 0}
                valueStyle={{ color: '#595959' }}
              />
            </Card>
          </Col>
        </Row>

        {/* Distribution Progress */}
        {data && data.total_count > 0 && (
          <Card title="Распределение по периодичности">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text>Ежемесячные</Text>
                <Progress
                  percent={Math.round((data.monthly_count / data.total_count) * 100)}
                  strokeColor="#1890ff"
                  format={(percent) => `${percent}% (${data.monthly_count})`}
                />
              </div>
              <div>
                <Text>Ежеквартальные</Text>
                <Progress
                  percent={Math.round((data.quarterly_count / data.total_count) * 100)}
                  strokeColor="#722ed1"
                  format={(percent) => `${percent}% (${data.quarterly_count})`}
                />
              </div>
              <div>
                <Text>Другие</Text>
                <Progress
                  percent={Math.round((data.other_count / data.total_count) * 100)}
                  strokeColor="#595959"
                  format={(percent) => `${percent}% (${data.other_count})`}
                />
              </div>
            </Space>
          </Card>
        )}

        {/* Patterns Table */}
        <Card title="Обнаруженные паттерны регулярных платежей">
          <Table
            columns={columns}
            dataSource={patterns}
            rowKey={(record) => `${record.counterparty_inn}-${record.category_id}`}
            loading={isLoading}
            rowSelection={{
              selectedRowKeys,
              onChange: setSelectedRowKeys,
            }}
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `Всего ${total} паттернов`,
            }}
            scroll={{ x: 1000 }}
          />
        </Card>
      </Space>
    </div>
  )
}
