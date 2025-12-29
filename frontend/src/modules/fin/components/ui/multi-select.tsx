import { useState, useRef, useEffect } from 'react';
import { Check, ChevronDown, Search } from 'lucide-react';

export interface MultiSelectOption {
  value: string;
  label: string;
}

export interface MultiSelectProps {
  options: MultiSelectOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
  label?: string;
  hint?: string;
  isLoading?: boolean;
  className?: string;
  searchPlaceholder?: string;
}

export function MultiSelect({
  options,
  selected,
  onChange,
  placeholder = 'Выберите',
  label,
  hint,
  isLoading = false,
  className = '',
  searchPlaceholder = 'Поиск...',
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredOptions = search.trim()
    ? options.filter((opt) => opt.label.toLowerCase().includes(search.toLowerCase()))
    : options;

  const toggleOption = (value: string) => {
    const newSelected = selected.includes(value)
      ? selected.filter((v) => v !== value)
      : [...selected, value];
    onChange(newSelected);
  };

  const selectAll = () => {
    onChange(options.map((opt) => opt.value));
  };

  const clearAll = () => {
    onChange([]);
  };

  const displayText = () => {
    if (selected.length === 0) {
      return placeholder;
    }
    if (selected.length === options.length) {
      return 'Все';
    }
    if (selected.length === 1) {
      const option = options.find((opt) => opt.value === selected[0]);
      return option?.label || selected[0];
    }
    return `Выбрано: ${selected.length}`;
  };

  return (
    <div className={`relative flex flex-col gap-1.5 ${className}`} ref={dropdownRef}>
      {label && <label className="text-xs font-medium text-gray-600">{label}</label>}

      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center justify-between w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <span className="truncate text-left">{displayText()}</span>
        <ChevronDown size={16} className="text-gray-500 flex-shrink-0 ml-2" />
      </button>

      {hint && <span className="text-[10px] text-gray-400 leading-tight">{hint}</span>}

      {isOpen && (
        <div className="absolute z-50 top-full left-0 mt-2 w-full min-w-[280px] rounded-xl border border-gray-200 bg-white shadow-2xl p-3">
          <div className="relative mb-2">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          </div>

          <div className="flex justify-between items-center mb-2 text-xs text-gray-500">
            <div className="flex gap-2">
              <button
                type="button"
                className="text-blue-600 hover:underline"
                onClick={selectAll}
              >
                Выбрать все
              </button>
              <button
                type="button"
                className="text-blue-600 hover:underline disabled:text-gray-400"
                onClick={clearAll}
                disabled={selected.length === 0}
              >
                Снять все
              </button>
            </div>
            <span>
              {isLoading ? 'Загружаем...' : `${filteredOptions.length} элементов`}
            </span>
          </div>

          <div className="max-h-64 overflow-y-auto pr-1">
            {isLoading && (
              <div className="text-sm text-gray-500 py-4 text-center">Загружаем...</div>
            )}
            {!isLoading && filteredOptions.length === 0 && (
              <div className="text-sm text-gray-500 py-4 text-center">Ничего не найдено</div>
            )}
            {!isLoading &&
              filteredOptions.map((option) => (
                <label
                  key={option.value}
                  className="flex items-center gap-2 text-sm py-1.5 px-2 rounded-lg hover:bg-gray-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    className="accent-blue-500"
                    checked={selected.includes(option.value)}
                    onChange={() => toggleOption(option.value)}
                  />
                  <span className="truncate flex-1">{option.label}</span>
                  {selected.includes(option.value) && (
                    <Check size={14} className="text-blue-500 flex-shrink-0" />
                  )}
                </label>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
