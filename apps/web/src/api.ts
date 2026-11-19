import {
  Streamer, Clip, Candidate, DestinationAccount,
  PublishJob, StorageUsage, SystemMetrics, HealthStatus
} from './types';

const API_BASE = '/api';

export function getAuthToken(): string | null {
  return localStorage.getItem('gta6_auth_token');
}

export function setAuthToken(token: string): void {
  localStorage.setItem('gta6_auth_token', token);
}

export function removeAuthToken(): void {
  localStorage.removeItem('gta6_auth_token');
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'API request failed');
  }

  return res.json();
}

export const api = {
  // Auth
  login: async (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
    if (!res.ok) throw new Error('Invalid login');
    const data = await res.json();
    setAuthToken(data.access_token);
    return data;
  },

  getMe: () => request<any>('/auth/me'),

  // Streamers
  getStreamers: () => request<Streamer[]>('/streamers'),
  addStreamer: (data: Partial<Streamer> & { permission?: any }) =>
    request<Streamer>('/streamers', { method: 'POST', body: JSON.stringify(data) }),
  checkStreamerLive: (id: number) =>
    request<Streamer>(`/streamers/${id}/check-live`, { method: 'POST' }),
  triggerInstantCapture: (id: number, duration: number = 60) =>
    request<any>(`/streamers/${id}/capture-now?duration=${duration}`, { method: 'POST' }),
  deleteStreamer: (id: number) =>
    request<void>(`/streamers/${id}`, { method: 'DELETE' }),

  // Permissions
  updatePermission: (id: number, data: any) =>
    request<any>(`/permissions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Candidates & Clips
  getCandidates: () => request<Candidate[]>('/candidates'),
  getClips: (status?: string) =>
    request<Clip[]>(`/clips${status ? `?approval_status=${status}` : ''}`),
  reviewClip: (id: number, action: 'approve' | 'reject', customMeta?: any) =>
    request<Clip>(`/clips/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ action, ...customMeta }),
    }),
  reRenderClip: (id: number, headline: string, caption?: string, tags?: string) =>
    request<Clip>(`/clips/${id}/re-render`, {
      method: 'POST',
      body: JSON.stringify({ headline, caption, tags }),
    }),

  // Publishing
  getDestinations: () => request<DestinationAccount[]>('/publishing/destinations'),
  syncZernioDestinations: () =>
    request<DestinationAccount[]>('/publishing/destinations/sync', { method: 'POST' }),
  addDestination: (data: any) =>
    request<DestinationAccount>('/publishing/destinations', { method: 'POST', body: JSON.stringify(data) }),
  deleteDestination: (id: number) =>
    request<void>(`/publishing/destinations/${id}`, { method: 'DELETE' }),
  getPublishJobs: () => request<PublishJob[]>('/publishing/jobs'),
  publishClip: (clip_id: number, destination_account_id: number) =>
    request<PublishJob>('/publishing/publish', {
      method: 'POST',
      body: JSON.stringify({ clip_id, destination_account_id }),
    }),
  retryPublishJob: (id: number) =>
    request<PublishJob>(`/publishing/jobs/${id}/retry`, { method: 'POST' }),
  getAutoPostStatus: () => request<{ auto_post_enabled: boolean; mode: string }>('/publishing/auto-post-status'),

  // Storage & Health
  getStorageUsage: () => request<StorageUsage>('/storage/usage'),
  triggerCleanup: () => request<any>('/storage/cleanup', { method: 'POST' }),
  getMetrics: () => request<SystemMetrics>('/metrics/summary'),
  getHealth: () => request<HealthStatus>('/health'),
};
