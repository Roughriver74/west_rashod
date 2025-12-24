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
  Switch,
} from 'antd'
import {
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloudServerOutlined,
  BankOutlined,
  TeamOutlined,
  TagsOutlined,
  ClockCircleOutlined,
  SettingOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import dayjs from 'dayjs'
import { testConnection } from '../api/sync1c'
import syncSettingsApi, { SyncSettings, SyncSettingsUpdate } from '../api/syncSettings'
import TaskProgress from '../components/TaskProgress'
import SyncHistory from '../components/SyncHistory'
import {
  startAsyncBankTransactionsSync,
  startAsyncCategoriesSync,
  startAsyncFullSync,
  startAsyncOrganizationsSync,
  TaskInfo,
  TaskStatus,
} from '../api/tasks'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

/**
 * Calculate the next scheduled sync time based on sync settings.
 * Returns a dayjs object representing the next sync time, or null if not applicable.
 */
function calculateNextSyncTime(settings: SyncSettings | undefined): dayjs.Dayjs | null {
  if (!settings || !settings.auto_sync_enabled) {
    return null
  }

  // Interval-based sync: next sync = last_sync_completed_at + sync_interval_hours
  if (settings.sync_interval_hours !== null && settings.sync_interval_hours > 0) {
    if (settings.last_sync_completed_at) {
      const lastSync = dayjs(settings.last_sync_completed_at)
      return lastSync.add(settings.sync_interval_hours, 'hour')
    }
    // If no previous sync, next sync is now (will run on next scheduler tick)
    return dayjs()
  }

  // Scheduled time sync: next sync at sync_time_hour:sync_time_minute
  if (settings.sync_time_hour !== null && settings.sync_time_minute !== null) {
    const now = dayjs()
    let nextSync = now
      .hour(settings.sync_time_hour)
      .minute(settings.sync_time_minute)
      .second(0)
      .millisecond(0)

    // If the scheduled time has already passed today, schedule for tomorrow
    if (nextSync.isBefore(now)) {
      nextSync = nextSync.add(1, 'day')
    }

    return nextSync
  }

  return null
}

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
  const [activeTask, setActiveTask] = useState<{
    id: string
    title: string
    type: TaskInfo['task_type']
  } | null>(null)
  const [showProgress, setShowProgress] = useState(false)
  const [syncResults, setSyncResults] = useState<{
    transactions?: TaskInfo
    organizations?: TaskInfo
    categories?: TaskInfo
    full?: TaskInfo
  }>({})

  // Fetch sync settings
  const {
    data: syncSettings,
    isLoading: isLoadingSettings,
    isError: isSettingsError,
    error: settingsError,
    refetch: refetchSettings,
  } = useQuery({
    queryKey: ['syncSettings'],
    queryFn: syncSettingsApi.getSettings,
  })

  // Update sync settings mutation (for toggle)
  const updateSettingsMutation = useMutation({
    mutationFn: (data: SyncSettingsUpdate) => syncSettingsApi.updateSettings(data),
    onSuccess: () => {
      refetchSettings()
      message.success('Настройки автосинхронизации обновлены')
    },
    onError: () => {
      message.error('Ошибка обновления настроек')
    },
  })

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

  // Helper to extract error message from API response
  const getErrorMessage = (error: unknown, fallback: string): string => {
    const err = error as Error & { response?: { data?: { detail?: string | Array<{msg: string}> } } }
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
    return fallback
  }

  // Helper to display sync status with colored tags
  const getStatusTag = (status: string | null) => {
    if (!status) return null

    switch (status) {
      case 'SUCCESS':
        return <Tag icon={<CheckCircleOutlined />} color="success">Успешно</Tag>
      case 'FAILED':
        return <Tag icon={<CloseCircleOutlined />} color="error">Ошибка</Tag>
      case 'IN_PROGRESS':
        return <Tag icon={<LoadingOutlined />} color="processing">Выполняется</Tag>
      default:
        return <Tag>{status}</Tag>
    }
  }

  const getTaskStatusTag = (status: TaskStatus) => {
    switch (status) {
      case 'completed':
        return <Tag icon={<CheckCircleOutlined />} color="success">Завершено</Tag>
      case 'failed':
        return <Tag icon={<CloseCircleOutlined />} color="error">Ошибка</Tag>
      case 'cancelled':
        return <Tag color="warning">Отменено</Tag>
      case 'running':
        return <Tag icon={<LoadingOutlined />} color="processing">Выполняется</Tag>
      default:
        return <Tag color="default">В очереди</Tag>
    }
  }

  const startTransactionsMutation = useMutation({
    mutationFn: () => {
      if (!dateRange) {
        throw new Error('Выберите период')
      }
      return startAsyncBankTransactionsSync({
        date_from: dateRange[0].format('YYYY-MM-DD'),
        date_to: dateRange[1].format('YYYY-MM-DD'),
        auto_classify: true,
      })
    },
    onSuccess: (data) => {
      setActiveTask({
        id: data.task_id,
        title: 'Синхронизация банковских операций',
        type: 'sync_bank_transactions',
      })
      setShowProgress(true)
      message.success('Фоновая синхронизация транзакций запущена')
    },
    onError: (error: unknown) => {
      message.error(getErrorMessage(error, 'Ошибка запуска синхронизации транзакций'))
    },
  })

  const startOrganizationsMutation = useMutation({
    mutationFn: startAsyncOrganizationsSync,
    onSuccess: (data) => {
      setActiveTask({
        id: data.task_id,
        title: 'Синхронизация организаций',
        type: 'sync_organizations',
      })
      setShowProgress(true)
      message.success('Фоновая синхронизация организаций запущена')
    },
    onError: (error: unknown) => {
      message.error(getErrorMessage(error, 'Ошибка запуска синхронизации организаций'))
    },
  })

  const startCategoriesMutation = useMutation({
    mutationFn: startAsyncCategoriesSync,
    onSuccess: (data) => {
      setActiveTask({
        id: data.task_id,
        title: 'Синхронизация категорий расходов',
        type: 'sync_categories',
      })
      setShowProgress(true)
      message.success('Фоновая синхронизация категорий запущена')
    },
    onError: (error: unknown) => {
      message.error(getErrorMessage(error, 'Ошибка запуска синхронизации категорий'))
    },
  })

  const startFullSyncMutation = useMutation({
    mutationFn: () => {
      if (!dateRange) {
        throw new Error('Выберите период')
      }
      return startAsyncFullSync({
        date_from: dateRange[0].format('YYYY-MM-DD'),
        date_to: dateRange[1].format('YYYY-MM-DD'),
        auto_classify: true,
      })
    },
    onSuccess: (data) => {
      setActiveTask({
        id: data.task_id,
        title: 'Полная синхронизация',
        type: 'sync_full',
      })
      setShowProgress(true)
      message.success('Полная синхронизация запущена')
    },
    onError: (error: unknown) => {
      message.error(getErrorMessage(error, 'Ошибка запуска полной синхронизации'))
    },
  })

  const handleTaskComplete = (task: TaskInfo) => {
    setSyncResults((prev) => {
      if (task.task_type === 'sync_bank_transactions') {
        return { ...prev, transactions: task }
      }
      if (task.task_type === 'sync_organizations') {
        return { ...prev, organizations: task }
      }
      if (task.task_type === 'sync_categories') {
        return { ...prev, categories: task }
      }
      if (task.task_type === 'sync_full') {
        return { ...prev, full: task }
      }
      return prev
    })

    setActiveTask(null)
    setShowProgress(false)

    if (task.status === 'completed') {
      const resultMessage = (task.result as Record<string, unknown> | undefined)?.message
      const content = typeof resultMessage === 'string'
        ? resultMessage
        : task.message || 'Синхронизация завершена'
      message.success(content)
    } else if (task.status === 'failed') {
      message.error(task.error || 'Синхронизация завершилась с ошибкой')
    } else if (task.status === 'cancelled') {
      message.info('Задача синхронизации отменена')
    }
  }

  const renderSyncResult = (task: TaskInfo | undefined, title: string) => {
    if (!task) return null

    const result = (task.result || {}) as Record<string, any>
    const created = result.created ?? result.total_created ?? 0
    const updated = result.updated ?? result.total_updated ?? 0
    const skipped = result.total_skipped ?? result.skipped ?? 0
    const totalProcessed =
      result.total ??
      result.total_fetched ??
      result.total_processed ??
      task.processed ??
      created + updated + skipped
    const errors = Array.isArray(result.errors) ? result.errors : []
    const statusTag = getTaskStatusTag(task.status)

    return (
      <Card size="small" style={{ marginTop: 8 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space align="center">
            {statusTag}
            <Text type="secondary">
              {result.message || task.message || 'Прогресс синхронизации'}
            </Text>
          </Space>
          <Descriptions title={title} column={2} size="small">
            <Descriptions.Item label="Обработано">
              {totalProcessed}
            </Descriptions.Item>
            <Descriptions.Item label="Создано">
              <Tag color="green">{created}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Обновлено">
              <Tag color="blue">{updated}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Пропущено">
              <Tag color="default">{skipped}</Tag>
            </Descriptions.Item>
            {errors.length > 0 && (
              <Descriptions.Item label="Ошибки" span={2}>
                <Tag color="red">{errors.length}</Tag>
              </Descriptions.Item>
            )}
          </Descriptions>
          {task.error && (
            <Alert type="error" showIcon message="Ошибка" description={task.error} />
          )}
        </Space>
      </Card>
    )
  }

  const renderFullSyncResult = (task: TaskInfo | undefined) => {
    if (!task) return null

    const result = (task.result || {}) as Record<string, any>
    const statusTag = getTaskStatusTag(task.status)
    const sections: Array<{ key: string; label: string }> = [
      { key: 'organizations', label: 'Организации' },
      { key: 'categories', label: 'Категории' },
      { key: 'transactions', label: 'Транзакции' },
    ]

    return (
      <Card size="small" style={{ marginTop: 12 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space align="center">
            {statusTag}
            <Text type="secondary">
              {result.message || task.message || 'Полная синхронизация'}
            </Text>
          </Space>
          {sections.map(({ key, label }) => {
            const data = result[key]
            if (!data) return null

            const created = data.created ?? data.total_created ?? 0
            const updated = data.updated ?? data.total_updated ?? 0
            const skipped = data.total_skipped ?? data.skipped ?? 0
            const total =
              data.total ?? data.total_fetched ?? created + updated + skipped
            const errorsCount = Array.isArray(data.errors) ? data.errors.length : 0

            return (
              <Descriptions key={key} title={label} column={2} size="small">
                <Descriptions.Item label="Обработано">
                  {total}
                </Descriptions.Item>
                <Descriptions.Item label="Создано">
                  <Tag color="green">{created}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Обновлено">
                  <Tag color="blue">{updated}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Пропущено">
                  <Tag color="default">{skipped}</Tag>
                </Descriptions.Item>
                {errorsCount > 0 && (
                  <Descriptions.Item label="Ошибки" span={2}>
                    <Tag color="red">{errorsCount}</Tag>
                  </Descriptions.Item>
                )}
              </Descriptions>
            )
          })}
          {task.error && (
            <Alert type="error" showIcon message="Ошибка" description={task.error} />
          )}
        </Space>
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

      {/* Auto-Sync Status Card */}
      <Card
        style={{ marginBottom: 16 }}
        title={
          <Space>
            <ClockCircleOutlined />
            <span>Автоматическая синхронизация</span>
          </Space>
        }
        extra={
          <Link to="/sync-settings">
            <Button icon={<SettingOutlined />}>
              Настройки
            </Button>
          </Link>
        }
      >
        {isLoadingSettings ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">Загрузка настроек...</Text>
            </div>
          </div>
        ) : isSettingsError ? (
          <Alert
            type="error"
            message="Ошибка загрузки настроек"
            description={
              <Space direction="vertical">
                <Text>
                  {(settingsError as Error & { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
                   (settingsError as Error)?.message ||
                   'Не удалось загрузить настройки автосинхронизации'}
                </Text>
                <Button onClick={() => refetchSettings()} icon={<SyncOutlined />}>
                  Повторить
                </Button>
              </Space>
            }
          />
        ) : syncSettings ? (
          <Row gutter={[24, 16]} align="middle">
            <Col xs={24} sm={12} md={6}>
              <Space direction="vertical" size={0}>
                <Text type="secondary">Статус</Text>
                <Space>
                  <Switch
                    checked={syncSettings.auto_sync_enabled}
                    loading={updateSettingsMutation.isPending}
                    onChange={(checked) =>
                      updateSettingsMutation.mutate({ auto_sync_enabled: checked })
                    }
                  />
                  <Text strong>
                    {syncSettings.auto_sync_enabled ? 'Включена' : 'Выключена'}
                  </Text>
                </Space>
              </Space>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Space direction="vertical" size={0}>
                <Text type="secondary">Расписание</Text>
                <Text>
                  {syncSettings.sync_interval_hours
                    ? `Каждые ${syncSettings.sync_interval_hours} ч.`
                    : syncSettings.sync_time_hour !== null && syncSettings.sync_time_minute !== null
                    ? `Ежедневно в ${String(syncSettings.sync_time_hour).padStart(2, '0')}:${String(syncSettings.sync_time_minute).padStart(2, '0')}`
                    : 'Не настроено'}
                </Text>
              </Space>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Space direction="vertical" size={0}>
                <Text type="secondary">Последняя синхронизация</Text>
                <Space>
                  {getStatusTag(syncSettings.last_sync_status)}
                  {syncSettings.last_sync_completed_at && (
                    <Text type="secondary">
                      {dayjs(syncSettings.last_sync_completed_at).format('DD.MM.YYYY HH:mm')}
                    </Text>
                  )}
                  {!syncSettings.last_sync_status && !syncSettings.last_sync_completed_at && (
                    <Text type="secondary">Ещё не выполнялась</Text>
                  )}
                </Space>
              </Space>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Space direction="vertical" size={0}>
                <Text type="secondary">Следующая синхронизация</Text>
                {(() => {
                  const nextSync = calculateNextSyncTime(syncSettings)
                  if (nextSync) {
                    return <Text>{nextSync.format('DD.MM.YYYY HH:mm')}</Text>
                  }
                  return (
                    <Text type="secondary">
                      {syncSettings.auto_sync_enabled ? 'Скоро' : '—'}
                    </Text>
                  )
                })()}
              </Space>
            </Col>
          </Row>
        ) : (
          <Alert
            type="info"
            message="Настройки не найдены"
            description={
              <Space>
                <Text>Настройте автоматическую синхронизацию</Text>
                <Link to="/sync-settings">
                  <Button type="primary" size="small">
                    Настроить
                  </Button>
                </Link>
              </Space>
            }
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
                icon={<SyncOutlined spin={startTransactionsMutation.isPending} />}
                onClick={() => startTransactionsMutation.mutate()}
                loading={startTransactionsMutation.isPending}
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
                icon={<SyncOutlined spin={startOrganizationsMutation.isPending} />}
                onClick={() => startOrganizationsMutation.mutate()}
                loading={startOrganizationsMutation.isPending}
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
                icon={<SyncOutlined spin={startCategoriesMutation.isPending} />}
                onClick={() => startCategoriesMutation.mutate()}
                loading={startCategoriesMutation.isPending}
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
                icon={<SyncOutlined spin={startFullSyncMutation.isPending} />}
                onClick={() => startFullSyncMutation.mutate()}
                loading={startFullSyncMutation.isPending}
                disabled={!dateRange}
              >
                Синхронизировать все
              </Button>
              {renderFullSyncResult(syncResults.full)}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Sync History */}
      <SyncHistory limit={20} />

      {activeTask && (
        <TaskProgress
          taskId={activeTask.id}
          title={activeTask.title}
          visible={showProgress}
          onClose={() => setShowProgress(false)}
          onComplete={handleTaskComplete}
          useWebSocket
          keepPollingWhenHidden
        />
      )}
    </div>
  )
}
