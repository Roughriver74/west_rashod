import { useState, useMemo } from 'react'
import {
  Card,
  Table,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Typography,
  Alert,
  Tabs,
  Button,
  Space,
  Modal,
  Form,
  Select,
  Input,
  InputNumber,
  Switch,
  Popconfirm,
  message,
} from 'antd'
import {
  RobotOutlined,
  CheckCircleOutlined,
  QuestionCircleOutlined,
  EditOutlined,
  PlusOutlined,
  DeleteOutlined,
  SettingOutlined,
  StopOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnsType } from 'antd/es/table'
import {
  getCounterpartyPatterns,
  getBusinessOperationPatterns,
  getCategorizationStats,
  type CounterpartyPattern,
  type BusinessOperationPattern,
} from '../api/categorizationPatterns'
import {
  getCategorizationRules,
  createCategorizationRule,
  updateCategorizationRule,
  deleteCategorizationRule,
  bulkActivateRules,
  bulkDeactivateRules,
  type CategorizationRule,
  type CategorizationRuleCreate,
  type RuleType,
} from '../api/categorizationRules'
import { getCategories, type Category } from '../api/categories'

const { Title, Paragraph } = Typography

const RULE_TYPE_LABELS: Record<RuleType, string> = {
  COUNTERPARTY_INN: 'По ИНН контрагента',
  COUNTERPARTY_NAME: 'По названию контрагента',
  BUSINESS_OPERATION: 'По хоз. операции',
  KEYWORD: 'По ключевому слову',
}

const DELETED_PATTERN_MARKER = '🗑️ Удалённый паттерн'

