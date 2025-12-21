import apiClient from './client'

export interface SyncSettings {
  id: number
  auto_sync_enabled: boolean
  sync_interval_hours: number | null
  sync_time_hour: number | null
  sync_time_minute: number | null
  auto_classify: boolean
  sync_days_back: number
  last_sync_started_at: string | null
  last_sync_completed_at: string | null
  last_sync_status: 'SUCCESS' | 'FAILED' | 'IN_PROGRESS' | null
  last_sync_message: string | null
  created_at: string
  updated_at: string
}

export interface SyncSettingsUpdate {
  auto_sync_enabled?: boolean
  sync_interval_hours?: number | null
  sync_time_hour?: number | null
  sync_time_minute?: number | null
  auto_classify?: boolean
  sync_days_back?: number
}

export interface TriggerSyncResponse {
  success: boolean
  message: string
  task_id: string
}

export interface TaskStatusResponse {
  task_id: string
  status: string
  result: any
  traceback: string | null
}

export const getSettings = async (): Promise<SyncSettings> => {
  const response = await apiClient.get('/sync-settings')
  return response.data
}

export const updateSettings = async (data: SyncSettingsUpdate): Promise<SyncSettings> => {
  const response = await apiClient.put('/sync-settings', data)
  return response.data
}

export const triggerSyncNow = async (): Promise<TriggerSyncResponse> => {
  const response = await apiClient.post('/sync-settings/trigger-now')
  return response.data
}

export const getTaskStatus = async (taskId: string): Promise<TaskStatusResponse> => {
  const response = await apiClient.get(`/sync-settings/task-status/${taskId}`)
  return response.data
}

const syncSettingsApi = {
  getSettings,
  updateSettings,
  triggerSyncNow,
  getTaskStatus,
}

export default syncSettingsApi