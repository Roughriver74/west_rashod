/**
 * Fin Turnover Balance Page - ОСВ (оборотно-сальдовая ведомость)
 * Adapted 1-to-1 from west_fin TurnoverBalancePage.tsx
 */
import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { useFinFilterValues } from '../stores/finFilterStore';
import { useDebounce } from '../hooks/usePerformance';
import { buildFilterPayload } from '../utils/filterParams';
import { getTurnoverBalance, type TurnoverBalanceRow } from '../api/finApi';
import { ChevronDown, ChevronRight } from 'lucide-react';

export default function FinTurnoverBalancePage() {
  const filters = useFinFilterValues();
  const debouncedFilters = useDebounce(filters, 500);
  const [expandedAccounts, setExpandedAccounts] = useState<Set<string>>(
    new Set()
  );
  const [expandedCounterparties, setExpandedCounterparties] = useState<
    Set<string>
  >(new Set());

  const filterPayload = useMemo(
    () => buildFilterPayload(debouncedFilters, { includeDefaultDateTo: true }),
    [debouncedFilters]
  );

  // Account filter disabled - show all accounts (account 67 may not exist in DB)
  const queryParams = useMemo(
    () => ({
      ...filterPayload,
      // account_number: '67',  // Disabled - account 67 may not exist in DB
    }),
    [filterPayload]
  );

  const turnoverQuery = useQuery({
    queryKey: ['fin', 'analytics', 'turnover-balance', queryParams],
    queryFn: () => getTurnoverBalance(queryParams),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  });

  const data = (turnoverQuery.data ?? []) as TurnoverBalanceRow[];
  const isInitialLoading = turnoverQuery.isLoading && !turnoverQuery.data;

  const toggleAccount = (account: string) => {
    const newSet = new Set(expandedAccounts);
    if (newSet.has(account)) {
      newSet.delete(account);
    } else {
      newSet.add(account);
    }
    setExpandedAccounts(newSet);
  };

  const toggleCounterparty = (account: string, counterparty: string) => {
    const key = `${account}:${counterparty}`;
    const newSet = new Set(expandedCounterparties);
    if (newSet.has(key)) {
      newSet.delete(key);
    } else {
      newSet.add(key);
    }
    setExpandedCounterparties(newSet);
  };

  // Format number with thousands separator
  const formatNumber = (value: number): string => {
    if (value === 0) return '0,00';
    return value.toLocaleString('ru-RU', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  // Group data by account and counterparty
  const groupedData = useMemo(() => {
    const accounts: Record<
      string,
      {
        account: string;
        counterparties: Record<
          string,
          {
            counterparty: string;
            inn?: string;
            contracts: TurnoverBalanceRow[];
            totals: {
              balanceStartDebit: number;
              balanceStartCredit: number;
              turnoverDebit: number;
              turnoverCredit: number;
              balanceEndDebit: number;
              balanceEndCredit: number;
            };
          }
        >;
        totals: TurnoverBalanceRow;
      }
    > = {};

    // First pass: collect all rows
    data.forEach(row => {
      const account = row.account || '';
      if (!account) return;

      // Initialize account if needed
      if (!accounts[account]) {
        accounts[account] = {
          account,
          counterparties: {},
          totals: {
            account,
            balanceStartDebit: 0,
            balanceStartCredit: 0,
            turnoverDebit: 0,
            turnoverCredit: 0,
            balanceEndDebit: 0,
            balanceEndCredit: 0,
            level: 0,
          },
        };
      }

      if (row.level === 0) {
        // Account level - update totals
        accounts[account].totals = row;
      } else if (row.level === 1) {
        // Counterparty level
        const counterparty = row.counterparty || '';
        if (counterparty && !accounts[account].counterparties[counterparty]) {
          accounts[account].counterparties[counterparty] = {
            counterparty,
            inn: row.inn || undefined,
            contracts: [],
            totals: {
              balanceStartDebit: 0,
              balanceStartCredit: 0,
              turnoverDebit: 0,
              turnoverCredit: 0,
              balanceEndDebit: 0,
              balanceEndCredit: 0,
            },
          };
        }
        // Update counterparty totals from level 1 row
        if (counterparty) {
          const cp = accounts[account].counterparties[counterparty];
          cp.totals.balanceStartDebit = row.balanceStartDebit;
          cp.totals.balanceStartCredit = row.balanceStartCredit;
          cp.totals.turnoverDebit = row.turnoverDebit;
          cp.totals.turnoverCredit = row.turnoverCredit;
          cp.totals.balanceEndDebit = row.balanceEndDebit;
          cp.totals.balanceEndCredit = row.balanceEndCredit;
        }
      } else if (row.level === 2) {
        // Contract level
        const counterparty = row.counterparty || row.parentCounterparty || '';
        if (counterparty) {
          if (!accounts[account].counterparties[counterparty]) {
            accounts[account].counterparties[counterparty] = {
              counterparty,
              inn: row.inn || undefined,
              contracts: [],
              totals: {
                balanceStartDebit: 0,
                balanceStartCredit: 0,
                turnoverDebit: 0,
                turnoverCredit: 0,
                balanceEndDebit: 0,
                balanceEndCredit: 0,
              },
            };
          }
          accounts[account].counterparties[counterparty].contracts.push(row);
        }
      }
    });

    return accounts;
  }, [data]);

  // Calculate totals
  const grandTotals = useMemo(() => {
    let balanceStartDebit = 0;
    let balanceStartCredit = 0;
    let turnoverDebit = 0;
    let turnoverCredit = 0;
    let balanceEndDebit = 0;
    let balanceEndCredit = 0;

    Object.values(groupedData).forEach(acc => {
      balanceStartDebit += acc.totals.balanceStartDebit;
      balanceStartCredit += acc.totals.balanceStartCredit;
      turnoverDebit += acc.totals.turnoverDebit;
      turnoverCredit += acc.totals.turnoverCredit;
      balanceEndDebit += acc.totals.balanceEndDebit;
      balanceEndCredit += acc.totals.balanceEndCredit;
    });

    return {
      balanceStartDebit,
      balanceStartCredit,
      turnoverDebit,
      turnoverCredit,
      balanceEndDebit,
      balanceEndCredit,
    };
  }, [groupedData]);

  if (turnoverQuery.isError) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4 text-center">
        <p className="text-gray-600">
          Не удалось загрузить данные оборотно-сальдовой ведомости. Попробуйте
          еще раз.
        </p>
        <button
          onClick={() => turnoverQuery.refetch()}
          className="px-4 py-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors"
        >
          Обновить
        </button>
      </div>
    );
  }

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
          <h1 className="text-3xl font-bold text-gray-900 m-0">
            Оборотно-сальдовая ведомость
          </h1>
          <p className="text-base text-gray-500 mt-1">За период</p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-green-50">
                <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-sm text-gray-700">
                  Контрагенты
                </th>
                <th className="border border-gray-300 px-4 py-3 text-left font-semibold text-sm text-gray-700">
                  ИНН
                </th>
                <th
                  className="border border-gray-300 px-4 py-3 text-center font-semibold text-sm text-gray-700"
                  colSpan={2}
                >
                  Сальдо на начало периода
                </th>
                <th
                  className="border border-gray-300 px-4 py-3 text-center font-semibold text-sm text-gray-700"
                  colSpan={2}
                >
                  Обороты за период
                </th>
                <th
                  className="border border-gray-300 px-4 py-3 text-center font-semibold text-sm text-gray-700"
                  colSpan={2}
                >
                  Сальдо на конец периода
                </th>
              </tr>
              <tr className="bg-green-50">
                <th className="border border-gray-300 px-4 py-2"></th>
                <th className="border border-gray-300 px-4 py-2"></th>
                <th className="border border-gray-300 px-4 py-2 text-center font-semibold text-xs text-gray-600">
                  Дебет
                </th>
                <th className="border border-gray-300 px-4 py-2 text-center font-semibold text-xs text-gray-600">
                  Кредит
                </th>
                <th className="border border-gray-300 px-4 py-2 text-center font-semibold text-xs text-gray-600">
                  Дебет
                </th>
                <th className="border border-gray-300 px-4 py-2 text-center font-semibold text-xs text-gray-600">
                  Кредит
                </th>
                <th className="border border-gray-300 px-4 py-2 text-center font-semibold text-xs text-gray-600">
                  Дебет
                </th>
                <th className="border border-gray-300 px-4 py-2 text-center font-semibold text-xs text-gray-600">
                  Кредит
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(groupedData).map(([account, accData]) => {
                const isAccountExpanded = expandedAccounts.has(account);
                return (
                  <React.Fragment key={account}>
                    {/* Account row */}
                    <tr className="bg-green-50 hover:bg-green-100">
                      <td
                        className="border border-gray-300 px-2 py-3 font-semibold"
                        colSpan={2}
                      >
                        <button
                          onClick={() => toggleAccount(account)}
                          className="flex items-center gap-2 hover:text-blue-600 pl-2"
                        >
                          {isAccountExpanded ? (
                            <ChevronDown size={16} />
                          ) : (
                            <ChevronRight size={16} />
                          )}
                          <span>{account}</span>
                        </button>
                      </td>
                      <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                        {formatNumber(accData.totals.balanceStartDebit)}
                      </td>
                      <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                        {formatNumber(accData.totals.balanceStartCredit)}
                      </td>
                      <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                        {formatNumber(accData.totals.turnoverDebit)}
                      </td>
                      <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                        {formatNumber(accData.totals.turnoverCredit)}
                      </td>
                      <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                        {formatNumber(accData.totals.balanceEndDebit)}
                      </td>
                      <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                        {formatNumber(accData.totals.balanceEndCredit)}
                      </td>
                    </tr>
                    {/* Counterparty rows */}
                    {isAccountExpanded &&
                      Object.entries(accData.counterparties).map(
                        ([counterparty, cpData]) => {
                          const cpKey = `${account}:${counterparty}`;
                          const isCounterpartyExpanded =
                            expandedCounterparties.has(cpKey);

                          // Use counterparty totals from data
                          const cpTotals = cpData.totals;

                          return (
                            <React.Fragment key={cpKey}>
                              <tr className="hover:bg-gray-50 bg-white">
                                <td className="border border-gray-300 px-2 py-2">
                                  <button
                                    onClick={() =>
                                      toggleCounterparty(account, counterparty)
                                    }
                                    className="flex items-center gap-2 hover:text-blue-600 pl-6"
                                  >
                                    {isCounterpartyExpanded ? (
                                      <ChevronDown size={14} />
                                    ) : (
                                      <ChevronRight size={14} />
                                    )}
                                    <span>{counterparty}</span>
                                  </button>
                                </td>
                                <td className="border border-gray-300 px-4 py-2">
                                  {cpData.inn || ''}
                                </td>
                                <td className="border border-gray-300 px-4 py-2 text-right">
                                  {formatNumber(cpTotals.balanceStartDebit)}
                                </td>
                                <td className="border border-gray-300 px-4 py-2 text-right">
                                  {formatNumber(cpTotals.balanceStartCredit)}
                                </td>
                                <td className="border border-gray-300 px-4 py-2 text-right">
                                  {formatNumber(cpTotals.turnoverDebit)}
                                </td>
                                <td className="border border-gray-300 px-4 py-2 text-right">
                                  {formatNumber(cpTotals.turnoverCredit)}
                                </td>
                                <td className="border border-gray-300 px-4 py-2 text-right">
                                  {formatNumber(cpTotals.balanceEndDebit)}
                                </td>
                                <td className="border border-gray-300 px-4 py-2 text-right">
                                  {formatNumber(cpTotals.balanceEndCredit)}
                                </td>
                              </tr>
                              {/* Contract rows */}
                              {isCounterpartyExpanded &&
                                cpData.contracts.map((contract, idx) => (
                                  <tr
                                    key={`${cpKey}-${idx}`}
                                    className="hover:bg-gray-50 bg-gray-50"
                                  >
                                    <td className="border border-gray-300 px-2 py-2">
                                      <div className="pl-10 text-sm">
                                        {contract.contract || ''}
                                      </div>
                                    </td>
                                    <td className="border border-gray-300 px-4 py-2"></td>
                                    <td className="border border-gray-300 px-4 py-2 text-right text-sm">
                                      {formatNumber(contract.balanceStartDebit)}
                                    </td>
                                    <td className="border border-gray-300 px-4 py-2 text-right text-sm">
                                      {formatNumber(
                                        contract.balanceStartCredit
                                      )}
                                    </td>
                                    <td className="border border-gray-300 px-4 py-2 text-right text-sm">
                                      {formatNumber(contract.turnoverDebit)}
                                    </td>
                                    <td className="border border-gray-300 px-4 py-2 text-right text-sm">
                                      {formatNumber(contract.turnoverCredit)}
                                    </td>
                                    <td className="border border-gray-300 px-4 py-2 text-right text-sm">
                                      {formatNumber(contract.balanceEndDebit)}
                                    </td>
                                    <td className="border border-gray-300 px-4 py-2 text-right text-sm">
                                      {formatNumber(contract.balanceEndCredit)}
                                    </td>
                                  </tr>
                                ))}
                            </React.Fragment>
                          );
                        }
                      )}
                  </React.Fragment>
                );
              })}
              {/* Grand totals row */}
              <tr className="bg-green-50 font-bold">
                <td
                  className="border border-gray-300 px-4 py-3 font-semibold"
                  colSpan={2}
                >
                  Итого
                </td>
                <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                  {formatNumber(grandTotals.balanceStartDebit)}
                </td>
                <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                  {formatNumber(grandTotals.balanceStartCredit)}
                </td>
                <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                  {formatNumber(grandTotals.turnoverDebit)}
                </td>
                <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                  {formatNumber(grandTotals.turnoverCredit)}
                </td>
                <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                  {formatNumber(grandTotals.balanceEndDebit)}
                </td>
                <td className="border border-gray-300 px-4 py-3 text-right font-semibold">
                  {formatNumber(grandTotals.balanceEndCredit)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  );
}
