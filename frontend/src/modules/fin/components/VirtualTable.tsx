import React, { useMemo, useState } from 'react';
import { useIsMobile } from '../hooks/usePerformance';
import { cn } from '@/lib/utils';

export interface VirtualTableColumn<T> {
  key: string;
  title?: string;  // alias for label
  label?: string;
  width?: number;
  flex?: number;
  minWidth?: string;
  maxWidth?: string;
  align?: 'left' | 'center' | 'right';
  render?: (item: T, index?: number) => React.ReactNode;
}

interface VirtualTableProps<T> {
  data: T[];
  columns: VirtualTableColumn<T>[];
  rowHeight?: number;
  height?: number;
  onRowClick?: (item: T, index: number) => void;
  emptyMessage?: string;
}

/**
 * Virtualized table component for rendering large datasets efficiently
 * Only renders visible rows, dramatically improving performance with 1000+ items
 */
export function VirtualTable<T extends Record<string, any>>({
  data = [],
  columns = [],
  rowHeight = 60,
  height = 600,
  onRowClick,
  emptyMessage = 'Нет данных'
}: VirtualTableProps<T>) {
  const isMobile = useIsMobile();

  const viewportHeight = typeof window !== 'undefined' ? window.innerHeight : 800;
  const actualRowHeight = isMobile ? 80 : rowHeight;
  const actualHeight = isMobile ? Math.min(height, viewportHeight - 200) : height;
  const [scrollTop, setScrollTop] = useState(0);
  const totalHeight = data.length * actualRowHeight;
  const visibleCount = Math.max(1, Math.ceil(actualHeight / actualRowHeight));
  const overscan = 5;
  const startIndex = Math.max(0, Math.floor(scrollTop / actualRowHeight) - overscan);
  const endIndex = Math.min(data.length, startIndex + visibleCount + overscan * 2);
  const visibleItems = useMemo(() => data.slice(startIndex, endIndex), [data, startIndex, endIndex]);
  const offsetY = startIndex * actualRowHeight;

  if (!data || data.length === 0) {
    return (
      <div className="p-15 text-center bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-sm text-gray-600 m-0">{emptyMessage}</p>
      </div>
    );
  }

  const renderRow = (item: T, index: number) => {
    const isEven = index % 2 === 0;

    return (
      <div
        key={index}
        className={cn(
          "border-b border-gray-200 transition-colors",
          isEven ? "bg-gray-50" : "bg-white",
          onRowClick && "cursor-pointer hover:bg-gray-100"
        )}
        style={{ height: actualRowHeight }}
        onClick={() => onRowClick && onRowClick(item, index)}
      >
        <div className="flex px-4 py-3 gap-3 items-center h-full">
          {columns.map((column, colIndex) => (
            <div
              key={colIndex}
              className="text-sm text-gray-900 overflow-hidden text-ellipsis whitespace-nowrap"
              style={{
                flex: column.width ? undefined : (column.flex || 1),
                width: column.width,
                minWidth: column.minWidth || (column.width ? undefined : (isMobile ? '80px' : '100px')),
                maxWidth: column.maxWidth,
                textAlign: column.align || 'left'
              }}
            >
              {column.render
                ? column.render(item, index)
                : item[column.key]}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      {/* Header */}
      <div className="bg-gray-50 border-b-2 border-gray-200 sticky top-0 z-10">
        <div className="flex px-4 py-3 gap-3">
          {columns.map((column, index) => (
            <div
              key={index}
              className="text-xs font-semibold text-gray-700 uppercase tracking-wider"
              style={{
                flex: column.width ? undefined : (column.flex || 1),
                width: column.width,
                minWidth: column.minWidth || (column.width ? undefined : (isMobile ? '80px' : '100px')),
                maxWidth: column.maxWidth,
                textAlign: column.align || 'left'
              }}
            >
              {column.label || column.title}
            </div>
          ))}
        </div>
      </div>

      {/* Virtualized List */}
      <div
        className="scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent"
        style={{ height: actualHeight, overflowY: 'auto' }}
        onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
      >
        <div style={{ height: totalHeight, position: 'relative' }}>
          <div style={{ transform: `translateY(${offsetY}px)` }}>
            {visibleItems.map((item, idx) => renderRow(item, startIndex + idx))}
          </div>
        </div>
      </div>

      {/* Footer with total count */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-[13px] text-gray-600 text-center">
        Всего записей: <strong>{data.length.toLocaleString()}</strong>
      </div>
    </div>
  );
}
