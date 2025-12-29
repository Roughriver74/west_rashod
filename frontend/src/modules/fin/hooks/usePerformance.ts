import { useMemo, useCallback, useState, useEffect, useRef } from 'react';

/**
 * Hook for optimizing expensive calculations with memoization
 */
export const useOptimizedData = <T>(
  data: T[] | null | undefined,
  filterFn?: (item: T) => boolean,
  dependencies: any[] = []
): T[] => {
  return useMemo(() => {
    if (!data || !Array.isArray(data)) return [];
    return filterFn ? data.filter(filterFn) : data;
  }, [data, filterFn, ...dependencies]);
};

/**
 * Hook for debouncing rapid changes (e.g., search input)
 */
export const useDebounce = <T>(value: T, delay: number = 500): T => {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
};

/**
 * Hook for paginating large datasets
 */
export interface UsePaginationResult<T> {
  paginatedData: T[];
  currentPage: number;
  totalPages: number;
  goToPage: (page: number) => void;
  nextPage: () => void;
  prevPage: () => void;
  hasNext: boolean;
  hasPrev: boolean;
}

export const usePagination = <T>(
  items: T[],
  itemsPerPage: number = 50
): UsePaginationResult<T> => {
  const [currentPage, setCurrentPage] = useState(1);

  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return items.slice(startIndex, endIndex);
  }, [items, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(items.length / itemsPerPage);

  const goToPage = useCallback((page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  }, [totalPages]);

  const nextPage = useCallback(() => {
    goToPage(currentPage + 1);
  }, [currentPage, goToPage]);

  const prevPage = useCallback(() => {
    goToPage(currentPage - 1);
  }, [currentPage, goToPage]);

  return {
    paginatedData,
    currentPage,
    totalPages,
    goToPage,
    nextPage,
    prevPage,
    hasNext: currentPage < totalPages,
    hasPrev: currentPage > 1
  };
};

/**
 * Hook for chunking large data processing
 */
export interface UseChunkedProcessingResult<T, R> {
  processedChunks: R[];
  isProcessing: boolean;
  processData: (processor: (chunk: T[]) => R) => Promise<void>;
}

export const useChunkedProcessing = <T, R = T[]>(
  data: T[],
  chunkSize: number = 1000
): UseChunkedProcessingResult<T, R> => {
  const [processedChunks, setProcessedChunks] = useState<R[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const processChunk = useCallback((chunk: T[], processor: (chunk: T[]) => R): Promise<R> => {
    return new Promise(resolve => {
      if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
        (window as any).requestIdleCallback(() => {
          resolve(processor(chunk));
        });
      } else {
        setTimeout(() => {
          resolve(processor(chunk));
        }, 0);
      }
    });
  }, []);

  const processData = useCallback(async (processor: (chunk: T[]) => R) => {
    setIsProcessing(true);
    const chunks: R[] = [];

    for (let i = 0; i < data.length; i += chunkSize) {
      const chunk = data.slice(i, i + chunkSize);
      const processed = await processChunk(chunk, processor);
      chunks.push(processed);
    }

    setProcessedChunks(chunks);
    setIsProcessing(false);
  }, [data, chunkSize, processChunk]);

  return { processedChunks, isProcessing, processData };
};

/**
 * Hook for lazy loading data on scroll
 */
export interface UseInfiniteScrollResult {
  isFetching: boolean;
}

export const useInfiniteScroll = (
  loadMore: () => Promise<void>,
  hasMore: boolean
): UseInfiniteScrollResult => {
  const [isFetching, setIsFetching] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (
        window.innerHeight + document.documentElement.scrollTop
        >= document.documentElement.offsetHeight - 100
        && hasMore
        && !isFetching
      ) {
        setIsFetching(true);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [hasMore, isFetching]);

  useEffect(() => {
    if (!isFetching) return;
    loadMore().finally(() => setIsFetching(false));
  }, [isFetching, loadMore]);

  return { isFetching };
};

/**
 * Hook for memoizing expensive computations
 */
export const useMemoizedComputation = <T>(
  computeFn: () => T,
  dependencies: any[]
): T => {
  return useMemo(() => {
    const startTime = performance.now();
    const result = computeFn();
    const endTime = performance.now();
    if (import.meta.env.DEV) {
      console.log(`Computation took ${(endTime - startTime).toFixed(2)}ms`);
    }
    return result;
  }, dependencies);
};

/**
 * Hook for throttling function calls
 */
export const useThrottle = <T extends (...args: any[]) => void>(
  callback: T,
  delay: number = 1000
): ((...args: Parameters<T>) => void) => {
  const lastRan = useRef(Date.now());

  return useCallback((...args: Parameters<T>) => {
    const now = Date.now();
    if (now - lastRan.current >= delay) {
      callback(...args);
      lastRan.current = now;
    }
  }, [callback, delay]);
};

/**
 * Hook for detecting mobile viewport
 */
export const useIsMobile = (breakpoint: number = 768): boolean => {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < breakpoint);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [breakpoint]);

  return isMobile;
};

export default {
  useOptimizedData,
  useDebounce,
  usePagination,
  useChunkedProcessing,
  useInfiniteScroll,
  useMemoizedComputation,
  useThrottle,
  useIsMobile
};
