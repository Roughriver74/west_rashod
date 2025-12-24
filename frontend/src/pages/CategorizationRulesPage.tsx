import { useState } from 'react'
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
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnsType } from 'antd/es/table'
import {
  getCategorizationStats,
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
import CategoryTreeSelect from '../components/CategoryTreeSelect'

const { Title, Paragraph } = Typography

const RULE_TYPE_LABELS: Record<RuleType, string> = {
  COUNTERPARTY_INN: 'По ИНН контрагента',
  COUNTERPARTY_NAME: 'По названию контрагента',
  BUSINESS_OPERATION: 'По хоз. операции',
  KEYWORD: 'По ключевому слову',
}

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

  // Паттерны больше не используются - система обучается только через ручные правила

  // Fetch all rules
  const { data: allRules = [], isLoading: loadingRules } = useQuery({
    queryKey: ['categorization-rules'],
    queryFn: () => getCategorizationRules({ limit: 500 }),
  })

  // CategoryTreeSelect loads categories internally, no need to fetch here

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

  // Паттерны удалены - система использует только ручные правила

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
        message="🎓 Как работает система обучения"
        description={
          <div>
            <Paragraph style={{ marginBottom: 12 }}>
              Система категоризации использует <strong>только ручные правила</strong>, которые вы создаёте сами.
              Когда вы категоризируете транзакцию вручную, система <strong>автоматически создаёт правило</strong>
              на основе вашего выбора.
            </Paragraph>

            <Paragraph style={{ marginBottom: 12 }}>
              <strong style={{ fontSize: '15px' }}>Преимущества:</strong>
            </Paragraph>
            <ul style={{ marginBottom: 16, paddingLeft: 20 }}>
              <li><strong>Быстрая работа</strong> - нет тяжелых вычислений паттернов</li>
              <li><strong>Прозрачность</strong> - вы видите все правила и можете их редактировать</li>
              <li><strong>Надежность</strong> - правила не исчезают при удалении транзакций</li>
              <li><strong>Контроль</strong> - полный контроль над логикой категоризации</li>
            </ul>

            <Paragraph style={{ marginBottom: 8 }}>
              <strong>Приоритет применения правил:</strong>
            </Paragraph>
            <ul style={{ marginBottom: 8 }}>
              <li>
                <strong>1. По ИНН контрагента</strong> - самое точное совпадение
              </li>
              <li>
                <strong>2. По названию контрагента</strong> - если ИНН не указан
              </li>
              <li>
                <strong>3. По хозяйственной операции</strong> - для типовых операций
              </li>
              <li>
                <strong>4. По ключевым словам</strong> - для сложных случаев
              </li>
            </ul>
            <Paragraph style={{ marginBottom: 0 }}>
              <strong>Совет:</strong> Создавайте правила по ИНН для максимальной точности категоризации.
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

      {/* Rules table */}
      <Card title={`Правила категоризации (${allRules.length})`}>
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
          dataSource={allRules}
          loading={loadingRules}
          rowSelection={rowSelection}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Всего: ${total}`,
          }}
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
            <CategoryTreeSelect
              placeholder="Выберите категорию или начните вводить для поиска"
              style={{ width: '100%' }}
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
