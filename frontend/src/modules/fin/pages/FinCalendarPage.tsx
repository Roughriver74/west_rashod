/**
 * Fin Calendar Page - Payments calendar
 * Adapted 1-to-1 from west_fin CalendarPage.tsx
 */
import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { useFinFilterValues } from '../stores/finFilterStore';
import { getExpenses } from '../api/finApi';
import type { FinExpense } from '../api/finApi';
import { formatAmount } from '../utils/formatters';
import { useDebounce } from '../hooks/usePerformance';
import { buildFilterPayload } from '../utils/filterParams';
import { Calendar as CalendarIcon, AlertCircle, Clock } from 'lucide-react';
import {
  format, parseISO, startOfMonth, endOfMonth, eachDayOfInterval,
  isSameDay, addMonths, subMonths
} from 'date-fns';
import { ru } from 'date-fns/locale';

interface PaymentStats {
  total: number;
  count: number;
  avgPerDay: number;
  daysWithPayments: number;
}

export default function FinCalendarPage() {
  const filters = useFinFilterValues();
  const debouncedFilters = useDebounce(filters, 500);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  // Get month range
  const monthStart = format(startOfMonth(currentDate), 'yyyy-MM-dd');
  const monthEnd = format(endOfMonth(currentDate), 'yyyy-MM-dd');

  const baseFilterPayload = useMemo(
    () => buildFilterPayload(debouncedFilters, { includeDefaultDateTo: true }),
    [debouncedFilters]
  );

  const calendarParams = useMemo(() => {
    const { payers, ...rest } = baseFilterPayload as { payers?: string };
    return {
      ...rest,
      date_from: monthStart,
      date_to: monthEnd,
      limit: 1000000,
      ...(payers ? { recipients: payers } : {}),
    };
  }, [baseFilterPayload, monthStart, monthEnd]);

  const expensesQuery = useQuery({
    queryKey: ['fin', 'expenses', 'calendar', calendarParams],
    queryFn: () => getExpenses(calendarParams),
    placeholderData: keepPreviousData,
    staleTime: 2 * 60 * 1000,
  });

  const expenses = expensesQuery.data?.items || [];

  const getPaymentsForDate = (date: Date): FinExpense[] => {
    return expenses.filter(e => {
      if (!e.document_date) return false;
      return isSameDay(parseISO(e.document_date), date);
    });
  };

  const getDaysInMonth = (): Date[] => {
    const start = startOfMonth(currentDate);
    const end = endOfMonth(currentDate);
    return eachDayOfInterval({ start, end });
  };

  const stats = useMemo<PaymentStats>(() => {
    const monthStartDate = startOfMonth(currentDate);
    const monthEndDate = endOfMonth(currentDate);

    const monthPayments = expenses.filter(e => {
      if (!e.document_date) return false;
      const date = parseISO(e.document_date);
      return date >= monthStartDate && date <= monthEndDate;
    });

    const total = monthPayments.reduce((sum, e) => sum + (Number(e.amount) || 0), 0);
    const avgPerDay = total / getDaysInMonth().length;
    const paymentsWithDates = monthPayments.filter(
      (payment): payment is FinExpense & { document_date: string } => Boolean(payment.document_date)
    );
    const daysWithPayments = new Set(
      paymentsWithDates.map(payment => format(parseISO(payment.document_date), 'yyyy-MM-dd'))
    ).size;

    return {
      total,
      count: monthPayments.length,
      avgPerDay,
      daysWithPayments
    };
  }, [expenses, currentDate]);

  if (expensesQuery.isLoading && !expensesQuery.data) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 border-4 border-gray-200 border-t-blue-500 rounded-full"
        />
        <p className="mt-4 text-gray-600">Загрузка календаря...</p>
      </div>
    );
  }

  if (expensesQuery.isError) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4 text-center">
        <p className="text-gray-600">Не удалось загрузить данные календаря. Попробуйте еще раз.</p>
        <button
          onClick={() => expensesQuery.refetch()}
          className="px-4 py-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors"
        >
          Обновить
        </button>
      </div>
    );
  }

  const days = getDaysInMonth();
  const selectedPayments = selectedDate ? getPaymentsForDate(selectedDate) : [];

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
          <h1 className="text-3xl font-bold text-gray-900 m-0">Календарь платежей</h1>
          <p className="text-base text-gray-500 mt-1">График и история транзакций</p>
        </div>
      </div>

      {/* Month Stats */}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-5 mb-6 kpi-grid-mobile">
        <motion.div whileHover={{ y: -4 }} className="p-5 bg-white rounded-xl shadow-sm flex items-center gap-4">
          <div className="flex"><CalendarIcon size={24} color="#3B82F6" /></div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Платежей за месяц</div>
            <div className="text-2xl font-bold text-gray-900">{stats.count}</div>
          </div>
        </motion.div>

        <motion.div whileHover={{ y: -4 }} className="p-5 bg-white rounded-xl shadow-sm flex items-center gap-4">
          <div className="flex"><Clock size={24} color="#10B981" /></div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Дней с платежами</div>
            <div className="text-2xl font-bold text-gray-900">{stats.daysWithPayments}</div>
          </div>
        </motion.div>

        <motion.div whileHover={{ y: -4 }} className="p-5 bg-white rounded-xl shadow-sm flex items-center gap-4">
          <div className="flex"><AlertCircle size={24} color="#F59E0B" /></div>
          <div>
            <div className="text-sm text-gray-500 mb-1">Общая сумма</div>
            <div className="text-2xl font-bold text-gray-900">{formatAmount(stats.total)}</div>
          </div>
        </motion.div>
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm">
        {/* Calendar Controls */}
        <div className="flex justify-between items-center mb-6">
          <button
            onClick={() => setCurrentDate(subMonths(currentDate, 1))}
            className="px-4 py-2 bg-gray-100 border-0 rounded-lg cursor-pointer text-lg font-semibold text-gray-700 hover:bg-gray-200"
          >
            ←
          </button>
          <h2 className="text-2xl font-semibold text-gray-900 capitalize m-0">
            {format(currentDate, 'LLLL yyyy', { locale: ru })}
          </h2>
          <button
            onClick={() => setCurrentDate(addMonths(currentDate, 1))}
            className="px-4 py-2 bg-gray-100 border-0 rounded-lg cursor-pointer text-lg font-semibold text-gray-700 hover:bg-gray-200"
          >
            →
          </button>
        </div>

        {/* Weekdays */}
        <div className="grid grid-cols-7 gap-2 mb-2">
          {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map(day => (
            <div key={day} className="text-center text-sm font-semibold text-gray-500 p-2">{day}</div>
          ))}
        </div>

        {/* Calendar Grid */}
        <div className="grid grid-cols-7 gap-2">
          {/* Empty cells for days before month starts */}
          {Array.from({ length: (days[0].getDay() + 6) % 7 }).map((_, i) => (
            <div key={`empty-${i}`} className="aspect-square" />
          ))}

          {/* Days */}
          {days.map(day => {
            const payments = getPaymentsForDate(day);
            const totalAmount = payments.reduce((sum, p) => sum + (Number(p.amount) || 0), 0);
            const isSelected = selectedDate && isSameDay(day, selectedDate);
            const isToday = isSameDay(day, new Date());

            return (
              <motion.div
                key={day.toISOString()}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setSelectedDate(day)}
                className={`aspect-square border rounded-lg p-2 cursor-pointer flex flex-col transition-all bg-white ${
                  isToday ? 'border-blue-500 border-2' : 'border-gray-200'
                } ${
                  isSelected ? 'bg-blue-50 border-blue-500' : ''
                } ${
                  payments.length > 0 ? 'bg-green-50 border-green-500' : ''
                }`}
              >
                <div className="text-sm font-semibold text-gray-900 mb-1">{format(day, 'd')}</div>
                {payments.length > 0 && (
                  <div className="text-[11px] mt-auto">
                    <div className="text-green-600 font-semibold">{payments.length}</div>
                    <div className="text-gray-500 text-[10px]">{formatAmount(totalAmount)}</div>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>

        {/* Selected Date Details */}
        {selectedDate && selectedPayments.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 p-5 bg-gray-50 rounded-lg border border-gray-200"
          >
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Платежи за {format(selectedDate, 'd MMMM yyyy', { locale: ru })}
            </h3>
            <div className="flex flex-col gap-3 mb-4">
              {selectedPayments.map((payment, idx) => (
                <div key={idx} className="flex justify-between items-center p-3 bg-white rounded border border-gray-200">
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-gray-900 mb-1">{payment.organization || 'Без организации'}</div>
                    <div className="text-xs text-gray-500">
                      {payment.contract_number
                        ? payment.contract_number.length > 50
                          ? payment.contract_number.substring(0, 47) + '...'
                          : payment.contract_number
                        : 'Без договора'}
                    </div>
                  </div>
                  <div className="text-base font-bold text-red-500">{formatAmount(payment.amount)}</div>
                </div>
              ))}
            </div>
            <div className="text-base font-semibold text-gray-900 text-right pt-3 border-t border-gray-200">
              <strong>Итого:</strong> {formatAmount(selectedPayments.reduce((sum, p) => sum + (Number(p.amount) || 0), 0))}
            </div>
          </motion.div>
        )}

        {selectedDate && selectedPayments.length === 0 && (
          <div className="mt-6 p-5 bg-gray-50 rounded-lg border border-gray-200 text-center text-gray-500">
            Нет платежей за {format(selectedDate, 'd MMMM yyyy', { locale: ru })}
          </div>
        )}
      </div>
    </motion.div>
  );
}
