import { useState } from 'react'
import {
  Card,
  Button,
  Space,
  message,
  Typography,
  DatePicker,
  Row,
  Col,
  Alert,
  Spin,
  Descriptions,
  Tag,
  Divider,
} from 'antd'
import {
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloudServerOutlined,
  BankOutlined,
  TeamOutlined,
  TagsOutlined,
} from '@ant-design/icons'
import { useMutation } from '@tanstack/react-query'
import dayjs from 'dayjs'
import {
  testConnection,
  syncTransactions,
  syncOrganizations,
  syncCategories,
  Sync1CResult,
} from '../api/sync1c'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

export default function Sync1CPage() {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>([
    dayjs().startOf('month'),
    dayjs(),
  ])
  const [connectionStatus, setConnectionStatus] = useState<{
    success: boolean
    message: string
    server_info?: unknown
  } | null>(null)
  const [syncResults, setSyncResults] = useState<{
    transactions?: Sync1CResult
    organizations?: Sync1CResult
    categories?: Sync1CResult
  }>({})

  // Test connection mutation
  const testConnectionMutation = useMutation({
    mutationFn: testConnection,
    onSuccess: (data) => {
      setConnectionStatus(data)
      if (data.success) {
        message.success('Подключение к 1С успешно!')
      } else {
        message.error('Ошибка подключения к 1С')
      }
    },
    onError: () => {
      setConnectionStatus({ success: false, message: 'Ошибка подключения' })
      message.error('Ошибка подключения к 1С')
    },
  })

  // Sync transactions mutation
  const syncTransactionsMutation = useMutation({
    mutationFn: () => {
      if (!dateRange) {
        throw new Error('Выберите период')
      }
      return syncTransactions({
        date_from: dateRange[0].format('YYYY-MM-DDTHH:mm:ss'),
        date_to: dateRange[1].format('YYYY-MM-DDTHH:mm:ss'),
      })
    },
    onSuccess: (data) => {
      setSyncResults((prev) => ({ ...prev, transactions: data }))
      message.success(`Синхронизировано: ${data.created} создано, ${data.updated} обновлено`)
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      message.error(error.response?.data?.detail || 'Ошибка синхронизации транзакций')
    },
  })

  // Sync organizations mutation
  const syncOrganizationsMutation = useMutation({
    mutationFn: () => syncOrganizations({}),
    onSuccess: (data) => {
      setSyncResults((prev) => ({ ...prev, organizations: data }))
      message.success(`Организации: ${data.created} создано, ${data.updated} обновлено`)
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      message.error(error.response?.data?.detail || 'Ошибка синхронизации организаций')
    },
  })

  // Sync categories mutation
  const syncCategoriesMutation = useMutation({
    mutationFn: () => syncCategories({}),
    onSuccess: (data) => {
      setSyncResults((prev) => ({ ...prev, categories: data }))
      message.success(`Категории: ${data.created} создано, ${data.updated} обновлено`)
    },
    onError: (error: Error & { response?: { data?: { detail?: string } } }) => {
      message.error(error.response?.data?.detail || 'Ошибка синхронизации категорий')
    },
  })

  const handleSyncAll = async () => {
    try {
      // Sync all in sequence
      await syncOrganizationsMutation.mutateAsync()
      await syncCategoriesMutation.mutateAsync()
      await syncTransactionsMutation.mutateAsync()
      message.success('Полная синхронизация завершена!')
    } catch {
      message.error('Ошибка при синхронизации')
    }
  }

  const isAnySyncing =
    syncTransactionsMutation.isPending ||
    syncOrganizationsMutation.isPending ||
    syncCategoriesMutation.isPending

  const renderSyncResult = (result: Sync1CResult | undefined, title: string) => {
    if (!result) return null

    return (
      <Card size="small" style={{ marginTop: 8 }}>
        <Descriptions title={title} column={2} size="small">
          <Descriptions.Item label="Обработано">
            {result.total_processed}
          </Descriptions.Item>
          <Descriptions.Item label="Создано">
            <Tag color="green">{result.created}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Обновлено">
            <Tag color="blue">{result.updated}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Пропущено">
            <Tag color="default">{result.skipped}</Tag>
          </Descriptions.Item>
          {result.errors.length > 0 && (
            <Descriptions.Item label="Ошибки" span={2}>
              <Tag color="red">{result.errors.length}</Tag>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>
    )
  }

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        Синхронизация с 1С
      </Title>

      {/* Connection Status Card */}
      <Card style={{ marginBottom: 16 }}>
        <Row align="middle" gutter={16}>
          <Col>
            <CloudServerOutlined style={{ fontSize: 32, color: '#1890ff' }} />
          </Col>
          <Col flex="auto">
            <Title level={5} style={{ margin: 0 }}>
              Подключение к 1С OData
            </Title>
            <Text type="secondary">Проверьте подключение перед синхронизацией</Text>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<SyncOutlined spin={testConnectionMutation.isPending} />}
              onClick={() => testConnectionMutation.mutate()}
              loading={testConnectionMutation.isPending}
            >
              Проверить подключение
            </Button>
          </Col>
        </Row>

        {connectionStatus && (
          <Alert
            style={{ marginTop: 16 }}
            type={connectionStatus.success ? 'success' : 'error'}
            icon={
              connectionStatus.success ? (
                <CheckCircleOutlined />
              ) : (
                <CloseCircleOutlined />
              )
            }
            message={
              connectionStatus.success
                ? 'Подключение успешно'
                : 'Ошибка подключения'
            }
            description={connectionStatus.message}
            showIcon
          />
        )}
      </Card>

      {/* Sync Controls */}
      <Row gutter={16}>
        {/* Bank Transactions */}
        <Col span={8}>
          <Card
            title={
              <Space>
                <BankOutlined />
                <span>Банковские операции</span>
              </Space>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text type="secondary">Период синхронизации:</Text>
                <RangePicker
                  style={{ width: '100%', marginTop: 8 }}
                  value={dateRange}
                  onChange={(dates) =>
                    setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)
                  }
                  format="DD.MM.YYYY"
                />
              </div>

              <Button
                type="primary"
                block
                icon={<SyncOutlined spin={syncTransactionsMutation.isPending} />}
                onClick={() => syncTransactionsMutation.mutate()}
                loading={syncTransactionsMutation.isPending}
                disabled={!dateRange}
              >
                Синхронизировать
              </Button>

              {renderSyncResult(syncResults.transactions, 'Результат')}
            </Space>
          </Card>
        </Col>

        {/* Organizations */}
        <Col span={8}>
          <Card
            title={
              <Space>
                <TeamOutlined />
                <span>Организации</span>
              </Space>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">
                Синхронизация справочника организаций из 1С
              </Text>

              <Button
                type="primary"
                block
                icon={<SyncOutlined spin={syncOrganizationsMutation.isPending} />}
                onClick={() => syncOrganizationsMutation.mutate()}
                loading={syncOrganizationsMutation.isPending}
              >
                Синхронизировать
              </Button>

              {renderSyncResult(syncResults.organizations, 'Результат')}
            </Space>
          </Card>
        </Col>

        {/* Categories */}
        <Col span={8}>
          <Card
            title={
              <Space>
                <TagsOutlined />
                <span>Категории расходов</span>
              </Space>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">
                Синхронизация статей расходов из 1С
              </Text>

              <Button
                type="primary"
                block
                icon={<SyncOutlined spin={syncCategoriesMutation.isPending} />}
                onClick={() => syncCategoriesMutation.mutate()}
                loading={syncCategoriesMutation.isPending}
              >
                Синхронизировать
              </Button>

              {renderSyncResult(syncResults.categories, 'Результат')}
            </Space>
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* Full Sync Button */}
      <Card>
        <Row justify="center">
          <Col>
            <Space direction="vertical" align="center">
              <Title level={5}>Полная синхронизация</Title>
              <Text type="secondary">
                Синхронизировать все данные: организации, категории, банковские операции
              </Text>
              <Button
                type="primary"
                size="large"
                icon={<SyncOutlined spin={isAnySyncing} />}
                onClick={handleSyncAll}
                loading={isAnySyncing}
                disabled={!dateRange}
              >
                Синхронизировать все
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Loading Overlay */}
      {isAnySyncing && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(255, 255, 255, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <Spin size="large" tip="Синхронизация..." />
        </div>
      )}
    </div>
  )
}
