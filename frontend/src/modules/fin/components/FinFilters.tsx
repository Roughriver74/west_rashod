import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Card,
  DatePicker,
  Select,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Divider,
  Tag,
} from 'antd'
import {
  ReloadOutlined,
  SettingOutlined,
  CalendarOutlined,
} from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import {
  useFinFilterStore,
  DEFAULT_DATE_FROM,
  DEFAULT_DATE_TO,
  useFinFilterValues,
} from '../stores/finFilterStore'
import { getOrganizations, getUniquePayers, getContracts } from '../api/finApi'

const { Text } = Typography
const { RangePicker } = DatePicker

// Date range presets
const getDateRange = (type: string): { from: string; to: string } => {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const formatDate = (date: Date): string => date.toISOString().split('T')[0]

  switch (type) {
    case 'today':
      return { from: formatDate(today), to: formatDate(today) }
    case 'week': {
      const weekStart = new Date(today)
      weekStart.setDate(today.getDate() - today.getDay() + 1)
      return { from: formatDate(weekStart), to: formatDate(today) }
    }
    case 'month': {
      const monthStart = new Date(today.getFullYear(), today.getMonth(), 1)
      return { from: formatDate(monthStart), to: formatDate(today) }
    }
    case 'quarter': {
      const quarterStart = new Date(today.getFullYear(), Math.floor(today.getMonth() / 3) * 3, 1)
      return { from: formatDate(quarterStart), to: formatDate(today) }
    }
    case 'year': {
      const yearStart = new Date(today.getFullYear(), 0, 1)
      return { from: formatDate(yearStart), to: formatDate(today) }
    }
    case 'prev-month': {
      const prevMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1)
      const prevMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0)
      return { from: formatDate(prevMonthStart), to: formatDate(prevMonthEnd) }
    }
    case 'prev-quarter': {
      const currentQuarter = Math.floor(today.getMonth() / 3)
      const prevQuarterStart = new Date(today.getFullYear(), (currentQuarter - 1) * 3, 1)
      const prevQuarterEnd = new Date(today.getFullYear(), currentQuarter * 3, 0)
      return { from: formatDate(prevQuarterStart), to: formatDate(prevQuarterEnd) }
    }
    case 'prev-year': {
      const prevYearStart = new Date(today.getFullYear() - 1, 0, 1)
      const prevYearEnd = new Date(today.getFullYear() - 1, 11, 31)
      return { from: formatDate(prevYearStart), to: formatDate(prevYearEnd) }
    }
    default:
      return { from: DEFAULT_DATE_FROM, to: DEFAULT_DATE_TO }
  }
}

// Generate years list
const generateYears = (): number[] => {
  const currentYear = new Date().getFullYear()
  const years: number[] = []
  for (let year = 2020; year <= currentYear + 3; year++) {
    years.push(year)
  }
  return years.reverse()
}

const MONTHS = [
  { value: 1, label: 'Январь' },
  { value: 2, label: 'Февраль' },
  { value: 3, label: 'Март' },
  { value: 4, label: 'Апрель' },
  { value: 5, label: 'Май' },
  { value: 6, label: 'Июнь' },
  { value: 7, label: 'Июль' },
  { value: 8, label: 'Август' },
  { value: 9, label: 'Сентябрь' },
  { value: 10, label: 'Октябрь' },
  { value: 11, label: 'Ноябрь' },
  { value: 12, label: 'Декабрь' },
]

