/**
 * Fin Contracts Page - Contracts management
 * Redesigned with Ant Design components for consistent UI
 */
import { useState, useMemo, useEffect } from 'react';
import { useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Input,
  Button,
  Spin,
  Typography,
  Space,
  Statistic,
  Pagination,
  Empty,
  Badge,
} from 'antd';
import {
  FileTextOutlined,
  SearchOutlined,
  DollarOutlined,
  BankOutlined,
  CalendarOutlined,
  ReloadOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { format, parseISO } from 'date-fns';

import { useFinFilterValues } from '../stores/finFilterStore';
import { formatAmount } from '../utils/formatters';
import { useDebounce } from '../hooks/usePerformance';
import { buildFilterPayload } from '../utils/filterParams';
import { getContractsSummary } from '../api/finApi';
import type {
  ContractsSummaryPagination,
  ContractsSummaryRecord,
} from '../api/finApi';

const { Title, Text } = Typography;

const PAGE_SIZE = 20;
const EMPTY_PAGINATION: ContractsSummaryPagination = {
  page: 1,
  limit: PAGE_SIZE,
  total: 0,
  pages: 1,
};

// Color scheme matching Dashboard
const COLORS = {
  primary: '#1890ff',
  success: '#52c41a',
  warning: '#faad14',
  error: '#ff4d4f',
  purple: '#722ed1',
};

export default function FinContractsPage() {
  const navigate = useNavigate();
  const filters = useFinFilterValues();
  const [page, setPage] = useState(EMPTY_PAGINATION.page);
  const [searchTerm, setSearchTerm] = useState('');

  const debouncedSearchTerm = useDebounce(searchTerm, 300);
  const debouncedFilters = useDebounce(filters, 500);

  const filterPayload = useMemo(
    () => buildFilterPayload(debouncedFilters, { includeDefaultDateTo: true }),
    [debouncedFilters]
  );

  const queryParams = useMemo(() => {
    const params: {
      date_from?: string;
      date_to?: string;
      organizations?: string;
      page: number;
      limit: number;
      search?: string;
    } = {
      ...filterPayload,
      page,
      limit: PAGE_SIZE,
    };

    if (debouncedSearchTerm) {
      params.search = debouncedSearchTerm;
    }

    return params;
  }, [filterPayload, page, debouncedSearchTerm]);

  const queryClient = useQueryClient();
  const contractsQuery = useQuery({
    queryKey: ['fin', 'contracts-summary', queryParams],
    queryFn: () => getContractsSummary(queryParams),
    placeholderData: keepPreviousData,
    staleTime: 2 * 60 * 1000,
  });

  const pagination = contractsQuery.data?.pagination ?? EMPTY_PAGINATION;
  const contracts: ContractsSummaryRecord[] = contractsQuery.data?.data ?? [];

  const totalSum = useMemo(
    () => contracts.reduce((sum, contract) => sum + (contract.totalPaid || 0), 0),
    [contracts]
  );

  useEffect(() => {
    setPage(1);
  }, [debouncedFilters, debouncedSearchTerm]);

  // Prefetch next page
  useEffect(() => {
    if (!contractsQuery.data?.pagination) return;
    const { page: currentPage, pages } = contractsQuery.data.pagination;
    if (currentPage >= pages) return;

    const nextParams = {
      ...queryParams,
      page: currentPage + 1,
    };

    queryClient.prefetchQuery({
      queryKey: ['fin', 'contracts-summary', nextParams],
      queryFn: () => getContractsSummary(nextParams),
      staleTime: 2 * 60 * 1000,
    });
  }, [contractsQuery.data?.pagination, queryClient, queryParams]);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  const handleContractClick = (contract: ContractsSummaryRecord) => {
    if (!contract.contractId) return;
    navigate(`/fin/contract-operations?id=${contract.contractId}`);
  };

  if (contractsQuery.isLoading && !contractsQuery.data) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', flexDirection: 'column', gap: 16 }}>
        <Spin size="large" />
        <Text type="secondary">Загрузка договоров...</Text>
      </div>
    );
  }

  if (contractsQuery.isError) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', flexDirection: 'column', gap: 16 }}>
        <Text type="secondary">Не удалось загрузить договоры. Попробуйте еще раз.</Text>
        <Button type="primary" onClick={() => contractsQuery.refetch()} icon={<ReloadOutlined />}>
          Обновить
        </Button>
      </div>
    );
  }

  return (
    <div style={{ padding: '0' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>Управление договорами</Title>
        <Text type="secondary">Детальная информация по кредитным договорам</Text>
      </div>

      {/* Summary Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={8}>
          <Card
            hoverable
            style={{ borderLeft: `4px solid ${COLORS.primary}` }}
          >
            <Statistic
              title={
                <Space>
                  <FileTextOutlined style={{ color: COLORS.primary }} />
                  <span>Всего договоров</span>
                </Space>
              }
              value={pagination.total}
              valueStyle={{ color: COLORS.primary, fontWeight: 600 }}
            />
            <Text type="secondary" style={{ fontSize: 11, fontStyle: 'italic' }}>
              Уникальные кредитные договоры с учетом фильтров
            </Text>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={8}>
          <Card
            hoverable
            style={{ borderLeft: `4px solid ${COLORS.success}` }}
          >
            <Statistic
              title={
                <Space>
                  <DollarOutlined style={{ color: COLORS.success }} />
                  <span>Сумма на странице</span>
                </Space>
              }
              value={formatAmount(totalSum)}
              valueStyle={{ color: COLORS.success, fontWeight: 600 }}
            />
            <Text type="secondary" style={{ fontSize: 11, fontStyle: 'italic' }}>
              Сумма всех платежей ({contracts.length} из {pagination.total})
            </Text>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={8}>
          <Card
            hoverable
            style={{ borderLeft: `4px solid ${COLORS.purple}` }}
          >
            <Statistic
              title={
                <Space>
                  <BankOutlined style={{ color: COLORS.purple }} />
                  <span>Активных</span>
                </Space>
              }
              value={contracts.filter(c => c.totalPaid > 0).length}
              suffix={`/ ${contracts.length}`}
              valueStyle={{ color: COLORS.purple, fontWeight: 600 }}
            />
            <Text type="secondary" style={{ fontSize: 11, fontStyle: 'italic' }}>
              Договоры с операциями на странице
            </Text>
          </Card>
        </Col>
      </Row>

      {/* Search */}
      <Card style={{ marginBottom: 24 }} bodyStyle={{ padding: 16 }}>
        <Input
          placeholder="Поиск по номеру договора или организации..."
          prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          allowClear
          size="large"
        />
      </Card>

      {/* Contracts List */}
      {contracts.length === 0 ? (
        <Card>
          <Empty description="Нет договоров по выбранным фильтрам" />
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {contracts.map((contract) => (
            <Card
              key={contract.contractNumber}
              hoverable
              onClick={() => handleContractClick(contract)}
              style={{ cursor: 'pointer' }}
              bodyStyle={{ padding: 16 }}
            >
              <Row gutter={[16, 16]} align="middle">
                {/* Contract Info */}
                <Col xs={24} lg={12}>
                  <Space direction="vertical" size={4} style={{ width: '100%' }}>
                    <Space>
                      <FileTextOutlined style={{ color: COLORS.primary, fontSize: 18 }} />
                      <Text strong style={{ fontSize: 15 }}>
                        {(contract.contractNumber || 'Без договора').length > 50
                          ? (contract.contractNumber || 'Без договора').substring(0, 47) + '...'
                          : (contract.contractNumber || 'Без договора')}
                      </Text>
                    </Space>
                    <Space wrap size={[16, 4]}>
                      <Space size={4}>
                        <BankOutlined style={{ color: '#8c8c8c' }} />
                        <Text type="secondary" style={{ fontSize: 13 }}>
                          {contract.organization}
                        </Text>
                      </Space>
                      {contract.payer && contract.payer !== '-' && (
                        <Space size={4}>
                          <DollarOutlined style={{ color: COLORS.primary }} />
                          <Text style={{ fontSize: 13, color: COLORS.primary }}>
                            {contract.payer.length > 20 ? contract.payer.substring(0, 17) + '...' : contract.payer}
                          </Text>
                        </Space>
                      )}
                      {contract.lastPayment && (
                        <Space size={4}>
                          <CalendarOutlined style={{ color: '#8c8c8c' }} />
                          <Text type="secondary" style={{ fontSize: 13 }}>
                            {format(parseISO(contract.lastPayment), 'dd.MM.yyyy')}
                          </Text>
                        </Space>
                      )}
                      <Badge
                        count={`${contract.operationsCount} операций`}
                        style={{ backgroundColor: '#f0f0f0', color: '#8c8c8c', fontWeight: 400 }}
                      />
                    </Space>
                  </Space>
                </Col>

                {/* Stats */}
                <Col xs={24} lg={11}>
                  <Row gutter={16} justify="end">
                    <Col>
                      <Statistic
                        title={<Text type="secondary" style={{ fontSize: 12 }}>Всего</Text>}
                        value={formatAmount(contract.totalPaid)}
                        valueStyle={{ fontSize: 16, fontWeight: 600 }}
                      />
                    </Col>
                    <Col>
                      <Statistic
                        title={<Text type="secondary" style={{ fontSize: 12 }}>Тело</Text>}
                        value={formatAmount(contract.principal)}
                        valueStyle={{ fontSize: 16, fontWeight: 600, color: COLORS.success }}
                      />
                    </Col>
                    <Col>
                      <Statistic
                        title={<Text type="secondary" style={{ fontSize: 12 }}>Проценты</Text>}
                        value={formatAmount(contract.interest)}
                        valueStyle={{ fontSize: 16, fontWeight: 600, color: COLORS.warning }}
                      />
                    </Col>
                  </Row>
                </Col>

                {/* Arrow */}
                <Col xs={0} lg={1} style={{ textAlign: 'right' }}>
                  <RightOutlined style={{ color: '#bfbfbf', fontSize: 16 }} />
                </Col>
              </Row>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {pagination.pages > 1 && (
        <Card style={{ marginTop: 24 }} bodyStyle={{ padding: 16, textAlign: 'center' }}>
          <Pagination
            current={pagination.page}
            total={pagination.total}
            pageSize={PAGE_SIZE}
            onChange={handlePageChange}
            showSizeChanger={false}
            showTotal={(total, range) => `${range[0]}-${range[1]} из ${total} договоров`}
          />
        </Card>
      )}
    </div>
  );
}
