import { parseISO, format, isValid } from 'date-fns';

/**
 * Format number with units
 */
export const formatAmount = (value: number | string | null | undefined): string => {
  if (value == null || isNaN(Number(value))) return '0';
  const num = Number(value);
  const sign = num < 0 ? '-' : '';
  const abs = Math.abs(num);

  if (abs >= 1000000000) {
    return sign + (abs / 1000000000).toFixed(1) + ' млрд';
  }
  if (abs >= 1000000) {
    return sign + (abs / 1000000).toFixed(1) + ' млн';
  }
  if (abs >= 1000) {
    return sign + (abs / 1000).toFixed(0) + ' тыс';
  }
  return sign + abs.toFixed(0);
};

/**
 * Format number for Y-axis
 */
export const formatAxisAmount = (value: number | string | null | undefined): string => {
  if (value == null || isNaN(Number(value))) return '0';
  const num = Number(value);
  if (num >= 1000000) {
    return (num / 1000000).toFixed(0) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(0) + 'K';
  }
  return num.toFixed(0);
};

/**
 * Format date for X-axis (short format)
 */
export const formatShortDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '';
  return dateStr;
};

/**
 * Format tooltip amount
 */
export const formatTooltipAmount = (value: number | string | null | undefined): string => {
  if (value == null || isNaN(Number(value))) return '0 млн ₽';
  const num = Number(value);
  return (num / 1000000).toFixed(2) + ' млн ₽';
};

/**
 * Sample array to reduce density (take every Nth element)
 */
export const sampleArray = <T>(arr: T[], n: number = 2): T[] => {
  if (!arr || arr.length === 0) return [];
  if (arr.length <= 20) return arr;
  return arr.filter((_, index) => index % n === 0);
};

/**
 * Format short amount (for axis labels)
 */
export const formatShortAmount = (value: number | string | null | undefined): string => {
  if (value == null || isNaN(Number(value))) return '0';
  const num = Number(value);
  const abs = Math.abs(num);

  if (abs >= 1000000000) {
    return (abs / 1000000000).toFixed(1) + ' млрд';
  }
  if (abs >= 1000000) {
    return (abs / 1000000).toFixed(1) + ' млн';
  }
  if (abs >= 1000) {
    return (abs / 1000).toFixed(0) + ' тыс';
  }
  return abs.toFixed(0);
};

/**
 * Format number with thousand separators
 */
export const formatFullAmount = (value: number | string | null | undefined): string => {
  if (value == null || isNaN(Number(value))) return '0';
  const num = Number(value);
  return num.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
};

/**
 * Safely format date with error handling
 */
export const safeFormatDate = (
  dateStr: string | null | undefined,
  formatStr: string,
  locale?: any
): string => {
  if (!dateStr) return '-';

  try {
    const parsed = parseISO(dateStr);

    if (!isValid(parsed)) {
      console.warn(`Invalid date value: ${dateStr}`);
      return '-';
    }

    return locale ? format(parsed, formatStr, { locale }) : format(parsed, formatStr);
  } catch (error) {
    console.error(`Error formatting date: ${dateStr}`, error);
    return '-';
  }
};
