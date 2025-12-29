/**
 * Fin KPI Page - Key Performance Indicators
 * Adapted 1-to-1 from west_fin KPIPage.tsx
 */
import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { useFinFilterValues } from '../stores/finFilterStore';
import { formatAmount } from '../utils/formatters';
import { useDebounce } from '../hooks/usePerformance';
import { buildFilterPayload } from '../utils/filterParams';
import { getKPIMetrics, getOrgEfficiency } from '../api/finApi';
import type { OrgEfficiencyMetric } from '../api/finApi';
import {
  Target, Award, Zap, DollarSign,
  Percent, Clock, BarChart2, AlertTriangle
} from 'lucide-react';
import {
  RadialBarChart, RadialBar, PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip
} from 'recharts';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

interface OrgPerformance {
  name: string;
  value: number;
  fill: string;
  [key: string]: string | number;
}

export default function FinKPIPage() {
  const filters = useFinFilterValues();
  const debouncedFilters = useDebounce(filters, 500);
  const filterPayload = useMemo(
    () => buildFilterPayload(debouncedFilters, { includeDefaultDateTo: true }),
    [debouncedFilters]
  );

  const metricsQuery = useQuery({
    queryKey: ['fin', 'kpi', 'metrics', filterPayload],
    queryFn: () => getKPIMetrics(filterPayload),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  });

  const orgEfficiencyQuery = useQuery({
    queryKey: ['fin', 'analytics', 'org-efficiency', filterPayload],
    queryFn: () => getOrgEfficiency(filterPayload),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  });

  const orgPerformanceData = useMemo<OrgPerformance[]>(() => {
    const raw = (orgEfficiencyQuery.data ?? []) as OrgEfficiencyMetric[];
    return [...raw]
      .sort((a, b) => b.totalPaid - a.totalPaid)
      .slice(0, 6)
      .map((org, idx) => ({
        name: org.name.length > 15 ? org.name.substring(0, 12) + '...' : org.name,
        value: org.totalPaid,
        fill: COLORS[idx % COLORS.length],
      }));
  }, [orgEfficiencyQuery.data]);

  const kpiData = metricsQuery.data;
  const isInitialLoading =
    (metricsQuery.isLoading && !metricsQuery.data) ||
    (orgEfficiencyQuery.isLoading && !orgEfficiencyQuery.data);

  if (metricsQuery.isError || orgEfficiencyQuery.isError) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4 text-center">
        <p className="text-gray-600">Не удалось загрузить KPI. Попробуйте еще раз.</p>
        <button
          onClick={() => {
            metricsQuery.refetch();
            orgEfficiencyQuery.refetch();
          }}
          className="px-4 py-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors"
        >
          Обновить
        </button>
      </div>
    );
  }

  if (isInitialLoading || !kpiData) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 border-4 border-gray-200 border-t-blue-500 rounded-full"
        />
        <p className="mt-4 text-gray-600">Загрузка KPI...</p>
      </div>
    );
  }

  // Use pre-calculated KPI data from backend
  const kpis = {
    repaymentVelocity: kpiData.repaymentVelocity || 0,
    paymentEfficiency: kpiData.paymentEfficiency || 0,
    avgInterestRate: kpiData.avgInterestRate || 0,
    debtRatio: kpiData.debtRatio || 0,
    activeContracts: kpiData.activeContracts || 0,
    totalContracts: kpiData.totalContracts || 0,
    totalReceived: kpiData.totalReceived || 0,
    totalExpenses: kpiData.totalExpenses || 0,
    principalPaid: kpiData.principalPaid || 0,
    interestPaid: kpiData.interestPaid || 0,
    debtBalance: (kpiData.totalReceived || 0) - (kpiData.principalPaid || 0),
    creditUtilization: kpiData.totalReceived > 0 ? (kpiData.totalExpenses / kpiData.totalReceived * 100) : 0,
    totalPayments: kpiData.totalContracts || 0
  };

  // Radial chart data
  const radialData = [
    {
      name: 'Эффективность',
      value: kpis.paymentEfficiency,
      fill: '#10B981'
    }
  ];

  const repaymentData = [
    { name: 'Погашено', value: kpis.principalPaid, fill: '#10B981' },
    { name: 'Остаток', value: kpis.debtBalance, fill: '#F59E0B' }
  ];

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
          <h1 className="text-3xl font-bold text-gray-900 m-0">KPI & Ключевые метрики</h1>
          <p className="text-base text-gray-500 mt-1">Комплексный анализ эффективности кредитного портфеля</p>
        </div>
      </div>

      {/* Main KPI Cards */}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-5 mb-6 kpi-grid-mobile">
        <motion.div
          whileHover={{ scale: 1.02, y: -4 }}
          className="p-6 rounded-2xl text-white shadow-md bg-gradient-to-br from-blue-500 to-blue-600"
        >
          <div className="flex justify-between items-start mb-4">
            <DollarSign size={32} />
            <div className="text-right">
              <span className="text-4xl font-bold">{kpis.repaymentVelocity.toFixed(1)}</span>
              <span className="text-xl opacity-80">%</span>
            </div>
          </div>
          <div className="text-lg font-semibold mb-1">Скорость погашения</div>
          <div className="text-[13px] opacity-80 mb-1">Velocity Index</div>
          <div className="text-[11px] opacity-75 mb-3 leading-snug italic">
            = (Погашено тела / Получено кредитов) × 100%
          </div>
          <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
            <div className="h-full bg-white/30 rounded-full transition-all duration-1000" style={{ width: `${kpis.repaymentVelocity}%` }} />
          </div>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.02, y: -4 }}
          className="p-6 rounded-2xl text-white shadow-md bg-gradient-to-br from-green-500 to-green-600"
        >
          <div className="flex justify-between items-start mb-4">
            <Target size={32} />
            <div className="text-right">
              <span className="text-4xl font-bold">{kpis.paymentEfficiency.toFixed(1)}</span>
              <span className="text-xl opacity-80">%</span>
            </div>
          </div>
          <div className="text-lg font-semibold mb-1">Эффективность платежей</div>
          <div className="text-[13px] opacity-80 mb-1">Payment Efficiency</div>
          <div className="text-[11px] opacity-75 mb-3 leading-snug italic">
            = (Погашено тела / Всего платежей) × 100%
          </div>
          <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
            <div className="h-full bg-white/30 rounded-full transition-all duration-1000" style={{ width: `${kpis.paymentEfficiency}%` }} />
          </div>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.02, y: -4 }}
          className="p-6 rounded-2xl text-white shadow-md bg-gradient-to-br from-orange-500 to-orange-600"
        >
          <div className="flex justify-between items-start mb-4">
            <Percent size={32} />
            <div className="text-right">
              <span className="text-4xl font-bold">{kpis.avgInterestRate.toFixed(2)}</span>
              <span className="text-xl opacity-80">%</span>
            </div>
          </div>
          <div className="text-lg font-semibold mb-1">Средняя ставка</div>
          <div className="text-[13px] opacity-80 mb-1">Average Rate</div>
          <div className="text-[11px] opacity-75 mb-3 leading-snug italic">
            = (Уплачено процентов / Получено кредитов) × 100%
          </div>
          <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
            <div className="h-full bg-white/30 rounded-full transition-all duration-1000" style={{ width: `${Math.min(kpis.avgInterestRate * 5, 100)}%` }} />
          </div>
        </motion.div>

        <motion.div
          whileHover={{ scale: 1.02, y: -4 }}
          className="p-6 rounded-2xl text-white shadow-md bg-gradient-to-br from-red-500 to-red-600"
        >
          <div className="flex justify-between items-start mb-4">
            <AlertTriangle size={32} />
            <div className="text-right">
              <span className="text-4xl font-bold">{kpis.debtRatio.toFixed(1)}</span>
              <span className="text-xl opacity-80">%</span>
            </div>
          </div>
          <div className="text-lg font-semibold mb-1">Долговая нагрузка</div>
          <div className="text-[13px] opacity-80 mb-1">Debt Ratio</div>
          <div className="text-[11px] opacity-75 mb-3 leading-snug italic">
            = (Остаток долга / Получено кредитов) × 100%
          </div>
          <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
            <div className="h-full bg-white/30 rounded-full transition-all duration-1000" style={{ width: `${kpis.debtRatio}%` }} />
          </div>
        </motion.div>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4 mb-6">
        <motion.div whileHover={{ y: -2 }} className="p-5 bg-white rounded-xl shadow-sm flex items-center gap-4">
          <div className="flex"><BarChart2 size={24} color="#3B82F6" /></div>
          <div>
            <div className="text-2xl font-bold text-gray-900">{kpis.activeContracts}</div>
            <div className="text-[13px] text-gray-500 mt-0.5">Активных договоров</div>
          </div>
        </motion.div>

        <motion.div whileHover={{ y: -2 }} className="p-5 bg-white rounded-xl shadow-sm flex items-center gap-4">
          <div className="flex"><Clock size={24} color="#10B981" /></div>
          <div>
            <div className="text-2xl font-bold text-gray-900">{kpis.totalPayments}</div>
            <div className="text-[13px] text-gray-500 mt-0.5">Всего платежей</div>
          </div>
        </motion.div>

        <motion.div whileHover={{ y: -2 }} className="p-5 bg-white rounded-xl shadow-sm flex items-center gap-4">
          <div className="flex"><Zap size={24} color="#F59E0B" /></div>
          <div>
            <div className="text-2xl font-bold text-gray-900">{kpis.creditUtilization.toFixed(1)}%</div>
            <div className="text-[13px] text-gray-500 mt-0.5">Использование кредитов</div>
          </div>
        </motion.div>

        <motion.div whileHover={{ y: -2 }} className="p-5 bg-white rounded-xl shadow-sm flex items-center gap-4">
          <div className="flex"><Award size={24} color="#8B5CF6" /></div>
          <div>
            <div className="text-2xl font-bold text-gray-900">{formatAmount(kpis.totalReceived)}</div>
            <div className="text-[13px] text-gray-500 mt-0.5">Общий объем кредитов</div>
          </div>
        </motion.div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-5 charts-grid-mobile">
        {/* Payment Efficiency Gauge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="p-6 bg-white rounded-xl shadow-sm"
        >
          <h2 className="text-lg font-semibold text-gray-900 mb-5">Эффективность погашения</h2>
          <ResponsiveContainer width="100%" height={300}>
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="100%"
              data={radialData}
              startAngle={180}
              endAngle={0}
            >
              <RadialBar
                background
                dataKey="value"
                cornerRadius={10}
              />
              <text
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="middle"
                style={{ fontSize: '32px', fontWeight: 'bold', fill: '#111827' }}
              >
                {kpis.paymentEfficiency.toFixed(1)}%
              </text>
            </RadialBarChart>
          </ResponsiveContainer>
          <div className="text-center text-[13px] text-gray-500 mt-4">
            Соотношение погашения тела к общим выплатам
          </div>
        </motion.div>

        {/* Debt Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="p-6 bg-white rounded-xl shadow-sm"
        >
          <h2 className="text-lg font-semibold text-gray-900 mb-5">Распределение долга</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={repaymentData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {repaymentData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => formatAmount(value as number)} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-6 mt-4">
            <div className="flex items-center gap-2 text-[13px] text-gray-700">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span>Погашено: {formatAmount(kpis.principalPaid)}</span>
            </div>
            <div className="flex items-center gap-2 text-[13px] text-gray-700">
              <div className="w-3 h-3 rounded-full bg-orange-500" />
              <span>Остаток: {formatAmount(kpis.debtBalance)}</span>
            </div>
          </div>
        </motion.div>

        {/* Organization Performance */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="col-span-2 p-6 bg-white rounded-xl shadow-sm"
        >
          <h2 className="text-lg font-semibold text-gray-900 mb-5">Распределение по организациям</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={orgPerformanceData}
                cx="50%"
                cy="50%"
                labelLine={true}
                label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(1)}%`}
                outerRadius={110}
                fill="#8884d8"
                dataKey="value"
              >
                {orgPerformanceData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => formatAmount(value as number)} />
            </PieChart>
          </ResponsiveContainer>
        </motion.div>
      </div>
    </motion.div>
  );
}
