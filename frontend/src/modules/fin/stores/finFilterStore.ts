/**
 * Zustand store for fin module global filters
 */
import { useMemo } from 'react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface FinFilterState {
  // Filter values
  organizations: string[];
  payers: string[];
  excludedPayers: string[];
  dateFrom: string;
  dateTo: string;
  contractNumber: string;
  contracts: string[];

  // Actions
  setOrganizations: (orgs: string[]) => void;
  setPayers: (payers: string[]) => void;
  setExcludedPayers: (payers: string[]) => void;
  setDateFrom: (date: string) => void;
  setDateTo: (date: string) => void;
  setContractNumber: (contract: string) => void;
  setContracts: (contracts: string[]) => void;
  resetFilters: () => void;

  // Bulk update
  setFilters: (filters: Partial<Omit<FinFilterState, keyof FinFilterActions>>) => void;
}

type FinFilterActions = {
  setOrganizations: (orgs: string[]) => void;
  setPayers: (payers: string[]) => void;
  setExcludedPayers: (payers: string[]) => void;
  setDateFrom: (date: string) => void;
  setDateTo: (date: string) => void;
  setContractNumber: (contract: string) => void;
  setContracts: (contracts: string[]) => void;
  resetFilters: () => void;
  setFilters: (filters: Partial<Omit<FinFilterState, keyof FinFilterActions>>) => void;
};

type PersistedFilters = Pick<
  FinFilterState,
  'organizations' | 'payers' | 'excludedPayers' | 'dateFrom' | 'dateTo' | 'contractNumber' | 'contracts'
>;

const sanitizeStringArray = (values?: string | string[]) => {
  // Handle migration from single string to array
  if (typeof values === 'string') {
    if (values === 'all' || !values || values.trim().length === 0) {
      return [];
    }
    return [values.trim()];
  }

  if (!values || !Array.isArray(values)) {
    return [];
  }

  const normalized = values
    .map((value) => value?.trim())
    .filter((value): value is string => Boolean(value) && value !== 'all');

  return Array.from(new Set(normalized));
};

export const DEFAULT_DATE_FROM = '2021-01-01';
export const DEFAULT_DATE_TO = '2028-12-31';

const initialState: PersistedFilters = {
  organizations: [],
  payers: [],
  excludedPayers: [],
  dateFrom: DEFAULT_DATE_FROM,
  dateTo: DEFAULT_DATE_TO,
  contractNumber: '',
  contracts: [],
};

export const useFinFilterStore = create<FinFilterState>()(
  persist(
    (set) => ({
      ...initialState,

      setOrganizations: (organizations) => set({ organizations: sanitizeStringArray(organizations) }),
      setPayers: (payers) => set({ payers: sanitizeStringArray(payers) }),
      setExcludedPayers: (excludedPayers) => set({ excludedPayers: sanitizeStringArray(excludedPayers) }),
      setDateFrom: (dateFrom) => set({ dateFrom }),
      setDateTo: (dateTo) => set({ dateTo }),
      setContractNumber: (contractNumber) => set({ contractNumber }),
      setContracts: (contracts) => set({ contracts: sanitizeStringArray(contracts) }),

      resetFilters: () => set(() => ({ ...initialState })),

      setFilters: (filters) =>
        set((state) => ({
          ...state,
          ...filters,
          ...(filters.organizations !== undefined
            ? { organizations: sanitizeStringArray(filters.organizations) }
            : {}),
          ...(filters.payers !== undefined
            ? { payers: sanitizeStringArray(filters.payers) }
            : {}),
          ...(filters.excludedPayers !== undefined
            ? { excludedPayers: sanitizeStringArray(filters.excludedPayers) }
            : {}),
          ...(filters.contracts !== undefined
            ? { contracts: sanitizeStringArray(filters.contracts) }
            : {}),
        })),
    }),
    {
      name: 'west-rashod-fin-filters', // LocalStorage key
      version: 1,
      partialize: (state): PersistedFilters => ({
        organizations: state.organizations,
        payers: state.payers,
        excludedPayers: state.excludedPayers,
        dateFrom: state.dateFrom,
        dateTo: state.dateTo,
        contractNumber: state.contractNumber,
        contracts: state.contracts,
      }),
    }
  )
);

// Selectors
export const selectFilters = (state: FinFilterState) => ({
  organizations: state.organizations,
  payers: state.payers,
  excludedPayers: state.excludedPayers,
  dateFrom: state.dateFrom,
  dateTo: state.dateTo,
  contractNumber: state.contractNumber,
  contracts: state.contracts,
});

export const selectHasActiveFilters = (state: FinFilterState) => {
  const hasOrganizations = state.organizations.length > 0;
  const hasPayers = state.payers.length > 0;
  const hasExcludedPayers = state.excludedPayers.length > 0;
  const hasContract = Boolean(state.contractNumber);
  const hasCustomDates =
    state.dateFrom !== DEFAULT_DATE_FROM || state.dateTo !== DEFAULT_DATE_TO;
  const hasContracts = state.contracts.length > 0;

  return hasOrganizations || hasPayers || hasExcludedPayers || hasContract || hasCustomDates || hasContracts;
};

export const useFinFilterValues = () => {
  const dateFrom = useFinFilterStore((state) => state.dateFrom);
  const dateTo = useFinFilterStore((state) => state.dateTo);
  const organizations = useFinFilterStore((state) => state.organizations);
  const payers = useFinFilterStore((state) => state.payers);
  const excludedPayers = useFinFilterStore((state) => state.excludedPayers);
  const contractNumber = useFinFilterStore((state) => state.contractNumber);
  const contracts = useFinFilterStore((state) => state.contracts);

  return useMemo(() => ({
    dateFrom,
    dateTo,
    organizations,
    payers,
    excludedPayers,
    contractNumber,
    contracts
  }), [dateFrom, dateTo, organizations, payers, excludedPayers, contractNumber, contracts]);
};