export default function CategorizationRulesPage() {
  const queryClient = useQueryClient()
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<CategorizationRule | null>(null)
  const [form] = Form.useForm()

  // Fetch stats
  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['categorization-stats'],
    queryFn: () => getCategorizationStats(),
  })

  // Fetch counterparty patterns
  const { data: counterpartyPatterns = [], isLoading: loadingCounterparty } = useQuery({
    queryKey: ['categorization-patterns-counterparties'],
    queryFn: () => getCounterpartyPatterns({ limit: 100, min_transactions: 2 }),
  })

  // Fetch business operation patterns
  const { data: operationPatterns = [], isLoading: loadingOperation } = useQuery({
    queryKey: ['categorization-patterns-operations'],
    queryFn: () => getBusinessOperationPatterns({ limit: 50, min_transactions: 3 }),
  })

  // Fetch manual rules
  const { data: manualRules = [], isLoading: loadingRules } = useQuery({
    queryKey: ['categorization-rules'],
    queryFn: () => getCategorizationRules({ limit: 200 }),
  })

  // Fetch categories for dropdown
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => getCategories({ is_active: true }),
  })

  // Filter out deleted patterns (patterns that have a matching deletion rule)
  const deletedPatternKeys = useMemo(() => {
    const keys = new Set<string>()
    manualRules.forEach((rule) => {
      if (rule.notes?.includes(DELETED_PATTERN_MARKER)) {
        if (rule.counterparty_inn) {
          keys.add(`inn:${rule.counterparty_inn}:${rule.category_id}`)
        }
        if (rule.counterparty_name) {
          keys.add(`name:${rule.counterparty_name}:${rule.category_id}`)
        }
        if (rule.business_operation) {
          keys.add(`operation:${rule.business_operation}:${rule.category_id}`)
        }
      }
    })
    return keys
  }, [manualRules])

  // Filtered patterns (excluding deleted ones)
  const filteredCounterpartyPatterns = useMemo(() => {
    return counterpartyPatterns.filter((pattern) => {
      if (pattern.counterparty_inn) {
        return !deletedPatternKeys.has(`inn:${pattern.counterparty_inn}:${pattern.category_id}`)
      }
      if (pattern.counterparty_name) {
        return !deletedPatternKeys.has(`name:${pattern.counterparty_name}:${pattern.category_id}`)
      }
      return true
    })
  }, [counterpartyPatterns, deletedPatternKeys])

  const filteredOperationPatterns = useMemo(() => {
    return operationPatterns.filter((pattern) => {
      return !deletedPatternKeys.has(`operation:${pattern.business_operation}:${pattern.category_id}`)
    })
  }, [operationPatterns, deletedPatternKeys])

  // Create mutation
  const createMutation = useMutation({
    mutationFn: createCategorizationRule,
    onSuccess: () => {
      message.success('Правило создано')
      queryClient.invalidateQueries({ queryKey: ['categorization-rules'] })
      setIsModalOpen(false)
      form.resetFields()
    },
    onError: () => {
      message.error('Ошибка создания правила')
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updateCategorizationRule(id, data),
    onSuccess: () => {
      message.success('Правило обновлено')
      queryClient.invalidateQueries({ queryKey: ['categorization-rules'] })
      setIsModalOpen(false)
      setEditingRule(null)
      form.resetFields()
    },
    onError: () => {
      message.error('Ошибка обновления правила')
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteCategorizationRule,
    onSuccess: () => {
      message.success('Правило удалено')
      queryClient.invalidateQueries({ queryKey: ['categorization-rules'] })
    },
    onError: () => {
      message.error('Ошибка удаления правила')
    },
  })

  // Bulk activate
  const bulkActivateMutation = useMutation({
    mutationFn: bulkActivateRules,
    onSuccess: () => {
      message.success('Правила активированы')
      queryClient.invalidateQueries({ queryKey: ['categorization-rules'] })
      setSelectedRowKeys([])
    },
  })

  // Bulk deactivate
  const bulkDeactivateMutation = useMutation({
    mutationFn: bulkDeactivateRules,
    onSuccess: () => {
      message.success('Правила деактивированы')
      queryClient.invalidateQueries({ queryKey: ['categorization-rules'] })
      setSelectedRowKeys([])
    },
  })

  const handleSubmit = (values: any) => {
    const data: CategorizationRuleCreate = {
      rule_type: values.rule_type,
      category_id: values.category_id,
      priority: values.priority ?? 100,
      confidence: values.confidence ?? 1.0,
      is_active: values.is_active ?? true,
      notes: values.notes,
      counterparty_inn: values.rule_type === 'COUNTERPARTY_INN' ? values.match_value : null,
      counterparty_name: values.rule_type === 'COUNTERPARTY_NAME' ? values.match_value : null,
      business_operation: values.rule_type === 'BUSINESS_OPERATION' ? values.match_value : null,
      keyword: values.rule_type === 'KEYWORD' ? values.match_value : null,
    }

    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleEdit = (record: CategorizationRule) => {
    setEditingRule(record)
    const matchValue =
      record.counterparty_inn ||
      record.counterparty_name ||
      record.business_operation ||
      record.keyword ||
      ''
    form.setFieldsValue({
      rule_type: record.rule_type,
      match_value: matchValue,
      category_id: record.category_id,
      priority: record.priority,
      confidence: record.confidence,
      is_active: record.is_active,
      notes: record.notes,
    })
    setIsModalOpen(true)
  }

  const handleAdd = () => {
    setEditingRule(null)
    form.resetFields()
    form.setFieldsValue({
      rule_type: 'COUNTERPARTY_INN',
      priority: 100,
      confidence: 1.0,
      is_active: true,
    })
    setIsModalOpen(true)
  }

  const handleCreateRuleFromPattern = (
    pattern: CounterpartyPattern | BusinessOperationPattern,
    type: 'counterparty' | 'operation'
  ) => {
    setEditingRule(null)
    form.resetFields()

    if (type === 'counterparty') {
      const cpPattern = pattern as CounterpartyPattern
      const ruleType = cpPattern.counterparty_inn ? 'COUNTERPARTY_INN' : 'COUNTERPARTY_NAME'
      const matchValue = cpPattern.counterparty_inn || cpPattern.counterparty_name || ''

      form.setFieldsValue({
        rule_type: ruleType,
        match_value: matchValue,
        category_id: cpPattern.category_id,
        priority: 100,
        confidence: 1.0,
        is_active: true,
        notes: `Создано из паттерна: ${cpPattern.transaction_count} транзакций`,
      })
    } else {
      const opPattern = pattern as BusinessOperationPattern
      form.setFieldsValue({
        rule_type: 'BUSINESS_OPERATION',
        match_value: opPattern.business_operation,
        category_id: opPattern.category_id,
        priority: 100,
        confidence: 1.0,
        is_active: true,
        notes: `Создано из паттерна: ${opPattern.transaction_count} транзакций`,
      })
    }

    setIsModalOpen(true)
  }

  const handleDisablePattern = (
    pattern: CounterpartyPattern | BusinessOperationPattern,
    type: 'counterparty' | 'operation'
  ) => {
    let ruleData: CategorizationRuleCreate

    if (type === 'counterparty') {
      const cpPattern = pattern as CounterpartyPattern
      const ruleType = cpPattern.counterparty_inn ? 'COUNTERPARTY_INN' : 'COUNTERPARTY_NAME'
      const matchValue = cpPattern.counterparty_inn || cpPattern.counterparty_name || ''

      ruleData = {
        rule_type: ruleType,
        category_id: cpPattern.category_id,
        priority: 200, // Высокий приоритет, чтобы блокировать автоматику
        confidence: 0.0,
        is_active: false, // Неактивно - блокирует паттерн
        notes: `🚫 Блокировка автоматического паттерна (${cpPattern.transaction_count} транзакций)`,
        counterparty_inn: ruleType === 'COUNTERPARTY_INN' ? matchValue : null,
        counterparty_name: ruleType === 'COUNTERPARTY_NAME' ? matchValue : null,
        business_operation: null,
        keyword: null,
      }
    } else {
      const opPattern = pattern as BusinessOperationPattern

      ruleData = {
        rule_type: 'BUSINESS_OPERATION',
        category_id: opPattern.category_id,
        priority: 200,
        confidence: 0.0,
        is_active: false,
        notes: `🚫 Блокировка автоматического паттерна (${opPattern.transaction_count} транзакций)`,
        counterparty_inn: null,
        counterparty_name: null,
        business_operation: opPattern.business_operation,
        keyword: null,
      }
    }

    createMutation.mutate(ruleData)
  }

  const handleDeletePattern = (
    pattern: CounterpartyPattern | BusinessOperationPattern,
    type: 'counterparty' | 'operation'
  ) => {
    let ruleData: CategorizationRuleCreate

    if (type === 'counterparty') {
      const cpPattern = pattern as CounterpartyPattern
      const ruleType = cpPattern.counterparty_inn ? 'COUNTERPARTY_INN' : 'COUNTERPARTY_NAME'
      const matchValue = cpPattern.counterparty_inn || cpPattern.counterparty_name || ''

      ruleData = {
        rule_type: ruleType,
        category_id: cpPattern.category_id,
        priority: 200, // Высокий приоритет
        confidence: 0.0,
        is_active: false, // Неактивно - блокирует паттерн
        notes: `${DELETED_PATTERN_MARKER} (${cpPattern.transaction_count} транзакций)`,
        counterparty_inn: ruleType === 'COUNTERPARTY_INN' ? matchValue : null,
        counterparty_name: ruleType === 'COUNTERPARTY_NAME' ? matchValue : null,
        business_operation: null,
        keyword: null,
      }
    } else {
      const opPattern = pattern as BusinessOperationPattern

      ruleData = {
        rule_type: 'BUSINESS_OPERATION',
        category_id: opPattern.category_id,
        priority: 200,
        confidence: 0.0,
        is_active: false,
        notes: `${DELETED_PATTERN_MARKER} (${opPattern.transaction_count} транзакций)`,
        counterparty_inn: null,
        counterparty_name: null,
        business_operation: opPattern.business_operation,
        keyword: null,
      }
    }

    createMutation.mutate(ruleData)
  }

  const counterpartyColumns: ColumnsType<CounterpartyPattern> = [
    {
      title: 'Контрагент',
      key: 'counterparty',
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.counterparty_name || '-'}</div>
          {record.counterparty_inn && (
            <div style={{ fontSize: '12px', color: '#8c8c8c' }}>ИНН: {record.counterparty_inn}</div>
          )}
        </div>
      ),
    },
    {
      title: 'Категория',
      dataIndex: 'category_name',
      key: 'category_name',
      render: (name) => <Tag color="blue">{name}</Tag>,
    },
    {
      title: 'Транзакций',
      dataIndex: 'transaction_count',
      key: 'transaction_count',
      width: 120,
      sorter: (a, b) => a.transaction_count - b.transaction_count,
    },
    {
      title: 'Средняя сумма',
      dataIndex: 'avg_amount',
      key: 'avg_amount',
      width: 150,
      render: (amount) => `${amount.toLocaleString('ru-RU')} ₽`,
    },
    {
      title: 'Уверенность',
      dataIndex: 'confidence_estimate',
      key: 'confidence_estimate',
      width: 150,
      render: (confidence) => (
        <Progress
          percent={Math.round(confidence * 100)}
          size="small"
          status={confidence >= 0.85 ? 'success' : confidence >= 0.60 ? 'normal' : 'exception'}
        />
      ),
      sorter: (a, b) => a.confidence_estimate - b.confidence_estimate,
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 250,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<PlusOutlined />}
            onClick={() => handleCreateRuleFromPattern(record, 'counterparty')}
            title="Создать правило"
          >
            Правило
          </Button>
          <Popconfirm
            title="Отключить паттерн?"
            description="Будет создано правило-блокировщик. Паттерн перестанет применяться автоматически."
            onConfirm={() => handleDisablePattern(record, 'counterparty')}
            okText="Отключить"
            cancelText="Отмена"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
              title="Отключить паттерн"
            >
              Отключить
            </Button>
          </Popconfirm>
          <Popconfirm
            title="Удалить паттерн?"
            description="Паттерн будет скрыт из списка. Для восстановления удалите соответствующее правило."
            onConfirm={() => handleDeletePattern(record, 'counterparty')}
            okText="Удалить"
            cancelText="Отмена"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              title="Удалить паттерн"
            >
              Удалить
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const operationColumns: ColumnsType<BusinessOperationPattern> = [
    {
      title: 'Хозяйственная операция',
      dataIndex: 'business_operation',
      key: 'business_operation',
    },
    {
      title: 'Категория',
      dataIndex: 'category_name',
      key: 'category_name',
      render: (name) => <Tag color="blue">{name}</Tag>,
    },
    {
      title: 'Транзакций',
      dataIndex: 'transaction_count',
      key: 'transaction_count',
      width: 120,
      sorter: (a, b) => a.transaction_count - b.transaction_count,
    },
    {
      title: 'Уверенность',
      dataIndex: 'confidence_estimate',
      key: 'confidence_estimate',
      width: 150,
      render: (confidence) => (
        <Progress
          percent={Math.round(confidence * 100)}
          size="small"
          status={confidence >= 0.85 ? 'success' : confidence >= 0.60 ? 'normal' : 'exception'}
        />
      ),
      sorter: (a, b) => a.confidence_estimate - b.confidence_estimate,
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 250,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<PlusOutlined />}
            onClick={() => handleCreateRuleFromPattern(record, 'operation')}
            title="Создать правило"
          >
            Правило
          </Button>
          <Popconfirm
            title="Отключить паттерн?"
            description="Будет создано правило-блокировщик. Паттерн перестанет применяться автоматически."
            onConfirm={() => handleDisablePattern(record, 'operation')}
            okText="Отключить"
            cancelText="Отмена"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
              title="Отключить паттерн"
            >
              Отключить
            </Button>
          </Popconfirm>
          <Popconfirm
            title="Удалить паттерн?"
            description="Паттерн будет скрыт из списка. Для восстановления удалите соответствующее правило."
            onConfirm={() => handleDeletePattern(record, 'operation')}
            okText="Удалить"
            cancelText="Отмена"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              title="Удалить паттерн"
            >
              Удалить
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const rulesColumns: ColumnsType<CategorizationRule> = [
    {
      title: 'Тип правила',
      dataIndex: 'rule_type',
      key: 'rule_type',
      width: 200,
      render: (type: RuleType) => <Tag>{RULE_TYPE_LABELS[type]}</Tag>,
    },
    {
      title: 'Значение',
      key: 'value',
      render: (_, record) => {
        const value =
          record.counterparty_inn ||
          record.counterparty_name ||
          record.business_operation ||
          record.keyword ||
          '-'
        return <span style={{ fontFamily: 'monospace' }}>{value}</span>
      },
    },
    {
      title: 'Категория',
      dataIndex: 'category_name',
      key: 'category_name',
      render: (name) => <Tag color="green">{name}</Tag>,
    },
    {
      title: 'Приоритет',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      sorter: (a, b) => a.priority - b.priority,
    },
    {
      title: 'Уверенность',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 150,
      render: (confidence) => (
        <Progress
          percent={Math.round(confidence * 100)}
          size="small"
          status="success"
          strokeColor="#52c41a"
        />
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive) => (
        <Tag color={isActive ? 'success' : 'default'}>{isActive ? 'Активно' : 'Неактивно'}</Tag>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm
            title="Удалить правило?"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="Да"
            cancelText="Нет"
          >
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys as number[]),
  }

  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        Правила автоматической категоризации
      </Title>

      <Alert
        message="Как работает автоматическая категоризация"
        description={
          <div>
            <Paragraph>
              Система <strong>учится на ваших действиях</strong> - каждый раз когда вы категоризируете
              транзакцию, она запоминает ваш выбор и использует его для похожих транзакций в будущем.
            </Paragraph>
            <Paragraph style={{ marginBottom: 8 }}>
              <strong>Приоритет категоризации:</strong>
            </Paragraph>
            <ul style={{ marginBottom: 8 }}>
              <li>
                <strong>0. Ручные правила</strong> (приоритет 100+) - правила, которые вы создаете руками,
                применяются ПЕРВЫМИ
              </li>
              <li>
                <strong>1. Точное совпадение по ИНН контрагента</strong> - базовая уверенность 70% + 5% за
                каждую прошлую транзакцию (макс 95%)
              </li>
              <li>
                <strong>2. Точное совпадение по названию контрагента</strong> - базовая уверенность 65% + 5%
                за каждую прошлую транзакцию (макс 90%)
              </li>
              <li>
                <strong>3. Совпадение хозяйственной операции</strong> - базовая уверенность 55% + 5% за
                каждую прошлую транзакцию (макс 80%)
              </li>
              <li>
                <strong>4. Совпадение ключевых слов в назначении</strong> - базовая уверенность 45% + 8% за
                каждое совпадение слова (макс 75%)
              </li>
            </ul>
            <Paragraph style={{ marginBottom: 0 }}>
              <strong>Пороги уверенности:</strong> ≥85% - категория применяется автоматически, 60-84% -
              предлагается для проверки, &lt;60% - не предлагается
            </Paragraph>
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={loadingStats}>
            <Statistic
              title="Всего транзакций"
              value={stats?.total_transactions || 0}
              prefix={<RobotOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loadingStats}>
            <Statistic
              title="Автоматически категоризировано"
              value={stats?.auto_categorized || 0}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
              suffix={
                stats?.total_transactions
                  ? `(${Math.round((stats.auto_categorized / stats.total_transactions) * 100)}%)`
                  : ''
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loadingStats}>
            <Statistic
              title="Требует проверки"
              value={stats?.needs_review || 0}
              valueStyle={{ color: '#faad14' }}
              prefix={<QuestionCircleOutlined />}
              suffix={
                stats?.total_transactions
                  ? `(${Math.round((stats.needs_review / stats.total_transactions) * 100)}%)`
                  : ''
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loadingStats}>
            <Statistic
              title="Вручную категоризировано"
              value={stats?.manual_categorized || 0}
              valueStyle={{ color: '#1890ff' }}
              prefix={<EditOutlined />}
              suffix={
                stats?.total_transactions
                  ? `(${Math.round((stats.manual_categorized / stats.total_transactions) * 100)}%)`
                  : ''
              }
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card loading={loadingStats}>
            <Statistic
              title="Высокая уверенность (≥85%)"
              value={stats?.high_confidence_count || 0}
              valueStyle={{ color: '#52c41a' }}
            />
            <Progress
              percent={
                stats?.total_transactions
                  ? Math.round((stats.high_confidence_count / stats.total_transactions) * 100)
                  : 0
              }
              strokeColor="#52c41a"
              showInfo={false}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card loading={loadingStats}>
            <Statistic
              title="Средняя уверенность (60-84%)"
              value={stats?.medium_confidence_count || 0}
              valueStyle={{ color: '#faad14' }}
            />
            <Progress
              percent={
                stats?.total_transactions
                  ? Math.round((stats.medium_confidence_count / stats.total_transactions) * 100)
                  : 0
              }
              strokeColor="#faad14"
              showInfo={false}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card loading={loadingStats}>
            <Statistic
              title="Средняя уверенность"
              value={stats?.avg_confidence ? `${Math.round(stats.avg_confidence * 100)}%` : '-'}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs with patterns and manual rules */}
      <Card>
        <Tabs
          items={[
            {
              key: 'manual-rules',
              label: (
                <span>
                  <SettingOutlined /> Ручные правила ({manualRules.length})
                </span>
              ),
              children: (
                <div>
                  <Paragraph type="secondary" style={{ marginBottom: 16 }}>
                    Ручные правила имеют наивысший приоритет и применяются ПЕРВЫМИ, переопределяя
                    автоматически выученные паттерны. Используйте их для точной настройки категоризации.
                  </Paragraph>

                  <Space wrap style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                      Добавить правило
                    </Button>
                    {selectedRowKeys.length > 0 && (
                      <>
                        <Button
                          onClick={() => bulkActivateMutation.mutate(selectedRowKeys)}
                          loading={bulkActivateMutation.isPending}
                        >
                          Активировать ({selectedRowKeys.length})
                        </Button>
                        <Button
                          onClick={() => bulkDeactivateMutation.mutate(selectedRowKeys)}
                          loading={bulkDeactivateMutation.isPending}
                        >
                          Деактивировать ({selectedRowKeys.length})
                        </Button>
                      </>
                    )}
                  </Space>

                  <Table
                    rowKey="id"
                    columns={rulesColumns}
                    dataSource={manualRules}
                    loading={loadingRules}
                    rowSelection={rowSelection}
                    pagination={{
                      pageSize: 20,
                      showSizeChanger: true,
                      showTotal: (total) => `Всего: ${total}`,
                    }}
                  />
                </div>
              ),
            },
            {
              key: 'counterparty',
              label: (
                <span>
                  <RobotOutlined /> Паттерны по контрагентам ({filteredCounterpartyPatterns.length})
                </span>
              ),
              children: (
                <div>
                  <Paragraph type="secondary" style={{ marginBottom: 16 }}>
                    Эти паттерны показывают, как система научилась категоризировать транзакции на основе
                    ваших прошлых действий. Чем больше транзакций от контрагента вы категоризировали, тем
                    выше уверенность системы. Вы можете создать <strong>ручное правило</strong> на основе
                    паттерна, чтобы зафиксировать или изменить его.
                  </Paragraph>
                  <Table
                    rowKey={(record) =>
                      `${record.counterparty_inn}-${record.counterparty_name}-${record.category_id}`
                    }
                    columns={counterpartyColumns}
                    dataSource={filteredCounterpartyPatterns}
                    loading={loadingCounterparty}
                    pagination={{
                      pageSize: 20,
                      showSizeChanger: true,
                      showTotal: (total) => `Всего: ${total}`,
                    }}
                  />
                </div>
              ),
            },
            {
              key: 'operation',
              label: (
                <span>
                  <CheckCircleOutlined /> Паттерны по хоз. операциям ({filteredOperationPatterns.length})
                </span>
              ),
              children: (
                <div>
                  <Paragraph type="secondary" style={{ marginBottom: 16 }}>
                    Эти паттерны показывают связь между хозяйственными операциями из 1С и категориями
                    бюджета. Система использует их когда не может найти совпадение по контрагенту. Вы можете
                    создать <strong>ручное правило</strong> на основе паттерна, чтобы зафиксировать или
                    изменить его.
                  </Paragraph>
                  <Table
                    rowKey={(record) => `${record.business_operation}-${record.category_id}`}
                    columns={operationColumns}
                    dataSource={filteredOperationPatterns}
                    loading={loadingOperation}
                    pagination={{
                      pageSize: 20,
                      showSizeChanger: true,
                      showTotal: (total) => `Всего: ${total}`,
                    }}
                  />
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingRule ? 'Редактировать правило' : 'Новое правило'}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false)
          setEditingRule(null)
          form.resetFields()
        }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="rule_type"
            label="Тип правила"
            rules={[{ required: true, message: 'Выберите тип правила' }]}
          >
            <Select
              placeholder="Выберите тип"
              options={Object.entries(RULE_TYPE_LABELS).map(([value, label]) => ({
                value,
                label,
              }))}
            />
          </Form.Item>

          <Form.Item
            name="match_value"
            label="Значение для поиска"
            rules={[{ required: true, message: 'Введите значение' }]}
            tooltip="ИНН, название контрагента, хоз.операция или ключевое слово - в зависимости от выбранного типа"
          >
            <Input placeholder="Например: 7701234567 или ОплатаПоставщику" />
          </Form.Item>

          <Form.Item
            name="category_id"
            label="Категория"
            rules={[{ required: true, message: 'Выберите категорию' }]}
          >
            <Select
              showSearch
              placeholder="Выберите категорию"
              optionFilterProp="children"
              options={categories.map((cat: Category) => ({
                value: cat.id,
                label: `${cat.name} (${cat.type})`,
              }))}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="priority"
                label="Приоритет"
                rules={[{ required: true, message: 'Введите приоритет' }]}
                tooltip="Чем выше число, тем раньше применится правило. По умолчанию 100."
              >
                <InputNumber min={0} max={1000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="confidence"
                label="Уверенность"
                rules={[{ required: true, message: 'Введите уверенность' }]}
                tooltip="0.0 - 1.0. Для ручных правил обычно 1.0 (100%)"
              >
                <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="notes" label="Примечание">
            <Input.TextArea rows={2} placeholder="Необязательно" />
          </Form.Item>

          <Form.Item name="is_active" label="Активно" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={createMutation.isPending || updateMutation.isPending}
              >
                {editingRule ? 'Сохранить' : 'Создать'}
              </Button>
              <Button
                onClick={() => {
                  setIsModalOpen(false)
                  setEditingRule(null)
                  form.resetFields()
                }}
              >
                Отмена
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
