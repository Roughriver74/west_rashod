import { useState, useEffect } from 'react'
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
  Statistic,
  Drawer,
  Form,
  Popconfirm,
  Progress,
  Modal,
} from 'antd'
import {
  UploadOutlined,
  DownloadOutlined,
  SearchOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
  TagOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  BankOutlined,
  WalletOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import * as XLSX from 'xlsx'
import { saveAs } from 'file-saver'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import type { ColumnsType } from 'antd/es/table'
import {
  getBankTransactions,
  BankTransaction,
  TransactionFilters,
  importFromExcel,
  bulkStatusUpdate,
  bulkCategorize,
  categorizeTransaction,
  getTransactionStats,
  bulkDelete,
  getCategorySuggestions,
  getSimilarTransactions,
  applyCategoryToSimilar,
} from '../api/bankTransactions'
import { getCategories } from '../api/categories'
import AccountsFilter from '../components/AccountsFilter'

const { Title, Text } = Typography
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

const statusShortLabels: Record<string, string> = {
  NEW: 'Новая',
  CATEGORIZED: 'Категориз.',
  APPROVED: 'Утв.',
  NEEDS_REVIEW: 'Проверка',
  IGNORED: 'Игнор.',
}

const formatAmount = (amount: number) => {
  return Number(amount).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₽'
}

export default function BankTransactionsPage() {
  const queryClient = useQueryClient()
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([])
  const [filters, setFilters] = useState<TransactionFilters>({
    limit: 50,
  })
  const [categorizeDrawerOpen, setCategorizeDrawerOpen] = useState(false)
  const [selectedTransaction, setSelectedTransaction] = useState<BankTransaction | null>(null)
  const [similarTransactionsDrawerOpen, setSimilarTransactionsDrawerOpen] = useState(false)
  const [selectedSimilarIds, setSelectedSimilarIds] = useState<number[]>([])
  const [activeQuickFilter, setActiveQuickFilter] = useState<string | null>(null)
  const [form] = Form.useForm()

  // Reset selected similar IDs when similar drawer opens
  useEffect(() => {
    if (similarTransactionsDrawerOpen) {
      setSelectedSimilarIds([])
    }
  }, [similarTransactionsDrawerOpen])

  // Fetch transactions
  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ['bank-transactions', filters],
    queryFn: () => getBankTransactions(filters),
  })

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['bank-transactions-stats', filters.date_from, filters.date_to],
    queryFn: () => getTransactionStats({
      date_from: filters.date_from,
      date_to: filters.date_to,
    }),
  })

  // Fetch categories
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => getCategories({ is_active: true }),
  })

  // Category suggestions
  const { data: suggestions = [] } = useQuery({
    queryKey: ['category-suggestions', selectedTransaction?.id],
    queryFn: () => selectedTransaction ? getCategorySuggestions(selectedTransaction.id) : Promise.resolve([]),
    enabled: !!selectedTransaction,
  })

  // Similar transactions
  const { data: similarTransactions = [], isLoading: loadingSimilar } = useQuery({
    queryKey: ['similar-transactions', selectedTransaction?.id],
    queryFn: () => selectedTransaction ? getSimilarTransactions(selectedTransaction.id, 0.5, 1000) : Promise.resolve([]),
    enabled: !!selectedTransaction && similarTransactionsDrawerOpen,
  })

  // Import mutation
  const importMutation = useMutation({
    mutationFn: (file: File) => importFromExcel(file),
    onSuccess: (data) => {
      message.success(`Импортировано: ${data.imported}, пропущено: ${data.skipped}`)
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })
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
      queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })
    },
  })

  // Bulk categorize mutation
  const bulkCategorizeMutation = useMutation({
    mutationFn: (category_id: number) =>
      bulkCategorize({ transaction_ids: selectedRowKeys, category_id }),
    onSuccess: () => {
      message.success('Категория назначена')
      setSelectedRowKeys([])
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })
    },
  })

  // Categorize single mutation
  const categorizeMutation = useMutation({
    mutationFn: ({ id, category_id, notes }: { id: number; category_id: number; notes?: string }) =>
      categorizeTransaction(id, { category_id, notes }),
    onSuccess: () => {
      message.success('Категория назначена')
      setCategorizeDrawerOpen(false)
      setSimilarTransactionsDrawerOpen(false)
      setSelectedTransaction(null)
      setSelectedSimilarIds([])
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })
    },
  })

  // Bulk delete mutation
  const bulkDeleteMutation = useMutation({
    mutationFn: () => bulkDelete(selectedRowKeys),
    onSuccess: (data) => {
      message.success(`Удалено: ${data.deleted}`)
      setSelectedRowKeys([])
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })
    },
  })

  // Apply category to similar mutation
  const applyCategoryToSimilarMutation = useMutation({
    mutationFn: ({ transactionId, categoryId, applyToIds }: {
      transactionId: number
      categoryId: number
      applyToIds?: number[]
    }) => applyCategoryToSimilar(transactionId, categoryId, applyToIds),
    onSuccess: (data) => {
      message.success(data.message)
      setSimilarTransactionsDrawerOpen(false)
      setCategorizeDrawerOpen(false)
      setSelectedTransaction(null)
      setSelectedSimilarIds([])
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })
    },
  })

  const openCategorizeDrawer = (record: BankTransaction) => {
    setSelectedTransaction(record)
    form.setFieldsValue({
      category_id: record.category_id,
      notes: record.notes,
    })
    setCategorizeDrawerOpen(true)
  }

  const handleCategorize = (values: { category_id: number; notes?: string }) => {
    if (selectedTransaction) {
      // Сохраняем выбранную категорию и примечание в форму
      form.setFieldsValue({
        category_id: values.category_id,
        notes: values.notes,
      })
      // Открываем окно с похожими операциями
      setSimilarTransactionsDrawerOpen(true)
    }
  }

  const handleExportExcel = () => {
    const dataToExport = selectedRowKeys.length > 0
      ? transactions.filter(t => selectedRowKeys.includes(t.id))
      : transactions

    if (dataToExport.length === 0) {
      message.warning('Нет данных для экспорта')
      return
    }

    const exportData = dataToExport.map(t => ({
      'Дата': dayjs(t.transaction_date).format('DD.MM.YYYY'),
      'Тип': t.transaction_type === 'DEBIT' ? 'Расход' : 'Приход',
      'Сумма': Number(t.amount),
      'Контрагент': t.counterparty_name || '',
      'ИНН': t.counterparty_inn || '',
      'КПП': t.counterparty_kpp || '',
      'Банк контрагента': t.counterparty_bank || '',
      'БИК': t.counterparty_bik || '',
      'Счёт контрагента': t.counterparty_account || '',
      'Назначение платежа': t.payment_purpose || '',
      'Хозяйственная операция': t.business_operation || '',
      'Категория': t.category_name || '',
      'Предложенная категория': t.suggested_category_name || '',
      'Уверенность AI (%)': t.category_confidence ? Math.round(t.category_confidence * 100) : '',
      'Статус': statusLabels[t.status] || t.status,
      'Организация': t.organization_name || '',
      'Номер счёта': t.account_number || '',
      'Номер документа': t.document_number || '',
      'Дата документа': t.document_date ? dayjs(t.document_date).format('DD.MM.YYYY') : '',
      'Источник': t.payment_source === 'CASH' ? 'Касса' : 'Банк',
      'Регулярный платёж': t.is_regular_payment ? 'Да' : 'Нет',
      'Примечание': t.notes || '',
    }))

    const worksheet = XLSX.utils.json_to_sheet(exportData)

    // Set column widths
    const colWidths = [
      { wch: 12 },  // Дата
      { wch: 10 },  // Тип
      { wch: 15 },  // Сумма
      { wch: 40 },  // Контрагент
      { wch: 12 },  // ИНН
      { wch: 10 },  // КПП
      { wch: 30 },  // Банк контрагента
      { wch: 10 },  // БИК
      { wch: 22 },  // Счёт контрагента
      { wch: 60 },  // Назначение платежа
      { wch: 25 },  // Хозяйственная операция
      { wch: 25 },  // Категория
      { wch: 25 },  // Предложенная категория
      { wch: 12 },  // Уверенность AI
      { wch: 18 },  // Статус
      { wch: 30 },  // Организация
      { wch: 22 },  // Номер счёта
      { wch: 15 },  // Номер документа
      { wch: 12 },  // Дата документа
      { wch: 10 },  // Источник
      { wch: 12 },  // Регулярный платёж
      { wch: 40 },  // Примечание
    ]
    worksheet['!cols'] = colWidths

    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Транзакции')

    const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' })
    const data = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })

    const filename = `bank_transactions_${dayjs().format('YYYY-MM-DD_HH-mm')}.xlsx`
    saveAs(data, filename)
    message.success(`Экспортировано ${exportData.length} операций`)
  }

  // Quick filter handlers
  const handleQuickFilter = (filterType: string) => {
    if (activeQuickFilter === filterType) {
      // Сбросить фильтр
      setActiveQuickFilter(null)
      setFilters((prev) => ({
        ...prev,
        transaction_type: undefined,
        status: undefined,
      }))
    } else {
      // Применить фильтр
      setActiveQuickFilter(filterType)

      switch (filterType) {
        case 'debit':
          setFilters((prev) => ({
            ...prev,
            transaction_type: 'DEBIT',
            status: undefined,
          }))
          break
        case 'credit':
          setFilters((prev) => ({
            ...prev,
            transaction_type: 'CREDIT',
            status: undefined,
          }))
          break
        case 'needs_review':
          setFilters((prev) => ({
            ...prev,
            transaction_type: undefined,
            status: 'NEEDS_REVIEW',
          }))
          break
        default:
          break
      }
    }
  }

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
      width: 120,
      render: (type, record) => (
        <Space direction="vertical" size={2}>
          <Tag color={type === 'DEBIT' ? 'red' : 'green'} style={{ margin: 0 }}>
            {type === 'DEBIT' ? 'Расход' : 'Приход'}
          </Tag>
          <Tag
            color={record.payment_source === 'CASH' ? 'purple' : 'blue'}
            icon={record.payment_source === 'CASH' ? <WalletOutlined /> : <BankOutlined />}
            style={{ margin: 0, fontSize: '11px' }}
          >
            {record.payment_source === 'CASH' ? 'Касса' : 'Безнал'}
          </Tag>
        </Space>
      ),
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      key: 'amount',
      width: 130,
      align: 'right',
      render: (amount, record) => (
        <Text strong style={{ color: record.transaction_type === 'DEBIT' ? '#cf1322' : '#3f8600' }}>
          {formatAmount(amount)}
        </Text>
      ),
      sorter: (a, b) => Number(a.amount) - Number(b.amount),
    },
    {
      title: 'Контрагент',
      dataIndex: 'counterparty_name',
      key: 'counterparty_name',
      width: 220,
      ellipsis: {
        showTitle: false,
      },
      render: (name, record) => (
        <Tooltip title={
          <div>
            <div>{name || '-'}</div>
            <div>ИНН: {record.counterparty_inn || '-'}</div>
            {record.counterparty_bank && <div>Банк: {record.counterparty_bank}</div>}
          </div>
        }>
          <span>{name || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Назначение',
      dataIndex: 'payment_purpose',
      key: 'payment_purpose',
      width: 250,
      ellipsis: {
        showTitle: false,
      },
      render: (purpose, record) => (
        <Tooltip title={
          <div>
            <div>{purpose || '-'}</div>
            {record.business_operation && (
              <div style={{ marginTop: 4, fontSize: '11px' }}>
                Хоз. операция: {record.business_operation}
              </div>
            )}
          </div>
        }>
          <span>{purpose || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Категория',
      dataIndex: 'category_name',
      key: 'category_name',
      width: 170,
      render: (name, record) => {
        if (name) {
          return (
            <Space>
              <Tag color="green">{name}</Tag>
              {record.category_confidence && (
                <Tooltip title={`Уверенность AI: ${(record.category_confidence * 100).toFixed(0)}%`}>
                  <Progress
                    type="circle"
                    percent={Math.round(record.category_confidence * 100)}
                    size={20}
                    strokeColor={record.category_confidence >= 0.9 ? '#52c41a' : record.category_confidence >= 0.7 ? '#faad14' : '#ff4d4f'}
                  />
                </Tooltip>
              )}
            </Space>
          )
        }
        if (record.suggested_category_name) {
          return (
            <Tooltip title={`Предложение AI (${((record.category_confidence || 0) * 100).toFixed(0)}%)`}>
              <Tag color="orange" style={{ cursor: 'pointer' }} onClick={() => openCategorizeDrawer(record)}>
                {record.suggested_category_name}?
              </Tag>
            </Tooltip>
          )
        }
        return (
          <Button type="link" size="small" onClick={() => openCategorizeDrawer(record)}>
            Назначить
          </Button>
        )
      },
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => (
        <Tooltip title={statusLabels[status]}>
          <Tag color={statusColors[status]}>{statusShortLabels[status] || statusLabels[status]}</Tag>
        </Tooltip>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Категоризировать">
            <Button type="text" size="small" icon={<TagOutlined />} onClick={() => openCategorizeDrawer(record)} />
          </Tooltip>
        </Space>
      ),
    },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys as number[]),
  }

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        <BankOutlined style={{ marginRight: 8 }} />
        Банковские операции
      </Title>

      {/* Statistics Cards */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="Всего операций"
              value={stats?.total || 0}
              prefix={<BankOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            size="small"
            onClick={() => handleQuickFilter('debit')}
            style={{
              cursor: 'pointer',
              border: activeQuickFilter === 'debit' ? '2px solid #cf1322' : undefined,
              boxShadow: activeQuickFilter === 'debit' ? '0 0 8px rgba(207, 19, 34, 0.3)' : undefined,
            }}
            hoverable
          >
            <Statistic
              title="Расход"
              value={stats?.total_debit || 0}
              precision={2}
              prefix={<ArrowDownOutlined style={{ color: '#cf1322' }} />}
              suffix="₽"
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            size="small"
            onClick={() => handleQuickFilter('credit')}
            style={{
              cursor: 'pointer',
              border: activeQuickFilter === 'credit' ? '2px solid #3f8600' : undefined,
              boxShadow: activeQuickFilter === 'credit' ? '0 0 8px rgba(63, 134, 0, 0.3)' : undefined,
            }}
            hoverable
          >
            <Statistic
              title="Приход"
              value={stats?.total_credit || 0}
              precision={2}
              prefix={<ArrowUpOutlined style={{ color: '#3f8600' }} />}
              suffix="₽"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            size="small"
            onClick={() => handleQuickFilter('needs_review')}
            style={{
              cursor: 'pointer',
              border: activeQuickFilter === 'needs_review' ? '2px solid #faad14' : undefined,
              boxShadow: activeQuickFilter === 'needs_review' ? '0 0 8px rgba(250, 173, 20, 0.3)' : undefined,
            }}
            hoverable
          >
            <Statistic
              title="Требуют проверки"
              value={stats?.needs_review || 0}
              prefix={<ExclamationCircleOutlined style={{ color: '#faad14' }} />}
              valueStyle={{ color: stats?.needs_review ? '#faad14' : undefined }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main content with two columns */}
      <Row gutter={16}>
        {/* Left column - Accounts Filter */}
        <Col xs={24} md={6} lg={4} style={{ marginBottom: 16 }}>
          <AccountsFilter
            dateFrom={filters.date_from}
            dateTo={filters.date_to}
            transactionType={filters.transaction_type}
            status={filters.status}
            selectedAccount={filters.account_number}
            onAccountSelect={(accountNumber) => {
              setFilters((prev) => ({ ...prev, account_number: accountNumber }))
            }}
          />
        </Col>

        {/* Right column - Filters and Table */}
        <Col xs={24} md={18} lg={20}>
          {/* Filters */}
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
                allowClear
              />
              <Select
                placeholder="Статус"
                style={{ width: 160 }}
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
              <Select
                placeholder="Источник"
                style={{ width: 120 }}
                allowClear
                onChange={(value) =>
                  setFilters((prev) => ({ ...prev, payment_source: value }))
                }
                options={[
                  { value: 'BANK', label: 'Банк' },
                  { value: 'CASH', label: 'Касса' },
                ]}
              />
              <Select
                placeholder="Категория"
                style={{ width: 200 }}
                allowClear
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                onChange={(value) =>
                  setFilters((prev) => ({ ...prev, category_id: value }))
                }
                options={categories.map((cat) => ({
                  value: cat.id,
                  label: cat.name,
                }))}
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
                <>
                  <Select
                    placeholder="Назначить категорию"
                    style={{ width: 200 }}
                    showSearch
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                    onChange={(value) => {
                      if (value) {
                        Modal.confirm({
                          title: `Назначить категорию для ${selectedRowKeys.length} операций?`,
                          onOk: () => bulkCategorizeMutation.mutate(value),
                        })
                      }
                    }}
                    options={categories.map((cat) => ({
                      value: cat.id,
                      label: cat.name,
                    }))}
                  />
                  <Button
                    icon={<CheckCircleOutlined />}
                    onClick={() => bulkStatusMutation.mutate('APPROVED')}
                    loading={bulkStatusMutation.isPending}
                  >
                    Утвердить ({selectedRowKeys.length})
                  </Button>
                  <Popconfirm
                    title={`Удалить ${selectedRowKeys.length} операций?`}
                    onConfirm={() => bulkDeleteMutation.mutate()}
                    okText="Да"
                    cancelText="Нет"
                  >
                    <Button danger icon={<DeleteOutlined />} loading={bulkDeleteMutation.isPending}>
                      Удалить
                    </Button>
                  </Popconfirm>
                </>
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
                icon={<DownloadOutlined />}
                onClick={handleExportExcel}
              >
                Экспорт {selectedRowKeys.length > 0 ? `(${selectedRowKeys.length})` : 'Excel'}
              </Button>
              <Button
                icon={<SyncOutlined />}
                onClick={() => {
                  queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
                  queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })
                }}
              >
                Обновить
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Table */}
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
          scroll={{ x: 1500 }}
          size="middle"
        />
      </Card>
        </Col>
      </Row>

      {/* Categorize Drawer */}
      <Drawer
        title="Категоризация операции"
        placement="right"
        width={500}
        open={categorizeDrawerOpen}
        onClose={() => {
          setCategorizeDrawerOpen(false)
          setSelectedTransaction(null)
          form.resetFields()
        }}
      >
        {selectedTransaction && (
          <div>
            <Card size="small" style={{ marginBottom: 16 }}>
              <Row gutter={[8, 8]}>
                <Col span={12}>
                  <Text type="secondary">Дата:</Text>
                  <div>{dayjs(selectedTransaction.transaction_date).format('DD.MM.YYYY')}</div>
                </Col>
                <Col span={12}>
                  <Text type="secondary">Сумма:</Text>
                  <div style={{ color: selectedTransaction.transaction_type === 'DEBIT' ? '#cf1322' : '#3f8600', fontWeight: 'bold' }}>
                    {formatAmount(selectedTransaction.amount)}
                  </div>
                </Col>
                <Col span={24}>
                  <Text type="secondary">Контрагент:</Text>
                  <div>{selectedTransaction.counterparty_name || '-'}</div>
                </Col>
                <Col span={24}>
                  <Text type="secondary">Назначение:</Text>
                  <div style={{ fontSize: '12px' }}>{selectedTransaction.payment_purpose || '-'}</div>
                </Col>
                {selectedTransaction.business_operation && (
                  <Col span={24}>
                    <Text type="secondary">Хозяйственная операция:</Text>
                    <div><Tag>{selectedTransaction.business_operation}</Tag></div>
                  </Col>
                )}
              </Row>
            </Card>

            {/* AI Suggestions */}
            {(selectedTransaction.suggested_category_id || suggestions.length > 0) && (
              <Card size="small" style={{ marginBottom: 16 }} title="Предложения AI">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {selectedTransaction.suggested_category_name && (
                    <Button
                      type="dashed"
                      block
                      onClick={() => {
                        form.setFieldsValue({ category_id: selectedTransaction.suggested_category_id })
                      }}
                    >
                      {selectedTransaction.suggested_category_name}
                      {selectedTransaction.category_confidence && (
                        <Tag color="blue" style={{ marginLeft: 8 }}>
                          {(selectedTransaction.category_confidence * 100).toFixed(0)}%
                        </Tag>
                      )}
                    </Button>
                  )}
                  {suggestions.map((sug: { category_id: number; category_name: string; confidence: number }) => (
                    <Button
                      key={sug.category_id}
                      type="dashed"
                      block
                      onClick={() => {
                        form.setFieldsValue({ category_id: sug.category_id })
                      }}
                    >
                      {sug.category_name}
                      <Tag color="blue" style={{ marginLeft: 8 }}>
                        {(sug.confidence * 100).toFixed(0)}%
                      </Tag>
                    </Button>
                  ))}
                </Space>
              </Card>
            )}

            <Form form={form} layout="vertical" onFinish={handleCategorize}>
              <Form.Item
                name="category_id"
                label="Категория"
                rules={[{ required: true, message: 'Выберите категорию' }]}
              >
                <Select
                  showSearch
                  placeholder="Выберите категорию"
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                  options={categories.map((cat) => ({
                    value: cat.id,
                    label: cat.name,
                  }))}
                />
              </Form.Item>
              <Form.Item name="notes" label="Примечание">
                <Input.TextArea rows={3} placeholder="Дополнительные заметки..." />
              </Form.Item>
              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={categorizeMutation.isPending}>
                    Сохранить
                  </Button>
                  <Button onClick={() => setCategorizeDrawerOpen(false)}>
                    Отмена
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </div>
        )}
      </Drawer>

      {/* Similar Transactions Drawer */}
      <Drawer
        title="Похожие транзакции"
        placement="right"
        width={800}
        open={similarTransactionsDrawerOpen}
        onClose={() => {
          setSimilarTransactionsDrawerOpen(false)
          setSelectedSimilarIds([])
        }}
      >
        {selectedTransaction && (
          <div>
            <Card size="small" style={{ marginBottom: 16 }}>
              <Row gutter={[8, 8]}>
                <Col span={12}>
                  <Text type="secondary">Контрагент:</Text>
                  <div>{selectedTransaction.counterparty_name || '-'}</div>
                </Col>
                <Col span={12}>
                  <Text type="secondary">Назначение:</Text>
                  <div style={{ fontSize: '12px' }}>{selectedTransaction.payment_purpose || '-'}</div>
                </Col>
              </Row>
            </Card>

            <div style={{ marginBottom: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text type="secondary">
                  Найдено похожих: {similarTransactions.length}
                </Text>
                {similarTransactions.length > 0 && (
                  <Space>
                    <Button
                      size="small"
                      onClick={() => {
                        const allIds = similarTransactions.map(t => t.id)
                        setSelectedSimilarIds(allIds)
                      }}
                    >
                      Выбрать все ({similarTransactions.length})
                    </Button>
                    <Button
                      size="small"
                      onClick={() => setSelectedSimilarIds([])}
                    >
                      Снять выделение
                    </Button>
                    {selectedSimilarIds.length > 0 && (
                      <Text type="secondary">
                        Выбрано: {selectedSimilarIds.length}
                      </Text>
                    )}
                  </Space>
                )}
              </Space>
            </div>

            {loadingSimilar ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Space>
                  <LoadingOutlined />
                  <Text>Поиск похожих транзакций...</Text>
                </Space>
              </div>
            ) : similarTransactions.length > 0 ? (
              <>
                <Table
                  rowKey="id"
                  dataSource={similarTransactions}
                  size="small"
                  pagination={{ pageSize: 20 }}
                  rowSelection={{
                    type: 'checkbox',
                    selectedRowKeys: selectedSimilarIds,
                    onChange: (selectedRowKeys) => {
                      setSelectedSimilarIds(selectedRowKeys as number[])
                    },
                  }}
                  columns={[
                    {
                      title: 'Дата',
                      dataIndex: 'transaction_date',
                      width: 100,
                      render: (date) => dayjs(date).format('DD.MM.YYYY'),
                    },
                    {
                      title: 'Сумма',
                      dataIndex: 'amount',
                      width: 120,
                      render: (amount, record) => (
                        <Text strong style={{ color: record.transaction_type === 'DEBIT' ? '#cf1322' : '#3f8600' }}>
                          {formatAmount(amount)}
                        </Text>
                      ),
                    },
                    {
                      title: 'Назначение',
                      dataIndex: 'payment_purpose',
                      ellipsis: true,
                    },
                    {
                      title: 'Категория',
                      dataIndex: 'category_name',
                      width: 150,
                      render: (name) => name ? <Tag color="green">{name}</Tag> : '-',
                    },
                  ]}
                />

                <div style={{ marginTop: 16 }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Button
                      type="primary"
                      block
                      onClick={() => {
                        const categoryId = form.getFieldValue('category_id')

                        if (!categoryId) {
                          message.warning('Сначала выберите категорию')
                          return
                        }

                        if (selectedSimilarIds.length === 0) {
                          message.warning('Выберите хотя бы одну похожую транзакцию')
                          return
                        }

                        applyCategoryToSimilarMutation.mutate({
                          transactionId: selectedTransaction.id,
                          categoryId,
                          applyToIds: selectedSimilarIds,
                        })
                      }}
                      loading={applyCategoryToSimilarMutation.isPending}
                    >
                      Применить к выбранным ({selectedSimilarIds.length})
                    </Button>
                    <Button
                      block
                      onClick={() => {
                        const categoryId = form.getFieldValue('category_id')
                        const notes = form.getFieldValue('notes')

                        if (!categoryId) {
                          message.warning('Сначала выберите категорию')
                          return
                        }

                        categorizeMutation.mutate({
                          id: selectedTransaction.id,
                          category_id: categoryId,
                          notes: notes,
                        })
                      }}
                      loading={categorizeMutation.isPending}
                    >
                      Применить только к этой операции
                    </Button>
                  </Space>
                </div>
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Text type="secondary">Похожие транзакции не найдены</Text>
                <div style={{ marginTop: 16 }}>
                  <Button
                    type="primary"
                    onClick={() => {
                      const categoryId = form.getFieldValue('category_id')
                      const notes = form.getFieldValue('notes')

                      if (!categoryId) {
                        message.warning('Сначала выберите категорию')
                        return
                      }

                      categorizeMutation.mutate({
                        id: selectedTransaction.id,
                        category_id: categoryId,
                        notes: notes,
                      })
                    }}
                    loading={categorizeMutation.isPending}
                  >
                    Применить к этой операции
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  )
}
