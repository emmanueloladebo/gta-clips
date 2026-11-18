"""
Shared enums for GTA 6 cloud clipping platform.
"""
from enum import Enum


class PlatformType(str, Enum):
    TWITCH = "twitch"
    YOUTUBE = "youtube"
    KICK = "kick"


class StreamerStatus(str, Enum):
    OFFLINE = "offline"
    LIVE = "live"
    UNKNOWN = "unknown"


class PermissionStatus(str, Enum):
    GRANTED = "granted"
    PENDING = "pending"
    DENIED = "denied"
    REVOKED = "revoked"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"
    INTERRUPTED = "interrupted"


class SegmentStatus(str, Enum):
    RECORDING = "recording"
    RECORDED = "recorded"
    TRANSCRIBING = "transcribing"
    SCORED = "scored"
    RENDERED = "rendered"
    CLEANED = "cleaned"
    FAILED = "failed"


class CandidateStatus(str, Enum):
    DETECTED = "detected"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    RENDERED = "rendered"


class ApprovalStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class PublishStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    SUBMITTED = "submitted"
    PUBLISHED = "published"
    FAILED = "failed"


class PublishPlatform(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE_SHORTS = "youtube_shorts"
    INSTAGRAM_REELS = "instagram_reels"
    X = "x"


class StorageType(str, Enum):
    SCRATCH = "scratch"
    R2 = "r2"


class StorageCategory(str, Enum):
    SEGMENT = "segment"
    CLIP = "clip"
    THUMBNAIL = "thumbnail"
    TEMP = "temp"


class MetricType(str, Enum):
    STREAM_BANDWIDTH_BYTES = "stream_bandwidth_bytes"
    CAPTURE_SECONDS = "capture_seconds"
    TRANSCRIPTION_SECONDS = "transcription_seconds"
    GROQ_PROMPT_TOKENS = "groq_prompt_tokens"
    GROQ_COMPLETION_TOKENS = "groq_completion_tokens"
    R2_STORAGE_BYTES = "r2_storage_bytes"
    R2_EGRESS_BYTES = "r2_egress_bytes"
    RENDER_SECONDS = "render_seconds"
