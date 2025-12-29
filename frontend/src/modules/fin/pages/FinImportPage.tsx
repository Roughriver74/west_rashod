/**
 * Fin Import Page - FTP Import management
 */
import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Progress, Table, Space, Typography, Checkbox, message, Tag, Alert } from 'antd';
import { CloudDownloadOutlined, StopOutlined, ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { triggerFTPImport, getFTPImportStatus, cancelFTPImport, getImportLogs } from '../api/finApi';

const { Title, Text, Paragraph } = Typography;

const FinImportPage: React.FC = () => {
  const [importing, setImporting] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [taskResult, setTaskResult] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [clearExisting, setClearExisting] = useState(true);

  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchLogs = async () => {
    setLogsLoading(true);
    try {
      const response = await getImportLogs({ limit: 50 });
      setLogs(response.items);
    } catch (error) {
      console.error('Error fetching logs:', error);
    } finally {
      setLogsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  const pollTaskStatus = async (id: string) => {
    try {
      const status = await getFTPImportStatus(id);
      setProgress(status.progress || 0);
      setStatusMessage(status.message || '');

      if (status.status === 'completed') {
        setImporting(false);
        setTaskResult(status.result);
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        message.success('Импорт завершён успешно');
        fetchLogs();
      } else if (status.status === 'failed') {
        setImporting(false);
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        message.error('Импорт завершился с ошибкой');
        fetchLogs();
      } else if (status.status === 'cancelled') {
        setImporting(false);
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        message.info('Импорт отменён');
        fetchLogs();
      }
    } catch (error) {
      console.error('Error polling task status:', error);
    }
  };

  const handleStartImport = async () => {
    try {
      setImporting(true);
      setProgress(0);
      setStatusMessage('Запуск импорта...');
      setTaskResult(null);

      const response = await triggerFTPImport(clearExisting);
      setTaskId(response.task_id);

      // Start polling
      pollingRef.current = setInterval(() => {
        pollTaskStatus(response.task_id);
      }, 1000);

    } catch (error: any) {
      setImporting(false);
      const errorDetail = error.response?.data?.detail || error.message;
      message.error('Ошибка запуска импорта: ' + errorDetail);
    }
  };

  const handleCancelImport = async () => {
    if (!taskId) return;

    try {
      await cancelFTPImport(taskId);
      message.info('Отправлен запрос на отмену');
    } catch (error: any) {
      const errorDetail = error.response?.data?.detail || error.message;
      message.error('Ошибка отмены: ' + errorDetail);
    }
  };

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'success':
        return <Tag color="green">Успешно</Tag>;
      case 'partial':
        return <Tag color="orange">Частично</Tag>;
      case 'failed':
        return <Tag color="red">Ошибка</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  const columns = [
    {
      title: 'Дата',
      dataIndex: 'import_date',
      key: 'import_date',
      width: 160,
      render: (val: string) => dayjs(val).format('DD.MM.YYYY HH:mm'),
    },
    {
      title: 'Файл',
      dataIndex: 'source_file',
      key: 'source_file',
      ellipsis: true,
    },
    {
      title: 'Таблица',
      dataIndex: 'table_name',
      key: 'table_name',
      width: 150,
    },
    {
      title: 'Вставлено',
      dataIndex: 'rows_inserted',
      key: 'rows_inserted',
      width: 100,
      align: 'right' as const,
    },
    {
      title: 'Обновлено',
      dataIndex: 'rows_updated',
      key: 'rows_updated',
      width: 100,
      align: 'right' as const,
    },
    {
      title: 'Ошибок',
      dataIndex: 'rows_failed',
      key: 'rows_failed',
      width: 80,
      align: 'right' as const,
      render: (val: number) => val > 0 ? <Text type="danger">{val}</Text> : val,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: getStatusTag,
    },
    {
      title: 'Время (сек)',
      dataIndex: 'processing_time_seconds',
      key: 'processing_time_seconds',
      width: 100,
      align: 'right' as const,
      render: (val: number) => val?.toFixed(1),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>FTP Импорт</Title>
      <Paragraph type="secondary">
        Загрузка данных из Excel файлов с FTP сервера
      </Paragraph>

      {/* Import Control Card */}
      <Card title="Управление импортом" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Checkbox
            checked={clearExisting}
            onChange={(e) => setClearExisting(e.target.checked)}
            disabled={importing}
          >
            Очистить существующие данные перед импортом
          </Checkbox>

          {clearExisting && (
            <Alert
              message="Внимание"
              description="Все существующие данные в таблицах fin_receipts, fin_expenses и fin_expense_details будут удалены. Ручные корректировки (fin_manual_adjustments) НЕ удаляются."
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          <Space>
            <Button
              type="primary"
              icon={<CloudDownloadOutlined />}
              onClick={handleStartImport}
              loading={importing}
              disabled={importing}
            >
              Запустить импорт
            </Button>
            {importing && (
              <Button
                danger
                icon={<StopOutlined />}
                onClick={handleCancelImport}
              >
                Отменить
              </Button>
            )}
          </Space>

          {importing && (
            <div style={{ marginTop: 16 }}>
              <Progress percent={progress} status="active" />
              <Text type="secondary">{statusMessage}</Text>
            </div>
          )}

          {taskResult && (
            <Alert
              message="Результат импорта"
              description={
                <div>
                  <p>Файлов скачано: {taskResult.files_downloaded}</p>
                  <p>Файлов обработано: {taskResult.files_processed}</p>
                  {taskResult.receipts && (
                    <p>Поступления: вставлено {taskResult.receipts.inserted}, обновлено {taskResult.receipts.updated}, ошибок {taskResult.receipts.failed}</p>
                  )}
                  {taskResult.expenses && (
                    <p>Списания: вставлено {taskResult.expenses.inserted}, обновлено {taskResult.expenses.updated}, ошибок {taskResult.expenses.failed}</p>
                  )}
                  {taskResult.details && (
                    <p>Расшифровки: вставлено {taskResult.details.inserted}, ошибок {taskResult.details.failed}</p>
                  )}
                </div>
              }
              type="success"
              showIcon
              closable
              onClose={() => setTaskResult(null)}
            />
          )}
        </Space>
      </Card>

      {/* Import Logs */}
      <Card
        title="Журнал импорта"
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchLogs} loading={logsLoading}>
            Обновить
          </Button>
        }
      >
        <Table
          dataSource={logs}
          columns={columns}
          rowKey="id"
          loading={logsLoading}
          pagination={{ pageSize: 20 }}
          scroll={{ x: 1000 }}
          size="small"
        />
      </Card>
    </div>
  );
};

export default FinImportPage;
