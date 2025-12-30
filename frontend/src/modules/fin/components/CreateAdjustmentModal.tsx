/**
 * CreateAdjustmentModal - Modal for creating manual adjustments
 * Can be pre-filled with contract data
 */
import { useState, useEffect, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  X,
  ChevronDown,
  Check,
  Search,
} from 'lucide-react';
import {
  createAdjustment,
  getContracts,
  getUniquePayers,
} from '../api/finApi';

// Searchable Select Component
interface SearchableSelectOption {
  value: string;
  label: string;
}

interface SearchableSelectProps {
  options: SearchableSelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  isLoading?: boolean;
}

function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = 'Выберите...',
  isLoading = false,
}: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredOptions = useMemo(() => {
    if (!search) return options;
    const lowerSearch = search.toLowerCase();
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(lowerSearch) ||
        opt.value.toLowerCase().includes(lowerSearch)
    );
  }, [options, search]);

  const selectedOption = options.find((opt) => opt.value === value);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setSearch('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleSelect = (optionValue: string) => {
    onChange(optionValue);
    setIsOpen(false);
    setSearch('');
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange('');
    setSearch('');
  };

  return (
    <div ref={containerRef} className="relative">
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="w-full py-2 px-3 border border-gray-300 rounded-lg bg-white cursor-pointer flex items-center justify-between gap-2 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500"
      >
        <span className={selectedOption ? 'text-gray-900' : 'text-gray-500'}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <div className="flex items-center gap-1">
          {value && (
            <button
              type="button"
              onClick={handleClear}
              className="p-0.5 hover:bg-gray-200 rounded"
            >
              <X size={14} className="text-gray-400" />
            </button>
          )}
          <ChevronDown
            size={16}
            className={`text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </div>
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-hidden"
          >
            <div className="p-2 border-b border-gray-200">
              <div className="relative">
                <Search size={16} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  ref={inputRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Поиск..."
                  className="w-full py-1.5 pl-8 pr-3 text-sm border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="max-h-48 overflow-y-auto">
              {isLoading ? (
                <div className="px-3 py-2 text-sm text-gray-500">Загрузка...</div>
              ) : filteredOptions.length === 0 ? (
                <div className="px-3 py-2 text-sm text-gray-500">Ничего не найдено</div>
              ) : (
                filteredOptions.map((option) => (
                  <div
                    key={option.value}
                    onClick={() => handleSelect(option.value)}
                    className={`px-3 py-2 text-sm cursor-pointer flex items-center justify-between hover:bg-blue-50 ${
                      option.value === value ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
                    }`}
                  >
                    <span className="truncate">{option.label}</span>
                    {option.value === value && <Check size={16} className="text-blue-600 flex-shrink-0" />}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Main Modal Component
type AdjustmentType = 'receipt' | 'expense';

interface FormData {
  adjustment_type: AdjustmentType;
  payment_type: string;  // For expense: 'Погашение долга' or 'Уплата процентов'
  amount: string;
  adjustment_date: string;
  contract_number: string;
  counterparty: string;
  description: string;
}

interface CreateAdjustmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  initialData?: {
    contractNumber?: string;
    counterparty?: string;
    description?: string;
  };
}

export default function CreateAdjustmentModal({
  isOpen,
  onClose,
  onSuccess,
  initialData,
}: CreateAdjustmentModalProps) {
  const queryClient = useQueryClient();

  const initialFormData: FormData = {
    adjustment_type: 'receipt',
    payment_type: 'Погашение долга',
    amount: '',
    adjustment_date: new Date().toISOString().split('T')[0],
    contract_number: initialData?.contractNumber || '',
    counterparty: initialData?.counterparty || '',
    description: initialData?.description || '',
  };

  const [formData, setFormData] = useState<FormData>(initialFormData);

  // Update form when initialData changes
  useEffect(() => {
    if (initialData) {
      setFormData(prev => ({
        ...prev,
        contract_number: initialData.contractNumber || prev.contract_number,
        counterparty: initialData.counterparty || prev.counterparty,
        description: initialData.description || prev.description,
      }));
    }
  }, [initialData]);

  // Queries
  const contractsQuery = useQuery({
    queryKey: ['fin', 'references', 'contracts'],
    queryFn: () => getContracts({ limit: 1000000 }),
    staleTime: 5 * 60 * 1000,
    enabled: isOpen, // Only fetch when modal is open
  });

  const payersQuery = useQuery({
    queryKey: ['fin', 'references', 'payers'],
    queryFn: () => getUniquePayers({ limit: 1000000 }),
    staleTime: 5 * 60 * 1000,
    enabled: isOpen, // Only fetch when modal is open
  });

  // Mutation
  const createMutation = useMutation({
    mutationFn: (data: {
      adjustment_date: string;
      counterparty?: string;
      contract_number?: string;
      adjustment_type: AdjustmentType;
      payment_type?: string;
      amount: number;
      description?: string;
    }) => createAdjustment(data),
    onSuccess: () => {
      // Invalidate only contract-operations to prevent duplication
      queryClient.invalidateQueries({ queryKey: ['fin', 'contract-operations'] });
      if (onSuccess) onSuccess();
      handleClose();
    },
  });

  const handleClose = () => {
    setFormData(initialFormData);
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const amount = parseFloat(formData.amount);

    // Allow negative amounts for reversals, but not zero
    if (!Number.isFinite(amount) || amount === 0) {
      alert('Введите корректную сумму (не равную нулю)');
      return;
    }

    const payload: {
      adjustment_type: AdjustmentType;
      amount: number;
      adjustment_date: string;
      contract_number?: string;
      counterparty?: string;
      description?: string;
      payment_type?: string;
    } = {
      adjustment_type: formData.adjustment_type,
      amount: amount,
      adjustment_date: formData.adjustment_date,
      contract_number: formData.contract_number || undefined,
      counterparty: formData.counterparty || undefined,
      description: formData.description || undefined,
    };

    // Add payment_type only for expense adjustments
    if (formData.adjustment_type === 'expense') {
      payload.payment_type = formData.payment_type;
    }

    createMutation.mutate(payload);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto"
      >
        <div className="p-6 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-xl font-bold text-gray-900">
            Новая корректировка
          </h2>
          <button
            onClick={handleClose}
            className="p-2 text-gray-500 hover:text-gray-700 rounded-lg"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Adjustment Type - Big Radio Cards */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Тип корректировки *
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label
                className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                  formData.adjustment_type === 'receipt'
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-300 hover:border-green-300'
                }`}
              >
                <input
                  type="radio"
                  name="adjustment_type"
                  value="receipt"
                  checked={formData.adjustment_type === 'receipt'}
                  onChange={(e) =>
                    setFormData({ ...formData, adjustment_type: e.target.value as AdjustmentType })
                  }
                  className="sr-only"
                />
                <div className="text-center">
                  <div className="text-2xl mb-1">💰</div>
                  <div className="font-semibold text-sm">Поступление</div>
                  <div className="text-xs text-gray-500 mt-1">Корректировка получения</div>
                </div>
              </label>

              <label
                className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                  formData.adjustment_type === 'expense'
                    ? 'border-orange-500 bg-orange-50'
                    : 'border-gray-300 hover:border-orange-300'
                }`}
              >
                <input
                  type="radio"
                  name="adjustment_type"
                  value="expense"
                  checked={formData.adjustment_type === 'expense'}
                  onChange={(e) =>
                    setFormData({ ...formData, adjustment_type: e.target.value as AdjustmentType })
                  }
                  className="sr-only"
                />
                <div className="text-center">
                  <div className="text-2xl mb-1">📤</div>
                  <div className="font-semibold text-sm">Списание</div>
                  <div className="text-xs text-gray-500 mt-1">Корректировка расхода</div>
                </div>
              </label>
            </div>
          </div>

          {/* Payment Type - Only for Expense */}
          {formData.adjustment_type === 'expense' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Тип платежа *
              </label>
              <select
                value={formData.payment_type}
                onChange={(e) =>
                  setFormData({ ...formData, payment_type: e.target.value })
                }
                className="w-full py-2 px-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="Погашение долга">Погашение долга</option>
                <option value="Уплата процентов">Уплата процентов</option>
              </select>
            </div>
          )}

          {/* Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Сумма *</label>
            <input
              type="number"
              step="0.01"
              value={formData.amount}
              onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              placeholder="Положительная увеличивает, отрицательная уменьшает"
              className="w-full py-2 px-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              💡 Для сторнирования введите отрицательную сумму (например: -50000)
            </p>
          </div>

          {/* Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Дата *</label>
            <input
              type="date"
              value={formData.adjustment_date}
              onChange={(e) => setFormData({ ...formData, adjustment_date: e.target.value })}
              className="w-full py-2 px-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          {/* Contract Number */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Номер договора
            </label>
            <SearchableSelect
              options={
                contractsQuery.data?.items?.map((contract) => ({
                  value: contract.contract_number,
                  label: contract.contract_number,
                })) ?? []
              }
              value={formData.contract_number}
              onChange={(val) => setFormData({ ...formData, contract_number: val })}
              placeholder="Выберите договор"
              isLoading={contractsQuery.isLoading}
            />
          </div>

          {/* Counterparty */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Контрагент</label>
            <SearchableSelect
              options={
                payersQuery.data?.items?.map((payer) => ({
                  value: payer,
                  label: payer,
                })) ?? []
              }
              value={formData.counterparty}
              onChange={(val) => setFormData({ ...formData, counterparty: val })}
              placeholder="Выберите контрагента"
              isLoading={payersQuery.isLoading}
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full py-2 px-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
              placeholder="Причина корректировки..."
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 py-2.5 px-4 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="flex-1 py-2.5 px-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
            >
              {createMutation.isPending ? 'Сохранение...' : 'Создать'}
            </button>
          </div>

          {/* Error message */}
          {createMutation.isError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              Ошибка при создании корректировки. Попробуйте еще раз.
            </div>
          )}
        </form>
      </motion.div>
    </div>
  );
}
