/**
 * Fin Expenses Page - Outgoing payments list
 * Converted to Tailwind + framer-motion styling
 */
import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { ArrowDownCircle, Search, FileText, Building, Calendar, RefreshCw, AlertTriangle } from 'lucide-react';
import { format, parseISO } from 'date-fns';

import { useFinFilterValues } from '../stores/finFilterStore';
import { formatAmount, formatFullAmount } from '../utils/formatters';
import { useDebounce } from '../hooks/usePerformance';
import { buildFilterPayload } from '../utils/filterParams';
import { getExpenses, getExpensesSummary } from '../api/finApi';
import type { FinExpense } from '../api/finApi';

const PAGE_SIZE = 20;

export default function FinExpensesPage() {
  const filters = useFinFilterValues();
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');

  const debouncedSearchTerm = useDebounce(searchTerm, 300);
  const debouncedFilters = useDebounce(filters, 500);

  const filterPayload = useMemo(
    () => buildFilterPayload(debouncedFilters, { includeDefaultDateTo: true }),
    [debouncedFilters]
  );

  const queryParams = useMemo(() => {
    const { payers, ...restFilters } = filterPayload as { payers?: string };

    const recipients = [
      payers,
      debouncedSearchTerm || undefined,
    ].filter(Boolean).join(',') || undefined;

    return {
      ...restFilters,
      skip: (page - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
      ...(recipients ? { recipients } : {}),
    };
  }, [filterPayload, page, debouncedSearchTerm]);

  const queryClient = useQueryClient();
  const expensesQuery = useQuery({
    queryKey: ['fin', 'expenses', queryParams],
    queryFn: () => getExpenses(queryParams),
    placeholderData: keepPreviousData,
    staleTime: 2 * 60 * 1000,
  });

  const summaryQuery = useQuery({
    queryKey: ['fin', 'expenses-summary', filterPayload],
    queryFn: () => getExpensesSummary(filterPayload),
    staleTime: 2 * 60 * 1000,
  });

  const expenses: FinExpense[] = expensesQuery.data?.items ?? [];
  const total = expensesQuery.data?.total ?? 0;
  const pages = Math.ceil(total / PAGE_SIZE);

  const hasNext = page < pages;
  const hasPrev = page > 1;

  useEffect(() => {
    setPage(1);
  }, [debouncedFilters, debouncedSearchTerm]);

  // Prefetch next page
  useEffect(() => {
    if (page >= pages) return;

    const nextParams = {
      ...queryParams,
      skip: page * PAGE_SIZE,
    };

    queryClient.prefetchQuery({
      queryKey: ['fin', 'expenses', nextParams],
      queryFn: () => getExpenses(nextParams),
      staleTime: 2 * 60 * 1000,
    });
  }, [page, pages, queryClient, queryParams]);

  const nextPage = () => {
    if (hasNext) {
      setPage((prev) => prev + 1);
    }
  };

  const prevPage = () => {
    if (hasPrev) {
      setPage((prev) => prev - 1);
    }
  };

  const handleRefresh = () => {
    expensesQuery.refetch();
    summaryQuery.refetch();
  };

  if (expensesQuery.isLoading && !expensesQuery.data) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 border-4 border-gray-200 border-t-red-500 rounded-full"
        />
        <p className="mt-4 text-gray-600">Загрузка расходов...</p>
      </div>
    );
  }

  if (expensesQuery.isError) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4 text-center">
        <p className="text-gray-600">Не удалось загрузить расходы. Попробуйте еще раз.</p>
        <button
          onClick={handleRefresh}
          className="px-4 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors"
        >
          Обновить
        </button>
      </div>
    );
  }

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
          <h1 className="text-3xl font-bold text-gray-900 m-0">Расходы</h1>
          <p className="text-base text-gray-500 mt-1">Исходящие платежи и списания</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] gap-5 mb-6 kpi-grid-mobile">
        <motion.div whileHover={{ y: -4 }} className="p-5 bg-white rounded-xl shadow-sm flex items-center gap-4 border-l-4 border-red-500 card-compact-mobile">
          <ArrowDownCircle size={24} color="#EF4444" />
          <div>
            <div className="text-sm text-gray-500 mb-1">Всего расходов</div>
            <div className="text-2xl font-bold text-gray-900">{summaryQuery.data?.total_records || 0}</div>
            <div className="text-[10px] text-gray-400 mt-1 leading-snug italic">
              Количество записей с учётом фильтров
            </div>
          </div>
        </motion.div>

        <motion.div whileHover={{ y: -4 }} className="p-5 bg-white rounded-xl shadow-sm flex items-center gap-4 border-l-4 border-rose-500 card-compact-mobile">
          <ArrowDownCircle size={24} color="#F43F5E" />
          <div>
            <div className="text-sm text-gray-500 mb-1">Общая сумма</div>
            <div className="text-2xl font-bold text-red-600">
              {formatAmount(summaryQuery.data?.total_amount || 0)}
            </div>
            <div className="text-[10px] text-gray-400 mt-1 leading-snug italic">
              Сумма всех расходов за выбранный период
            </div>
          </div>
        </motion.div>
      </div>

      {/* Search and Refresh */}
      <div className="flex gap-4 mb-6 flex-wrap">
        <div className="relative flex-1 min-w-[250px]">
          <Search size={20} color="#6B7280" className="absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Поиск по получателю..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full py-3 px-4 pl-12 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-red-500"
          />
        </div>
        <button
          onClick={handleRefresh}
          disabled={expensesQuery.isFetching}
          className="px-5 py-3 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors flex items-center gap-2 text-gray-700"
        >
          <RefreshCw size={18} className={expensesQuery.isFetching ? 'animate-spin' : ''} />
          Обновить
        </button>
      </div>

      {/* Expenses List */}
      <div className="flex flex-col gap-3">
        {expenses.map((expense, idx) => (
          <motion.div
            key={expense.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.03 }}
            className="bg-white rounded-xl shadow-sm overflow-hidden"
          >
            <div className="p-5 flex justify-between items-center expense-row-mobile">
              <div className="flex-1">
                <div className="text-base font-semibold text-gray-900 mb-2 flex items-center gap-2">
                  <FileText size={18} color="#EF4444" />
                  {expense.document_number || 'Без номера'}
                  {expense.unconfirmed_by_bank && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-yellow-100 text-yellow-700">
                      <AlertTriangle size={12} />
                      Не подтверждён
                    </span>
                  )}
                </div>
                <div className="text-[13px] text-gray-500 flex gap-4 items-center flex-wrap">
                  {expense.recipient && (
                    <span className="flex items-center gap-1 text-orange-600">
                      <Building size={14} />
                      {expense.recipient.length > 40 ? expense.recipient.substring(0, 37) + '...' : expense.recipient}
                    </span>
                  )}
                  {expense.organization && (
                    <span className="flex items-center gap-1">
                      <Building size={14} />
                      {expense.organization.length > 30 ? expense.organization.substring(0, 27) + '...' : expense.organization}
                    </span>
                  )}
                  {expense.document_date && (
                    <span className="flex items-center gap-1">
                      <Calendar size={14} />
                      {format(parseISO(expense.document_date), 'dd.MM.yyyy')}
                    </span>
                  )}
                </div>
                <div className="mt-2 flex gap-2 flex-wrap">
                  {expense.contract_number && (
                    <span className="px-2 py-1 rounded text-xs bg-orange-100 text-orange-700">
                      {expense.contract_number}
                    </span>
                  )}
                  {expense.expense_article && (
                    <span className="px-2 py-1 rounded text-xs bg-gray-100 text-gray-600">
                      {expense.expense_article}
                    </span>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-500 mb-1">Сумма</div>
                <div className="text-lg font-semibold text-red-600">
                  −{formatFullAmount(expense.amount)} ₽
                </div>
              </div>
            </div>
            {expense.payment_purpose && (
              <div className="px-5 pb-4 pt-0">
                <div className="text-xs text-gray-400 mb-1">Назначение платежа</div>
                <div className="text-sm text-gray-600 line-clamp-2">
                  {expense.payment_purpose}
                </div>
              </div>
            )}
          </motion.div>
        ))}

        {expenses.length === 0 && !expensesQuery.isLoading && (
          <div className="text-center py-12 text-gray-500">
            Расходы не найдены
          </div>
        )}
      </div>

      {/* Pagination Controls */}
      {pages > 1 && (
        <div className="flex justify-center items-center gap-4 mt-6 p-5">
          <button
            onClick={prevPage}
            disabled={!hasPrev}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              hasPrev
                ? 'bg-red-500 text-white hover:bg-red-600'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Предыдущая
          </button>
          <div className="text-sm text-gray-500 font-medium">
            Страница {page} из {pages} ({total} записей)
          </div>
          <button
            onClick={nextPage}
            disabled={!hasNext}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              hasNext
                ? 'bg-red-500 text-white hover:bg-red-600'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Следующая
          </button>
        </div>
      )}
    </motion.div>
  );
}
