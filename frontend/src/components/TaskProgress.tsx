/**
 * Task Progress Component
 * Shows real-time progress of background tasks
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Modal, Progress, Typography, Space, Button, Tag, Descriptions, Alert } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { TaskInfo, TaskStatus, getTaskStatus, cancelTask, TaskWebSocket } from '../api/tasks';

const { Text } = Typography;

interface TaskProgressProps {
  taskId: string;
  title?: string;
  visible: boolean;
  onClose: () => void;
  onComplete?: (task: TaskInfo) => void;
  useWebSocket?: boolean;
  keepPollingWhenHidden?: boolean;
}

const statusConfig: Record<TaskStatus, { color: string; icon: React.ReactNode; text: string }> = {
  pending: { color: 'default', icon: <ClockCircleOutlined />, text: 'Ожидание' },
  running: { color: 'processing', icon: <LoadingOutlined />, text: 'Выполняется' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: 'Завершено' },
  failed: { color: 'error', icon: <CloseCircleOutlined />, text: 'Ошибка' },
  cancelled: { color: 'warning', icon: <StopOutlined />, text: 'Отменено' },
};

export const TaskProgress: React.FC<TaskProgressProps> = ({
  taskId,
  title = 'Выполнение задачи',
  visible,
  onClose,
  onComplete,
  useWebSocket = true,
  keepPollingWhenHidden = false,
}) => {
  const [task, setTask] = useState<TaskInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [taskNotFound, setTaskNotFound] = useState(false);

  // Fetch task status via polling (fallback)
  const fetchStatus = useCallback(async () => {
    try {
      const data = await getTaskStatus(taskId);
      setTask(data);
      setError(null);

      // Check if task is complete
      if (['completed', 'failed', 'cancelled'].includes(data.status)) {
        onComplete?.(data);
      }
    } catch (err: unknown) {
      // Проверяем 404 ошибку - задача не найдена (возможно сервер перезапускался)
      const axiosError = err as { response?: { status?: number } };
      if (axiosError?.response?.status === 404) {
        setTaskNotFound(true);
        setError('Задача не найдена. Возможно, сервер был перезапущен. Пожалуйста, запустите синхронизацию заново.');
        // Создаём фиктивную задачу с ошибкой для отображения
        setTask({
          task_id: taskId,
          task_type: 'unknown',
          status: 'failed' as TaskStatus,
          progress: 0,
          total: 0,
          processed: 0,
          message: 'Задача не найдена',
          error: 'Задача не найдена на сервере. Возможно, сервер был перезапущен.',
          metadata: {},
        });
      } else {
        setError('Не удалось получить статус задачи');
        console.error('Error fetching task status:', err);
      }
    } finally {
      setLoading(false);
    }
  }, [taskId, onComplete]);

  // WebSocket connection
  useEffect(() => {
    if ((!visible && !keepPollingWhenHidden) || !taskId || taskNotFound) return;

    let ws: TaskWebSocket | null = null;
    let pollInterval: ReturnType<typeof setInterval> | null = null;
    let isFinished = false;

    if (useWebSocket) {
      ws = new TaskWebSocket(
        taskId,
        (updatedTask) => {
          setTask(updatedTask);
          setLoading(false);
          setError(null);

          if (['completed', 'failed', 'cancelled'].includes(updatedTask.status)) {
            isFinished = true;
            onComplete?.(updatedTask);
            // Clear polling when task is finished
            if (pollInterval) {
              clearInterval(pollInterval);
            }
          }
        },
        () => {
          // On error, fall back to polling silently
          console.warn('WebSocket error, falling back to polling');
        }
      );
      ws.connect();
    }

    // Always set up polling as fallback
    fetchStatus();
    pollInterval = setInterval(async () => {
      if (!isFinished && !taskNotFound) {
        await fetchStatus();
      }
    }, 2000);

    return () => {
      ws?.disconnect();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [visible, taskId, useWebSocket, fetchStatus, onComplete, keepPollingWhenHidden, taskNotFound]);

  const handleCancel = async () => {
    if (!taskId) return;
    setCancelling(true);
    try {
      await cancelTask(taskId);
      fetchStatus();
    } catch (err) {
      setError('Не удалось отменить задачу');
    } finally {
      setCancelling(false);
    }
  };

  const isFinished = task && ['completed', 'failed', 'cancelled'].includes(task.status);
  const config = task ? statusConfig[task.status] : statusConfig.pending;

  return (
    <Modal
      title={
        <Space>
          {config.icon}
          <span>{title}</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={
        <Space>
          {!isFinished && task?.status === 'running' && (
            <Button danger onClick={handleCancel} loading={cancelling}>
              Отменить
            </Button>
          )}
          <Button type={isFinished ? 'primary' : 'default'} onClick={onClose}>
            {isFinished ? 'Закрыть' : 'Свернуть'}
          </Button>
        </Space>
      }
      maskClosable={false}
      width={500}
    >
      {loading && !task ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <LoadingOutlined style={{ fontSize: 32 }} />
          <Text style={{ display: 'block', marginTop: 16 }}>Загрузка...</Text>
        </div>
      ) : error && !task ? (
        <Alert type="error" message={error} />
      ) : task ? (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Status */}
          <div style={{ textAlign: 'center' }}>
            <Tag color={config.color} style={{ fontSize: 14, padding: '4px 12px' }}>
              {config.icon} {config.text}
            </Tag>
          </div>

          {/* Progress bar */}
          <Progress
            percent={task.progress}
            status={
              task.status === 'failed'
                ? 'exception'
                : task.status === 'completed'
                ? 'success'
                : 'active'
            }
            strokeColor={
              task.status === 'running'
                ? {
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }
                : undefined
            }
          />

          {/* Message */}
          {task.message && (
            <Text type="secondary" style={{ display: 'block', textAlign: 'center' }}>
              {task.message}
            </Text>
          )}

          {/* Stats */}
          {(task.processed > 0 || task.total > 0) && (
            <Descriptions size="small" column={2}>
              <Descriptions.Item label="Обработано">
                {task.processed} из {task.total}
              </Descriptions.Item>
              <Descriptions.Item label="Прогресс">{task.progress}%</Descriptions.Item>
            </Descriptions>
          )}

          {/* Error */}
          {task.error && <Alert type="error" message="Ошибка" description={task.error} />}

          {/* Result */}
          {task.status === 'completed' && task.result && (
            <Alert
              type="success"
              message="Результат"
              description={
                <Descriptions size="small" column={1}>
                  {Object.entries(task.result).map(([key, value]) => (
                    <Descriptions.Item key={key} label={key}>
                      {String(value)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              }
            />
          )}
        </Space>
      ) : null}
    </Modal>
  );
};

export default TaskProgress;
