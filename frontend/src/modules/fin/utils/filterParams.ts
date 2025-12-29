import type { FinFilterState } from '../stores/finFilterStore';
import { DEFAULT_DATE_TO } from '../stores/finFilterStore';

export interface FilterParamOptions {
  includeContract?: boolean;
  includeDefaultDateTo?: boolean;
  includeExcludedPayers?: boolean;
}

type FilterPayload = Record<string, string>;

const normalizeValue = (value?: string | null) =>
  value && value.trim().length > 0 ? value : undefined;

const normalizeArrayToString = (values?: string[]) => {
  if (!values || values.length === 0) {
    return undefined;
  }
  // Join array with commas for query params
  return values.filter(v => v && v.trim().length > 0).join(',');
};

export const buildFilterPayload = (
  filters: Partial<FinFilterState>,
  options: FilterParamOptions = {}
): FilterPayload => {
  const payload: FilterPayload = {};

  if (filters.dateFrom) {
    payload.date_from = filters.dateFrom;
  }

  if (
    filters.dateTo &&
    (options.includeDefaultDateTo || filters.dateTo !== DEFAULT_DATE_TO)
  ) {
    payload.date_to = filters.dateTo;
  }

  const organizations = normalizeArrayToString(filters.organizations);
  if (organizations) {
    payload.organizations = organizations;
  }

  const payers = normalizeArrayToString(filters.payers);
  if (payers) {
    payload.payers = payers;
  }

  const contracts = normalizeArrayToString(filters.contracts);
  if (contracts) {
    payload.contracts = contracts;
  }

  if (options.includeExcludedPayers !== false) {
    const excludedPayers = normalizeArrayToString(filters.excludedPayers);
    if (excludedPayers) {
      payload.excluded_payers = excludedPayers;
    }
  }

  if (options.includeContract) {
    const contract = normalizeValue(filters.contractNumber);
    if (contract) {
      payload.contract_number = contract;
    }
  }

  return payload;
};

export const buildFilterQueryString = (
  filters: Partial<FinFilterState>,
  options?: FilterParamOptions
): string => {
  const payload = buildFilterPayload(filters, options);
  const params = new URLSearchParams(payload);
  return params.toString();
};

export const filtersToCacheKey = (
  filters: Partial<FinFilterState>,
  options?: FilterParamOptions
): string => {
  // Always include date_to in cache key to avoid collisions
  const payload = buildFilterPayload(filters, {
    ...options,
    includeDefaultDateTo: true
  });
  return JSON.stringify(payload);
};

export const buildFilterParamsObject = (
  filters: Partial<FinFilterState>,
  options?: FilterParamOptions
) => {
  return buildFilterPayload(filters, options);
};
