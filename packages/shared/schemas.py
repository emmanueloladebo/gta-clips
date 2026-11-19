"""
Pydantic Schemas for validation, API requests/responses, and AI contracts.
"""
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

from packages.shared.enums import (
    PlatformType, StreamerStatus, PermissionStatus, SessionStatus,
    SegmentStatus, CandidateStatus, ApprovalStatus, PublishStatus,
    PublishPlatform, StorageType, MetricType
)


# =====================
# Auth Schemas
# =====================
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# =====================
# Streamer & Permission Schemas
# =====================
class CreatorPermissionCreate(BaseModel):
    permission_status: PermissionStatus = PermissionStatus.PENDING
    authorized_by: Optional[str] = None
    license_url: Optional[str] = None
    notes: Optional[str] = None
    valid_until: Optional[datetime] = None


class CreatorPermissionUpdate(BaseModel):
    permission_status: Optional[PermissionStatus] = None
    authorized_by: Optional[str] = None
    license_url: Optional[str] = None
    notes: Optional[str] = None
    valid_until: Optional[datetime] = None


class CreatorPermissionResponse(BaseModel):
    id: int
    streamer_id: int
    permission_status: str
    authorized_by: Optional[str]
    license_url: Optional[str]
    notes: Optional[str]
    valid_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StreamerCreate(BaseModel):
    platform: PlatformType = PlatformType.TWITCH
    channel_id: str
    channel_url: str
    display_name: str
    avatar_url: Optional[str] = None
    is_monitored: bool = True
    permission: Optional[CreatorPermissionCreate] = None


class StreamerUpdate(BaseModel):
    display_name: Optional[str] = None
    channel_url: Optional[str] = None
    avatar_url: Optional[str] = None
    is_monitored: Optional[bool] = None


class StreamerResponse(BaseModel):
    id: int
    platform: str
    channel_id: str
    channel_url: str
    display_name: str
    avatar_url: Optional[str]
    is_monitored: bool
    live_status: str
    stream_title: Optional[str]
    game_name: Optional[str]
    viewer_count: int
    last_checked_at: Optional[datetime]
    created_at: datetime
    permissions: List[CreatorPermissionResponse] = []

    model_config = ConfigDict(from_attributes=True)


# =====================
# Sessions & Segments
# =====================
class SegmentResponse(BaseModel):
    id: int
    session_id: int
    sequence_num: int
    file_path: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: float
    status: str
    disk_bytes: int
    error_message: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StreamSessionResponse(BaseModel):
    id: int
    streamer_id: int
    platform_session_id: Optional[str]
    title: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    status: str
    total_segments: int
    total_duration_seconds: float
    segments: List[SegmentResponse] = []

    model_config = ConfigDict(from_attributes=True)


# =====================
# Transcript & Scoring Schemas
# =====================
class TranscriptWord(BaseModel):
    word: str
    start: float
    end: float
    confidence: float


class TranscriptResponse(BaseModel):
    id: int
    segment_id: int
    text: str
    words_json: Optional[List[Dict[str, Any]]] = None
    sound_events_json: Optional[List[Dict[str, Any]]] = None
    provider: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HighlightCandidateScoring(BaseModel):
    """Schema expected back from Groq LLM scoring."""
    hook_summary: str = Field(..., description="Short catchy hook for the clip, 5-10 words")
    headline: Optional[str] = Field(default=None, description="Punchy headline banner text for split-screen video, 3-7 words")
    caption: Optional[str] = Field(default=None, description="Engaging, natural TikTok caption (1-2 sentences)")
    hashtags: Optional[List[str]] = Field(default_factory=lambda: ["#gta", "#gta6", "#gaming", "#gtaclips", "#viral"], description="Max 5 lowercase trending GTA 6 hashtags")
    facecam_position: Optional[str] = Field(default="top_right", description="Quadrant of streamer facecam: top_right, top_left, bottom_left, bottom_right, or center_zoom")
    start_second: float = Field(..., description="Start timestamp relative to segment in seconds")
    end_second: float = Field(..., description="End timestamp relative to segment in seconds")
    duration_seconds: float = Field(..., description="Total length between 15 and 60 seconds")
    score: float = Field(..., ge=0, le=100, description="Overall highlight quality score from 0 to 100")
    excitement_score: float = Field(..., ge=0, le=100, description="Excitement/reaction intensity")
    clarity_score: float = Field(..., ge=0, le=100, description="Speech and context clarity")
    why_highlight: str = Field(..., description="Natural explanation of why this moment is fun or intense")
    evidence_quote: str = Field(..., description="Exact spoken words from transcript supporting the highlight")
    safety_flags: List[str] = Field(default=[], description="Any safety warnings, e.g. 'dmca_music', 'extreme_profanity'")
    visual_score: Optional[float] = Field(default=None, description="Visual action score if vision verified; null if text-only")
    visual_description: Optional[str] = Field(default=None, description="Visual description if vision verified; null if text-only")


