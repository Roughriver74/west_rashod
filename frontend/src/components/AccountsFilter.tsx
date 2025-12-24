import { useState, useMemo } from 'react'
import { Card, Badge, Typography, Space } from 'antd'
import { BankOutlined, RightOutlined, DownOutlined, ShopOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { getAccountGrouping, type AccountGrouping } from '../api/bankTransactions'

const { Text } = Typography

interface AccountsFilterProps {
  dateFrom?: string
  dateTo?: string
  transactionType?: string
  status?: string
  selectedAccount?: string
  selectedOrganizationId?: number
  onAccountSelect: (accountNumber: string | undefined, organizationId: number | undefined) => void
}

const formatAmount = (amount: number) => {
  return Number(amount).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₽'
}

const maskAccountNumber = (accountNumber: string) => {
  if (!accountNumber || accountNumber === 'Не указан') return accountNumber
  if (accountNumber === 'Касса') return accountNumber
  if (accountNumber.length <= 8) return accountNumber

  const first4 = accountNumber.substring(0, 4)
  const last4 = accountNumber.substring(accountNumber.length - 4)
  return `${first4}****${last4}`
}

// Структура: Организация → Банк → Счета
interface BankAccount {
  account: AccountGrouping
}

interface OrganizationBank {
  bank_name: string
  bank_bik: string | null
  accounts: BankAccount[]
  total_count: number
  total_credit_amount: number
  total_debit_amount: number
  balance: number
  needs_processing_count: number
  approved_count: number
}

interface OrganizationGroup {
  organization_id: number | null
  organization_name: string | null
  banks: OrganizationBank[]
  total_count: number
  total_credit_amount: number
  total_debit_amount: number
  balance: number
  needs_processing_count: number
  approved_count: number
}

export default function AccountsFilter({
  dateFrom,
  dateTo,
  transactionType,
  status,
  selectedAccount,
  selectedOrganizationId,
  onAccountSelect,
}: AccountsFilterProps) {
  const [expandedOrgs, setExpandedOrgs] = useState<string[]>([])
  const [expandedBanks, setExpandedBanks] = useState<string[]>([])

  const { data: accountData, isLoading } = useQuery({
    queryKey: ['account-grouping', dateFrom, dateTo, transactionType],
    queryFn: () => getAccountGrouping({
      date_from: dateFrom,
      date_to: dateTo,
      transaction_type: transactionType,
      // Не передаём status - счета должны показываться всегда
    }),
  })

  // Группируем: Организация → Банк → Счета
  const organizationGroups = useMemo(() => {
    const accounts = accountData?.accounts || []
    const groups: Record<string, OrganizationGroup> = {}

    for (const acc of accounts) {
      const orgKey = `org_${acc.organization_id || 'null'}`

      // Инициализируем группу организации
      if (!groups[orgKey]) {
        groups[orgKey] = {
          organization_id: acc.organization_id,
          organization_name: acc.organization_name,
          banks: [],
          total_count: 0,
          total_credit_amount: 0,
          total_debit_amount: 0,
          balance: 0,
          needs_processing_count: 0,
          approved_count: 0,
        }
      }

      const orgGroup = groups[orgKey]

      // Ищем или создаем банк внутри организации
      const bankKey = acc.our_bank_name || 'Не указан банк'
      let bank = orgGroup.banks.find(b => b.bank_name === bankKey)

      if (!bank) {
        bank = {
          bank_name: bankKey,
          bank_bik: acc.our_bank_bik,
          accounts: [],
          total_count: 0,
          total_credit_amount: 0,
          total_debit_amount: 0,
          balance: 0,
          needs_processing_count: 0,
          approved_count: 0,
        }
        orgGroup.banks.push(bank)
      }

      // Добавляем счет в банк
      bank.accounts.push({ account: acc })
      bank.total_count += acc.total_count
      bank.total_credit_amount += Number(acc.total_credit_amount)
      bank.total_debit_amount += Number(acc.total_debit_amount)
      bank.balance += Number(acc.balance)
      bank.needs_processing_count += acc.needs_processing_count
      bank.approved_count += acc.approved_count

      // Обновляем итоги организации
      orgGroup.total_count += acc.total_count
      orgGroup.total_credit_amount += Number(acc.total_credit_amount)
      orgGroup.total_debit_amount += Number(acc.total_debit_amount)
      orgGroup.balance += Number(acc.balance)
      orgGroup.needs_processing_count += acc.needs_processing_count
      orgGroup.approved_count += acc.approved_count
    }

    // Сортировка: "Без организации" первым, затем по количеству транзакций
    return Object.values(groups).sort((a, b) => {
      if (a.organization_id === null) return -1
      if (b.organization_id === null) return 1
      return b.total_count - a.total_count
    })
  }, [accountData])

  const handleAccountClick = (accountNumber: string, organizationId: number | null) => {
    // Если уже выбран этот счет - снимаем выделение
    if (selectedAccount === accountNumber && selectedOrganizationId === organizationId) {
      onAccountSelect(undefined, undefined)
    } else {
      // Выбираем счет
      onAccountSelect(accountNumber, organizationId || undefined)
    }
  }

  const toggleOrgExpand = (orgId: number | null, e: React.MouseEvent) => {
    e.stopPropagation()
    const key = `org_${orgId}`
    setExpandedOrgs(prev =>
      prev.includes(key)
        ? prev.filter(o => o !== key)
        : [...prev, key]
    )
  }

  const toggleBankExpand = (orgId: number | null, bankName: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const key = `${orgId}_${bankName}`
    setExpandedBanks(prev =>
      prev.includes(key)
        ? prev.filter(b => b !== key)
        : [...prev, key]
    )
  }

  const isAccountSelected = (accountNumber: string, organizationId: number | null) =>
    selectedAccount === accountNumber && selectedOrganizationId === organizationId

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
      styles={{ body: { padding: '8px' } }}
    >
      {organizationGroups.length === 0 ? (
        <Text type="secondary" style={{ fontSize: '12px' }}>Нет данных</Text>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {organizationGroups.map((org) => {
            const orgKey = `org_${org.organization_id}`
            const isOrgExpanded = expandedOrgs.includes(orgKey)

            return (
              <div key={orgKey} style={{ marginBottom: '6px' }}>
                {/* Заголовок организации */}
                <div
                  onClick={(e) => toggleOrgExpand(org.organization_id, e)}
                  style={{
                    cursor: 'pointer',
                    padding: '6px 8px',
                    background: '#f5f5f5',
                    borderRadius: '4px',
                    borderLeft: '3px solid #52c41a',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#e8e8e8'}
                  onMouseLeave={(e) => e.currentTarget.style.background = '#f5f5f5'}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {isOrgExpanded ? (
                      <DownOutlined style={{ fontSize: '9px', color: '#999' }} />
                    ) : (
                      <RightOutlined style={{ fontSize: '9px', color: '#999' }} />
                    )}
                    <ShopOutlined style={{ fontSize: '11px', color: '#52c41a' }} />
                    <Text
                      strong
                      style={{
                        fontSize: '11px',
                        flex: 1,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}
                      title={org.organization_name || 'Без организации'}
                    >
                      {org.organization_name || 'Без организации'}
                    </Text>
                    <Text type="secondary" style={{ fontSize: '9px', whiteSpace: 'nowrap' }}>
                      {org.total_count}
                    </Text>
                    {!status && org.needs_processing_count > 0 && (
                      <Badge
                        count={org.needs_processing_count}
                        style={{ backgroundColor: '#faad14', fontSize: '9px' }}
                        title="Требует обработки"
                      />
                    )}
                  </div>
                </div>

                {/* Банки внутри организации */}
                {isOrgExpanded && (
                  <div style={{ marginLeft: '12px', marginTop: '4px', borderLeft: '1px solid #e8e8e8', paddingLeft: '6px' }}>
                    {org.banks.map((bank) => {
                      const bankKey = `${org.organization_id}_${bank.bank_name}`
                      const isBankExpanded = expandedBanks.includes(bankKey)
                      const hasMultipleAccounts = bank.accounts.length > 1

                      return (
                        <div key={bankKey} style={{ marginBottom: '2px' }}>
                          {/* Заголовок банка */}
                          <div
                            onClick={(e) => {
                              if (hasMultipleAccounts) {
                                toggleBankExpand(org.organization_id, bank.bank_name, e)
                              }
                            }}
                            style={{
                              cursor: hasMultipleAccounts ? 'pointer' : 'default',
                              padding: '4px 6px',
                              borderRadius: '3px',
                              transition: 'all 0.2s',
                            }}
                            onMouseEnter={(e) => {
                              if (hasMultipleAccounts) {
                                e.currentTarget.style.background = '#f5f5f5'
                              }
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = 'transparent'
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              {hasMultipleAccounts && (
                                isBankExpanded ? (
                                  <DownOutlined style={{ fontSize: '8px', color: '#999' }} />
                                ) : (
                                  <RightOutlined style={{ fontSize: '8px', color: '#999' }} />
                                )
                              )}
                              <BankOutlined style={{ fontSize: '10px', color: '#1890ff' }} />
                              <Text
                                type="secondary"
                                style={{
                                  fontSize: '10px',
                                  flex: 1,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap'
                                }}
                                title={bank.bank_name}
                              >
                                {bank.bank_name}
                              </Text>
                              <Text type="secondary" style={{ fontSize: '9px', whiteSpace: 'nowrap' }}>
                                {bank.total_count}
                              </Text>
                              {!status && bank.needs_processing_count > 0 && (
                                <Badge
                                  count={bank.needs_processing_count}
                                  style={{ backgroundColor: '#faad14', fontSize: '9px' }}
                                  size="small"
                                />
                              )}
                            </div>
                          </div>

                          {/* Счета банка */}
                          {(!hasMultipleAccounts || isBankExpanded) && (
                            <div style={{ marginLeft: '12px', marginTop: '2px' }}>
                              {bank.accounts.map(({ account }, accIdx) => {
                                const maskedNumber = maskAccountNumber(account.account_number)
                                const accountSelected = isAccountSelected(account.account_number, account.organization_id)

                                return (
                                  <div
                                    key={`${account.account_number}_${accIdx}`}
                                    onClick={() => handleAccountClick(account.account_number, account.organization_id)}
                                    style={{
                                      cursor: 'pointer',
                                      padding: '3px 6px',
                                      marginBottom: '2px',
                                      background: accountSelected ? '#e6f7ff' : 'transparent',
                                      borderRadius: '3px',
                                      border: accountSelected ? '1px solid #1890ff' : '1px solid transparent',
                                      transition: 'all 0.2s',
                                    }}
                                    onMouseEnter={(e) => {
                                      if (!accountSelected) {
                                        e.currentTarget.style.background = '#f5f5f5'
                                      }
                                    }}
                                    onMouseLeave={(e) => {
                                      if (!accountSelected) {
                                        e.currentTarget.style.background = 'transparent'
                                      }
                                    }}
                                  >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <Text style={{ fontSize: '10px', fontFamily: 'monospace', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {maskedNumber}
                                      </Text>
                                      {!hasMultipleAccounts && (
                                        <Text type="secondary" style={{ fontSize: '9px', whiteSpace: 'nowrap' }}>
                                          {account.total_count}
                                        </Text>
                                      )}
                                      {!status && account.needs_processing_count > 0 && (
                                        <Badge
                                          count={account.needs_processing_count}
                                          style={{ backgroundColor: '#faad14', fontSize: '9px' }}
                                          size="small"
                                        />
                                      )}
                                    </div>

                                    {/* Детали счета при выборе */}
                                    {accountSelected && (
                                      <div style={{ marginTop: '8px' }}>
                                        <div style={{ display: 'flex', gap: '8px' }}>
                                          <div style={{ flex: 1 }}>
                                            <div style={{
                                              background: '#f0f9ff',
                                              border: '1px solid #91d5ff',
                                              padding: '4px 6px',
                                              borderRadius: '4px'
                                            }}>
                                              <Text type="secondary" style={{ fontSize: '9px', display: 'block' }}>Приход</Text>
                                              <Text strong style={{ color: '#3f8600', fontSize: '11px' }}>
                                                {formatAmount(account.total_credit_amount)}
                                              </Text>
                                            </div>
                                          </div>
                                          <div style={{ flex: 1 }}>
                                            <div style={{
                                              background: '#fff1f0',
                                              border: '1px solid #ffccc7',
                                              padding: '4px 6px',
                                              borderRadius: '4px'
                                            }}>
                                              <Text type="secondary" style={{ fontSize: '9px', display: 'block' }}>Расход</Text>
                                              <Text strong style={{ color: '#cf1322', fontSize: '11px' }}>
                                                {formatAmount(account.total_debit_amount)}
                                              </Text>
                                            </div>
                                          </div>
                                        </div>
                                        <div style={{
                                          background: '#fafafa',
                                          padding: '4px 6px',
                                          borderRadius: '4px',
                                          marginTop: '4px'
                                        }}>
                                          <Text type="secondary" style={{ fontSize: '9px', display: 'block' }}>Сальдо</Text>
                                          <Text strong style={{
                                            color: account.balance >= 0 ? '#3f8600' : '#cf1322',
                                            fontSize: '12px',
                                          }}>
                                            {formatAmount(account.balance)}
                                          </Text>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}
