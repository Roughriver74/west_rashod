import { useState } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Input,
  Select,
  DatePicker,
  Upload,
  message,
  Typography,
  Row,
  Col,
  Tooltip,
} from 'antd'
import {
  UploadOutlined,
  SearchOutlined,
  SyncOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import type { ColumnsType } from 'antd/es/table'
import {
  getBankTransactions,
  BankTransaction,
  TransactionFilters,
  importFromExcel,
  bulkStatusUpdate,
} from '../api/bankTransactions'
import { getCategories, Category } from '../api/categories'
import { useDepartment } from '../contexts/DepartmentContext'

const { Title } = Typography
const { RangePicker } = DatePicker

const statusColors: Record<string, string> = {
  NEW: 'blue',
  CATEGORIZED: 'green',
  APPROVED: 'cyan',
  NEEDS_REVIEW: 'orange',
  IGNORED: 'default',
}

const statusLabels: Record<string, string> = {
  NEW: 'Новая',
  CATEGORIZED: 'Категоризирована',
  APPROVED: 'Утверждена',
  NEEDS_REVIEW: 'Требует проверки',
  IGNORED: 'Игнорирована',
}

export default function BankTransactionsPage() {
  const { selectedDepartment } = useDepartment()
  const queryClient = useQueryClient()
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([])
  const [filters, setFilters] = useState<TransactionFilters>({
    limit: 50,
  })

  // Fetch transactions
  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ['bank-transactions', selectedDepartment?.id, filters],
    queryFn: () =>
      getBankTransactions({
        ...filters,
        department_id: selectedDepartment?.id,
      }),
    enabled: !!selectedDepartment,
  })

  // Fetch categories
  const { data: categories = [] } = useQuery({
    queryKey: ['categories', selectedDepartment?.id],
    queryFn: () => getCategories({ department_id: selectedDepartment?.id, is_active: true }),
    enabled: !!selectedDepartment,
  })

  // Import mutation
  const importMutation = useMutation({
    mutationFn: (file: File) => importFromExcel(file, selectedDepartment!.id),
    onSuccess: (data) => {
      message.success(`Импортировано: ${data.imported}, пропущено: ${data.skipped}`)
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
    },
    onError: () => {
      message.error('Ошибка импорта')
    },
  })

  // Bulk status update mutation
  const bulkStatusMutation = useMutation({
    mutationFn: (status: string) =>
      bulkStatusUpdate({ transaction_ids: selectedRowKeys, status }),
    onSuccess: () => {
      message.success('Статус обновлен')
      setSelectedRowKeys([])
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
    },
  })

  const columns: ColumnsType<BankTransaction> = [
    {
      title: 'Дата',
      dataIndex: 'transaction_date',
      key: 'transaction_date',
      width: 100,
      render: (date) => dayjs(date).format('DD.MM.YYYY'),
      sorter: (a, b) => dayjs(a.transaction_date).unix() - dayjs(b.transaction_date).unix(),
    },
    {
      title: 'Тип',
      dataIndex: 'transaction_type',
      key: 'transaction_type',
      width: 80,
      render: (type) => (
        <Tag color={type === 'DEBIT' ? 'red' : 'green'}>
          {type === 'DEBIT' ? 'Расход' : 'Приход'}
        </Tag>
      ),
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      align: 'right',
      render: (amount, record) => (
        <span style={{ color: record.transaction_type === 'DEBIT' ? '#cf1322' : '#3f8600' }}>
          {Number(amount).toLocaleString('ru-RU', { minimumFractionDigits: 2 })} ₽
        </span>
      ),
      sorter: (a, b) => Number(a.amount) - Number(b.amount),
    },
    {
      title: 'Контрагент',
      dataIndex: 'counterparty_name',
      key: 'counterparty_name',
      width: 200,
      ellipsis: true,
      render: (name, record) => (
        <Tooltip title={`ИНН: ${record.counterparty_inn || '-'}`}>
          {name || '-'}
        </Tooltip>
      ),
    },
    {
      title: 'Назначение',
      dataIndex: 'payment_purpose',
      key: 'payment_purpose',
      ellipsis: true,
      render: (purpose) => (
        <Tooltip title={purpose}>
          <span>{purpose || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Категория',
      dataIndex: 'category_name',
      key: 'category_name',
      width: 150,
      render: (name) => name || <Tag color="warning">Не назначена</Tag>,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status) => <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>,
    },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys as number[]),
  }

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        Банковские операции
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="Поиск..."
                prefix={<SearchOutlined />}
                style={{ width: 200 }}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, search: e.target.value }))
                }
              />
              <Select
                placeholder="Статус"
                style={{ width: 150 }}
                allowClear
                onChange={(value) =>
                  setFilters((prev) => ({ ...prev, status: value }))
                }
                options={Object.entries(statusLabels).map(([value, label]) => ({
                  value,
                  label,
                }))}
              />
              <Select
                placeholder="Тип"
                style={{ width: 120 }}
                allowClear
                onChange={(value) =>
                  setFilters((prev) => ({ ...prev, transaction_type: value }))
                }
                options={[
                  { value: 'DEBIT', label: 'Расход' },
                  { value: 'CREDIT', label: 'Приход' },
                ]}
              />
              <RangePicker
                onChange={(dates) => {
                  setFilters((prev) => ({
                    ...prev,
                    date_from: dates?.[0]?.format('YYYY-MM-DD'),
                    date_to: dates?.[1]?.format('YYYY-MM-DD'),
                  }))
                }}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              {selectedRowKeys.length > 0 && (
                <Button
                  icon={<CheckCircleOutlined />}
                  onClick={() => bulkStatusMutation.mutate('APPROVED')}
                  loading={bulkStatusMutation.isPending}
                >
                  Утвердить ({selectedRowKeys.length})
                </Button>
              )}
              <Upload
                accept=".xlsx,.xls"
                showUploadList={false}
                beforeUpload={(file) => {
                  importMutation.mutate(file)
                  return false
                }}
              >
                <Button icon={<UploadOutlined />} loading={importMutation.isPending}>
                  Импорт Excel
                </Button>
              </Upload>
              <Button
                icon={<SyncOutlined />}
                onClick={() =>
                  queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
                }
              >
                Обновить
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={transactions}
          loading={isLoading}
          rowSelection={rowSelection}
          pagination={{
            pageSize: 50,
            showSizeChanger: true,
            showTotal: (total) => `Всего: ${total}`,
          }}
          scroll={{ x: 1200 }}
          size="middle"
        />
      </Card>
    </div>
  )
}