export default function FinFilters() {
  const setFilters = useFinFilterStore(state => state.setFilters)
  const resetFilters = useFinFilterStore(state => state.resetFilters)
  const { dateFrom, dateTo, organizations, payers, excludedPayers, contracts } = useFinFilterValues()

  const [showSettings, setShowSettings] = useState(false)

  const [localDateFrom, setLocalDateFrom] = useState(dateFrom)
  const [localDateTo, setLocalDateTo] = useState(dateTo)
  const [localOrganizations, setLocalOrganizations] = useState<string[]>(organizations)
  const [localPayers, setLocalPayers] = useState<string[]>(payers)
  const [localExcludedPayers, setLocalExcludedPayers] = useState<string[]>(excludedPayers)
  const [localContracts, setLocalContracts] = useState<string[]>(contracts)
  const [selectedQuickRange, setSelectedQuickRange] = useState<string | null>(null)

  const [selectedYear, setSelectedYear] = useState<number | null>(null)
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null)

  const years = useMemo(() => generateYears(), [])

  useEffect(() => setLocalDateFrom(dateFrom), [dateFrom])
  useEffect(() => setLocalDateTo(dateTo), [dateTo])
  useEffect(() => setLocalOrganizations(organizations), [organizations])
  useEffect(() => setLocalPayers(payers), [payers])
  useEffect(() => setLocalExcludedPayers(excludedPayers), [excludedPayers])
  useEffect(() => setLocalContracts(contracts), [contracts])

  // Fetch organizations
  const { data: orgsData } = useQuery({
    queryKey: ['fin', 'organizations'],
    queryFn: () => getOrganizations(),
    staleTime: 5 * 60 * 1000,
  })

  // Fetch payers
  const { data: payersData } = useQuery({
    queryKey: ['fin', 'payers'],
    queryFn: () => getUniquePayers({ limit: 1000000 }),
    staleTime: 5 * 60 * 1000,
  })

  // Fetch contracts
  const { data: contractsData, isLoading: contractsLoading } = useQuery({
    queryKey: ['fin', 'contracts', localOrganizations],
    queryFn: () => getContracts({ limit: 1000000 }),
    staleTime: 2 * 60 * 1000,
  })

  const organizationOptions = useMemo(
    () => (orgsData?.items || []).map(org => ({ value: org.name, label: org.name })),
    [orgsData]
  )

  // Own organizations to exclude from payers
  const ownOrganizations = useMemo(
    () =>
      new Set([
        'Вест', 'ВЕСТ', 'вест', 'Лекпрофи', 'ЛЕКПРОФИ', 'лекпрофи',
        'Мирумед', 'МИРУМЕД', 'мирумед', 'АртБГ', 'АРТБГ', 'артбг',
        'Вест Дент', 'ВЕСТ ДЕНТ', 'вест дент', 'Вест Стом', 'ВЕСТ СТОМ', 'вест стом',
        'Вест Торг', 'ВЕСТ ТОРГ', 'вест торг',
        'ООО "Вест"', 'ООО "Лекпрофи"', 'ООО "Мирумед"', 'ООО "АртБГ"',
        'ООО "Вест Дент"', 'ООО "Вест Стом"', 'ООО "Вест Торг"',
        'ООО «Вест»', 'ООО «Лекпрофи»', 'ООО «Мирумед»', 'ООО «АртБГ»',
        'ООО «Вест Дент»', 'ООО «Вест Стом»', 'ООО «Вест Торг»',
      ]),
    []
  )

  // All payer options
  const allPayerOptions = useMemo(
    () => (payersData?.items || []).map(payer => ({ value: payer, label: payer })),
    [payersData]
  )

  // Payer options without own orgs
  const payerOptions = useMemo(
    () =>
      (payersData?.items || [])
        .filter(payer => {
          const name = payer?.toLowerCase() || ''
          const isOwnOrg = Array.from(ownOrganizations).some(org => name.includes(org.toLowerCase()))
          const isExcluded = localExcludedPayers.some(excl => name === excl.toLowerCase())
          return !isOwnOrg && !isExcluded
        })
        .map(payer => ({ value: payer, label: payer })),
    [payersData, ownOrganizations, localExcludedPayers]
  )

  const contractOptions = useMemo(
    () =>
      (contractsData?.items || [])
        .filter(contract => Boolean(contract.contract_number))
        .map(contract => ({ value: contract.contract_number, label: contract.contract_number })),
    [contractsData]
  )

  const periodLabel = useMemo(() => {
    if (localDateFrom && localDateTo) {
      return `${dayjs(localDateFrom).format('DD.MM.YYYY')} — ${dayjs(localDateTo).format('DD.MM.YYYY')}`
    }
    return 'Весь период'
  }, [localDateFrom, localDateTo])

  // Quick filter handlers
  const handleQuickFilter = (type: string) => {
    setSelectedQuickRange(type)
    const range = getDateRange(type)
    setLocalDateFrom(range.from)
    setLocalDateTo(range.to)
    setSelectedYear(null)
    setSelectedMonth(null)
  }

  const handleYearChange = (year: number | null) => {
    setSelectedYear(year)
    setSelectedMonth(null)
    if (year) {
      setLocalDateFrom(`${year}-01-01`)
      setLocalDateTo(`${year}-12-31`)
    }
  }

  const handleMonthChange = (month: number | null) => {
    setSelectedMonth(month)
    if (month && selectedYear) {
      const lastDay = new Date(selectedYear, month, 0).getDate()
      const monthStr = month.toString().padStart(2, '0')
      setLocalDateFrom(`${selectedYear}-${monthStr}-01`)
      setLocalDateTo(`${selectedYear}-${monthStr}-${lastDay}`)
    }
  }

  const handleDateRangeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      setLocalDateFrom(dates[0].format('YYYY-MM-DD'))
      setLocalDateTo(dates[1].format('YYYY-MM-DD'))
      setSelectedYear(null)
      setSelectedMonth(null)
    }
  }

  const arraysEqual = (a: string[], b: string[]) => {
    if (a.length !== b.length) return false
    const sortedA = [...a].sort()
    const sortedB = [...b].sort()
    return sortedA.every((value, index) => value === sortedB[index])
  }

  const hasChanges =
    localDateFrom !== dateFrom ||
    localDateTo !== dateTo ||
    !arraysEqual(localOrganizations, organizations) ||
    !arraysEqual(localPayers, payers) ||
    !arraysEqual(localExcludedPayers, excludedPayers) ||
    !arraysEqual(localContracts, contracts)

  const handleApply = () => {
    setFilters({
      dateFrom: localDateFrom,
      dateTo: localDateTo,
      organizations: localOrganizations,
      payers: localPayers,
      excludedPayers: localExcludedPayers,
      contracts: localContracts,
    })
  }

  const handleReset = () => {
    resetFilters()
    setLocalDateFrom(DEFAULT_DATE_FROM)
    setLocalDateTo(DEFAULT_DATE_TO)
    setLocalOrganizations([])
    setLocalPayers([])
    setLocalExcludedPayers([])
    setLocalContracts([])
    setSelectedYear(null)
    setSelectedMonth(null)
    setSelectedQuickRange(null)
  }

  return (
    <Card size="small" className="fin-filter-card" bodyStyle={{ padding: 16 }}>
      <div className="fin-filter-card__header">
        <div>
          <Text strong style={{ fontSize: 15 }}>Фильтры по кредитам</Text>
          <div className="fin-filter-card__chips">
            <Tag icon={<CalendarOutlined />} color="blue">{periodLabel}</Tag>
            <Tag color="geekblue">Орг: {localOrganizations.length || 'все'}</Tag>
            <Tag color="geekblue">Плательщики: {localPayers.length || 'все'}</Tag>
            <Tag color="geekblue">Договоры: {localContracts.length || 'все'}</Tag>
            {hasChanges && <Tag color="orange">Изменено</Tag>}
          </div>
        </div>
        <Space size={8} wrap>
          <Button
            type="primary"
            onClick={handleApply}
            disabled={!hasChanges}
          >
            Применить
          </Button>
          <Button icon={<ReloadOutlined />} onClick={handleReset} />
          <Button
            icon={<SettingOutlined />}
            type={showSettings ? 'primary' : 'default'}
            onClick={() => setShowSettings(!showSettings)}
          />
        </Space>
      </div>

      <div className="fin-filter-quick">
        <div className="fin-filter-quick__row">
          <Text type="secondary">Текущие:</Text>
          <Button size="small" type={selectedQuickRange === 'today' ? 'primary' : 'default'} onClick={() => handleQuickFilter('today')}>Сегодня</Button>
          <Button size="small" type={selectedQuickRange === 'week' ? 'primary' : 'default'} onClick={() => handleQuickFilter('week')}>Неделя</Button>
          <Button size="small" type={selectedQuickRange === 'month' ? 'primary' : 'default'} onClick={() => handleQuickFilter('month')}>Месяц</Button>
          <Button size="small" type={selectedQuickRange === 'quarter' ? 'primary' : 'default'} onClick={() => handleQuickFilter('quarter')}>Квартал</Button>
          <Button size="small" type={selectedQuickRange === 'year' ? 'primary' : 'default'} onClick={() => handleQuickFilter('year')}>Год</Button>
        </div>
        <div className="fin-filter-quick__row" style={{ marginTop: 6 }}>
          <Text type="secondary">Предыдущие:</Text>
          <Button size="small" type={selectedQuickRange === 'prev-month' ? 'primary' : 'default'} onClick={() => handleQuickFilter('prev-month')}>Месяц</Button>
          <Button size="small" type={selectedQuickRange === 'prev-quarter' ? 'primary' : 'default'} onClick={() => handleQuickFilter('prev-quarter')}>Квартал</Button>
          <Button size="small" type={selectedQuickRange === 'prev-year' ? 'primary' : 'default'} onClick={() => handleQuickFilter('prev-year')}>Год</Button>
        </div>
      </div>

      <Row gutter={[12, 12]}>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>Год:</Text>
            <Select
              value={selectedYear}
              onChange={handleYearChange}
              style={{ width: '100%' }}
              placeholder="Все годы"
              allowClear
              options={years.map(year => ({ value: year, label: year.toString() }))}
            />
          </Space>
        </Col>

        <Col xs={24} sm={12} md={8} lg={6}>
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>Месяц:</Text>
            <Select
              value={selectedMonth}
              onChange={handleMonthChange}
              style={{ width: '100%' }}
              placeholder="Весь год"
              allowClear
              disabled={!selectedYear}
              options={MONTHS.map(m => ({ value: m.value, label: m.label }))}
            />
          </Space>
        </Col>

        <Col xs={24} md={12} lg={8}>
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>Период:</Text>
            <RangePicker
              value={[dayjs(localDateFrom), dayjs(localDateTo)]}
              onChange={handleDateRangeChange}
              format="DD.MM.YYYY"
              style={{ width: '100%' }}
            />
          </Space>
        </Col>

        <Col xs={24} md={12} lg={8}>
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>Организация:</Text>
            <Select
              mode="multiple"
              value={localOrganizations}
              onChange={setLocalOrganizations}
              style={{ width: '100%' }}
              placeholder="Все организации"
              options={organizationOptions}
              maxTagCount={2}
              allowClear
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Space>
        </Col>

        <Col xs={24} md={12} lg={8}>
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>Плательщик:</Text>
            <Select
              mode="multiple"
              value={localPayers}
              onChange={setLocalPayers}
              style={{ width: '100%' }}
              placeholder="Все плательщики"
              options={payerOptions}
              maxTagCount={2}
              allowClear
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Space>
        </Col>

        <Col xs={24} md={12} lg={8}>
          <Space direction="vertical" size={2} style={{ width: '100%' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>Договоры:</Text>
            <Select
              mode="multiple"
              value={localContracts}
              onChange={setLocalContracts}
              style={{ width: '100%' }}
              placeholder="Все договоры"
              options={contractOptions}
              maxTagCount={2}
              allowClear
              loading={contractsLoading}
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Space>
        </Col>
      </Row>

      {/* Settings panel */}
      {showSettings && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <SettingOutlined />
              <Text strong>Исключить плательщиков:</Text>
              <Text type="secondary">(эти плательщики не будут показываться в данных)</Text>
            </Space>
            <Select
              mode="multiple"
              value={localExcludedPayers}
              onChange={setLocalExcludedPayers}
              style={{ width: '100%', maxWidth: 600 }}
              placeholder="Выберите плательщиков для исключения..."
              options={allPayerOptions}
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
            {localExcludedPayers.length > 0 && (
              <Tag color="warning">Исключено: {localExcludedPayers.length} плательщик(ов)</Tag>
            )}
          </Space>
        </>
      )}
    </Card>
  )
}
