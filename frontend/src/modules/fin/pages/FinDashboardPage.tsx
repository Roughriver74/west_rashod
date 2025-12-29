/**
 * Fin Dashboard Page - Credit Analytics Dashboard
 * Adapted from west_fin CreditDashboard.tsx for credit-focused analytics
 */
import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import {
  Row,
  Col,
  Card,
  Statistic,
  Typography,
  Space,
  Button,
  Empty,
  Tabs,
  Collapse,
  Tag,
  Badge,
  TabsProps,
  Divider,
} from 'antd';
import {
  DollarOutlined,
  BankOutlined,
  PercentageOutlined,
  WalletOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  TableOutlined,
  LineChartOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import {
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  BarChart,
  Cell,
  PieChart,
  Pie,
} from 'recharts';
import { motion } from 'framer-motion';

import { useFinFilterValues } from '../stores/finFilterStore';
import {
  getCreditBalances,
  getContractsSummary,
  getMonthlyEfficiency,
  getOrgEfficiency,
} from '../api/finApi';
import { formatFullAmount, formatShortAmount, formatAmount } from '../utils/formatters';
import { useDebounce } from '../hooks/usePerformance';
import { buildFilterPayload } from '../utils/filterParams';
import { VirtualTable, VirtualTableColumn } from '../components/VirtualTable';
import { ExportButton, ExportColumn } from '../components/ExportButton';
import { DashboardSkeleton } from '../components/SkeletonLoader';
import '../styles/fin-theme.css';

const { Text, Paragraph } = Typography;

// Color palette
const COLORS = {
  primary: '#1890ff',
  success: '#52c41a',
  warning: '#faad14',
  error: '#ff4d4f',
  purple: '#722ed1',
  cyan: '#13c2c2',
};

const PIE_COLORS = ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#eb2f96', '#13c2c2', '#a0d911'];

// Contract item type for the table
interface ContractItem {
  contractId: number;
  contractNumber: string;
  organization: string;
  payer: string;
  totalPaid: number;
  principal: number;
  interest: number;
  totalReceived: number;
  balance: number;
  openingBalance: number;
  paidPercent: number;
  operationsCount: number;
  lastPayment: string | null;
  firstReceipt: string | null;
}

export default function FinDashboardPage() {
  const navigate = useNavigate();
  const filters = useFinFilterValues();
  const debouncedFilters = useDebounce(filters, 500);
  const [activeTab, setActiveTab] = useState<'debt' | 'activity'>('debt');

  const filterParams = useMemo(
    () =>
      buildFilterPayload(debouncedFilters, {
        includeDefaultDateTo: true,
        includeContract: true,
      }),
    [debouncedFilters]
  );

  const balancesQuery = useQuery({
    queryKey: ['fin', 'credit-balances', filterParams],
    queryFn: () => getCreditBalances(filterParams),
    placeholderData: keepPreviousData,
    staleTime: 2 * 60 * 1000,
  });

  const contractsQuery = useQuery({
    queryKey: ['fin', 'contracts-summary', { ...filterParams, page: 1, limit: 100000 }],
    queryFn: () => getContractsSummary({ ...filterParams, page: 1, limit: 100000 }),
    placeholderData: keepPreviousData,
    staleTime: 2 * 60 * 1000,
  });

  const monthlyQuery = useQuery({
    queryKey: ['fin', 'monthly-efficiency', filterParams],
    queryFn: () => getMonthlyEfficiency(filterParams),
    placeholderData: keepPreviousData,
    staleTime: 2 * 60 * 1000,
  });

  const orgQuery = useQuery({
    queryKey: ['fin', 'org-efficiency', filterParams],
    queryFn: () => getOrgEfficiency(filterParams),
    placeholderData: keepPreviousData,
    staleTime: 2 * 60 * 1000,
  });

  const balances = balancesQuery.data;
  const contracts: ContractItem[] = contractsQuery.data?.data || [];
  const monthlyData = monthlyQuery.data || [];
  const orgData = orgQuery.data || [];

  const isLoading = balancesQuery.isLoading && !balances;

  const contractTotals = useMemo(() => {
    return contracts.reduce(
      (acc, contract) => ({
        totalPaid: acc.totalPaid + (contract.totalPaid || 0),
        principal: acc.principal + (contract.principal || 0),
        interest: acc.interest + (contract.interest || 0),
        balance: acc.balance + (contract.balance || 0),
        received: acc.received + (contract.totalReceived || 0),
      }),
      { totalPaid: 0, principal: 0, interest: 0, balance: 0, received: 0 }
    );
  }, [contracts]);

  const monthlyChartData = useMemo(() => {
    return monthlyData.map((item: any) => ({
      month: item.month,
      principal: item.principal || 0,
      interest: item.interest || 0,
      total: (item.principal || 0) + (item.interest || 0),
      efficiency: item.efficiency || 0,
    }));
  }, [monthlyData]);

  const creditorsPieData = useMemo(() => {
    return orgData.slice(0, 6).map((org: any, index: number) => ({
      name: org.organization?.length > 20
        ? org.organization.substring(0, 17) + '...'
        : org.organization,
      value: org.totalPaid || 0,
      color: PIE_COLORS[index % PIE_COLORS.length],
    }));
  }, [orgData]);

  const formatMonth = useCallback((value: string) => {
    if (!value) return '';
    const [year, month] = value.split('-');
    const months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
    return `${months[parseInt(month) - 1]} ${year?.slice(2) || ''}`;
  }, []);

  const tableColumns: VirtualTableColumn<ContractItem>[] = useMemo(() => [
    {
      key: 'contractNumber',
      title: 'Договор',
      minWidth: '160px',
      render: (item) => (
        <Button
          type="link"
          onClick={() => navigate(`/fin/contract-operations?id=${item.contractId}`)}
          style={{ padding: 0, textAlign: 'left' }}
        >
          <Text ellipsis style={{ maxWidth: 180 }}>{item.contractNumber || 'Без номера'}</Text>
        </Button>
      ),
    },
    {
      key: 'organization',
      title: 'Организация',
      minWidth: '160px',
      render: (item) => <Text ellipsis style={{ maxWidth: 180 }}>{item.organization}</Text>,
    },
    {
      key: 'payer',
      title: 'Кредитор',
      minWidth: '150px',
      render: (item) => <Text ellipsis style={{ maxWidth: 160 }}>{item.payer || '-'}</Text>,
    },
    {
      key: 'totalPaid',
      title: 'Всего выплачено',
      width: 140,
      align: 'right',
      render: (item) => (
        <Text style={{ fontFamily: 'monospace' }}>{formatAmount(item.totalPaid)}</Text>
      ),
    },
    {
      key: 'totalReceived',
      title: 'Получено',
      width: 140,
      align: 'right',
      render: (item) => (
        <Text style={{ fontFamily: 'monospace' }}>{formatAmount(item.totalReceived)}</Text>
      ),
    },
    {
      key: 'openingBalance',
      title: 'Баланс на начало',
      width: 150,
      align: 'right',
      render: (item) => (
        <Text style={{ fontFamily: 'monospace', color: COLORS.purple }}>{formatAmount(item.openingBalance)}</Text>
      ),
    },
    {
      key: 'principal',
      title: 'Тело',
      width: 120,
      align: 'right',
      render: (item) => (
        <Text style={{ fontFamily: 'monospace', color: COLORS.success }}>{formatAmount(item.principal)}</Text>
      ),
    },
    {
      key: 'interest',
      title: 'Проценты',
      width: 120,
      align: 'right',
      render: (item) => (
        <Text style={{ fontFamily: 'monospace', color: COLORS.warning }}>{formatAmount(item.interest)}</Text>
      ),
    },
    {
      key: 'balance',
      title: 'Остаток',
      width: 140,
      align: 'right',
      render: (item) => (
        <Text style={{ fontFamily: 'monospace', color: COLORS.primary }}>{formatAmount(item.balance)}</Text>
      ),
    },
    {
      key: 'paidPercent',
      title: 'Уплачено %',
      width: 110,
      align: 'right',
      render: (item) => {
        const totalDebt = (item.openingBalance || 0) + (item.totalReceived || 0);
        return (
          <Text style={{ fontFamily: 'monospace' }}>
            {totalDebt > 0 ? `${item.paidPercent?.toFixed(1) || '0.0'}%` : '-'}
          </Text>
        );
      },
    },
    {
      key: 'firstReceipt',
      title: 'Дата получения',
      width: 130,
      render: (item) => <Text>{item.firstReceipt ? item.firstReceipt : '-'}</Text>,
    },
    {
      key: 'operationsCount',
      title: 'Операций',
      width: 90,
      align: 'center',
      render: (item) => <Tag>{item.operationsCount}</Tag>,
    },
    {
      key: 'lastPayment',
      title: 'Последний платеж',
      width: 130,
      render: (item) => <Text>{item.lastPayment ? item.lastPayment : '-'}</Text>,
    },
  ], [navigate]);

  const exportColumns: ExportColumn<ContractItem>[] = useMemo(() => [
    { key: 'contractNumber', header: 'Договор' },
    { key: 'organization', header: 'Организация' },
    { key: 'payer', header: 'Кредитор' },
    { key: 'totalReceived', header: 'Получено' },
    { key: 'openingBalance', header: 'Баланс на начало' },
    { key: 'totalPaid', header: 'Всего выплачено' },
    { key: 'principal', header: 'Тело' },
    { key: 'interest', header: 'Проценты' },
    { key: 'balance', header: 'Остаток' },
    { key: 'paidPercent', header: 'Уплачено %' },
    { key: 'firstReceipt', header: 'Дата получения' },
    { key: 'lastPayment', header: 'Последний платеж' },
    { key: 'operationsCount', header: 'Операций' },
  ], []);

  // Вкладка 1: "По задолженности" - только контракты с остатком > 100 руб
  const debtSortedContracts = useMemo(
    () => contracts
      .filter(c => (c.balance || 0) > 100)
      .sort((a, b) => (b.balance || 0) - (a.balance || 0)),
    [contracts]
  );

  // Вкладка 2: "По активности" - контракты с операциями в периоде
  const activitySortedContracts = useMemo(
    () => contracts
      .filter(c => (c.operationsCount || 0) > 0 || (c.totalReceived || 0) > 0 || (c.principal || 0) > 0)
      .sort((a, b) => (b.operationsCount || 0) - (a.operationsCount || 0)),
    [contracts]
  );

  const tableHeight = useMemo(
    () => Math.min(520, Math.max(240, contracts.length * 52 + 120)),
    [contracts.length]
  );

  const principalShare = useMemo(() => {
    if (!contractTotals.totalPaid) return 0;
    return Math.round((contractTotals.principal / contractTotals.totalPaid) * 100);
  }, [contractTotals.principal, contractTotals.totalPaid]);

  const activeCreditTabs: TabsProps['items'] = [
    {
      key: 'debt',
      label: `По задолженности (${debtSortedContracts.length})`,
      children: (
        <VirtualTable
          data={debtSortedContracts}
          columns={tableColumns}
          rowHeight={52}
          height={tableHeight}
          onRowClick={(item) => {
            if (item.contractId) {
              navigate(`/fin/contract-operations?id=${item.contractId}`);
            }
          }}
        />
      ),
    },
    {
      key: 'activity',
      label: `По активности (${activitySortedContracts.length})`,
      children: (
        <VirtualTable
          data={activitySortedContracts}
          columns={tableColumns}
          rowHeight={52}
          height={tableHeight}
          onRowClick={(item) => {
            if (item.contractId) {
              navigate(`/fin/contract-operations?id=${item.contractId}`);
            }
          }}
        />
      ),
    },
  ];

  const summaryCards = [
    {
      key: 'opening',
      title: 'Сальдо на начало',
      value: balances?.openingBalance || 0,
      accent: COLORS.purple,
      icon: <WalletOutlined />,
      meta: 'С учетом всех операций до периода',
    },
    {
      key: 'interest',
      title: 'Уплачено процентов',
      value: balances?.periodInterestPaid || contractTotals.interest,
      accent: COLORS.warning,
      icon: <PercentageOutlined />,
      meta: 'Нагрузка по займам за период',
    },
    {
      key: 'contracts',
      title: 'Активных договоров',
      value: contractsQuery.data?.pagination?.total || contracts.length,
      accent: COLORS.cyan,
      icon: <FileTextOutlined />,
      meta: 'С остатком долга > 100 руб',
    },
    {
      key: 'share',
      title: 'Доля тела в платежах',
      value: principalShare,
      suffix: '%',
      accent: COLORS.success,
      icon: <LineChartOutlined />,
      meta: 'Цель: выше 60%',
    },
  ];

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="fin-page"
    >
      <div className="fin-kpi-grid">
        {summaryCards.map(card => (
          <Card key={card.key} className="fin-kpi-card" bodyStyle={{ padding: 16 }}>
            <Space align="start" size={12} style={{ width: '100%' }}>
              <div style={{
                width: 40,
                height: 40,
                borderRadius: 12,
                background: `${card.accent}10`,
                color: card.accent,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                {card.icon}
              </div>
              <div style={{ width: '100%' }}>
                <Text type="secondary">{card.title}</Text>
                <Statistic
                  value={card.value}
                  suffix={card.suffix}
                  valueStyle={{ fontSize: 26, color: card.accent, lineHeight: 1.2 }}
                  formatter={(value) => typeof value === 'number' ? formatShortAmount(value) : value}
                />
                <div className="fin-kpi-card__meta">{card.meta}</div>
              </div>
            </Space>
          </Card>
        ))}
      </div>

      <Card
        className="fin-section-card"
        title={
          <Space size={10}>
            <BankOutlined style={{ color: COLORS.error }} />
            <span style={{ color: COLORS.error, fontWeight: 600 }}>Активные кредиты</span>
            <Badge count={contracts.length} style={{ backgroundColor: COLORS.error }} />
          </Space>
        }
        extra={
          <Space size={10}>
            <Tag color="geekblue">Готово к экспорту</Tag>
            <ExportButton
              data={contracts}
              columns={exportColumns}
              filename="credit-contracts"
            />
          </Space>
        }
      >
        <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Statistic
              title="Всего выплачено"
              value={contractTotals.totalPaid}
              formatter={(v) => formatFullAmount(Number(v))}
              valueStyle={{ fontSize: 18 }}
            />
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Statistic
              title="Тело"
              value={contractTotals.principal}
              formatter={(v) => formatFullAmount(Number(v))}
              valueStyle={{ fontSize: 18, color: COLORS.success }}
            />
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Statistic
              title="Проценты"
              value={contractTotals.interest}
              formatter={(v) => formatFullAmount(Number(v))}
              valueStyle={{ fontSize: 18, color: COLORS.warning }}
            />
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Statistic
              title="Остаток"
              value={contractTotals.balance}
              formatter={(v) => formatFullAmount(Number(v))}
              valueStyle={{ fontSize: 18, color: COLORS.primary }}
            />
          </Col>
          <Col xs={24} sm={12} md={6} lg={4}>
            <Statistic
              title="Доля тела в платежах"
              value={principalShare}
              suffix="%"
              valueStyle={{ fontSize: 18, color: principalShare > 60 ? COLORS.success : COLORS.warning }}
            />
          </Col>
        </Row>

        <Divider style={{ margin: '6px 0 14px' }} />

        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as 'debt' | 'activity')}
          items={activeCreditTabs}
        />
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card
            className="fin-section-card"
            title="Динамика кредитных платежей"
            extra={
              <Button type="link" onClick={() => navigate('/fin/analytics')}>
                Подробнее
              </Button>
            }
          >
            <div style={{ height: 320 }}>
              {monthlyChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={monthlyChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="month"
                      tickFormatter={formatMonth}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis
                      yAxisId="left"
                      tickFormatter={(v) => formatShortAmount(v)}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tickFormatter={(v) => `${v}%`}
                      tick={{ fontSize: 11 }}
                    />
                    <RechartsTooltip
                      formatter={(value: number | undefined, name: string | undefined) => [
                        formatFullAmount(value ?? 0),
                        name === 'principal' ? 'Тело' :
                        name === 'interest' ? 'Проценты' :
                        name === 'efficiency' ? 'Эффективность' : (name ?? '')
                      ]}
                      labelFormatter={(label) => formatMonth(label)}
                    />
                    <Legend />
                    <Bar
                      yAxisId="left"
                      dataKey="principal"
                      fill={COLORS.success}
                      name="Тело"
                      radius={[4, 4, 0, 0]}
                      stackId="payments"
                    />
                    <Bar
                      yAxisId="left"
                      dataKey="interest"
                      fill={COLORS.warning}
                      name="Проценты"
                      radius={[4, 4, 0, 0]}
                      stackId="payments"
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="efficiency"
                      stroke={COLORS.primary}
                      strokeWidth={2}
                      dot={{ fill: COLORS.primary, strokeWidth: 2 }}
                      name="Эффективность %"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <Empty description="Нет данных за период" />
              )}
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card className="fin-section-card" title="Топ кредиторов">
            <div style={{ height: 320 }}>
              {creditorsPieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={creditorsPieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={90}
                      paddingAngle={2}
                      dataKey="value"
                      label={({ name, percent }) =>
                        `${name} (${((percent ?? 0) * 100).toFixed(0)}%)`
                      }
                      labelLine={false}
                    >
                      {creditorsPieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip
                      formatter={(value: number | undefined) => formatFullAmount(value ?? 0)}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <Empty description="Нет данных" />
              )}
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card className="fin-section-card" title="Распределение по организациям">
            <div style={{ height: 280 }}>
              {orgData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={orgData.slice(0, 8)}
                    layout="vertical"
                    margin={{ left: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      type="number"
                      tickFormatter={(v) => formatShortAmount(v)}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis
                      type="category"
                      dataKey="organization"
                      tick={{ fontSize: 10 }}
                      width={120}
                      tickFormatter={(v) => v?.length > 15 ? v.substring(0, 12) + '...' : v}
                    />
                    <RechartsTooltip
                      formatter={(value: number | undefined, name: string | undefined) => [
                        formatFullAmount(value ?? 0),
                        name === 'principal' ? 'Тело' : 'Проценты'
                      ]}
                    />
                    <Legend />
                    <Bar dataKey="principal" fill={COLORS.success} name="Тело" stackId="a" />
                    <Bar dataKey="interest" fill={COLORS.warning} name="Проценты" stackId="a" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Empty description="Нет данных" />
              )}
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            className="fin-section-card"
            title="Последние платежи"
            extra={
              <Button type="link" onClick={() => navigate('/fin/expenses')}>
                Все списания →
              </Button>
            }
          >
            <div style={{ maxHeight: 280, overflowY: 'auto' }}>
              {contracts.slice(0, 8).map((contract, idx) => (
                <div
                  key={contract.contractNumber || idx}
                  style={{
                    padding: '12px 0',
                    borderBottom: idx < 7 ? '1px solid #f0f0f0' : 'none',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <Text ellipsis style={{ maxWidth: 200, display: 'block' }}>
                      {contract.contractNumber || 'Без номера'}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {contract.organization}
                    </Text>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <Text strong style={{ fontFamily: 'monospace' }}>
                      {formatAmount(contract.totalPaid)}
                    </Text>
                    <br />
                    <Space size={4}>
                      <Tag color="green" style={{ fontSize: 10 }}>Т: {formatShortAmount(contract.principal)}</Tag>
                      <Tag color="orange" style={{ fontSize: 10 }}>%: {formatShortAmount(contract.interest)}</Tag>
                    </Space>
                  </div>
                </div>
              ))}
              {contracts.length === 0 && <Empty description="Нет данных" />}
            </div>
          </Card>
        </Col>
      </Row>

      <Collapse
        ghost
        style={{ marginTop: 8 }}
        items={[
          {
            key: 'help',
            label: (
              <Space>
                <QuestionCircleOutlined />
                <Text strong>Как рассчитываются показатели?</Text>
              </Space>
            ),
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} md={12} lg={8}>
                  <Card size="small" title={<><DollarOutlined /> Получено кредитов</>}>
                    <Paragraph style={{ fontSize: 12, marginBottom: 0 }}>
                      Сумма всех поступлений по кредитным договорам за выбранный период.
                      Учитываются только документы "Поступление на расчётный счёт".
                    </Paragraph>
                  </Card>
                </Col>
                <Col xs={24} md={12} lg={8}>
                  <Card size="small" title={<><BankOutlined /> Погашено тела</>}>
                    <Paragraph style={{ fontSize: 12, marginBottom: 0 }}>
                      Суммы с типом платежа "Погашение долга" из детализации расходных документов.
                      Это погашение основного долга по кредитам.
                    </Paragraph>
                  </Card>
                </Col>
                <Col xs={24} md={12} lg={8}>
                  <Card size="small" title={<><PercentageOutlined /> Уплачено процентов</>}>
                    <Paragraph style={{ fontSize: 12, marginBottom: 0 }}>
                      Суммы с типом платежа "Уплата процентов" из детализации расходных документов.
                      Это проценты по кредитным договорам.
                    </Paragraph>
                  </Card>
                </Col>
                <Col xs={24} md={12} lg={8}>
                  <Card size="small" title={<><WalletOutlined /> Сальдо на начало</>}>
                    <Paragraph style={{ fontSize: 12, marginBottom: 0 }}>
                      Остаток задолженности на начало выбранного периода.
                      Рассчитывается на основе всех операций до начала периода.
                    </Paragraph>
                  </Card>
                </Col>
                <Col xs={24} md={12} lg={8}>
                  <Card size="small" title={<><FileTextOutlined /> Остаток задолженности</>}>
                    <Paragraph style={{ fontSize: 12, marginBottom: 0 }}>
                      Сальдо на начало + Получено кредитов - Погашено тела.
                      Текущий остаток основного долга на конец периода.
                    </Paragraph>
                  </Card>
                </Col>
                <Col xs={24} md={12} lg={8}>
                  <Card size="small" title={<><InfoCircleOutlined /> Важно</>}>
                    <Paragraph style={{ fontSize: 12, marginBottom: 0 }}>
                      Расчёты основаны на поле <code>payment_type</code> в детализации документов.
                      Данные берутся из FinExpenseDetail.
                    </Paragraph>
                  </Card>
                </Col>
              </Row>
            ),
          },
        ]}
      />

      <Row gutter={[16, 16]} className="fin-quick-links" style={{ marginTop: 16 }}>
        <Col xs={12} sm={6}>
          <Card
            hoverable
            onClick={() => navigate('/fin/contracts')}
            bodyStyle={{ textAlign: 'center', padding: 16 }}
          >
            <FileTextOutlined style={{ fontSize: 24, color: COLORS.purple, marginBottom: 8 }} />
            <div>
              <Text strong>Договоры</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>Все кредиты</Text>
            </div>
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card
            hoverable
            onClick={() => navigate('/fin/expenses')}
            bodyStyle={{ textAlign: 'center', padding: 16 }}
          >
            <BankOutlined style={{ fontSize: 24, color: COLORS.error, marginBottom: 8 }} />
            <div>
              <Text strong>Списания</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>Все платежи</Text>
            </div>
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card
            hoverable
            onClick={() => navigate('/fin/analytics')}
            bodyStyle={{ textAlign: 'center', padding: 16 }}
          >
            <LineChartOutlined style={{ fontSize: 24, color: COLORS.primary, marginBottom: 8 }} />
            <div>
              <Text strong>Аналитика</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>Подробно</Text>
            </div>
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card
            hoverable
            onClick={() => navigate('/fin/osv')}
            bodyStyle={{ textAlign: 'center', padding: 16 }}
          >
            <TableOutlined style={{ fontSize: 24, color: COLORS.cyan, marginBottom: 8 }} />
            <div>
              <Text strong>ОСВ</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>Оборотная ведомость</Text>
            </div>
          </Card>
        </Col>
      </Row>
    </motion.div>
  );
}
