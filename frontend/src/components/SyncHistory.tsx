/**
 * Sync History Component
 * Displays history of sync tasks with statistics
 */
import { Card, Table, Tag, Space, Typography, Tooltip, Alert, Descriptions, Button, message, Popconfirm } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined, ClockCircleOutlined, StopOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { listTasks, TaskInfo, TaskStatus, cancelTask } from '../api/tasks'

const { Text, Paragraph } = Typography

const taskTypeLabels: Record<string, string> = {
  sync_bank_transactions: 'Банковские операции',
  sync_organizations: 'Организации',
  sync_categories: 'Категории',
  sync_contractors: 'Контрагенты',
  sync_full: 'Полная синхронизация',
}

const getStatusTag = (status: TaskStatus) => {
  switch (status) {
    case 'completed':
      return <Tag icon={<CheckCircleOutlined />} color="success">Завершено</Tag>
    case 'failed':
      return <Tag icon={<CloseCircleOutlined />} color="error">Ошибка</Tag>
    case 'cancelled':
      return <Tag color="warning">Отменено</Tag>
    case 'running':
      return <Tag icon={<LoadingOutlined />} color="processing">Выполняется</Tag>
    case 'pending':
      return <Tag icon={<ClockCircleOutlined />} color="default">В очереди</Tag>
    default:
      return <Tag color="default">{status}</Tag>
  }
}

interface SyncHistoryProps {
  limit?: number
}

