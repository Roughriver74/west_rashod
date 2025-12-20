import { useState } from 'react'
import {
  Card, Table, Button, Space, Typography, Input, Modal, Form, message,
  Tag, Tooltip, Popconfirm, Switch, Row, Col, Descriptions
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined,
  ReloadOutlined, EyeOutlined, BankOutlined, PhoneOutlined, MailOutlined
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getContractors, createContractor, updateContractor, deleteContractor, Contractor } from '../api/contractors'
import type { ColumnsType } from 'antd/es/table'

const { Title, Text } = Typography
const { Search } = Input

export default function ContractorsPage() {
  const queryClient = useQueryClient()
  const [searchText, setSearchText] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isViewModalOpen, setIsViewModalOpen] = useState(false)
  const [editingContractor, setEditingContractor] = useState<Contractor | null>(null)
  const [viewingContractor, setViewingContractor] = useState<Contractor | null>(null)
  const [form] = Form.useForm()

  const { data: contractors = [], isLoading, refetch } = useQuery({
    queryKey: ['contractors', searchText, showInactive],
    queryFn: () => getContractors({
      search: searchText || undefined,
      is_active: showInactive ? undefined : true,
      limit: 500
    }),
  })

  const createMutation = useMutation({
    mutationFn: createContractor,
    onSuccess: () => {
      message.success('Контрагент создан')
      queryClient.invalidateQueries({ queryKey: ['contractors'] })
      setIsModalOpen(false)
      form.resetFields()
    },
    onError: () => message.error('Ошибка при создании контрагента'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Contractor> }) =>
      updateContractor(id, data),
    onSuccess: () => {
      message.success('Контрагент обновлён')
      queryClient.invalidateQueries({ queryKey: ['contractors'] })
      setIsModalOpen(false)
      setEditingContractor(null)
      form.resetFields()
    },
    onError: () => message.error('Ошибка при обновлении контрагента'),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteContractor,
    onSuccess: () => {
      message.success('Контрагент деактивирован')
      queryClient.invalidateQueries({ queryKey: ['contractors'] })
    },
    onError: () => message.error('Ошибка при удалении контрагента'),
  })

  const handleOpenModal = (contractor?: Contractor) => {
    if (contractor) {
      setEditingContractor(contractor)
      form.setFieldsValue(contractor)
    } else {
      setEditingContractor(null)
      form.resetFields()
    }
    setIsModalOpen(true)
  }

  const handleSubmit = (values: Partial<Contractor>) => {
    if (editingContractor) {
      updateMutation.mutate({ id: editingContractor.id, data: values })
    } else {
      createMutation.mutate(values)
    }
  }

  const handleView = (contractor: Contractor) => {
    setViewingContractor(contractor)
    setIsViewModalOpen(true)
  }

  const columns: ColumnsType<Contractor> = [
    {
      title: 'Наименование',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      width: 300,
      render: (text, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          {record.short_name && (
            <Text type="secondary" style={{ fontSize: 12 }}>{record.short_name}</Text>
          )}
        </Space>
      ),
    },
    {
      title: 'ИНН',
      dataIndex: 'inn',
      key: 'inn',
      width: 130,
      render: (inn) => inn || <Text type="secondary">—</Text>,
    },
    {
      title: 'КПП',
      dataIndex: 'kpp',
      key: 'kpp',
      width: 100,
      render: (kpp) => kpp || <Text type="secondary">—</Text>,
    },
    {
      title: 'Контакты',
      key: 'contacts',
      width: 200,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          {record.phone && (
            <Text style={{ fontSize: 12 }}>
              <PhoneOutlined /> {record.phone}
            </Text>
          )}
          {record.email && (
            <Text style={{ fontSize: 12 }}>
              <MailOutlined /> {record.email}
            </Text>
          )}
          {!record.phone && !record.email && <Text type="secondary">—</Text>}
        </Space>
      ),
    },
    {
      title: 'Банк',
      key: 'bank',
      width: 180,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          {record.bank_name && (
            <Tooltip title={record.bank_account}>
              <Text style={{ fontSize: 12 }}>
                <BankOutlined /> {record.bank_name.slice(0, 20)}...
              </Text>
            </Tooltip>
          )}
          {!record.bank_name && <Text type="secondary">—</Text>}
        </Space>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? 'Активен' : 'Неактивен'}
        </Tag>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 130,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Tooltip title="Просмотр">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleView(record)}
            />
          </Tooltip>
          <Tooltip title="Редактировать">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleOpenModal(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Деактивировать контрагента?"
            description="Контрагент будет помечен как неактивный"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="Да"
            cancelText="Нет"
          >
            <Tooltip title="Деактивировать">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                disabled={!record.is_active}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>Контрагенты</Title>
        </Col>
        <Col>
          <Space>
            <Search
              placeholder="Поиск по названию или ИНН..."
              allowClear
              style={{ width: 300 }}
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={setSearchText}
            />
            <Switch
              checkedChildren="Все"
              unCheckedChildren="Активные"
              checked={showInactive}
              onChange={setShowInactive}
            />
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              Обновить
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
              Добавить
            </Button>
          </Space>
        </Col>
      </Row>

      <Card>
        <Table
          columns={columns}
          dataSource={contractors}
          rowKey="id"
          loading={isLoading}
          scroll={{ x: 1200 }}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `Всего: ${total}`,
            defaultPageSize: 20,
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingContractor ? 'Редактировать контрагента' : 'Новый контрагент'}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false)
          setEditingContractor(null)
          form.resetFields()
        }}
        footer={null}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="name"
                label="Полное наименование"
                rules={[{ required: true, message: 'Введите наименование' }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="short_name" label="Краткое наименование">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="contact_person" label="Контактное лицо">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="inn" label="ИНН">
                <Input maxLength={12} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="kpp" label="КПП">
                <Input maxLength={9} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="ogrn" label="ОГРН">
                <Input maxLength={15} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="address" label="Адрес">
                <Input.TextArea rows={2} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="phone" label="Телефон">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="email" label="Email">
                <Input type="email" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="bank_name" label="Название банка">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="bank_bik" label="БИК">
                <Input maxLength={9} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="bank_account" label="Расчётный счёт">
                <Input maxLength={20} />
              </Form.Item>
            </Col>
            {editingContractor && (
              <Col span={12}>
                <Form.Item name="is_active" label="Активен" valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
            )}
          </Row>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setIsModalOpen(false)}>Отмена</Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={createMutation.isPending || updateMutation.isPending}
              >
                {editingContractor ? 'Сохранить' : 'Создать'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* View Modal */}
      <Modal
        title="Информация о контрагенте"
        open={isViewModalOpen}
        onCancel={() => {
          setIsViewModalOpen(false)
          setViewingContractor(null)
        }}
        footer={[
          <Button key="edit" onClick={() => {
            setIsViewModalOpen(false)
            handleOpenModal(viewingContractor!)
          }}>
            Редактировать
          </Button>,
          <Button key="close" type="primary" onClick={() => setIsViewModalOpen(false)}>
            Закрыть
          </Button>
        ]}
        width={700}
      >
        {viewingContractor && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="Наименование" span={2}>
              {viewingContractor.name}
            </Descriptions.Item>
            <Descriptions.Item label="Краткое название">
              {viewingContractor.short_name || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Контактное лицо">
              {viewingContractor.contact_person || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="ИНН">
              {viewingContractor.inn || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="КПП">
              {viewingContractor.kpp || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="ОГРН" span={2}>
              {viewingContractor.ogrn || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Адрес" span={2}>
              {viewingContractor.address || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Телефон">
              {viewingContractor.phone || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Email">
              {viewingContractor.email || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Банк" span={2}>
              {viewingContractor.bank_name || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="БИК">
              {viewingContractor.bank_bik || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Расчётный счёт">
              {viewingContractor.bank_account || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Статус">
              <Tag color={viewingContractor.is_active ? 'green' : 'red'}>
                {viewingContractor.is_active ? 'Активен' : 'Неактивен'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="GUID 1C">
              {viewingContractor.guid_1c || '—'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}
