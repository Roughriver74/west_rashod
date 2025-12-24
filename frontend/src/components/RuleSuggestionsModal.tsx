import React, { useState } from 'react'
import { Modal, Card, Button, Space, InputNumber, message, Typography, Alert, Tag, Checkbox, Input } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import type { RuleSuggestionsResponse, RuleSuggestion } from '../types/bankTransaction'
import { createRuleFromSuggestion } from '../api/bankTransactions'

const { Title, Text, Paragraph } = Typography

interface Props {
  visible: boolean
  suggestions: RuleSuggestionsResponse | null
  onClose: () => void
  onRuleCreated?: () => void
}

interface RuleConfig {
  priority: number
  confidence: number
  applyToExisting: boolean
  customMatchValue?: string // Для редактирования ключевого слова
}

const DEFAULT_CONFIG: RuleConfig = {
  priority: 10,
  confidence: 0.95,
  applyToExisting: false
}

export const RuleSuggestionsModal: React.FC<Props> = ({
  visible,
  suggestions,
  onClose,
  onRuleCreated
}) => {
  // Отдельный config для каждого предложения (по индексу)
  const [configs, setConfigs] = useState<Record<number, RuleConfig>>({})
  const [creating, setCreating] = useState(false)

  // Получить config для конкретного suggestion
  const getConfig = (index: number): RuleConfig => {
    return configs[index] || DEFAULT_CONFIG
  }

  // Обновить config для конкретного suggestion
  const updateConfig = (index: number, updates: Partial<RuleConfig>) => {
    setConfigs(prev => ({
      ...prev,
      [index]: { ...getConfig(index), ...updates }
    }))
  }

  const handleCreateRule = async (suggestion: RuleSuggestion, index: number) => {
    if (!suggestions) return

    const config = getConfig(index)
    const matchValue = config.customMatchValue !== undefined ? config.customMatchValue : suggestion.match_value

    // Проверка что ключевое слово не пустое
    if (!matchValue || matchValue.trim() === '') {
      message.error('Ключевое слово не может быть пустым')
      return
    }

    setCreating(true)
    try {
      const result = await createRuleFromSuggestion({
        rule_type: suggestion.rule_type,
        match_value: matchValue.trim(),
        category_id: suggestions.category_id,
        priority: config.priority,
        confidence: config.confidence,
        apply_to_existing: config.applyToExisting
      })

      if (config.applyToExisting) {
        if (result.applied_count && result.applied_count > 0) {
          message.success(`✅ Правило создано и применено к ${result.applied_count} операциям!`)
        } else {
          message.success('✅ Правило создано (подходящих транзакций не найдено)')
        }
      } else {
        message.success('✅ Правило успешно создано!')
      }
      onRuleCreated?.()
      handleClose()
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Ошибка при создании правила')
    } finally {
      setCreating(false)
    }
  }

  const handleClose = () => {
    setConfigs({})
    onClose()
  }

  const getRuleTypeLabel = (ruleType: string): string => {
    const labels: Record<string, string> = {
      COUNTERPARTY_INN: 'По ИНН контрагента',
      COUNTERPARTY_NAME: 'По названию контрагента',
      BUSINESS_OPERATION: 'По хозяйственной операции',
      KEYWORD: 'По ключевому слову'
    }
    return labels[ruleType] || ruleType
  }

  const getRuleTypeColor = (ruleType: string): string => {
    const colors: Record<string, string> = {
      COUNTERPARTY_INN: 'green',
      COUNTERPARTY_NAME: 'blue',
      BUSINESS_OPERATION: 'purple',
      KEYWORD: 'orange'
    }
    return colors[ruleType] || 'default'
  }

  if (!suggestions) return null

  return (
    <Modal
      title={
        <Space direction="vertical" size={0}>
          <Title level={4} style={{ margin: 0 }}>
            💡 Предложения по созданию правил
          </Title>
          <Text type="secondary">
            Категория: <strong>{suggestions.category_name}</strong>
          </Text>
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      footer={null}
      width={700}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Alert
          message="Создайте правила для автоматической категоризации"
          description={
            <>
              <Paragraph style={{ marginBottom: 8 }}>
                На основе выбранных операций ({suggestions.total_transactions} шт.) система предлагает
                создать правила автоматической категоризации.
              </Paragraph>
              <Paragraph style={{ marginBottom: 0 }}>
                <strong>Приоритет</strong> определяет порядок применения правил (чем выше, тем раньше).
                <br />
                <strong>Уверенность</strong> показывает, насколько система уверена в правильности категоризации.
              </Paragraph>
            </>
          }
          type="info"
          showIcon
        />

        {suggestions.suggestions.length === 0 ? (
          <Alert
            message="Нет предложений"
            description="Для выбранных операций не удалось сформировать предложения по созданию правил."
            type="warning"
            showIcon
          />
        ) : (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {suggestions.suggestions.map((suggestion, index) => (
              <Card
                key={index}
                size="small"
                title={
                  <Space>
                    <Tag color={getRuleTypeColor(suggestion.rule_type)}>
                      {getRuleTypeLabel(suggestion.rule_type)}
                    </Tag>
                    {suggestion.can_create ? (
                      <Tag icon={<CheckCircleOutlined />} color="success">
                        Можно создать
                      </Tag>
                    ) : (
                      <Tag icon={<CloseCircleOutlined />} color="error">
                        Уже существует
                      </Tag>
                    )}
                  </Space>
                }
                extra={
                  suggestion.can_create && (
                    <Button
                      type="primary"
                      size="small"
                      loading={creating}
                      onClick={() => handleCreateRule(suggestion, index)}
                    >
                      Создать правило
                    </Button>
                  )
                }
              >
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <div>
                    <Text strong>Описание:</Text>
                    <br />
                    <Text>{suggestion.description}</Text>
                  </div>

                  {/* Для ключевых слов - позволить редактировать */}
                  {suggestion.can_create && suggestion.rule_type === 'KEYWORD' && (
                    <div>
                      <Text strong>Ключевое слово:</Text>
                      <br />
                      <Space>
                        <Input
                          placeholder="Введите ключевое слово"
                          value={getConfig(index).customMatchValue !== undefined
                            ? getConfig(index).customMatchValue
                            : suggestion.match_value}
                          onChange={(e) => updateConfig(index, { customMatchValue: e.target.value })}
                          size="small"
                          style={{ minWidth: '250px' }}
                        />
                        <Text type="secondary">(можно изменить)</Text>
                      </Space>
                    </div>
                  )}

                  <div>
                    <Text type="secondary">
                      Подходящих операций: <strong>{suggestion.transaction_count}</strong> из{' '}
                      {suggestions.total_transactions}
                    </Text>
                  </div>

                  {suggestion.can_create && (
                    <>
                      <Space size="large">
                        <Space>
                          <Text>Приоритет:</Text>
                          <InputNumber
                            min={1}
                            max={100}
                            value={getConfig(index).priority}
                            onChange={(value) => updateConfig(index, { priority: value || 10 })}
                            size="small"
                            style={{ width: 80 }}
                          />
                        </Space>

                        <Space>
                          <Text>Уверенность:</Text>
                          <InputNumber
                            min={0}
                            max={1}
                            step={0.05}
                            value={getConfig(index).confidence}
                            onChange={(value) => updateConfig(index, { confidence: value || 0.95 })}
                            size="small"
                            style={{ width: 80 }}
                            formatter={(value) => `${Math.round((value || 0) * 100)}%`}
                          />
                        </Space>
                      </Space>

                      <Checkbox
                        checked={getConfig(index).applyToExisting}
                        onChange={(e) => updateConfig(index, { applyToExisting: e.target.checked })}
                      >
                        <Text>
                          Также применить к существующим операциям{' '}
                          {suggestion.matching_existing_count > 0 && (
                            <Text strong type="success">
                              ({suggestion.matching_existing_count} шт.)
                            </Text>
                          )}
                          {suggestion.matching_existing_count === 0 && (
                            <Text type="secondary">(0 шт.)</Text>
                          )}
                        </Text>
                      </Checkbox>
                    </>
                  )}
                </Space>
              </Card>
            ))}
          </Space>
        )}

        <div style={{ textAlign: 'right' }}>
          <Button onClick={handleClose}>Закрыть</Button>
        </div>
      </Space>
    </Modal>
  )
}
