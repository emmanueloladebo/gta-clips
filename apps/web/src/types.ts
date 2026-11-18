export interface Streamer {
  id: number;
  platform: 'twitch' | 'youtube' | 'kick';
  channel_id: string;
  channel_url: string;
  display_name: string;
  avatar_url?: string;
  is_monitored: boolean;
  live_status: 'offline' | 'live' | 'unknown';
  stream_title?: string;
  game_name?: string;
  viewer_count: number;
  last_checked_at?: string;
  created_at: string;
  permissions: CreatorPermission[];
}

export interface CreatorPermission {
  id: number;
  streamer_id: number;
  permission_status: 'granted' | 'pending' | 'denied' | 'revoked';
  authorized_by?: string;
  license_url?: string;
  notes?: string;
  valid_until?: string;
  created_at: string;
  updated_at: string;
}

export interface Clip {
  id: number;
  candidate_id?: number;
  streamer_id: number;
  title: string;
  description?: string;
  tags?: string;
  portrait_video_path?: string;
  thumbnail_path?: string;
  duration_seconds: number;
  r2_key?: string;
  r2_thumbnail_key?: string;
  r2_url?: string;
  r2_thumbnail_url?: string;
  file_size_bytes: number;
  resolution: string;
  aspect_ratio: string;
  approval_status: 'pending_review' | 'approved' | 'rejected' | 'published';
  auto_post_eligible: boolean;
  created_at: string;
  expires_at: string;
}

export interface Candidate {
  id: number;
  segment_id: number;
  start_second: number;
  end_second: number;
  duration_seconds: number;
  score: number;
  excitement_score: number;
  clarity_score: number;
  hook_summary: string;
  why_highlight: string;
  evidence_quote: string;
  safety_flags?: string[];
  visual_score?: number;
  visual_description?: string;
  status: string;
  created_at: string;
}

export interface DestinationAccount {
  id: number;
  platform: string;
  account_name: string;
  external_account_id: string;
  is_active: boolean;
  auto_post_enabled: boolean;
  created_at: string;
}

export interface PublishJob {
  id: number;
  clip_id: number;
  destination_account_id: number;
  platform: string;
  status: 'pending' | 'queued' | 'submitted' | 'published' | 'failed';
  idempotency_key: string;
  external_post_id?: string;
  scheduled_at?: string;
  published_at?: string;
  error_message?: string;
  retry_count: number;
  created_at: string;
}

export interface StorageUsage {
  r2_used_bytes: number;
  r2_soft_limit_bytes: number;
  r2_hard_limit_bytes: number;
  r2_soft_limit_exceeded: boolean;
  r2_hard_limit_exceeded: boolean;
  r2_object_count: number;
  scratch_used_bytes: number;
  scratch_limit_bytes: number;
  scratch_limit_exceeded: boolean;
  media_ttl_hours: number;
}

export interface SystemMetrics {
  total_streamers_monitored: number;
  active_live_streams: number;
  total_clips_ready: number;
  total_clips_published: number;
  r2_storage_gb: number;
  scratch_storage_gb: number;
  estimated_api_usage: {
    deepgram_minutes: number;
    groq_prompt_tokens: number;
    groq_completion_tokens: number;
    bandwidth_gb: number;
  };
}

export interface HealthStatus {
  status: string;
  environment: string;
  database_connected: boolean;
  storage_r2_healthy: boolean;
  scratch_disk_healthy: boolean;
  workers_active: number;
  auto_post_enabled: boolean;
  blockers: string[];
}
