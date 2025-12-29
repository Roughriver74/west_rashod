/**
 * Fin Adjustments Page - Manual adjustments
 * Adapted 1-to-1 from west_fin AdjustmentsPage.tsx
 */
import { useState, useMemo, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Pencil,
  Trash2,
  Search,
  ArrowUpCircle,
  ArrowDownCircle,
  FileText,
  Calendar,
  Building,
  X,
  ChevronDown,
  Check,
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import {
  getAdjustments,
  createAdjustment,
  deleteAdjustment,
  getContracts,
  getUniquePayers,
  type ManualAdjustment,
} from '../api/finApi';
import { formatAmount } from '../utils/formatters';
import { useDebounce } from '../hooks/usePerformance';

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

const PAGE_SIZE = 20;

type AdjustmentType = 'principal' | 'interest' | 'other';

interface FormData {
  adjustment_type: AdjustmentType;
  amount: string;
  adjustment_date: string;
  contract_number: string;
  counterparty: string;
  description: string;
}

const initialFormData: FormData = {
  adjustment_type: 'principal',
  amount: '',
  adjustment_date: new Date().toISOString().split('T')[0],
  contract_number: '',
  counterparty: '',
  description: '',
};

export default function FinAdjustmentsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<AdjustmentType | ''>('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<FormData>(initialFormData);

  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  const queryParams = useMemo(() => {
    const params: { skip?: number; limit?: number; adjustment_type?: string } = {
      skip: (page - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
    };
    if (typeFilter) params.adjustment_type = typeFilter;
    return params;
  }, [page, typeFilter]);

  // Queries
  const adjustmentsQuery = useQuery({
    queryKey: ['fin', 'adjustments', queryParams],
    queryFn: () => getAdjustments(queryParams),
    staleTime: 60 * 1000,
  });

  const contractsQuery = useQuery({
    queryKey: ['fin', 'references', 'contracts'],
    queryFn: () => getContracts({ limit: 1000000 }),
    staleTime: 5 * 60 * 1000,
  });

  const payersQuery = useQuery({
    queryKey: ['fin', 'references', 'payers'],
    queryFn: () => getUniquePayers({ limit: 1000000 }),
    staleTime: 5 * 60 * 1000,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: {
      adjustment_date: string;
      counterparty?: string;
      contract_number?: string;
      adjustment_type: AdjustmentType;
      amount: number;
      description?: string;
    }) => createAdjustment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fin', 'adjustments'] });
      closeModal();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteAdjustment(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fin', 'adjustments'] });
    },
  });

  const adjustments = adjustmentsQuery.data?.items ?? [];
  const total = adjustmentsQuery.data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Filter adjustments by search term (client-side)
  const filteredAdjustments = useMemo(() => {
    if (!debouncedSearchTerm) return adjustments;
    const lowerSearch = debouncedSearchTerm.toLowerCase();
    return adjustments.filter(
      (adj) =>
        (adj.counterparty && adj.counterparty.toLowerCase().includes(lowerSearch)) ||
        (adj.contract_number && adj.contract_number.toLowerCase().includes(lowerSearch)) ||
        (adj.description && adj.description.toLowerCase().includes(lowerSearch))
    );
  }, [adjustments, debouncedSearchTerm]);

  const openCreateModal = () => {
    setEditingId(null);
    setFormData(initialFormData);
    setIsModalOpen(true);
  };

  const openEditModal = (adj: ManualAdjustment) => {
    setEditingId(adj.id);
    setFormData({
      adjustment_type: adj.adjustment_type,
      amount: String(adj.amount),
      adjustment_date: adj.adjustment_date,
      contract_number: adj.contract_number || '',
      counterparty: adj.counterparty || '',
      description: adj.description || '',
    });
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingId(null);
    setFormData(initialFormData);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const payload = {
      adjustment_type: formData.adjustment_type,
      amount: parseFloat(formData.amount),
      adjustment_date: formData.adjustment_date,
      contract_number: formData.contract_number || undefined,
      counterparty: formData.counterparty || undefined,
      description: formData.description || undefined,
    };

    // Note: Update functionality would need backend support
    // For now, only create is supported
    createMutation.mutate(payload);
  };

  const handleDelete = (id: number) => {
    if (window.confirm('Удалить эту корректировку?')) {
      deleteMutation.mutate(id);
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'principal': return 'Основной долг';
      case 'interest': return 'Проценты';
      case 'other': return 'Прочее';
      default: return type;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'principal': return 'bg-blue-100 text-blue-700';
      case 'interest': return 'bg-orange-100 text-orange-700';
      case 'other': return 'bg-gray-100 text-gray-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  if (adjustmentsQuery.isLoading && !adjustmentsQuery.data) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 border-4 border-gray-200 border-t-blue-500 rounded-full"
        />
        <p className="mt-4 text-gray-600">Загрузка корректировок...</p>
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
      <div className="mb-6 page-header-mobile flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 m-0">Ручные корректировки</h1>
          <p className="text-base text-gray-500 mt-1">
            Корректировки не удаляются при импорте из FTP
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          <Plus size={20} />
          Добавить
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4 mb-6">
        <motion.div
          whileHover={{ y: -4 }}
          className="p-4 bg-white rounded-xl shadow-sm flex items-center gap-3 border-l-4 border-blue-500"
        >
          <ArrowDownCircle size={24} color="#3B82F6" />
          <div>
            <div className="text-sm text-gray-500">Основной долг</div>
            <div className="text-xl font-bold text-blue-600">
              {filteredAdjustments.filter((a) => a.adjustment_type === 'principal').length}
            </div>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -4 }}
          className="p-4 bg-white rounded-xl shadow-sm flex items-center gap-3 border-l-4 border-orange-500"
        >
          <ArrowUpCircle size={24} color="#F97316" />
          <div>
            <div className="text-sm text-gray-500">Проценты</div>
            <div className="text-xl font-bold text-orange-600">
              {filteredAdjustments.filter((a) => a.adjustment_type === 'interest').length}
            </div>
          </div>
        </motion.div>

        <motion.div
          whileHover={{ y: -4 }}
          className="p-4 bg-white rounded-xl shadow-sm flex items-center gap-3 border-l-4 border-gray-500"
        >
          <FileText size={24} color="#6B7280" />
          <div>
            <div className="text-sm text-gray-500">Всего записей</div>
            <div className="text-xl font-bold text-gray-900">{total}</div>
          </div>
        </motion.div>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={20} color="#6B7280" className="absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Поиск по контрагенту, договору..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full py-3 px-4 pl-12 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as AdjustmentType | '')}
          className="py-3 px-4 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Все типы</option>
          <option value="principal">Основной долг</option>
          <option value="interest">Проценты</option>
          <option value="other">Прочее</option>
        </select>
      </div>

      {/* Adjustments List */}
      <div className="flex flex-col gap-4">
        {filteredAdjustments.map((adj, idx) => (
          <motion.div
            key={adj.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.03 }}
            className="bg-white rounded-xl shadow-sm overflow-hidden"
          >
            <div className="p-5 flex justify-between items-center">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <span className={`px-2 py-1 text-xs font-medium ${getTypeColor(adj.adjustment_type)} rounded`}>
                    {getTypeLabel(adj.adjustment_type)}
                  </span>
                  <span className="text-lg font-bold text-gray-900">
                    {formatAmount(Number(adj.amount))}
                  </span>
                </div>

                <div className="text-sm text-gray-600 flex flex-wrap gap-4">
                  {adj.contract_number && (
                    <span className="flex items-center gap-1">
                      <FileText size={14} /> {adj.contract_number}
                    </span>
                  )}
                  {adj.counterparty && (
                    <span className="flex items-center gap-1">
                      <Building size={14} /> {adj.counterparty}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Calendar size={14} /> {format(parseISO(adj.adjustment_date), 'dd.MM.yyyy')}
                  </span>
                </div>

                {adj.description && (
                  <div className="mt-2 text-sm text-gray-500 italic">{adj.description}</div>
                )}
              </div>

              <div className="flex gap-2 ml-4">
                <button
                  onClick={() => openEditModal(adj)}
                  className="p-2 text-gray-500 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors"
                  title="Редактировать"
                >
                  <Pencil size={18} />
                </button>
                <button
                  onClick={() => handleDelete(adj.id)}
                  className="p-2 text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  title="Удалить"
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          </motion.div>
        ))}

        {filteredAdjustments.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            Корректировки не найдены
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-4 mt-6 p-5">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              page > 1
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Предыдущая
          </button>
          <div className="text-sm text-gray-500 font-medium">
            Страница {page} из {totalPages} ({total} записей)
          </div>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className={`px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              page < totalPages
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Следующая
          </button>
        </div>
      )}

      {/* Modal */}
      <AnimatePresence>
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto"
            >
              <div className="p-6 border-b border-gray-200 flex justify-between items-center">
                <h2 className="text-xl font-bold text-gray-900">
                  {editingId ? 'Редактировать корректировку' : 'Новая корректировка'}
                </h2>
                <button
                  onClick={closeModal}
                  className="p-2 text-gray-500 hover:text-gray-700 rounded-lg"
                >
                  <X size={20} />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                {/* Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Тип корректировки *
                  </label>
                  <select
                    value={formData.adjustment_type}
                    onChange={(e) =>
                      setFormData({ ...formData, adjustment_type: e.target.value as AdjustmentType })
                    }
                    className="w-full py-2 px-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  >
                    <option value="principal">Основной долг</option>
                    <option value="interest">Проценты</option>
                    <option value="other">Прочее</option>
                  </select>
                </div>

                {/* Amount */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Сумма *</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                    className="w-full py-2 px-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
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
                    onClick={closeModal}
                    className="flex-1 py-2.5 px-4 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Отмена
                  </button>
                  <button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="flex-1 py-2.5 px-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
                  >
                    {createMutation.isPending
                      ? 'Сохранение...'
                      : editingId
                        ? 'Сохранить'
                        : 'Создать'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
