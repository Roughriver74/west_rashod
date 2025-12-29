import apiClient from './client'

export interface SyncSettings {
  id: number
  auto_sync_enabled: boolean
  sync_interval_hours: number | null
  sync_time_hour: number | null
  sync_time_minute: number | null
  auto_classify: boolean
  sync_days_back: number
  auto_sync_expenses_enabled: boolean
  sync_expenses_interval_hours: number
  // FTP import settings
  ftp_import_enabled: boolean
  ftp_import_interval_hours: number
  ftp_import_time_hour: number | null
  ftp_import_time_minute: number
  ftp_import_clear_existing: boolean
  // Last FTP import info
  last_ftp_import_started_at: string | null
  last_ftp_import_completed_at: string | null
  last_ftp_import_status: 'SUCCESS' | 'FAILED' | 'IN_PROGRESS' | null
  last_ftp_import_message: string | null
  // Last sync info
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
  auto_sync_expenses_enabled?: boolean
  sync_expenses_interval_hours?: number
  // FTP import settings
  ftp_import_enabled?: boolean
  ftp_import_interval_hours?: number
  ftp_import_time_hour?: number | null
  ftp_import_time_minute?: number
  ftp_import_clear_existing?: boolean
}

export interface TriggerSyncResponse {
  success: boolean
  message: string
  task_id: string
}

export interface TaskStatusResponse {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  processed: number
  total: number
  message: string
  result: any
  error: string | null
  created_at: string | null
  started_at: string | null
  completed_at: string | null
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

export const refreshSyncStatus = async (): Promise<{ success: boolean; message: string; status?: string }> => {
  const response = await apiClient.post('/sync-settings/refresh-status')
  return response.data
}

export const triggerFtpImport = async (): Promise<TriggerSyncResponse> => {
  const response = await apiClient.post('/sync-settings/trigger-ftp-import')
  return response.data
}

export const refreshFtpStatus = async (): Promise<{ success: boolean; message: string; status?: string }> => {
  const response = await apiClient.post('/sync-settings/refresh-ftp-status')
  return response.data
}

const syncSettingsApi = {
  getSettings,
  updateSettings,
  triggerSyncNow,
  getTaskStatus,
  refreshSyncStatus,
  triggerFtpImport,
  refreshFtpStatus,
}

export default syncSettingsApi