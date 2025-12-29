/**
 * Fin Receipts Page - Incoming payments list
 * Converted to Tailwind + framer-motion styling
 */
import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { ArrowUpCircle, Search, FileText, Building, Calendar, RefreshCw } from 'lucide-react';
import { format, parseISO } from 'date-fns';

import { useFinFilterValues } from '../stores/finFilterStore';
import { formatAmount, formatFullAmount } from '../utils/formatters';
import { useDebounce } from '../hooks/usePerformance';
import { buildFilterPayload } from '../utils/filterParams';
import { getReceipts, getReceiptsSummary } from '../api/finApi';
import type { FinReceipt } from '../api/finApi';

const PAGE_SIZE = 20;

export default function FinReceiptsPage() {
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
    const params: {
      date_from?: string;
      date_to?: string;
      organizations?: string;
      skip: number;
      limit: number;
      payers?: string;
    } = {
      ...filterPayload,
      skip: (page - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
    };

    if (debouncedSearchTerm) {
      params.payers = debouncedSearchTerm;
    }

    return params;
  }, [filterPayload, page, debouncedSearchTerm]);

  const queryClient = useQueryClient();
  const receiptsQuery = useQuery({
    queryKey: ['fin', 'receipts', queryParams],
    queryFn: () => getReceipts(queryParams),
    placeholderData: keepPreviousData,
    staleTime: 2 * 60 * 1000,
  });

  const summaryQuery = useQuery({
    queryKey: ['fin', 'receipts-summary', filterPayload],
    queryFn: () => getReceiptsSummary(filterPayload),
    staleTime: 2 * 60 * 1000,
  });

  const receipts: FinReceipt[] = receiptsQuery.data?.items ?? [];
  const total = receiptsQuery.data?.total ?? 0;
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
      queryKey: ['fin', 'receipts', nextParams],
      queryFn: () => getReceipts(nextParams),
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
    receiptsQuery.refetch();
    summaryQuery.refetch();
  };

  if (receiptsQuery.isLoading && !receiptsQuery.data) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 border-4 border-gray-200 border-t-green-500 rounded-full"
        />
        <p className="mt-4 text-gray-600">Загрузка поступлений...</p>
      </div>
    );
  }

  if (receiptsQuery.isError) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4 text-center">
        <p className="text-gray-600">Не удалось загрузить поступления. Попробуйте еще раз.</p>
        <button
          onClick={handleRefresh}
          className="px-4 py-2 rounded-lg bg-green-500 text-white hover:bg-green-600 transition-colors"
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
          <h1 className="text-3xl font-bold text-gray-900 m-0">Поступления</h1>
          <p className="text-base text-gray-500 mt-1">Входящие платежи и зачисления</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] gap-5 mb-6 kpi-grid-mobile">
        <motion.div whileHover={{ y: -4 }} className="p-5 bg-white rounded-xl shadow-sm flex items-center gap-4 border-l-4 border-green-500 card-compact-mobile">
          <ArrowUpCircle size={24} color="#10B981" />
          <div>
            <div className="text-sm text-gray-500 mb-1">Всего поступлений</div>
            <div className="text-2xl font-bold text-gray-900">{summaryQuery.data?.total_records || 0}</div>
            <div className="text-[10px] text-gray-400 mt-1 leading-snug italic">
              Количество записей с учётом фильтров
            </div>
          </div>
        </motion.div>

        <motion.div whileHover={{ y: -4 }} className="p-5 bg-white rounded-xl shadow-sm flex items-center gap-4 border-l-4 border-emerald-500 card-compact-mobile">
          <ArrowUpCircle size={24} color="#059669" />
          <div>
            <div className="text-sm text-gray-500 mb-1">Общая сумма</div>
            <div className="text-2xl font-bold text-green-600">
              {formatAmount(summaryQuery.data?.total_amount || 0)}
            </div>
            <div className="text-[10px] text-gray-400 mt-1 leading-snug italic">
              Сумма всех поступлений за выбранный период
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
            placeholder="Поиск по плательщику..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full py-3 px-4 pl-12 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
          />
        </div>
        <button
          onClick={handleRefresh}
          disabled={receiptsQuery.isFetching}
          className="px-5 py-3 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors flex items-center gap-2 text-gray-700"
        >
          <RefreshCw size={18} className={receiptsQuery.isFetching ? 'animate-spin' : ''} />
          Обновить
        </button>
      </div>

      {/* Receipts List */}
      <div className="flex flex-col gap-3">
        {receipts.map((receipt, idx) => (
          <motion.div
            key={receipt.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.03 }}
            className="bg-white rounded-xl shadow-sm overflow-hidden"
          >
            <div className="p-5 flex justify-between items-center receipt-row-mobile">
              <div className="flex-1">
                <div className="text-base font-semibold text-gray-900 mb-2 flex items-center gap-2">
                  <FileText size={18} color="#10B981" />
                  {receipt.document_number || 'Без номера'}
                </div>
                <div className="text-[13px] text-gray-500 flex gap-4 items-center flex-wrap">
                  {receipt.payer && (
                    <span className="flex items-center gap-1 text-blue-600">
                      <Building size={14} />
                      {receipt.payer.length > 40 ? receipt.payer.substring(0, 37) + '...' : receipt.payer}
                    </span>
                  )}
                  {receipt.organization && (
                    <span className="flex items-center gap-1">
                      <Building size={14} />
                      {receipt.organization.length > 30 ? receipt.organization.substring(0, 27) + '...' : receipt.organization}
                    </span>
                  )}
                  {receipt.document_date && (
                    <span className="flex items-center gap-1">
                      <Calendar size={14} />
                      {format(parseISO(receipt.document_date), 'dd.MM.yyyy')}
                    </span>
                  )}
                </div>
                {receipt.contract_number && (
                  <div className="mt-2">
                    <span className="px-2 py-1 rounded text-xs bg-blue-100 text-blue-700">
                      {receipt.contract_number}
                    </span>
                  </div>
                )}
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-500 mb-1">Сумма</div>
                <div className="text-lg font-semibold text-green-600">
                  +{formatFullAmount(receipt.amount)} ₽
                </div>
                {receipt.commission !== 0 && receipt.commission !== null && (
                  <div className="text-xs text-gray-400 mt-1">
                    Комиссия: {formatFullAmount(receipt.commission)} ₽
                  </div>
                )}
              </div>
            </div>
            {receipt.payment_purpose && (
              <div className="px-5 pb-4 pt-0">
                <div className="text-xs text-gray-400 mb-1">Назначение платежа</div>
                <div className="text-sm text-gray-600 line-clamp-2">
                  {receipt.payment_purpose}
                </div>
              </div>
            )}
          </motion.div>
        ))}

        {receipts.length === 0 && !receiptsQuery.isLoading && (
          <div className="text-center py-12 text-gray-500">
            Поступления не найдены
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
                ? 'bg-green-500 text-white hover:bg-green-600'
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
                ? 'bg-green-500 text-white hover:bg-green-600'
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
