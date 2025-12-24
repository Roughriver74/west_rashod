/**
 * Background Tasks API
 */
import api from './client';

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface TaskInfo {
  task_id: string;
  task_type: string;
  status: TaskStatus;
  progress: number;
  total: number;
  processed: number;
  message: string;
  result?: Record<string, unknown>;
  error?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  metadata: Record<string, unknown>;
}

export interface TaskListResponse {
  tasks: TaskInfo[];
  total: number;
}

export interface AsyncSyncRequest {
  date_from?: string;
  date_to?: string;
  auto_classify?: boolean;
}

export interface AsyncSyncResponse {
  task_id: string;
  message: string;
}

// Get task status
export const getTaskStatus = async (taskId: string): Promise<TaskInfo> => {
  const response = await api.get(`/tasks/${taskId}`);
  return response.data;
};

// List all tasks
export const listTasks = async (taskType?: string, limit = 20): Promise<TaskListResponse> => {
  const params: Record<string, unknown> = { limit };
  if (taskType) params.task_type = taskType;
  const response = await api.get('/tasks', { params });
  return response.data;
};

// Cancel a task
export const cancelTask = async (taskId: string): Promise<{ message: string }> => {
  const response = await api.post(`/tasks/${taskId}/cancel`);
  return response.data;
};

// Start async bank transactions sync
export const startAsyncBankTransactionsSync = async (
  request: AsyncSyncRequest
): Promise<AsyncSyncResponse> => {
  const response = await api.post('/sync-1c/bank-transactions/sync-async', request);
  return response.data;
};

// Start async contractors sync
export const startAsyncContractorsSync = async (): Promise<AsyncSyncResponse> => {
  const response = await api.post('/sync-1c/contractors/sync-async');
  return response.data;
};

// Start async organizations sync
export const startAsyncOrganizationsSync = async (): Promise<AsyncSyncResponse> => {
  const response = await api.post('/sync-1c/organizations/sync-async');
  return response.data;
};

// Start async categories sync
export const startAsyncCategoriesSync = async (): Promise<AsyncSyncResponse> => {
  const response = await api.post('/sync-1c/categories/sync-async');
  return response.data;
};

// Start full async sync (organizations + categories + transactions)
export const startAsyncFullSync = async (
  request: AsyncSyncRequest
): Promise<AsyncSyncResponse> => {
  const response = await api.post('/sync-1c/full/sync-async', request);
  return response.data;
};

// WebSocket connection for task updates
export class TaskWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private taskId: string;
  private onUpdate: (task: TaskInfo) => void;
  private onError?: (error: Event) => void;
  private onClose?: () => void;

  constructor(
    taskId: string,
    onUpdate: (task: TaskInfo) => void,
    onError?: (error: Event) => void,
    onClose?: () => void
  ) {
    this.taskId = taskId;
    this.onUpdate = onUpdate;
    this.onError = onError;
    this.onClose = onClose;
  }

  connect(): void {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8001';
    const wsUrl = `${protocol}//${host}/api/v1/ws/tasks/${this.taskId}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected for task:', this.taskId);
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'task_update' && message.data) {
          this.onUpdate(message.data as TaskInfo);
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.onError?.(error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed');
      this.onClose?.();

      // Try to reconnect
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
      }
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  sendPing(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send('ping');
    }
  }

  cancelTask(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'cancel' }));
    }
  }
}
