/**
 * Sync Modal Component
 * Modal for starting and tracking 1C sync operations
 */
import React, { useState } from 'react';
import {
  Modal,
  Form,
  DatePicker,
  Switch,
  Button,
  Space,
  Typography,
  message,
  Tabs,
  Card,
} from 'antd';
import {
  SyncOutlined,
  CloudDownloadOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import {
  startAsyncBankTransactionsSync,
  startAsyncContractorsSync,
  AsyncSyncRequest,
} from '../api/tasks';
import TaskProgress from './TaskProgress';

const { Text } = Typography;
const { RangePicker } = DatePicker;

interface SyncModalProps {
  visible: boolean;
  onClose: () => void;
  onSyncComplete?: () => void;
}

export const SyncModal: React.FC<SyncModalProps> = ({ visible, onClose, onSyncComplete }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [showProgress, setShowProgress] = useState(false);
  const [activeTab, setActiveTab] = useState('transactions');

  const handleStartTransactionsSync = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const request: AsyncSyncRequest = {
        auto_classify: values.auto_classify ?? true,
      };

      if (values.dateRange) {
        request.date_from = values.dateRange[0].format('YYYY-MM-DD');
        request.date_to = values.dateRange[1].format('YYYY-MM-DD');
      }

      const response = await startAsyncBankTransactionsSync(request);
      setTaskId(response.task_id);
      setShowProgress(true);
      message.success('Синхронизация запущена');
    } catch (error) {
      message.error('Не удалось запустить синхронизацию');
      console.error('Sync error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartContractorsSync = async () => {
    try {
      setLoading(true);
      const response = await startAsyncContractorsSync();
      setTaskId(response.task_id);
      setShowProgress(true);
      message.success('Синхронизация контрагентов запущена');
    } catch (error) {
      message.error('Не удалось запустить синхронизацию');
      console.error('Sync error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTaskComplete = () => {
    onSyncComplete?.();
  };

  const handleProgressClose = () => {
    setShowProgress(false);
    setTaskId(null);
  };

  const handleClose = () => {
    if (!showProgress) {
      onClose();
    }
  };

  // Default date range: last 30 days
  const defaultDateRange: [Dayjs, Dayjs] = [dayjs().subtract(30, 'day'), dayjs()];

  return (
    <>
      <Modal
        title={
          <Space>
            <SyncOutlined />
            <span>Синхронизация с 1С</span>
          </Space>
        }
        open={visible && !showProgress}
        onCancel={handleClose}
        footer={null}
        width={600}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'transactions',
              label: (
                <span>
                  <CloudDownloadOutlined /> Транзакции
                </span>
              ),
              children: (
                <Card>
                  <Form
                    form={form}
                    layout="vertical"
                    initialValues={{
                      dateRange: defaultDateRange,
                      auto_classify: true,
                    }}
                  >
                    <Form.Item
                      name="dateRange"
                      label="Период синхронизации"
                      rules={[{ required: true, message: 'Выберите период' }]}
                    >
                      <RangePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
                    </Form.Item>

                    <Form.Item
                      name="auto_classify"
                      label="Автоматическая классификация"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>

                    <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                      Будут загружены банковские поступления, списания, ПКО и РКО за выбранный
                      период.
                    </Text>

                    <Button
                      type="primary"
                      icon={<SyncOutlined />}
                      onClick={handleStartTransactionsSync}
                      loading={loading}
                      block
                    >
                      Запустить синхронизацию
                    </Button>
                  </Form>
                </Card>
              ),
            },
            {
              key: 'contractors',
              label: (
                <span>
                  <TeamOutlined /> Контрагенты
                </span>
              ),
              children: (
                <Card>
                  <Text style={{ display: 'block', marginBottom: 24 }}>
                    Синхронизация справочника контрагентов из 1С. Будут обновлены существующие
                    записи и созданы новые.
                  </Text>

                  <Button
                    type="primary"
                    icon={<SyncOutlined />}
                    onClick={handleStartContractorsSync}
                    loading={loading}
                    block
                  >
                    Синхронизировать контрагентов
                  </Button>
                </Card>
              ),
            },
          ]}
        />
      </Modal>

      {/* Task Progress Modal */}
      {taskId && (
        <TaskProgress
          taskId={taskId}
          title={activeTab === 'transactions' ? 'Синхронизация транзакций' : 'Синхронизация контрагентов'}
          visible={showProgress}
          onClose={handleProgressClose}
          onComplete={handleTaskComplete}
        />
      )}
    </>
  );
};

export default SyncModal;
