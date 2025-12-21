import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1';

export interface SyncSettings {
  id: number;
  auto_sync_enabled: boolean;
  sync_interval_hours: number;
  sync_time_hour: number | null;
  sync_time_minute: number;
  auto_classify: boolean;
  sync_days_back: number;
  last_sync_started_at: string | null;
  last_sync_completed_at: string | null;
  last_sync_status: string | null;
  last_sync_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface SyncSettingsUpdate {
  auto_sync_enabled?: boolean;
  sync_interval_hours?: number;
  sync_time_hour?: number | null;
  sync_time_minute?: number;
  auto_classify?: boolean;
  sync_days_back?: number;
}

export interface TriggerSyncResponse {
  success: boolean;
  message: string;
  task_id: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string;
  result: any;
  traceback: string | null;
}

const syncSettingsApi = {
  // Get current sync settings
  getSettings: async (): Promise<SyncSettings> => {
    const response = await axios.get(`${API_URL}/sync-settings`);
    return response.data;
  },

  // Update sync settings
  updateSettings: async (settings: SyncSettingsUpdate): Promise<SyncSettings> => {
    const response = await axios.put(`${API_URL}/sync-settings`, settings);
    return response.data;
  },

  // Trigger sync manually
  triggerSyncNow: async (): Promise<TriggerSyncResponse> => {
    const response = await axios.post(`${API_URL}/sync-settings/trigger-now`);
    return response.data;
  },

  // Get task status
  getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    const response = await axios.get(`${API_URL}/sync-settings/task-status/${taskId}`);
    return response.data;
  },
};

export default syncSettingsApi;
