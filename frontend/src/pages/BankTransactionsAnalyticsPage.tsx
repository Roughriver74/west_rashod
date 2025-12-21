import React, { useState, useMemo } from 'react'
import { Card, Tabs, Select, DatePicker, Row, Col, Button, Space, message } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import type { Dayjs } from 'dayjs'
import { bankTransactionsApi } from '../api/bankTransactions'
import BankTransactionsKPICards from '../components/bank/BankTransactionsKPICards'
import CashFlowChart from '../components/bank/CashFlowChart'
import DailyFlowChart from '../components/bank/DailyFlowChart'
import ActivityHeatmapChart from '../components/bank/ActivityHeatmapChart'
import StatusTimelineChart from '../components/bank/StatusTimelineChart'
import CategoryBreakdownChart from '../components/bank/CategoryBreakdownChart'
import CounterpartyAnalysisChart from '../components/bank/CounterpartyAnalysisChart'
import RegionalDistributionChart from '../components/bank/RegionalDistributionChart'
import ProcessingEfficiencyChart from '../components/bank/ProcessingEfficiencyChart'
import ConfidenceScatterChart from '../components/bank/ConfidenceScatterChart'
import TransactionInsightsPanel from '../components/bank/TransactionInsightsPanel'
import RegularPaymentsInsights from '../components/bank/RegularPaymentsInsights'
import ExhibitionSpendingInsights from '../components/bank/ExhibitionSpendingInsights'
import type { BankTransactionType, BankTransactionStatus } from '../types/bankTransaction'

const { TabPane } = Tabs
const { RangePicker } = DatePicker
const { Option } = Select
import { useAvailableYearsOptions } from '../hooks/useAvailableYears'

