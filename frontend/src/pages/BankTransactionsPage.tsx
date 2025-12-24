import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
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
  ClearOutlined,
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
  PaginatedBankTransactions,
  deleteByFilter,
  updateTransaction,
} from '../api/bankTransactions'
import type { RuleSuggestionsResponse } from '../types/bankTransaction'
import AccountsFilter from '../components/AccountsFilter'
import CategoryTreeSelect from '../components/CategoryTreeSelect'
import { RuleSuggestionsModal } from '../components/RuleSuggestionsModal'

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

const truncateCategoryName = (text: string, max = 22) =>
  text && text.length > max ? `${text.slice(0, max - 3)}...` : text

export default function BankTransactionsPage() {
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([])

  // Инициализация фильтров из URL параметров
  const initializeFiltersFromURL = (): TransactionFilters => {
    const urlFilters: TransactionFilters = {
      limit: 50,
      offset: 0,
    }

    // Читаем фильтры из URL
    const status = searchParams.get('status')
    const transactionType = searchParams.get('transaction_type')
    const dateFrom = searchParams.get('date_from')
    const dateTo = searchParams.get('date_to')
    const onlyUnprocessed = searchParams.get('only_unprocessed')
    const categoryId = searchParams.get('category_id')
    const search = searchParams.get('search')
    const accountNumber = searchParams.get('account_number')
    const organizationId = searchParams.get('organization_id')

    if (status) urlFilters.status = status
    if (transactionType) urlFilters.transaction_type = transactionType
    if (dateFrom) urlFilters.date_from = dateFrom
    if (dateTo) urlFilters.date_to = dateTo
    if (onlyUnprocessed === 'true') urlFilters.only_unprocessed = true
    if (categoryId) urlFilters.category_id = parseInt(categoryId)
    if (search) urlFilters.search = search
    if (accountNumber) urlFilters.account_number = accountNumber
    if (organizationId) urlFilters.organization_id = parseInt(organizationId)

    return urlFilters
  }

  const [filters, setFilters] = useState<TransactionFilters>(initializeFiltersFromURL())
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [categorizeDrawerOpen, setCategorizeDrawerOpen] = useState(false)
  const [selectedTransaction, setSelectedTransaction] = useState<BankTransaction | null>(null)
  const [similarTransactionsDrawerOpen, setSimilarTransactionsDrawerOpen] = useState(false)
  const [selectedSimilarIds, setSelectedSimilarIds] = useState<number[]>([])
  const [activeQuickFilter, setActiveQuickFilter] = useState<string | null>(null)
  const [ruleSuggestionsVisible, setRuleSuggestionsVisible] = useState(false)
  const [ruleSuggestions, setRuleSuggestions] = useState<RuleSuggestionsResponse | null>(null)
  const [form] = Form.useForm()

  // Reset selected similar IDs when similar drawer opens
  useEffect(() => {
    if (similarTransactionsDrawerOpen) {
      setSelectedSimilarIds([])
    }
  }, [similarTransactionsDrawerOpen])

  // Reset page to 1 when filters change (except limit and offset)
  useEffect(() => {
    setCurrentPage(1)
    setFilters((prev) => ({ ...prev, offset: 0 }))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    filters.search,
    filters.status,
    filters.transaction_type,
    filters.payment_source,
    filters.category_id,
    filters.account_number,
    filters.organization_id,
    filters.only_unprocessed,
    filters.date_from,
    filters.date_to,
  ])

  // Fetch transactions
  const { data: transactionsData, isLoading } = useQuery<PaginatedBankTransactions>({
    queryKey: ['bank-transactions', filters],
    queryFn: () => getBankTransactions(filters),
  })

  const transactions = transactionsData?.items || []
  const totalTransactions = transactionsData?.total || 0

  // Fetch stats with all filters
  const { data: stats } = useQuery({
    queryKey: ['bank-transactions-stats', filters],
    queryFn: () => getTransactionStats({
      date_from: filters.date_from,
      date_to: filters.date_to,
      transaction_type: filters.transaction_type,
      payment_source: filters.payment_source,
      account_number: filters.account_number,
      organization_id: filters.organization_id,
      category_id: filters.category_id,
      search: filters.search,
    }),
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
    onSuccess: (data) => {
      console.log('🔍 Bulk categorize response:', data)
      console.log('🔍 Rule suggestions:', data.rule_suggestions)

      message.success('Категория назначена')
      setSelectedRowKeys([])
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })

      // Показываем модалку с предложениями правил
      if (data.rule_suggestions && data.rule_suggestions.suggestions.length > 0) {
        console.log('✅ Показываем модалку с предложениями')
        setRuleSuggestions(data.rule_suggestions)
        setRuleSuggestionsVisible(true)
      } else {
        console.log('❌ Модалка не показана. Причина:', {
          hasRuleSuggestions: !!data.rule_suggestions,
          suggestionsCount: data.rule_suggestions?.suggestions?.length || 0
        })
      }
    },
  })

  // Categorize single mutation
  const categorizeMutation = useMutation({
    mutationFn: ({ id, category_id, notes }: { id: number; category_id: number; notes?: string }) =>
      categorizeTransaction(id, { category_id, notes }),
    onSuccess: (data) => {
      message.success('Категория назначена')
      setCategorizeDrawerOpen(false)
      setSimilarTransactionsDrawerOpen(false)
      setSelectedTransaction(null)
      setSelectedSimilarIds([])
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })

      // Показываем модалку с предложениями правил
      if (data.rule_suggestions && data.rule_suggestions.suggestions.length > 0) {
        setRuleSuggestions(data.rule_suggestions)
        setRuleSuggestionsVisible(true)
      }
    },
  })

  // Update transaction mutation (for VAT and other fields)
  const updateTransactionMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<BankTransaction> }) =>
      updateTransaction(id, data),
    onSuccess: () => {
      message.success('Транзакция обновлена')
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

  // Delete by filter mutation
  const deleteByFilterMutation = useMutation({
    mutationFn: () => deleteByFilter(filters),
    onSuccess: (data) => {
      message.success(`Удалено: ${data.deleted}`)
      setSelectedRowKeys([])
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })
      queryClient.invalidateQueries({ queryKey: ['account-grouping'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || 'Ошибка удаления')
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
      console.log('🔍 Apply to similar response:', data)
      console.log('🔍 Rule suggestions:', data.rule_suggestions)

      message.success(data.message)
      setSimilarTransactionsDrawerOpen(false)
      setCategorizeDrawerOpen(false)
      setSelectedTransaction(null)
      setSelectedSimilarIds([])
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
      queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })

      // Показываем модалку с предложениями правил
      if (data.rule_suggestions && data.rule_suggestions.suggestions.length > 0) {
        console.log('✅ Показываем модалку с предложениями')
        setRuleSuggestions(data.rule_suggestions)
        setRuleSuggestionsVisible(true)
      } else {
        console.log('❌ Модалка не показана. Причина:', {
          hasRuleSuggestions: !!data.rule_suggestions,
          suggestionsCount: data.rule_suggestions?.suggestions?.length || 0
        })
      }
    },
  })

  const openCategorizeDrawer = (record: BankTransaction) => {
    setSelectedTransaction(record)
    form.setFieldsValue({
      category_id: record.category_id,
      notes: record.notes,
      vat_rate: record.vat_rate,
      vat_amount: record.vat_amount,
    })
    setCategorizeDrawerOpen(true)
  }

  const handleCategorize = async (values: { category_id: number; notes?: string; vat_rate?: number; vat_amount?: number }) => {
    if (selectedTransaction) {
      // Сначала обновляем НДС если они были изменены
      if (values.vat_rate !== undefined || values.vat_amount !== undefined) {
        await updateTransactionMutation.mutateAsync({
          id: selectedTransaction.id,
          data: {
            vat_rate: values.vat_rate,
            vat_amount: values.vat_amount,
          },
        })
        // Обновляем selectedTransaction чтобы в окне похожих операций были новые значения
        setSelectedTransaction({
          ...selectedTransaction,
          vat_rate: values.vat_rate,
          vat_amount: values.vat_amount,
        })
      }

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
      'НДС %': t.vat_rate || '',
      'Сумма НДС': t.vat_amount ? Number(t.vat_amount) : '',
      'Сумма без НДС': t.vat_amount ? Number(t.amount) - Number(t.vat_amount) : '',
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

  // Quick filter handlers - сквозная фильтрация (комбинирование фильтров)
  const handleQuickFilter = (filterType: string) => {
    if (activeQuickFilter === filterType) {
      // Сбросить только этот конкретный фильтр, не трогая остальные
      setActiveQuickFilter(null)
      setFilters((prev) => ({
        ...prev,
        transaction_type: undefined,
        status: undefined,
        only_unprocessed: undefined,
        // account_number и organization_id НЕ сбрасываются!
      }))
    } else {
      // Применить фильтр, сохраняя все остальные (включая счет и организацию)
      setActiveQuickFilter(filterType)

      switch (filterType) {
        case 'debit':
          setFilters((prev) => ({
            ...prev,
            transaction_type: 'DEBIT',
            status: undefined,
            only_unprocessed: undefined,
            // account_number и organization_id сохраняются!
          }))
          break
        case 'credit':
          setFilters((prev) => ({
            ...prev,
            transaction_type: 'CREDIT',
            status: undefined,
            only_unprocessed: undefined,
            // account_number и organization_id сохраняются!
          }))
          break
        case 'needs_review':
          setFilters((prev) => ({
            ...prev,
            transaction_type: undefined,
            status: undefined,
            only_unprocessed: true,
            // account_number и organization_id сохраняются!
          }))
          break
        default:
          break
      }
    }
  }

  // Сброс всех фильтров
  const handleClearAllFilters = () => {
    setActiveQuickFilter(null)
    setFilters({
      limit: pageSize,
      offset: 0,
    })
    setCurrentPage(1)
  }

  // Проверка наличия активных фильтров
  const hasActiveFilters = !!(
    filters.search ||
    filters.status ||
    filters.transaction_type ||
    filters.payment_source ||
    filters.category_id ||
    filters.account_number ||
    filters.organization_id ||
    filters.date_from ||
    filters.date_to ||
    filters.only_unprocessed
  )

  const columns: ColumnsType<BankTransaction> = [
    {
      title: 'Дата',
      dataIndex: 'transaction_date',
      key: 'transaction_date',
      width: 100,
      render: (date, record) => (
        <Space direction="vertical" size={2}>
          <Text>{dayjs(date).format('DD.MM.YYYY')}</Text>
          {record.document_number && (
            <Text type="secondary" style={{ fontSize: '11px' }}>
              № {record.document_number}
            </Text>
          )}
        </Space>
      ),
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
        <Space direction="vertical" size={0} style={{ alignItems: 'flex-end' }}>
          <Text strong style={{ color: record.transaction_type === 'DEBIT' ? '#cf1322' : '#3f8600' }}>
            {formatAmount(amount)}
          </Text>
          {record.vat_amount && record.vat_amount > 0 && (
            <Tooltip title={`НДС ${record.vat_rate || 0}%: ${formatAmount(record.vat_amount)}`}>
              <Text type="secondary" style={{ fontSize: '11px' }}>
                без НДС: {formatAmount(Number(amount) - Number(record.vat_amount))}
              </Text>
            </Tooltip>
          )}
        </Space>
      ),
      sorter: (a, b) => Number(a.amount) - Number(b.amount),
    },
    {
      title: 'НДС',
      key: 'vat',
      width: 100,
      align: 'right',
      render: (_, record) => {
        if (!record.vat_amount || record.vat_amount === 0) {
          return <Text type="secondary" style={{ fontSize: '11px' }}>—</Text>
        }
        return (
          <Space direction="vertical" size={0} style={{ alignItems: 'flex-end' }}>
            <Tooltip title={`Ставка НДС: ${record.vat_rate || 0}%`}>
              <Tag color="blue" style={{ margin: 0 }}>
                {record.vat_rate || 0}%
              </Tag>
            </Tooltip>
            <Text style={{ fontSize: '11px' }}>
              {formatAmount(record.vat_amount)}
            </Text>
          </Space>
        )
      },
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
      width: 160,
      render: (name, record) => {
        const confidenceBadge = record.category_confidence ? (
          <Tooltip title={`Уверенность AI: ${(record.category_confidence * 100).toFixed(0)}%`}>
            <Progress
              type="circle"
              percent={Math.round(record.category_confidence * 100)}
              size={20}
              strokeColor={record.category_confidence >= 0.9 ? '#52c41a' : record.category_confidence >= 0.7 ? '#faad14' : '#ff4d4f'}
            />
          </Tooltip>
        ) : null

        if (name) {
          return (
            <Space size={6} wrap align="center">
              <Tooltip title={name}>
                <Tag
                  color="green"
                  style={{
                    maxWidth: 140,
                    display: 'inline-flex',
                    alignItems: 'center',
                    overflow: 'hidden',
                  }}
                >
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {truncateCategoryName(name)}
                  </span>
                </Tag>
              </Tooltip>
              {confidenceBadge}
            </Space>
          )
        }
        if (record.suggested_category_name) {
          return (
            <Tooltip title={`Предложение AI (${((record.category_confidence || 0) * 100).toFixed(0)}%)`}>
              <Tag
                color="orange"
                style={{
                  cursor: 'pointer',
                  maxWidth: 140,
                  display: 'inline-flex',
                  alignItems: 'center',
                }}
                onClick={() => openCategorizeDrawer(record)}
              >
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {truncateCategoryName(record.suggested_category_name)}
                </span>
                <span style={{ marginLeft: 4 }}>?</span>
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
              title={
                <Space size={4}>
                  <span>Расход</span>
                  {activeQuickFilter === 'debit' && <Tag color="red" style={{ fontSize: '10px', margin: 0 }}>фильтр</Tag>}
                </Space>
              }
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
              title={
                <Space size={4}>
                  <span>Приход</span>
                  {activeQuickFilter === 'credit' && <Tag color="green" style={{ fontSize: '10px', margin: 0 }}>фильтр</Tag>}
                </Space>
              }
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
              title={
                <Space size={4}>
                  <span>Требуют проверки</span>
                  {activeQuickFilter === 'needs_review' && <Tag color="orange" style={{ fontSize: '10px', margin: 0 }}>фильтр</Tag>}
                </Space>
              }
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
            selectedOrganizationId={filters.organization_id}
            onAccountSelect={(accountNumber, organizationId) => {
              setFilters((prev) => ({
                ...prev,
                account_number: accountNumber,
                organization_id: organizationId,
              }))
            }}
          />
        </Col>

        {/* Right column - Filters and Table */}
        <Col xs={24} md={18} lg={20}>
          {/* Active Filters Indicator */}
          {hasActiveFilters && (
            <Card size="small" style={{ marginBottom: 8, background: '#f0f5ff', borderColor: '#1890ff' }}>
              <Space wrap size={[8, 8]}>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  <strong>Активные фильтры:</strong>
                </Text>
                {filters.account_number && (
                  <Tag
                    closable
                    onClose={() => setFilters((prev) => ({ ...prev, account_number: undefined, organization_id: undefined }))}
                    color="blue"
                  >
                    Счёт: {filters.account_number}
                  </Tag>
                )}
                {filters.search && (
                  <Tag
                    closable
                    onClose={() => setFilters((prev) => ({ ...prev, search: undefined }))}
                    color="blue"
                  >
                    Поиск: {filters.search}
                  </Tag>
                )}
                {filters.status && (
                  <Tag
                    closable
                    onClose={() => setFilters((prev) => ({ ...prev, status: undefined }))}
                    color="blue"
                  >
                    Статус: {statusLabels[filters.status]}
                  </Tag>
                )}
                {filters.only_unprocessed && (
                  <Tag
                    closable
                    onClose={() => setFilters((prev) => ({ ...prev, only_unprocessed: undefined }))}
                    color="orange"
                  >
                    Необработанные
                  </Tag>
                )}
                {filters.transaction_type && (
                  <Tag
                    closable
                    onClose={() => setFilters((prev) => ({ ...prev, transaction_type: undefined }))}
                    color={filters.transaction_type === 'DEBIT' ? 'red' : 'green'}
                  >
                    {filters.transaction_type === 'DEBIT' ? 'Расход' : 'Приход'}
                  </Tag>
                )}
                {filters.payment_source && (
                  <Tag
                    closable
                    onClose={() => setFilters((prev) => ({ ...prev, payment_source: undefined }))}
                    color="blue"
                  >
                    Источник: {filters.payment_source === 'BANK' ? 'Банк' : 'Касса'}
                  </Tag>
                )}
                {(filters.date_from || filters.date_to) && (
                  <Tag
                    closable
                    onClose={() => setFilters((prev) => ({ ...prev, date_from: undefined, date_to: undefined }))}
                    color="blue"
                  >
                    Период: {filters.date_from || '...'} — {filters.date_to || '...'}
                  </Tag>
                )}
              </Space>
            </Card>
          )}

          {/* Filters */}
          <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="Поиск..."
                prefix={<SearchOutlined />}
                style={{ width: 200 }}
                value={filters.search}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, search: e.target.value }))
                }
                allowClear
              />
              <Select
                placeholder="Статус"
                style={{ width: 160 }}
                value={filters.status}
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
                value={filters.transaction_type}
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
                value={filters.payment_source}
                allowClear
                onChange={(value) =>
                  setFilters((prev) => ({ ...prev, payment_source: value }))
                }
                options={[
                  { value: 'BANK', label: 'Банк' },
                  { value: 'CASH', label: 'Касса' },
                ]}
              />
              <CategoryTreeSelect
                placeholder="Категория"
                style={{ width: 220 }}
                onChange={(value) =>
                  setFilters((prev) => ({ ...prev, category_id: value }))
                }
                value={filters.category_id}
              />
              <RangePicker
                value={filters.date_from && filters.date_to ? [dayjs(filters.date_from), dayjs(filters.date_to)] : null}
                onChange={(dates) => {
                  setFilters((prev) => ({
                    ...prev,
                    date_from: dates?.[0]?.format('YYYY-MM-DD'),
                    date_to: dates?.[1]?.format('YYYY-MM-DD'),
                  }))
                }}
              />
              {hasActiveFilters && (
                <Button
                  icon={<ClearOutlined />}
                  onClick={handleClearAllFilters}
                  type="dashed"
                  danger
                >
                  Сбросить все фильтры
                </Button>
              )}
            </Space>
          </Col>
          <Col>
            <Space>
              {selectedRowKeys.length > 0 && (
                <>
                  <CategoryTreeSelect
                    placeholder="Назначить категорию"
                    style={{ width: 220 }}
                    onChange={(value) => {
                      if (value) {
                        Modal.confirm({
                          title: `Назначить категорию для ${selectedRowKeys.length} операций?`,
                          onOk: () => bulkCategorizeMutation.mutate(value),
                        })
                      }
                    }}
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
              <Popconfirm
                title={
                  <div>
                    <div>Удалить все транзакции?</div>
                    <div style={{ fontSize: '12px', color: '#999', marginTop: 4 }}>
                      {totalTransactions > 0 ? `Будет удалено ${totalTransactions} операций` : 'Нет операций для удаления'}
                    </div>
                  </div>
                }
                onConfirm={() => deleteByFilterMutation.mutate()}
                okText="Да, удалить всё"
                cancelText="Отмена"
                okButtonProps={{ danger: true }}
              >
                <Button
                  danger
                  icon={<DeleteOutlined />}
                  loading={deleteByFilterMutation.isPending}
                  disabled={totalTransactions === 0}
                >
                  Удалить все ({totalTransactions})
                </Button>
              </Popconfirm>
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
            current: currentPage,
            pageSize: pageSize,
            total: totalTransactions,
            showSizeChanger: true,
            showTotal: (total) => `Всего: ${total}`,
            onChange: (page, size) => {
              setCurrentPage(page)
              setPageSize(size || 50)
              setFilters((prev) => ({
                ...prev,
                limit: size || 50,
                offset: ((page - 1) * (size || 50)),
              }))
            },
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
                  {selectedTransaction.vat_amount && selectedTransaction.vat_amount > 0 && (
                    <div style={{ fontSize: '11px', color: '#8c8c8c' }}>
                      НДС {selectedTransaction.vat_rate}%: {formatAmount(selectedTransaction.vat_amount)}
                      <br />
                      Без НДС: {formatAmount(Number(selectedTransaction.amount) - Number(selectedTransaction.vat_amount))}
                    </div>
                  )}
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
                <CategoryTreeSelect
                  placeholder="Выберите категорию"
                />
              </Form.Item>

              {/* VAT Fields */}
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="vat_rate" label="Ставка НДС (%)">
                    <Select
                      placeholder="Выберите ставку"
                      allowClear
                      options={[
                        { label: '0%', value: 0 },
                        { label: '10%', value: 10 },
                        { label: '20%', value: 20 },
                      ]}
                      onChange={(rate) => {
                        if (rate && selectedTransaction) {
                          const vatAmount = (Number(selectedTransaction.amount) * rate) / (100 + rate)
                          form.setFieldsValue({ vat_amount: Number(vatAmount.toFixed(2)) })
                        } else {
                          form.setFieldsValue({ vat_amount: undefined })
                        }
                      }}
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="vat_amount" label="Сумма НДС (₽)">
                    <Input type="number" step="0.01" placeholder="0.00" />
                  </Form.Item>
                </Col>
              </Row>

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

      {/* Модалка предложений правил */}
      <RuleSuggestionsModal
        visible={ruleSuggestionsVisible}
        suggestions={ruleSuggestions}
        onClose={() => {
          setRuleSuggestionsVisible(false)
          setRuleSuggestions(null)
        }}
        onRuleCreated={() => {
          // Обновляем данные после создания правила
          queryClient.invalidateQueries({ queryKey: ['categorization-rules'] })
          // Обновляем транзакции если правило было применено к существующим
          queryClient.invalidateQueries({ queryKey: ['bank-transactions'] })
          queryClient.invalidateQueries({ queryKey: ['bank-transactions-stats'] })
        }}
      />
    </div>
  )
}
