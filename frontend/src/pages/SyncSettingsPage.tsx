import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Switch,
  InputNumber,
  Button,
  Space,
  Typography,
  Divider,
  message,
  Alert,
  Spin,
  Tag,
  Row,
  Col,
  Radio,
} from 'antd';
import {
  SyncOutlined,
  ClockCircleOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import syncSettingsApi, { SyncSettings, SyncSettingsUpdate } from '../api/syncSettings';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

const SyncSettingsPage: React.FC = () => {
  const [form] = Form.useForm();
  const [settings, setSettings] = useState<SyncSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMode, setSyncMode] = useState<'interval' | 'time'>('interval');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await syncSettingsApi.getSettings();

      // Auto-refresh status if it's stuck in IN_PROGRESS
      if (data.last_sync_status === 'IN_PROGRESS') {
        try {
          await syncSettingsApi.refreshSyncStatus();
          // Reload settings after refresh
          const updatedData = await syncSettingsApi.getSettings();
          setSettings(updatedData);
        } catch (refreshError) {
          console.error('Failed to refresh status:', refreshError);
          setSettings(data);
        }
      } else {
        setSettings(data);
      }

      // Determine sync mode
      if (data.sync_time_hour !== null) {
        setSyncMode('time');
      } else {
        setSyncMode('interval');
      }

      // Set form values
      form.setFieldsValue({
        auto_sync_enabled: data.auto_sync_enabled,
        sync_interval_hours: data.sync_interval_hours,
        sync_time_hour: data.sync_time_hour ?? 4,
        sync_time_minute: data.sync_time_minute,
        auto_classify: data.auto_classify,
        sync_days_back: data.sync_days_back,
        auto_sync_expenses_enabled: data.auto_sync_expenses_enabled,
        sync_expenses_interval_hours: data.sync_expenses_interval_hours,
      });
    } catch (error: any) {
      message.error('Не удалось загрузить настройки');
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: any) => {
    try {
      setSaving(true);

      const updateData: SyncSettingsUpdate = {
        auto_sync_enabled: values.auto_sync_enabled,
        sync_interval_hours: values.sync_interval_hours,
        sync_time_hour: syncMode === 'time' ? values.sync_time_hour : null,
        sync_time_minute: values.sync_time_minute,
        auto_classify: values.auto_classify,
        sync_days_back: values.sync_days_back,
        auto_sync_expenses_enabled: values.auto_sync_expenses_enabled,
        sync_expenses_interval_hours: values.sync_expenses_interval_hours,
      };

      const updatedSettings = await syncSettingsApi.updateSettings(updateData);
      setSettings(updatedSettings);
      message.success('Настройки сохранены');
    } catch (error: any) {
      message.error('Не удалось сохранить настройки');
      console.error('Failed to save settings:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleTriggerSync = async () => {
    try {
      setSyncing(true);
      const response = await syncSettingsApi.triggerSyncNow();
      message.success(response.message);

      // Monitor task status
      const taskId = response.task_id;
      let attempts = 0;
      const maxAttempts = 120; // 10 minutes max (5s interval)

      const checkStatus = async () => {
        try {
          const taskStatus = await syncSettingsApi.getTaskStatus(taskId);

          if (taskStatus.status === 'completed' || taskStatus.status === 'failed' || taskStatus.status === 'cancelled') {
            // Task finished, reload settings
            await loadSettings();
            setSyncing(false);

            if (taskStatus.status === 'completed') {
              message.success('Синхронизация завершена успешно');
            } else if (taskStatus.status === 'failed') {
              message.error(`Синхронизация завершилась с ошибкой: ${taskStatus.error || 'Неизвестная ошибка'}`);
            }
          } else if (attempts < maxAttempts) {
            // Still running, check again
            attempts++;
            setTimeout(checkStatus, 5000); // Check every 5 seconds
          } else {
            // Timeout
            setSyncing(false);
            await loadSettings();
            message.warning('Превышено время ожидания. Проверьте статус синхронизации позже.');
          }
        } catch (error) {
          console.error('Failed to check task status:', error);
          // Still reload settings on error
          await loadSettings();
          setSyncing(false);
        }
      };

      // Start checking after 2 seconds
      setTimeout(checkStatus, 2000);

    } catch (error: any) {
      message.error('Не удалось запустить синхронизацию');
      console.error('Failed to trigger sync:', error);
      setSyncing(false);
    }
  };

  const getStatusTag = (status: string | null) => {
    if (!status) return null;

    switch (status) {
      case 'SUCCESS':
        return <Tag icon={<CheckCircleOutlined />} color="success">Успешно</Tag>;
      case 'FAILED':
        return <Tag icon={<CloseCircleOutlined />} color="error">Ошибка</Tag>;
      case 'IN_PROGRESS':
        return <Tag icon={<LoadingOutlined />} color="processing">Выполняется</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <SettingOutlined /> Настройки синхронизации с 1С
      </Title>

      <Row gutter={16}>
        <Col span={16}>
          <Card title="Настройки автоматической синхронизации">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={{
                auto_sync_enabled: false,
                sync_interval_hours: 4,
                sync_time_hour: 4,
                sync_time_minute: 0,
                auto_classify: true,
                sync_days_back: 30,
                auto_sync_expenses_enabled: false,
                sync_expenses_interval_hours: 24,
              }}
            >
              <Form.Item
                name="auto_sync_enabled"
                label="Автоматическая синхронизация"
                valuePropName="checked"
              >
                <Switch
                  checkedChildren="Включено"
                  unCheckedChildren="Выключено"
                />
              </Form.Item>

              <Form.Item label="Режим синхронизации">
                <Radio.Group value={syncMode} onChange={(e) => setSyncMode(e.target.value)}>
                  <Radio.Button value="interval">По интервалу</Radio.Button>
                  <Radio.Button value="time">В определённое время</Radio.Button>
                </Radio.Group>
              </Form.Item>

              {syncMode === 'interval' ? (
                <Form.Item
                  name="sync_interval_hours"
                  label="Интервал синхронизации (часы)"
                  rules={[{ required: true, message: 'Укажите интервал' }]}
                >
                  <InputNumber
                    min={1}
                    max={24}
                    style={{ width: '200px' }}
                    suffix="час(ов)"
                  />
                </Form.Item>
              ) : (
                <Space>
                  <Form.Item
                    name="sync_time_hour"
                    label="Час"
                    rules={[{ required: true, message: 'Укажите час' }]}
                  >
                    <InputNumber min={0} max={23} style={{ width: '100px' }} />
                  </Form.Item>
                  <Form.Item
                    name="sync_time_minute"
                    label="Минута"
                    rules={[{ required: true, message: 'Укажите минуту' }]}
                  >
                    <InputNumber min={0} max={59} style={{ width: '100px' }} />
                  </Form.Item>
                </Space>
              )}

              <Divider />

              <Form.Item
                name="sync_days_back"
                label="Синхронизировать за последние N дней"
                rules={[{ required: true, message: 'Укажите количество дней' }]}
                tooltip="Сколько дней назад загружать операции при синхронизации"
              >
                <InputNumber
                  min={1}
                  max={365}
                  style={{ width: '200px' }}
                  suffix="дн."
                />
              </Form.Item>

              <Form.Item
                name="auto_classify"
                label="Автоматическая категоризация"
                valuePropName="checked"
                tooltip="Применять AI-классификацию при импорте"
              >
                <Switch
                  checkedChildren="Включено"
                  unCheckedChildren="Выключено"
                />
              </Form.Item>

              <Divider>Синхронизация заявок</Divider>

              <Form.Item
                name="auto_sync_expenses_enabled"
                label="Автоматическая синхронизация заявок"
                valuePropName="checked"
                tooltip="Автоматически загружать заявки на расход из 1С"
              >
                <Switch
                  checkedChildren="Включено"
                  unCheckedChildren="Выключено"
                />
              </Form.Item>

              <Form.Item
                name="sync_expenses_interval_hours"
                label="Интервал синхронизации заявок (часы)"
                rules={[{ required: true, message: 'Укажите интервал' }]}
                tooltip="Как часто синхронизировать заявки (по умолчанию раз в сутки)"
              >
                <InputNumber
                  min={1}
                  max={72}
                  style={{ width: '200px' }}
                  suffix="час(ов)"
                />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={saving}>
                    Сохранить настройки
                  </Button>
                  <Button onClick={() => form.resetFields()}>
                    Отменить
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col span={8}>
          <Card title="Информация о синхронизации">
            {settings?.last_sync_started_at && (
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text strong>Последний запуск:</Text>
                  <br />
                  <Text>
                    <ClockCircleOutlined />{' '}
                    {dayjs(settings.last_sync_started_at).format('DD.MM.YYYY HH:mm:ss')}
                  </Text>
                </div>

                {settings.last_sync_completed_at && (
                  <div>
                    <Text strong>Завершена:</Text>
                    <br />
                    <Text>
                      <ClockCircleOutlined />{' '}
                      {dayjs(settings.last_sync_completed_at).format('DD.MM.YYYY HH:mm:ss')}
                    </Text>
                  </div>
                )}

                <div>
                  <Text strong>Статус:</Text>
                  <br />
                  <Space>
                    {getStatusTag(settings.last_sync_status)}
                    {settings.last_sync_status === 'IN_PROGRESS' && (
                      <Button
                        size="small"
                        type="link"
                        onClick={async () => {
                          try {
                            await syncSettingsApi.refreshSyncStatus();
                            await loadSettings();
                            message.success('Статус обновлен');
                          } catch (error) {
                            message.error('Не удалось обновить статус');
                          }
                        }}
                      >
                        Обновить
                      </Button>
                    )}
                  </Space>
                </div>

                {settings.last_sync_message && (
                  <Alert
                    message="Результат"
                    description={settings.last_sync_message}
                    type={settings.last_sync_status === 'SUCCESS' ? 'success' : 'info'}
                    showIcon
                  />
                )}
              </Space>
            )}

            {!settings?.last_sync_started_at && (
              <Alert
                message="Синхронизация ещё не запускалась"
                type="info"
              />
            )}

            <Divider />

            <Button
              type="primary"
              icon={<SyncOutlined />}
              onClick={handleTriggerSync}
              loading={syncing}
              block
              size="large"
            >
              Запустить синхронизацию сейчас
            </Button>

            <div style={{ marginTop: '16px' }}>
              <Alert
                message="Синхронизация импортирует:"
                description={
                  <ul style={{ margin: 0, paddingLeft: '20px' }}>
                    <li>Банковские поступления</li>
                    <li>Банковские списания</li>
                    <li>Приходные кассовые ордера (ПКО)</li>
                    <li>Расходные кассовые ордера (РКО)</li>
                  </ul>
                }
                type="info"
              />
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default SyncSettingsPage;
