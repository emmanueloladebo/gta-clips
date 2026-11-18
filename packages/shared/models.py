"""
SQLAlchemy Async database models for the GTA 6 clipping platform.
"""
from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy import (
    String, Integer, BigInteger, Float, Boolean, Text, JSON, DateTime, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from packages.shared.enums import (
    PlatformType, StreamerStatus, PermissionStatus, SessionStatus,
    SegmentStatus, CandidateStatus, ApprovalStatus, PublishStatus,
    PublishPlatform, StorageType, StorageCategory, MetricType
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Streamer(Base):
    __tablename__ = "streamers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), default=PlatformType.TWITCH.value, index=True)
    channel_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    channel_url: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=True)
    live_status: Mapped[str] = mapped_column(String(32), default=StreamerStatus.OFFLINE.value, index=True)
    stream_title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    game_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    viewer_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    permissions: Mapped[List["CreatorPermission"]] = relationship("CreatorPermission", back_populates="streamer", cascade="all, delete-orphan")
    sessions: Mapped[List["StreamSession"]] = relationship("StreamSession", back_populates="streamer", cascade="all, delete-orphan")
    clips: Mapped[List["Clip"]] = relationship("Clip", back_populates="streamer", cascade="all, delete-orphan")


class CreatorPermission(Base):
    __tablename__ = "creator_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    streamer_id: Mapped[int] = mapped_column(Integer, ForeignKey("streamers.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_status: Mapped[str] = mapped_column(String(32), default=PermissionStatus.PENDING.value, index=True)
    authorized_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    license_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    streamer: Mapped["Streamer"] = relationship("Streamer", back_populates="permissions")


class StreamSession(Base):
    __tablename__ = "stream_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    streamer_id: Mapped[int] = mapped_column(Integer, ForeignKey("streamers.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=SessionStatus.ACTIVE.value, index=True)
    total_segments: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    streamer: Mapped["Streamer"] = relationship("Streamer", back_populates="sessions")
    segments: Mapped[List["Segment"]] = relationship("Segment", back_populates="session", cascade="all, delete-orphan")


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("stream_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_num: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default=SegmentStatus.RECORDING.value, index=True)
    disk_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped["StreamSession"] = relationship("StreamSession", back_populates="segments")
    transcript: Mapped[Optional["Transcript"]] = relationship("Transcript", back_populates="segment", uselist=False, cascade="all, delete-orphan")
    candidates: Mapped[List["Candidate"]] = relationship("Candidate", back_populates="segment", cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    segment_id: Mapped[int] = mapped_column(Integer, ForeignKey("segments.id", ondelete="CASCADE"), unique=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    words_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    sound_events_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    provider: Mapped[str] = mapped_column(String(64), default="deepgram")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    segment: Mapped["Segment"] = relationship("Segment", back_populates="transcript")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    segment_id: Mapped[int] = mapped_column(Integer, ForeignKey("segments.id", ondelete="CASCADE"), nullable=False, index=True)
    start_second: Mapped[float] = mapped_column(Float, nullable=False)
    end_second: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    excitement_score: Mapped[float] = mapped_column(Float, default=0.0)
    clarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    hook_summary: Mapped[str] = mapped_column(String(255), nullable=False)
    why_highlight: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_quote: Mapped[str] = mapped_column(Text, nullable=False)
    safety_flags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    visual_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    visual_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=CandidateStatus.DETECTED.value, index=True)
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    segment: Mapped["Segment"] = relationship("Segment", back_populates="candidates")
    clips: Mapped[List["Clip"]] = relationship("Clip", back_populates="candidate")


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True)
    streamer_id: Mapped[int] = mapped_column(Integer, ForeignKey("streamers.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    portrait_video_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    r2_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, index=True)
    r2_thumbnail_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    r2_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    r2_thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    resolution: Mapped[str] = mapped_column(String(32), default="1080x1920")
    aspect_ratio: Mapped[str] = mapped_column(String(16), default="9:16")
    approval_status: Mapped[str] = mapped_column(String(32), default=ApprovalStatus.PENDING_REVIEW.value, index=True)
    auto_post_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    candidate: Mapped[Optional["Candidate"]] = relationship("Candidate", back_populates="clips")
    streamer: Mapped["Streamer"] = relationship("Streamer", back_populates="clips")
    publish_jobs: Mapped[List["PublishJob"]] = relationship("PublishJob", back_populates="clip", cascade="all, delete-orphan")


class DestinationAccount(Base):
    __tablename__ = "destination_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    account_name: Mapped[str] = mapped_column(String(128), nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_post_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_metadata: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    publish_jobs: Mapped[List["PublishJob"]] = relationship("PublishJob", back_populates="destination_account")


class PublishJob(Base):
    __tablename__ = "publish_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clip_id: Mapped[int] = mapped_column(Integer, ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, index=True)
    destination_account_id: Mapped[int] = mapped_column(Integer, ForeignKey("destination_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=PublishStatus.PENDING.value, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    external_post_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    clip: Mapped["Clip"] = relationship("Clip", back_populates="publish_jobs")
    destination_account: Mapped["DestinationAccount"] = relationship("DestinationAccount", back_populates="publish_jobs")


class StorageObject(Base):
    __tablename__ = "storage_objects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    storage_type: Mapped[str] = mapped_column(String(32), default=StorageType.SCRATCH.value, index=True)
    file_path_or_key: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    category: Mapped[str] = mapped_column(String(32), default=StorageCategory.TEMP.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    count_or_value: Mapped[float] = mapped_column(Float, nullable=False)
    streamer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("streamers.id", ondelete="SET NULL"), nullable=True)
    metadata_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(128), default="system")
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    details_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