export default function SyncHistory({ limit = 10 }: SyncHistoryProps) {
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['task-history', limit],
    queryFn: () => listTasks(undefined, limit),
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  const cancelTaskMutation = useMutation({
    mutationFn: cancelTask,
    onSuccess: () => {
      message.success('Задача отменена')
      queryClient.invalidateQueries({ queryKey: ['task-history'] })
    },
    onError: (error: Error) => {
      message.error(`Ошибка отмены задачи: ${error.message}`)
    },
  })

  const handleCancelTask = (taskId: string) => {
    cancelTaskMutation.mutate(taskId)
  }

  const columns = [
    {
      title: 'Дата и время',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => (
        <Tooltip title={dayjs(date).format('DD.MM.YYYY HH:mm:ss')}>
          <Text>{dayjs(date).format('DD.MM HH:mm')}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Тип задачи',
      dataIndex: 'task_type',
      key: 'task_type',
      width: 200,
      render: (type: string, record: TaskInfo) => {
        const label = taskTypeLabels[type] || type
        const isAuto = record.metadata?.auto_sync === true
        return (
          <Space direction="vertical" size={0}>
            <Text>{label}</Text>
            {isAuto && <Tag color="blue" style={{ fontSize: '10px' }}>Авто</Tag>}
          </Space>
        )
      },
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (status: TaskStatus) => getStatusTag(status),
    },
    {
      title: 'Прогресс',
      dataIndex: 'progress',
      key: 'progress',
      width: 80,
      render: (progress: number, record: TaskInfo) => {
        if (record.status === 'running' || record.status === 'pending') {
          return <Text>{progress}%</Text>
        }
        return <Text type="secondary">{record.processed || 0} / {record.total || 0}</Text>
      },
    },
    {
      title: 'Создано',
      key: 'created',
      width: 80,
      render: (_: unknown, record: TaskInfo) => {
        const result = record.result as Record<string, any> | undefined

        // Handle full sync results
        if (record.task_type === 'sync_full') {
          const totalCreated =
            (result?.organizations?.created ?? 0) +
            (result?.categories?.created ?? 0) +
            (result?.transactions?.created ?? 0)
          return totalCreated > 0 ? <Tag color="green">{totalCreated}</Tag> : <Text type="secondary">0</Text>
        }

        const created = result?.created ?? result?.total_created ?? 0
        return created > 0 ? <Tag color="green">{created}</Tag> : <Text type="secondary">0</Text>
      },
    },
    {
      title: 'Обновлено',
      key: 'updated',
      width: 90,
      render: (_: unknown, record: TaskInfo) => {
        const result = record.result as Record<string, any> | undefined

        // Handle full sync results
        if (record.task_type === 'sync_full') {
          const totalUpdated =
            (result?.organizations?.updated ?? 0) +
            (result?.categories?.updated ?? 0) +
            (result?.transactions?.updated ?? 0)
          return totalUpdated > 0 ? <Tag color="blue">{totalUpdated}</Tag> : <Text type="secondary">0</Text>
        }

        const updated = result?.updated ?? result?.total_updated ?? 0
        return updated > 0 ? <Tag color="blue">{updated}</Tag> : <Text type="secondary">0</Text>
      },
    },
    {
      title: 'Ошибки',
      key: 'errors',
      width: 80,
      render: (_: unknown, record: TaskInfo) => {
        const result = record.result as Record<string, any> | undefined

        if (record.error) {
          return (
            <Tooltip title={record.error}>
              <Tag color="red">Ошибка</Tag>
            </Tooltip>
          )
        }

        // Handle full sync results
        if (record.task_type === 'sync_full') {
          const totalErrors =
            (Array.isArray(result?.organizations?.errors) ? result.organizations.errors.length : 0) +
            (Array.isArray(result?.categories?.errors) ? result.categories.errors.length : 0) +
            (Array.isArray(result?.transactions?.errors) ? result.transactions.errors.length : 0)

          if (totalErrors > 0) {
            return (
              <Tooltip title={`${totalErrors} ошибок`}>
                <Tag color="orange">{totalErrors}</Tag>
              </Tooltip>
            )
          }
          return <Text type="secondary">0</Text>
        }

        const errors = Array.isArray(result?.errors) ? result.errors : []
        const errorCount = errors.length || 0

        if (errorCount > 0) {
          return (
            <Tooltip title={`${errorCount} ошибок`}>
              <Tag color="orange">{errorCount}</Tag>
            </Tooltip>
          )
        }

        return <Text type="secondary">0</Text>
      },
    },
    {
      title: 'Сообщение',
      dataIndex: 'message',
      key: 'message',
      ellipsis: { showTitle: false },
      render: (message: string) => (
        <Tooltip title={message}>
          <Text type="secondary" ellipsis style={{ maxWidth: 200 }}>
            {message}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: TaskInfo) => {
        const canCancel = record.status === 'running' || record.status === 'pending'

        if (!canCancel) {
          return null
        }

        return (
          <Popconfirm
            title="Отменить задачу?"
            description="Вы уверены, что хотите отменить эту задачу?"
            onConfirm={() => handleCancelTask(record.task_id)}
            okText="Да"
            cancelText="Нет"
          >
            <Button
              type="link"
              danger
              size="small"
              icon={<StopOutlined />}
              loading={cancelTaskMutation.isPending}
            >
              Отменить
            </Button>
          </Popconfirm>
        )
      },
    },
  ]

  if (error) {
    return (
      <Alert
        type="error"
        message="Ошибка загрузки истории"
        description={(error as Error).message}
      />
    )
  }

  const expandedRowRender = (record: TaskInfo) => {
    const result = record.result as Record<string, any> | undefined
    const isFullSync = record.task_type === 'sync_full'

    return (
      <div style={{ padding: '12px 24px', background: '#fafafa' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* Basic Info */}
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="ID задачи">{record.task_id}</Descriptions.Item>
            <Descriptions.Item label="Тип">{taskTypeLabels[record.task_type] || record.task_type}</Descriptions.Item>
            <Descriptions.Item label="Создана">
              {dayjs(record.created_at).format('DD.MM.YYYY HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="Завершена">
              {record.completed_at ? dayjs(record.completed_at).format('DD.MM.YYYY HH:mm:ss') : '—'}
            </Descriptions.Item>
          </Descriptions>

          {/* Full Sync Details */}
          {isFullSync && result && (
            <div>
              <Text strong>Детали полной синхронизации:</Text>
              {['organizations', 'categories', 'transactions'].map((key) => {
                const data = result[key]
                if (!data) return null

                const labels: Record<string, string> = {
                  organizations: 'Организации',
                  categories: 'Категории',
                  transactions: 'Транзакции',
                }

                return (
                  <Descriptions
                    key={key}
                    title={labels[key]}
                    size="small"
                    column={3}
                    bordered
                    style={{ marginTop: 8 }}
                  >
                    <Descriptions.Item label="Создано">
                      <Tag color="green">{data.created ?? 0}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="Обновлено">
                      <Tag color="blue">{data.updated ?? 0}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="Ошибки">
                      <Tag color={Array.isArray(data.errors) && data.errors.length > 0 ? 'red' : 'default'}>
                        {Array.isArray(data.errors) ? data.errors.length : 0}
                      </Tag>
                    </Descriptions.Item>
                  </Descriptions>
                )
              })}
            </div>
          )}

          {/* Single Sync Details */}
          {!isFullSync && result && (
            <Descriptions size="small" column={3} bordered title="Детали">
              <Descriptions.Item label="Создано">
                <Tag color="green">{result.created ?? result.total_created ?? 0}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Обновлено">
                <Tag color="blue">{result.updated ?? result.total_updated ?? 0}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Пропущено">
                <Tag>{result.skipped ?? result.total_skipped ?? 0}</Tag>
              </Descriptions.Item>
            </Descriptions>
          )}

          {/* Error Details */}
          {record.error && (
            <Alert
              type="error"
              message="Ошибка выполнения"
              description={<Paragraph copyable>{record.error}</Paragraph>}
            />
          )}

          {/* Result Message */}
          {result?.message && (
            <Alert type="info" message="Результат" description={result.message} />
          )}
        </Space>
      </div>
    )
  }

  return (
    <Card title="История синхронизаций" style={{ marginTop: 16 }}>
      <Table
        dataSource={data?.tasks || []}
        columns={columns}
        rowKey="task_id"
        loading={isLoading}
        pagination={{
          pageSize: 10,
          showTotal: (total) => `Всего задач: ${total}`,
          showSizeChanger: false,
        }}
        size="small"
        expandable={{
          expandedRowRender,
          rowExpandable: (record) => record.status !== 'pending',
        }}
      />
    </Card>
  )
}
