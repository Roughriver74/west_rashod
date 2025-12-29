/**
 * Fin Contract Operations Page
 * Shows detailed operations for a specific contract
 */
import { useMemo, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import {
  Row,
  Col,
  Card,
  Statistic,
  Spin,
  Typography,
  Space,
  Button,
  Empty,
  Tag,
  Tabs,
  Tooltip,
  Breadcrumb,
} from 'antd';
import {
  ArrowLeftOutlined,
  DollarOutlined,
  BankOutlined,
  PercentageOutlined,
  WalletOutlined,
  FileTextOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import { motion } from 'framer-motion';
import { format, parseISO } from 'date-fns';

import { useFinFilterValues } from '../stores/finFilterStore';
import { getContractOperationsById, ContractOperation } from '../api/finApi';
import { formatFullAmount, formatShortAmount, formatAmount } from '../utils/formatters';
import { VirtualTable, VirtualTableColumn } from '../components/VirtualTable';
import { ExportButton, ExportColumn } from '../components/ExportButton';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

// Color palette
const COLORS = {
  primary: '#1890ff',
  success: '#52c41a',
  warning: '#faad14',
  error: '#ff4d4f',
  purple: '#722ed1',
  cyan: '#13c2c2',
};

export default function FinContractOperationsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const filters = useFinFilterValues();
  const { dateFrom, dateTo } = filters;
  const [activeTab, setActiveTab] = useState<'all' | 'receipts' | 'expenses'>('all');

  // Extract contract ID from query parameters
  const contractIdStr = searchParams.get('id') || '';
  const contractId = contractIdStr ? parseInt(contractIdStr, 10) : 0;

  // Build filter params
  const filterParams = useMemo(() => {
    const params: { date_from?: string; date_to?: string } = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    return params;
  }, [dateFrom, dateTo]);

  // Query contract operations
  const operationsQuery = useQuery({
    queryKey: ['fin', 'contract-operations', contractId, filterParams],
    queryFn: () => getContractOperationsById(contractId, filterParams),
    enabled: !!contractId && contractId > 0,
    placeholderData: keepPreviousData,
    staleTime: 2 * 60 * 1000,
  });

  const data = operationsQuery.data;
  const operations = data?.operations || [];
  const summary = data?.summary;
  const statistics = data?.statistics;
  const decodedContractNumber = data?.contract_number || 'Не указан';

  // Filter operations by type
  const filteredOperations = useMemo(() => {
    if (activeTab === 'all') return operations;
    return operations.filter(op => op.type === (activeTab === 'receipts' ? 'receipt' : 'expense'));
  }, [operations, activeTab]);

  // Format date
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    try {
      return format(parseISO(dateStr), 'dd.MM.yyyy');
    } catch {
      return dateStr;
    }
  };

  // Table columns
  const tableColumns: VirtualTableColumn<ContractOperation>[] = useMemo(() => [
    {
      key: 'document_date',
      title: 'Дата',
      width: 100,
      render: (item) => (
        <Text>{formatDate(item.document_date)}</Text>
      ),
    },
    {
      key: 'type',
      title: 'Тип',
      width: 100,
      render: (item) => (
        <Tag color={item.type === 'receipt' ? 'green' : 'red'}>
          {item.type === 'receipt' ? 'Получение' : 'Списание'}
        </Tag>
      ),
    },
    {
      key: 'document_number',
      title: 'Документ',
      width: 120,
      render: (item) => (
        <Text ellipsis style={{ maxWidth: 100 }}>{item.document_number || '-'}</Text>
      ),
    },
    {
      key: 'counterparty',
      title: 'Контрагент',
      width: 200,
      render: (item) => (
        <Text ellipsis style={{ maxWidth: 180 }}>
          {item.payer || item.recipient || '-'}
        </Text>
      ),
    },
    {
      key: 'amount',
      title: 'Сумма',
      width: 130,
      align: 'right',
      render: (item) => (
        <Text
          style={{
            fontFamily: 'monospace',
            color: item.type === 'receipt' ? COLORS.success : COLORS.error,
          }}
        >
          {item.type === 'receipt' ? '+' : '-'}{formatAmount(item.amount)}
        </Text>
      ),
    },
    {
      key: 'principal',
      title: 'Тело',
      width: 110,
      align: 'right',
      render: (item) => (
        <Text style={{ fontFamily: 'monospace', color: COLORS.success }}>
          {item.principal > 0 ? formatAmount(item.principal) : '-'}
        </Text>
      ),
    },
    {
      key: 'interest',
      title: 'Проценты',
      width: 110,
      align: 'right',
      render: (item) => (
        <Text style={{ fontFamily: 'monospace', color: COLORS.warning }}>
          {item.interest > 0 ? formatAmount(item.interest) : '-'}
        </Text>
      ),
    },
    {
      key: 'payment_purpose',
      title: 'Назначение',
      width: 250,
      render: (item) => (
        <Tooltip title={item.payment_purpose}>
          <Text ellipsis style={{ maxWidth: 230 }}>{item.payment_purpose || '-'}</Text>
        </Tooltip>
      ),
    },
  ], []);

  // Export columns
  const exportColumns: ExportColumn<ContractOperation>[] = useMemo(() => [
    { key: 'document_date', header: 'Дата' },
    { key: 'type', header: 'Тип', formatter: (v) => v === 'receipt' ? 'Получение' : 'Списание' },
    { key: 'document_number', header: 'Документ' },
    { key: 'payer', header: 'Плательщик' },
    { key: 'recipient', header: 'Получатель' },
    { key: 'amount', header: 'Сумма' },
    { key: 'principal', header: 'Тело' },
    { key: 'interest', header: 'Проценты' },
    { key: 'payment_purpose', header: 'Назначение' },
  ], []);

  if (operationsQuery.isLoading && !data) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Space direction="vertical" align="center">
          <Spin size="large" />
          <Text type="secondary">Загрузка операций по договору...</Text>
        </Space>
      </div>
    );
  }

  if (operationsQuery.isError) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Space direction="vertical" align="center">
          <Text type="danger">Ошибка загрузки данных</Text>
          <Button onClick={() => operationsQuery.refetch()}>Повторить</Button>
          <Button type="link" onClick={() => navigate('/fin/contracts')}>
            Вернуться к списку договоров
          </Button>
        </Space>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Breadcrumb */}
      <Breadcrumb style={{ marginBottom: 16 }}>
        <Breadcrumb.Item>
          <a onClick={() => navigate('/fin')}>Финансы</a>
        </Breadcrumb.Item>
        <Breadcrumb.Item>
          <a onClick={() => navigate('/fin/contracts')}>Договоры</a>
        </Breadcrumb.Item>
        <Breadcrumb.Item>
          {decodedContractNumber.length > 30
            ? decodedContractNumber.substring(0, 27) + '...'
            : decodedContractNumber}
        </Breadcrumb.Item>
      </Breadcrumb>

      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Space align="center" style={{ marginBottom: 8 }}>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/fin/contracts')}
            >
              Назад
            </Button>
            <Title level={2} style={{ marginBottom: 0 }}>
              <FileTextOutlined style={{ marginRight: 12 }} />
              {decodedContractNumber || 'Договор'}
            </Title>
          </Space>
          {data?.organization && (
            <Text type="secondary" style={{ display: 'block', marginLeft: 40 }}>
              Организация: {data.organization}
            </Text>
          )}
        </div>
        <ExportButton
          data={filteredOperations}
          columns={exportColumns}
          filename={`contract-${decodedContractNumber.replace(/[^a-zA-Z0-9]/g, '_')}`}
        />
      </div>

      {/* KPI Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={8} xl={4}>
          <Card
            style={{
              background: 'linear-gradient(135deg, #722ed1 0%, #531dab 100%)',
              borderRadius: 12,
            }}
            bodyStyle={{ padding: 16 }}
          >
            <Statistic
              title={<span style={{ color: 'rgba(255,255,255,0.85)' }}>Сальдо на начало</span>}
              value={summary?.opening_balance || 0}
              precision={0}
              prefix={<WalletOutlined />}
              valueStyle={{ color: 'white', fontSize: 18 }}
              formatter={(value) => formatShortAmount(Number(value))}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={8} xl={4}>
          <Card
            style={{
              background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
              borderRadius: 12,
            }}
            bodyStyle={{ padding: 16 }}
          >
            <Statistic
              title={<span style={{ color: 'rgba(255,255,255,0.85)' }}>Получено</span>}
              value={summary?.total_received || 0}
              precision={0}
              prefix={<ArrowDownOutlined />}
              valueStyle={{ color: 'white', fontSize: 18 }}
              formatter={(value) => formatShortAmount(Number(value))}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={8} xl={4}>
          <Card
            style={{
              background: 'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)',
              borderRadius: 12,
            }}
            bodyStyle={{ padding: 16 }}
          >
            <Statistic
              title={<span style={{ color: 'rgba(255,255,255,0.85)' }}>Погашено тела</span>}
              value={summary?.principal_paid || 0}
              precision={0}
              prefix={<BankOutlined />}
              valueStyle={{ color: 'white', fontSize: 18 }}
              formatter={(value) => formatShortAmount(Number(value))}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={8} xl={4}>
          <Card
            style={{
              background: 'linear-gradient(135deg, #faad14 0%, #d48806 100%)',
              borderRadius: 12,
            }}
            bodyStyle={{ padding: 16 }}
          >
            <Statistic
              title={<span style={{ color: 'rgba(255,255,255,0.85)' }}>Уплачено процентов</span>}
              value={summary?.interest_paid || 0}
              precision={0}
              prefix={<PercentageOutlined />}
              valueStyle={{ color: 'white', fontSize: 18 }}
              formatter={(value) => formatShortAmount(Number(value))}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={8} xl={4}>
          <Card
            style={{
              background: 'linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%)',
              borderRadius: 12,
            }}
            bodyStyle={{ padding: 16 }}
          >
            <Statistic
              title={<span style={{ color: 'rgba(255,255,255,0.85)' }}>Остаток долга</span>}
              value={summary?.closing_balance || 0}
              precision={0}
              prefix={<DollarOutlined />}
              valueStyle={{ color: 'white', fontSize: 18 }}
              formatter={(value) => formatShortAmount(Number(value))}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={8} xl={4}>
          <Card
            style={{
              background: 'linear-gradient(135deg, #13c2c2 0%, #08979c 100%)',
              borderRadius: 12,
            }}
            bodyStyle={{ padding: 16 }}
          >
            <Statistic
              title={<span style={{ color: 'rgba(255,255,255,0.85)' }}>Операций</span>}
              value={statistics?.total_operations || 0}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: 'white', fontSize: 18 }}
            />
            <Text style={{ color: 'rgba(255,255,255,0.65)', fontSize: 11 }}>
              {statistics?.receipts_count || 0} поступлений / {statistics?.expenses_count || 0} списаний
            </Text>
          </Card>
        </Col>
      </Row>

      {/* Operations Table */}
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>Операции по договору</span>
            <Tag color="blue">{filteredOperations.length}</Tag>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={(key) => setActiveTab(key as 'all' | 'receipts' | 'expenses')}>
          <TabPane
            tab={
              <span>
                Все <Tag>{operations.length}</Tag>
              </span>
            }
            key="all"
          />
          <TabPane
            tab={
              <span>
                <ArrowDownOutlined style={{ color: COLORS.success }} /> Поступления{' '}
                <Tag color="green">{statistics?.receipts_count || 0}</Tag>
              </span>
            }
            key="receipts"
          />
          <TabPane
            tab={
              <span>
                <ArrowUpOutlined style={{ color: COLORS.error }} /> Списания{' '}
                <Tag color="red">{statistics?.expenses_count || 0}</Tag>
              </span>
            }
            key="expenses"
          />
        </Tabs>

        {filteredOperations.length > 0 ? (
          <VirtualTable
            data={filteredOperations}
            columns={tableColumns}
            rowHeight={52}
            height={500}
          />
        ) : (
          <Empty description="Нет операций по договору" />
        )}

        {/* Summary Footer */}
        {filteredOperations.length > 0 && (
          <div
            style={{
              marginTop: 16,
              padding: 16,
              background: '#fafafa',
              borderRadius: 8,
              display: 'flex',
              justifyContent: 'space-around',
              flexWrap: 'wrap',
              gap: 16,
            }}
          >
            <Statistic
              title="Итого получено"
              value={filteredOperations
                .filter(op => op.type === 'receipt')
                .reduce((sum, op) => sum + op.amount, 0)}
              formatter={(v) => formatFullAmount(Number(v))}
              valueStyle={{ fontSize: 16, color: COLORS.success }}
            />
            <Statistic
              title="Итого списано"
              value={filteredOperations
                .filter(op => op.type === 'expense')
                .reduce((sum, op) => sum + op.amount, 0)}
              formatter={(v) => formatFullAmount(Number(v))}
              valueStyle={{ fontSize: 16, color: COLORS.error }}
            />
            <Statistic
              title="Погашено тела"
              value={filteredOperations.reduce((sum, op) => sum + op.principal, 0)}
              formatter={(v) => formatFullAmount(Number(v))}
              valueStyle={{ fontSize: 16, color: COLORS.success }}
            />
            <Statistic
              title="Уплачено процентов"
              value={filteredOperations.reduce((sum, op) => sum + op.interest, 0)}
              formatter={(v) => formatFullAmount(Number(v))}
              valueStyle={{ fontSize: 16, color: COLORS.warning }}
            />
          </div>
        )}
      </Card>

      {/* Quick Actions */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={12} sm={6}>
          <Card
            hoverable
            onClick={() => navigate('/fin/contracts')}
            bodyStyle={{ textAlign: 'center', padding: 16 }}
          >
            <FileTextOutlined style={{ fontSize: 24, color: COLORS.purple, marginBottom: 8 }} />
            <div>
              <Text strong>Все договоры</Text>
            </div>
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card
            hoverable
            onClick={() => navigate('/fin')}
            bodyStyle={{ textAlign: 'center', padding: 16 }}
          >
            <DollarOutlined style={{ fontSize: 24, color: COLORS.primary, marginBottom: 8 }} />
            <div>
              <Text strong>Dashboard</Text>
            </div>
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card
            hoverable
            onClick={() => navigate('/fin/analytics')}
            bodyStyle={{ textAlign: 'center', padding: 16 }}
          >
            <BankOutlined style={{ fontSize: 24, color: COLORS.cyan, marginBottom: 8 }} />
            <div>
              <Text strong>Аналитика</Text>
            </div>
          </Card>
        </Col>

        <Col xs={12} sm={6}>
          <Card
            hoverable
            onClick={() => navigate('/fin/osv')}
            bodyStyle={{ textAlign: 'center', padding: 16 }}
          >
            <WalletOutlined style={{ fontSize: 24, color: COLORS.success, marginBottom: 8 }} />
            <div>
              <Text strong>ОСВ</Text>
            </div>
          </Card>
        </Col>
      </Row>
    </motion.div>
  );
}
