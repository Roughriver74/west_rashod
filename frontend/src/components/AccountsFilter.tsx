import { useState } from 'react'
import { Card, Collapse, Badge, Typography, Space, Row, Col, Tag } from 'antd'
import { BankOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { getAccountGrouping, type AccountGrouping } from '../api/bankTransactions'

const { Text } = Typography
const { Panel } = Collapse

interface AccountsFilterProps {
  dateFrom?: string
  dateTo?: string
  transactionType?: string
  status?: string
  selectedAccount?: string
  onAccountSelect: (accountNumber: string) => void
}

const formatAmount = (amount: number) => {
  return Number(amount).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₽'
}

const maskAccountNumber = (accountNumber: string) => {
  if (!accountNumber || accountNumber === 'Не указан') return accountNumber
  if (accountNumber.length <= 8) return accountNumber

  const first4 = accountNumber.substring(0, 4)
  const last4 = accountNumber.substring(accountNumber.length - 4)
  return `${first4}****${last4}`
}

export default function AccountsFilter({
  dateFrom,
  dateTo,
  transactionType,
  status,
  selectedAccount,
  onAccountSelect,
}: AccountsFilterProps) {
  const [activeKeys, setActiveKeys] = useState<string[]>([])

  const { data: accountData, isLoading } = useQuery({
    queryKey: ['account-grouping', dateFrom, dateTo, transactionType, status],
    queryFn: () => getAccountGrouping({
      date_from: dateFrom,
      date_to: dateTo,
      transaction_type: transactionType,
      status: status,
    }),
  })

  const accounts = accountData?.accounts || []

  const handleAccountClick = (accountNumber: string) => {
    if (selectedAccount === accountNumber) {
      onAccountSelect('')
    } else {
      onAccountSelect(accountNumber)
    }
  }

  const handleCollapseChange = (keys: string | string[]) => {
    setActiveKeys(Array.isArray(keys) ? keys : [keys])
  }

  return (
    <Card
      title={
        <Space size="small">
          <BankOutlined style={{ fontSize: '14px' }} />
          <Text strong style={{ fontSize: '13px' }}>Счета</Text>
        </Space>
      }
      size="small"
      loading={isLoading}
      bodyStyle={{ padding: '8px' }}
    >
      {accounts.length === 0 ? (
        <Text type="secondary" style={{ fontSize: '12px' }}>Нет данных</Text>
      ) : (
        <Collapse
          accordion={false}
          activeKey={activeKeys}
          onChange={handleCollapseChange}
          expandIconPosition="end"
          size="small"
        >
          {accounts.map((account: AccountGrouping, index) => {
            const isSelected = selectedAccount === account.account_number
            const maskedNumber = maskAccountNumber(account.account_number)

            return (
              <Panel
                key={`account-${index}`}
                header={
                  <div
                    onClick={(e) => {
                      e.stopPropagation()
                      handleAccountClick(account.account_number)
                    }}
                    style={{
                      cursor: 'pointer',
                      padding: '2px 0',
                      background: isSelected ? '#e6f7ff' : 'transparent',
                      borderRadius: '4px',
                      marginLeft: isSelected ? '-6px' : '0',
                      paddingLeft: isSelected ? '6px' : '0',
                    }}
                  >
                    <Row align="middle" justify="space-between">
                      <Col flex="auto">
                        <Space direction="vertical" size={0}>
                          <Space size="small">
                            <Text strong style={{ fontSize: '12px' }}>
                              {maskedNumber}
                            </Text>
                            {account.organization_name && (
                              <Tag color="blue" style={{ margin: 0, fontSize: '10px', padding: '0 4px', lineHeight: '18px' }}>
                                {account.organization_name}
                              </Tag>
                            )}
                          </Space>
                          <Text type="secondary" style={{ fontSize: '11px' }}>
                            {account.total_count} шт.
                          </Text>
                        </Space>
                      </Col>
                      <Col>
                        <Space size={4}>
                          {!status && account.needs_processing_count > 0 && (
                            <Badge
                              count={account.needs_processing_count}
                              style={{ backgroundColor: '#faad14', fontSize: '10px' }}
                              title="Требует обработки"
                            />
                          )}
                          {!status && account.approved_count > 0 && (
                            <Badge
                              count={account.approved_count}
                              style={{ backgroundColor: '#52c41a', fontSize: '10px' }}
                              title="Обработано"
                            />
                          )}
                        </Space>
                      </Col>
                    </Row>
                  </div>
                }
              >
                <Space direction="vertical" style={{ width: '100%' }} size={4}>
                  <Row gutter={8}>
                    <Col span={12}>
                      <div style={{
                        background: '#f0f9ff',
                        border: '1px solid #91d5ff',
                        padding: '6px 8px',
                        borderRadius: '4px'
                      }}>
                        <Text type="secondary" style={{ fontSize: '10px', display: 'block' }}>Приход</Text>
                        <Text strong style={{ color: '#3f8600', fontSize: '13px' }}>
                          {formatAmount(account.total_credit_amount)}
                        </Text>
                        <Text type="secondary" style={{ fontSize: '10px', display: 'block', marginTop: '2px' }}>
                          {account.credit_count} шт.
                        </Text>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{
                        background: '#fff1f0',
                        border: '1px solid #ffccc7',
                        padding: '6px 8px',
                        borderRadius: '4px'
                      }}>
                        <Text type="secondary" style={{ fontSize: '10px', display: 'block' }}>Расход</Text>
                        <Text strong style={{ color: '#cf1322', fontSize: '13px' }}>
                          {formatAmount(account.total_debit_amount)}
                        </Text>
                        <Text type="secondary" style={{ fontSize: '10px', display: 'block', marginTop: '2px' }}>
                          {account.debit_count} шт.
                        </Text>
                      </div>
                    </Col>
                  </Row>

                  <div style={{
                    background: '#fafafa',
                    padding: '6px 8px',
                    borderRadius: '4px'
                  }}>
                    <Text type="secondary" style={{ fontSize: '10px', display: 'block' }}>Сальдо</Text>
                    <Text strong style={{
                      color: account.balance >= 0 ? '#3f8600' : '#cf1322',
                      fontSize: '14px',
                      fontWeight: 'bold',
                    }}>
                      {formatAmount(account.balance)}
                    </Text>
                  </div>

                  {!status && account.needs_processing_count > 0 && (
                    <div style={{
                      background: '#fffbe6',
                      border: '1px solid #ffe58f',
                      padding: '4px 8px',
                      borderRadius: '4px'
                    }}>
                      <Space size={4}>
                        <WarningOutlined style={{ color: '#faad14', fontSize: '12px' }} />
                        <Text style={{ fontSize: '11px' }}>Требует: {account.needs_processing_count}</Text>
                      </Space>
                    </div>
                  )}
                </Space>
              </Panel>
            )
          })}
        </Collapse>
      )}
    </Card>
  )
}
