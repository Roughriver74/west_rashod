import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, FileText } from 'lucide-react';
import { Button, message } from 'antd';
import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';
import { cn } from '@/lib/utils';

export interface ExportColumn<T> {
  key: keyof T | string;
  header: string;
  formatter?: (value: any) => string;
}

interface ExportButtonProps<T> {
  data: T[];
  columns: ExportColumn<T>[];
  filename?: string;
}

export function ExportButton<T extends Record<string, any>>({
  data,
  columns,
  filename = 'export'
}: ExportButtonProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  const formatValue = (item: T, column: ExportColumn<T>): string => {
    const value = item[column.key as keyof T];
    if (column.formatter) {
      return column.formatter(value);
    }
    if (value === null || value === undefined) {
      return '';
    }
    return String(value);
  };

  const exportToCSV = () => {
    try {
      setExporting(true);
      message.loading('Экспорт в CSV...', 0);

      if (!data || !Array.isArray(data) || data.length === 0) {
        message.destroy();
        message.error('Нет данных для экспорта');
        return;
      }

      const headers = columns.map(col => col.header);
      const csvContent = [
        headers.join(','),
        ...data.map(row =>
          columns.map(column => {
            const value = formatValue(row, column);
            return value.includes(',') || value.includes('"') || value.includes('\n')
              ? `"${value.replace(/"/g, '""')}"`
              : value;
          }).join(',')
        )
      ].join('\n');

      const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
      saveAs(blob, `${filename}.csv`);

      message.destroy();
      message.success('CSV сохранен!');
      setIsOpen(false);
    } catch (error) {
      console.error('Export error:', error);
      message.destroy();
      message.error('Ошибка при экспорте');
    } finally {
      setExporting(false);
    }
  };

  const exportToXLSX = () => {
    try {
      setExporting(true);
      message.loading('Экспорт в Excel...', 0);

      if (!data || !Array.isArray(data) || data.length === 0) {
        message.destroy();
        message.error('Нет данных для экспорта');
        return;
      }

      // Convert data to format with headers
      const exportData = data.map(row => {
        const obj: Record<string, string> = {};
        columns.forEach(column => {
          obj[column.header] = formatValue(row, column);
        });
        return obj;
      });

      const worksheet = XLSX.utils.json_to_sheet(exportData);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Данные');

      // Auto-size columns
      const colWidths = columns.map(col => ({
        wch: Math.max(
          col.header.length,
          ...data.map(row => formatValue(row, col).length)
        ) + 2
      }));
      worksheet['!cols'] = colWidths;

      const xlsxBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
      const blob = new Blob([xlsxBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      saveAs(blob, `${filename}.xlsx`);

      message.destroy();
      message.success('Excel файл сохранен!');
      setIsOpen(false);
    } catch (error) {
      console.error('Export error:', error);
      message.destroy();
      message.error('Ошибка при экспорте');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="relative">
      <Button
        onClick={() => setIsOpen(!isOpen)}
        disabled={exporting}
        icon={<Download size={18} />}
      >
        Экспорт
      </Button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div
              className="fixed inset-0 z-[999]"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="absolute top-full right-0 mt-2 bg-white rounded-lg shadow-lg z-[1000] min-w-[200px] p-2 border border-gray-200"
            >
              <motion.button
                whileHover={{ backgroundColor: '#F3F4F6' }}
                onClick={exportToCSV}
                disabled={exporting}
                className={cn(
                  "flex items-center gap-3 w-full px-3 py-2.5 bg-transparent border-none rounded-md cursor-pointer text-sm text-gray-700 text-left transition-colors",
                  exporting && "opacity-50 cursor-not-allowed"
                )}
              >
                <FileText size={16} />
                <span>Экспорт в CSV</span>
              </motion.button>

              <motion.button
                whileHover={{ backgroundColor: '#F3F4F6' }}
                onClick={exportToXLSX}
                disabled={exporting}
                className={cn(
                  "flex items-center gap-3 w-full px-3 py-2.5 bg-transparent border-none rounded-md cursor-pointer text-sm text-gray-700 text-left transition-colors",
                  exporting && "opacity-50 cursor-not-allowed"
                )}
              >
                <FileText size={16} />
                <span>Экспорт в Excel</span>
              </motion.button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

export default ExportButton;
