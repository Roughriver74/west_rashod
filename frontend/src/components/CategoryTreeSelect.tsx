import { useMemo, useState, useCallback } from 'react'
import { Select, Tree } from 'antd'
import type { TreeProps } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { FolderOutlined, FileOutlined } from '@ant-design/icons'
import { getCategoryTree, CategoryTreeNode, Category } from '../api/categories'

interface CategoryTreeSelectProps {
  value?: number
  onChange?: (value: number | undefined) => void
  placeholder?: string
  style?: React.CSSProperties
  allowClear?: boolean
  disabled?: boolean
  categoryType?: 'OPEX' | 'CAPEX'
}

// Собираем плоский список всех категорий из дерева (с дедупликацией)
const flattenTree = (nodes: CategoryTreeNode[], parentPath: string = '', seenIds: Set<number> = new Set()): Array<Category & { path: string }> => {
  const result: Array<Category & { path: string }> = []

  for (const node of nodes) {
    // Пропускаем дубликаты
    if (seenIds.has(node.id)) {
      continue
    }
    seenIds.add(node.id)

    const currentPath = parentPath ? `${parentPath} → ${node.name}` : node.name
    result.push({ ...node, path: currentPath })

    if (node.children?.length > 0) {
      result.push(...flattenTree(node.children, currentPath, seenIds))
    }
  }

  return result
}

// Конвертируем для Tree компонента (с уникальными ключами)
const convertToTreeData = (nodes: CategoryTreeNode[], seenKeys: Set<number> = new Set()): TreeProps['treeData'] => {
  return nodes
    .filter(node => {
      if (seenKeys.has(node.id)) return false
      seenKeys.add(node.id)
      return true
    })
    .map(node => ({
      key: node.id,
      title: (
        <span>
          {node.is_folder ? (
            <FolderOutlined style={{ color: '#faad14', marginRight: 4 }} />
          ) : (
            <FileOutlined style={{ color: '#1890ff', marginRight: 4 }} />
          )}
          {node.name}
          {node.code_1c && (
            <span style={{ color: '#999', fontSize: 11, marginLeft: 4 }}>
              [{node.code_1c}]
            </span>
          )}
        </span>
      ),
      children: node.children?.length > 0 ? convertToTreeData(node.children, seenKeys) : undefined,
    }))
}

export default function CategoryTreeSelect({
  value,
  onChange,
  placeholder = 'Выберите категорию',
  style,
  allowClear = true,
  disabled = false,
  categoryType: _categoryType,
}: CategoryTreeSelectProps) {
  const [searchValue, setSearchValue] = useState('')
  const [isOpen, setIsOpen] = useState(false)

  // Загружаем дерево категорий
  const { data: categoryTree = [], isLoading } = useQuery({
    queryKey: ['categoryTree'],
    queryFn: () => getCategoryTree({}),
    staleTime: 5 * 60 * 1000,
  })

  // Плоский список для поиска и отображения выбранного значения
  const flatCategories = useMemo(() => {
    return flattenTree(categoryTree)
  }, [categoryTree])

  // Данные для Tree компонента
  const treeData = useMemo(() => {
    return convertToTreeData(categoryTree)
  }, [categoryTree])

  // Режим поиска
  const isSearchMode = searchValue.length >= 2

  // Фильтрованные категории для поиска
  const filteredCategories = useMemo(() => {
    if (!isSearchMode) return []

    const search = searchValue.toLowerCase()
    return flatCategories
      .filter(cat => {
        const nameMatch = cat.name.toLowerCase().includes(search)
        const codeMatch = cat.code_1c?.toLowerCase().includes(search)
        return nameMatch || codeMatch
      })
      .slice(0, 50)
  }, [flatCategories, searchValue, isSearchMode])

  // Опции для Select (используются для отображения выбранного значения)
  const selectOptions = useMemo(() => {
    return flatCategories.map(cat => ({
      value: cat.id,
      label: cat.name,
    }))
  }, [flatCategories])

  const handleSelect = useCallback((categoryId: number) => {
    onChange?.(categoryId)
    setSearchValue('')
    setIsOpen(false)
  }, [onChange])

  const handleClear = useCallback(() => {
    onChange?.(undefined)
    setSearchValue('')
  }, [onChange])

  // Кастомный popup с деревом или списком поиска
  const popupRender = () => {
    if (isSearchMode) {
      // Режим поиска - плоский список
      return (
        <div key={`search-${searchValue}`} style={{ padding: 8, maxHeight: 400, overflow: 'auto' }}>
          {filteredCategories.length === 0 ? (
            <div style={{ color: '#999', textAlign: 'center', padding: 16 }}>
              Категории не найдены
            </div>
          ) : (
            filteredCategories.map(cat => (
              <div
                key={cat.id}
                onClick={() => handleSelect(cat.id)}
                style={{
                  padding: '8px 12px',
                  cursor: 'pointer',
                  borderRadius: 4,
                  marginBottom: 2,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#f5f5f5'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent'
                }}
              >
                <div style={{ fontWeight: 500 }}>
                  {cat.is_folder ? (
                    <FolderOutlined style={{ color: '#faad14', marginRight: 4 }} />
                  ) : (
                    <FileOutlined style={{ color: '#1890ff', marginRight: 4 }} />
                  )}
                  {cat.name}
                  {cat.code_1c && (
                    <span style={{ color: '#999', fontSize: 11, marginLeft: 4 }}>
                      [{cat.code_1c}]
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 11, color: '#999', marginLeft: 20 }}>
                  {cat.path}
                </div>
              </div>
            ))
          )}
        </div>
      )
    }

    // Режим дерева
    return (
      <div key="tree" style={{ padding: 8, maxHeight: 400, overflow: 'auto' }}>
        <Tree
          treeData={treeData}
          defaultExpandAll
          selectedKeys={value ? [value] : []}
          onSelect={(keys) => {
            if (keys.length > 0) {
              handleSelect(keys[0] as number)
            }
          }}
          style={{ background: 'transparent' }}
        />
      </div>
    )
  }

  return (
    <Select
      showSearch
      value={value}
      placeholder={placeholder}
      style={style}
      allowClear={allowClear}
      disabled={disabled}
      loading={isLoading}
      options={selectOptions}
      open={isOpen}
      onOpenChange={setIsOpen}
      searchValue={searchValue}
      onSearch={setSearchValue}
      onClear={handleClear}
      onChange={(val) => {
        if (val !== undefined) {
          handleSelect(val)
        }
      }}
      filterOption={false}
      popupRender={popupRender}
      styles={{ popup: { root: { minWidth: 300 } } }}
      notFoundContent={null}
    />
  )
}