class GroqScoringPayload(BaseModel):
    highlights: List[HighlightCandidateScoring] = []


class CandidateResponse(BaseModel):
    id: int
    segment_id: int
    start_second: float
    end_second: float
    duration_seconds: float
    score: float
    excitement_score: float
    clarity_score: float
    hook_summary: str
    why_highlight: str
    evidence_quote: str
    safety_flags: Optional[Any]
    visual_score: Optional[float]
    visual_description: Optional[str]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================
# Clips & Approval
# =====================
class ClipApprovalRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    custom_title: Optional[str] = None
    custom_description: Optional[str] = None
    custom_tags: Optional[str] = None


class ClipReRenderRequest(BaseModel):
    headline: str
    caption: Optional[str] = None
    tags: Optional[str] = None


class ClipUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    approval_status: Optional[ApprovalStatus] = None


class ClipResponse(BaseModel):
    id: int
    candidate_id: Optional[int]
    streamer_id: int
    title: str
    description: Optional[str]
    tags: Optional[str]
    portrait_video_path: Optional[str]
    thumbnail_path: Optional[str]
    duration_seconds: float
    r2_key: Optional[str]
    r2_thumbnail_key: Optional[str]
    r2_url: Optional[str]
    r2_thumbnail_url: Optional[str]
    file_size_bytes: int
    resolution: str
    aspect_ratio: str
    approval_status: str
    auto_post_eligible: bool
    created_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================
# Publishing & Destinations
# =====================
class DestinationAccountCreate(BaseModel):
    platform: PublishPlatform
    account_name: str
    external_account_id: str
    is_active: bool = True
    auto_post_enabled: bool = False
    auth_metadata: Optional[Dict[str, Any]] = None


class DestinationAccountResponse(BaseModel):
    id: int
    platform: str
    account_name: str
    external_account_id: str
    is_active: bool
    auto_post_enabled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublishJobCreate(BaseModel):
    clip_id: int
    destination_account_id: int
    scheduled_at: Optional[datetime] = None


class PublishJobResponse(BaseModel):
    id: int
    clip_id: int
    destination_account_id: int
    platform: str
    status: str
    idempotency_key: str
    external_post_id: Optional[str]
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================
# Storage & Metrics
# =====================
class StorageUsageResponse(BaseModel):
    r2_used_bytes: int
    r2_soft_limit_bytes: int
    r2_hard_limit_bytes: int
    r2_soft_limit_exceeded: bool
    r2_hard_limit_exceeded: bool
    r2_object_count: int
    scratch_used_bytes: int
    scratch_limit_bytes: int
    scratch_limit_exceeded: bool
    media_ttl_hours: int


class MetricSummaryResponse(BaseModel):
    total_streamers_monitored: int
    active_live_streams: int
    total_clips_ready: int
    total_clips_published: int
    r2_storage_gb: float
    scratch_storage_gb: float
    estimated_api_usage: Dict[str, Any]


class AuditEventResponse(BaseModel):
    id: int
    actor: str
    action: str
    target_type: str
    target_id: Optional[str]
    details_json: Optional[Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthStatusResponse(BaseModel):
    status: str
    environment: str
    database_connected: bool
    storage_r2_healthy: bool
    scratch_disk_healthy: bool
    workers_active: int
    auto_post_enabled: bool
    blockers: List[str] = []