const BankTransactionsAnalyticsPage: React.FC = () => {
  const { options: yearOptions } = useAvailableYearsOptions()

  // Filter states
  const [year, setYear] = useState<number>(new Date().getFullYear())
  const [month, setMonth] = useState<number | undefined>(undefined)
  const [quarter, setQuarter] = useState<number | undefined>(undefined)
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [transactionType, setTransactionType] = useState<BankTransactionType | undefined>(undefined)
  const [paymentSource, setPaymentSource] = useState<'BANK' | 'CASH' | undefined>(undefined)
  const [status, setStatus] = useState<BankTransactionStatus | undefined>(undefined)
  const [region, setRegion] = useState<string | undefined>(undefined)

  // Build query params
  const analyticsParams = useMemo(() => {
    const params: any = {
      
      compare_previous_period: true,
    }

    if (dateRange && dateRange[0] && dateRange[1]) {
      params.date_from = dateRange[0].format('YYYY-MM-DD')
      params.date_to = dateRange[1].format('YYYY-MM-DD')
    } else {
      if (year) params.year = year
      if (month) params.month = month
      if (quarter) params.quarter = quarter
    }

    if (transactionType) params.transaction_type = transactionType
    if (paymentSource) params.payment_source = paymentSource
    if (status) params.status = status
    if (region) params.region = region

    return params
  }, [selectedDepartment, year, month, quarter, dateRange, transactionType, paymentSource, status, region])

  // Fetch analytics data
  const {
    data: analytics,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['bank-transactions-analytics', analyticsParams],
    queryFn: () => bankTransactionsApi.getAnalytics(analyticsParams),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Handle date range change
  const handleDateRangeChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      setDateRange([dates[0], dates[1]])
    } else {
      setDateRange(null)
    }
  }

  // Reset filters
  const handleResetFilters = () => {
    setYear(new Date().getFullYear())
    setMonth(undefined)
    setQuarter(undefined)
    setDateRange(null)
    setTransactionType(undefined)
    setPaymentSource(undefined)
    setStatus(undefined)
    setRegion(undefined)
  }

  // Handle export (placeholder)
  const handleExport = () => {
    message.info('Экспорт в разработке')
    // TODO: Implement export functionality
  }

  if (error) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0', color: '#ff4d4f' }}>
          Ошибка загрузки данных: {(error as Error).message}
        </div>
      </Card>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ marginBottom: 24 }}>📊 Аналитика банковских транзакций</h1>

      {/* Filters */}
      <Card style={{ marginBottom: 24 }} title="🔍 Фильтры">
        <Row gutter={[16, 16]}>
          {/* Date Filters */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#8c8c8c' }}>
              Год
            </label>
            <Select
              value={year}
              onChange={setYear}
              style={{ width: '100%' }}
              disabled={!!dateRange}
            >
              {yearOptions.map((option) => (
                <Option key={option.value} value={option.value}>
                  {option.label}
                </Option>
              ))}
            </Select>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#8c8c8c' }}>
              Месяц
            </label>
            <Select
              value={month}
              onChange={setMonth}
              style={{ width: '100%' }}
              placeholder="Все месяцы"
              allowClear
              disabled={!!dateRange || !!quarter}
            >
              {[
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
              ].map((m) => (
                <Option key={m.value} value={m.value}>
                  {m.label}
                </Option>
              ))}
            </Select>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#8c8c8c' }}>
              Квартал
            </label>
            <Select
              value={quarter}
              onChange={setQuarter}
              style={{ width: '100%' }}
              placeholder="Все кварталы"
              allowClear
              disabled={!!dateRange || !!month}
            >
              <Option value={1}>Q1 (Янв-Мар)</Option>
              <Option value={2}>Q2 (Апр-Июн)</Option>
              <Option value={3}>Q3 (Июл-Сен)</Option>
              <Option value={4}>Q4 (Окт-Дек)</Option>
            </Select>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#8c8c8c' }}>
              Произвольный период
            </label>
            <RangePicker
              value={dateRange}
              onChange={handleDateRangeChange}
              style={{ width: '100%' }}
              format="YYYY-MM-DD"
            />
          </Col>

          {/* Transaction Filters */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#8c8c8c' }}>
              Тип транзакции
            </label>
            <Select
              value={transactionType}
              onChange={setTransactionType}
              style={{ width: '100%' }}
              placeholder="Все типы"
              allowClear
            >
              <Option value="DEBIT">DEBIT (Расход)</Option>
              <Option value="CREDIT">CREDIT (Приход)</Option>
            </Select>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#8c8c8c' }}>
              Источник платежа
            </label>
            <Select
              value={paymentSource}
              onChange={setPaymentSource}
              style={{ width: '100%' }}
              placeholder="Все источники"
              allowClear
            >
              <Option value="BANK">BANK (Банк)</Option>
              <Option value="CASH">CASH (Касса)</Option>
            </Select>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#8c8c8c' }}>
              Статус
            </label>
            <Select
              value={status}
              onChange={setStatus}
              style={{ width: '100%' }}
              placeholder="Все статусы"
              allowClear
            >
              <Option value="NEW">NEW</Option>
              <Option value="CATEGORIZED">CATEGORIZED</Option>
              <Option value="MATCHED">MATCHED</Option>
              <Option value="APPROVED">APPROVED</Option>
              <Option value="NEEDS_REVIEW">NEEDS_REVIEW</Option>
              <Option value="IGNORED">IGNORED</Option>
            </Select>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#8c8c8c' }}>
              Регион
            </label>
            <Select
              value={region}
              onChange={setRegion}
              style={{ width: '100%' }}
              placeholder="Все регионы"
              allowClear
            >
              <Option value="MOSCOW">Москва</Option>
              <Option value="SPB">Санкт-Петербург</Option>
              <Option value="REGIONS">Регионы</Option>
              <Option value="FOREIGN">Заграница</Option>
            </Select>
          </Col>

          {/* Action Buttons */}
          <Col xs={24}>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
                Обновить
              </Button>
              <Button onClick={handleResetFilters}>Сбросить фильтры</Button>
              <Button icon={<DownloadOutlined />} onClick={handleExport}>
                Экспорт Excel
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* KPI Cards */}
      {analytics && (
        <>
          <BankTransactionsKPICards kpis={analytics.kpis} loading={isLoading} />
          <div style={{ marginTop: 24 }}>
            <TransactionInsightsPanel
              monthlyFlow={analytics.monthly_flow}
              topCategories={analytics.top_categories}
              topCounterparties={analytics.top_counterparties}
              loading={isLoading}
            />
          </div>
        </>
      )}

      {/* Charts Tabs */}
      <Card style={{ marginTop: 24 }}>
        <Tabs defaultActiveKey="monthly">
          <TabPane tab="📈 Временная динамика" key="monthly">
            <CashFlowChart
              data={analytics?.monthly_flow || []}
              loading={isLoading}
            />
          </TabPane>

          <TabPane tab="📅 Ежедневные тренды" key="daily">
            <DailyFlowChart
              data={analytics?.daily_flow || []}
              loading={isLoading}
            />
            <div style={{ marginTop: 24 }}>
              <StatusTimelineChart
                data={analytics?.status_timeline || []}
                loading={isLoading}
              />
            </div>
          </TabPane>

          <TabPane tab="🔥 Активность" key="activity">
            <ActivityHeatmapChart
              data={analytics?.activity_heatmap || []}
              loading={isLoading}
            />
          </TabPane>

          <TabPane tab="📊 Категории" key="categories">
            <CategoryBreakdownChart
              topCategories={analytics?.top_categories || []}
              categoryTypeDistribution={analytics?.category_type_distribution || []}
              loading={isLoading}
            />
          </TabPane>

          <TabPane tab="👥 Контрагенты" key="counterparties">
            <CounterpartyAnalysisChart
              data={analytics?.top_counterparties || []}
              loading={isLoading}
            />
          </TabPane>

          <TabPane tab="🌍 География" key="geo">
            <RegionalDistributionChart
              regionalData={analytics?.regional_distribution || []}
              sourceData={analytics?.source_distribution || []}
              loading={isLoading}
            />
          </TabPane>

          <TabPane tab="⚙️ Обработка и AI" key="processing">
            <ProcessingEfficiencyChart
              processingFunnel={analytics?.processing_funnel || { stages: [], total_count: 0, conversion_rate_to_approved: 0 }}
              aiPerformance={analytics?.ai_performance || {
                confidence_distribution: [],
                avg_confidence: 0,
                high_confidence_count: 0,
                high_confidence_percent: 0,
                low_confidence_count: 0,
                low_confidence_percent: 0
              }}
              lowConfidenceItems={analytics?.low_confidence_items || []}
              loading={isLoading}
            />
            <div style={{ marginTop: 24 }}>
              <ConfidenceScatterChart
                data={analytics?.confidence_scatter || []}
                loading={isLoading}
              />
            </div>
          </TabPane>

          <TabPane tab="🔁 Регулярные платежи" key="regular">
            <RegularPaymentsInsights
              data={analytics?.regular_payments || []}
              loading={isLoading}
            />
          </TabPane>

          <TabPane tab="🎪 События и выставки" key="events">
            <ExhibitionSpendingInsights
              data={analytics?.exhibitions || []}
              loading={isLoading}
            />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default BankTransactionsAnalyticsPage
