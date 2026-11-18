"""
System metrics, cost estimation, and usage overview endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.database import get_db
from packages.shared.models import Streamer, Clip, UsageRecord, User
from packages.shared.enums import StreamerStatus, ApprovalStatus, PublishStatus, MetricType
from packages.shared.schemas import MetricSummaryResponse
from packages.shared.storage import storage_manager
from apps.api.auth import require_current_user

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/summary", response_model=MetricSummaryResponse)
async def get_metrics_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    # Monitored streamers count
    total_streamers = await db.scalar(select(func.count(Streamer.id)).where(Streamer.is_monitored == True)) or 0
    active_live = await db.scalar(select(func.count(Streamer.id)).where(Streamer.live_status == StreamerStatus.LIVE.value)) or 0

    # Clips ready and published
    clips_ready = await db.scalar(select(func.count(Clip.id)).where(Clip.approval_status == ApprovalStatus.PENDING_REVIEW.value)) or 0
    clips_published = await db.scalar(select(func.count(Clip.id)).where(Clip.approval_status == ApprovalStatus.APPROVED.value)) or 0

    # Storage in GB
    r2_used, _ = storage_manager.get_r2_usage()
    scratch_used, _ = storage_manager.get_scratch_usage()

    # Sum usage records
    deepgram_seconds = await db.scalar(
        select(func.sum(UsageRecord.count_or_value)).where(UsageRecord.metric_type == MetricType.TRANSCRIPTION_SECONDS.value)
    ) or 0.0

    groq_prompt_tokens = await db.scalar(
        select(func.sum(UsageRecord.count_or_value)).where(UsageRecord.metric_type == MetricType.GROQ_PROMPT_TOKENS.value)
    ) or 0.0

    groq_completion_tokens = await db.scalar(
        select(func.sum(UsageRecord.count_or_value)).where(UsageRecord.metric_type == MetricType.GROQ_COMPLETION_TOKENS.value)
    ) or 0.0

    bandwidth_bytes = await db.scalar(
        select(func.sum(UsageRecord.count_or_value)).where(UsageRecord.metric_type == MetricType.STREAM_BANDWIDTH_BYTES.value)
    ) or 0.0

    return MetricSummaryResponse(
        total_streamers_monitored=total_streamers,
        active_live_streams=active_live,
        total_clips_ready=clips_ready,
        total_clips_published=clips_published,
        r2_storage_gb=round(r2_used / (1024 ** 3), 3),
        scratch_storage_gb=round(scratch_used / (1024 ** 3), 3),
        estimated_api_usage={
            "deepgram_minutes": round(deepgram_seconds / 60.0, 1),
            "groq_prompt_tokens": int(groq_prompt_tokens),
            "groq_completion_tokens": int(groq_completion_tokens),
            "bandwidth_gb": round(bandwidth_bytes / (1024 ** 3), 2),
        }
    )
