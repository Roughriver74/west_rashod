/**
 * Fin Cash Flow Page - Cash flow analysis
 * Adapted 1-to-1 from west_fin CashFlowPage.tsx
 */
import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { formatAmount, formatAxisAmount, formatTooltipAmount } from '../utils/formatters';
import { useFinFilterValues } from '../stores/finFilterStore';
import { useDebounce } from '../hooks/usePerformance';
import { buildFilterPayload } from '../utils/filterParams';
import {
  AreaChart, Area, Bar, BarChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ComposedChart
} from 'recharts';
import { ArrowUpCircle, ArrowDownCircle, Wallet } from 'lucide-react';
import { getMonthlyCashFlow, getOrganizations } from '../api/finApi';
import type { MonthlyCashFlow } from '../api/finApi';

type MonthlyData = MonthlyCashFlow;

interface QuarterlyData {
  quarter: string;
  inflow: number;
  outflow: number;
  net: number;
}

interface Metrics {
  totalInflow: number;
  totalOutflow: number;
  netCashFlow: number;
  avgMonthlyInflow: number;
  avgMonthlyOutflow: number;
}

export default function FinCashFlowPage() {
  const filters = useFinFilterValues();
  const debouncedFilters = useDebounce(filters, 500);
  const filterPayload = useMemo(
    () => buildFilterPayload(debouncedFilters, { includeDefaultDateTo: true }),
    [debouncedFilters]
  );

  const organizationsQuery = useQuery({
    queryKey: ['fin', 'organizations'],
    queryFn: () => getOrganizations(),
    staleTime: 5 * 60 * 1000,
  });

  const organizationId = useMemo(() => {
    if (filters.organizations.length !== 1) return undefined;
    const orgs = organizationsQuery.data?.items || [];
    return orgs.find((org: { id: number; name: string }) => org.name === filters.organizations[0])?.id;
  }, [filters.organizations, organizationsQuery.data]);

  const cashflowParams = useMemo(() => {
    const params: Record<string, any> = { ...filterPayload };
    if (organizationId) {
      params.organization_id = organizationId;
    }
    delete params.organizations;
    return params;
  }, [filterPayload, organizationId]);

  const cashflowQuery = useQuery({
    queryKey: ['fin', 'analytics', 'cashflow-monthly', cashflowParams],
    queryFn: () => getMonthlyCashFlow(cashflowParams),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  });

  const monthlyData = (cashflowQuery.data ?? []) as MonthlyData[];
  const isInitialLoading = cashflowQuery.isLoading && !cashflowQuery.data;

  if (cashflowQuery.isError) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4 text-center">
        <p className="text-gray-600">Не удалось загрузить данные cash flow. Попробуйте еще раз.</p>
        <button
          onClick={() => cashflowQuery.refetch()}
          className="px-4 py-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors"
        >
          Обновить
        </button>
      </div>
    );
  }

  // Calculate quarterly cash flow - memoized
  const quarterlyData = useMemo(() => {
    const quarterly: Record<string, QuarterlyData> = {};

    monthlyData.forEach(m => {
      const [year, month] = m.month.split('-');
      const monthNum = parseInt(month);
      const quarter = `Q${Math.floor((monthNum - 1) / 3) + 1} ${year}`;

      if (!quarterly[quarter]) {
        quarterly[quarter] = { quarter, inflow: 0, outflow: 0, net: 0 };
      }
      quarterly[quarter].inflow += m.inflow || 0;
      quarterly[quarter].outflow += m.outflow || 0;
    });

    return Object.values(quarterly)
      .map(q => ({ ...q, net: q.inflow - q.outflow }))
      .sort((a, b) => a.quarter.localeCompare(b.quarter));
  }, [monthlyData]);

  // Calculate cash flow metrics - memoized
  const metrics = useMemo<Metrics>(() => {
    const totalInflow = monthlyData.reduce((sum, m) => sum + (m.inflow || 0), 0);
    const totalOutflow = monthlyData.reduce((sum, m) => sum + (m.outflow || 0), 0);
    const netCashFlow = totalInflow - totalOutflow;

    // Average monthly inflow/outflow
    const avgMonthlyInflow = monthlyData.length > 0
      ? totalInflow / monthlyData.length
      : 0;
    const avgMonthlyOutflow = monthlyData.length > 0
      ? totalOutflow / monthlyData.length
      : 0;

    return {
      totalInflow,
      totalOutflow,
      netCashFlow,
      avgMonthlyInflow,
      avgMonthlyOutflow
    };
  }, [monthlyData]);

  if (isInitialLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 border-4 border-gray-200 border-t-blue-500 rounded-full"
        />
        <p className="mt-4 text-gray-600">Загрузка данных...</p>
      </div>
    );
  }

  const dateTickFormatter = (value: string) => {
    if (!value) return '';
    const [year, month] = value.split('-');
    const months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
    return `${months[parseInt(month) - 1]} '${year.slice(-2)}`;
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="mobile-container"
    >
      {/* Header */}
      <div className="mb-6 page-header-mobile">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 m-0">Анализ денежных потоков</h1>
          <p className="text-base text-gray-500 mt-1">Cash Flow Analysis - движение средств</p>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-5 mb-6 kpi-grid-mobile">
        <motion.div whileHover={{ y: -4 }} className="p-6 rounded-xl shadow-md text-white flex gap-4 items-center bg-gradient-to-br from-green-500 to-green-600 metric-card-mobile card-compact-mobile">
          <div className="text-4xl opacity-90"><ArrowUpCircle size={32} /></div>
          <div>
            <div className="text-sm opacity-95 mb-1">Общий приток</div>
            <div className="text-3xl font-bold mb-1">{formatAmount(metrics.totalInflow)}</div>
            <div className="text-xs opacity-85">Ср. {formatAmount(metrics.avgMonthlyInflow)}/мес</div>
            <div className="text-[10px] opacity-70 mt-1 leading-snug italic">
              Сумма всех поступлений (receipts) за период, сгруппированных по месяцам
            </div>
          </div>
        </motion.div>

        <motion.div whileHover={{ y: -4 }} className="p-6 rounded-xl shadow-md text-white flex gap-4 items-center bg-gradient-to-br from-red-500 to-red-600 metric-card-mobile card-compact-mobile">
          <div className="text-4xl opacity-90"><ArrowDownCircle size={32} /></div>
          <div>
            <div className="text-sm opacity-95 mb-1">Общий отток</div>
            <div className="text-3xl font-bold mb-1">{formatAmount(metrics.totalOutflow)}</div>
            <div className="text-xs opacity-85">Ср. {formatAmount(metrics.avgMonthlyOutflow)}/мес</div>
            <div className="text-[10px] opacity-70 mt-1 leading-snug italic">
              Сумма всех платежей (expenses) за период, сгруппированных по месяцам
            </div>
          </div>
        </motion.div>

        <motion.div whileHover={{ y: -4 }} className={`p-6 rounded-xl shadow-md text-white flex gap-4 items-center ${metrics.netCashFlow >= 0 ? 'bg-gradient-to-br from-blue-500 to-blue-600' : 'bg-gradient-to-br from-orange-500 to-orange-600'} metric-card-mobile card-compact-mobile`}>
          <div className="text-4xl opacity-90"><Wallet size={32} /></div>
          <div>
            <div className="text-sm opacity-95 mb-1">Чистый поток</div>
            <div className="text-3xl font-bold mb-1">{formatAmount(metrics.netCashFlow)}</div>
            <div className="text-xs opacity-85">{metrics.netCashFlow >= 0 ? 'Положительный' : 'Отрицательный'}</div>
            <div className="text-[10px] opacity-70 mt-1 leading-snug italic">
              Расчет: Приток ({formatAmount(metrics.totalInflow)}) - Отток ({formatAmount(metrics.totalOutflow)})
            </div>
          </div>
        </motion.div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-5 charts-grid-mobile">
        {/* Monthly Cash Flow with Cumulative */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="col-span-2 p-6 bg-white rounded-xl shadow-sm"
        >
          <h2 className="text-lg font-semibold text-gray-900 m-0 mb-1">Ежемесячные денежные потоки</h2>
          <p className="text-[13px] text-gray-500 mb-5">Приток, отток и накопительный баланс</p>
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis
                dataKey="month"
                tickFormatter={dateTickFormatter}
                tick={{ fontSize: 11, fill: '#6B7280' }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis
                yAxisId="left"
                tickFormatter={formatAxisAmount}
                tick={{ fontSize: 11, fill: '#6B7280' }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tickFormatter={formatAxisAmount}
                tick={{ fontSize: 11, fill: '#6B7280' }}
              />
              <Tooltip formatter={formatTooltipAmount as any} labelFormatter={dateTickFormatter} />
              <Legend />
              <Bar yAxisId="left" dataKey="inflow" name="Приток" fill="#10B981" />
              <Bar yAxisId="left" dataKey="outflow" name="Отток" fill="#EF4444" />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="cumulative"
                name="Накопительный"
                stroke="#3B82F6"
                strokeWidth={3}
                dot={{ r: 4 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Net Cash Flow Area */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="col-span-2 p-6 bg-white rounded-xl shadow-sm"
        >
          <h2 className="text-lg font-semibold text-gray-900 m-0 mb-1">Чистый денежный поток</h2>
          <p className="text-[13px] text-gray-500 mb-5">Разница между притоком и оттоком</p>
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={monthlyData}>
              <defs>
                <linearGradient id="colorNetCashFlow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis
                dataKey="month"
                tickFormatter={dateTickFormatter}
                tick={{ fontSize: 11, fill: '#6B7280' }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis tickFormatter={formatAxisAmount} tick={{ fontSize: 11, fill: '#6B7280' }} />
              <Tooltip formatter={formatTooltipAmount as any} labelFormatter={dateTickFormatter} />
              <Area
                type="monotone"
                dataKey="net"
                stroke="#3B82F6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorNetCashFlow)"
                name="Чистый поток"
              />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Quarterly Analysis */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="col-span-2 p-6 bg-white rounded-xl shadow-sm"
        >
          <h2 className="text-lg font-semibold text-gray-900 m-0 mb-1">Квартальный анализ</h2>
          <p className="text-[13px] text-gray-500 mb-5">Денежные потоки по кварталам</p>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={quarterlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis dataKey="quarter" tick={{ fontSize: 11, fill: '#6B7280' }} />
              <YAxis tickFormatter={formatAxisAmount} tick={{ fontSize: 11, fill: '#6B7280' }} />
              <Tooltip formatter={formatTooltipAmount as any} />
              <Legend />
              <Bar dataKey="inflow" name="Приток" fill="#10B981" />
              <Bar dataKey="outflow" name="Отток" fill="#EF4444" />
              <Bar dataKey="net" name="Чистый" fill="#3B82F6" />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      </div>
    </motion.div>
  );
}
