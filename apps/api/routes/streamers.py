"""
Streamer management API endpoints.
"""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.database import get_db
from packages.shared.models import Streamer, CreatorPermission, AuditEvent, User
from packages.shared.enums import StreamerStatus, PermissionStatus
from packages.shared.schemas import StreamerCreate, StreamerUpdate, StreamerResponse
from packages.shared.platforms import check_streamer_live
from apps.api.auth import require_current_user

router = APIRouter(prefix="/api/streamers", tags=["streamers"])


@router.get("", response_model=List[StreamerResponse])
async def list_streamers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(Streamer).options(selectinload(Streamer.permissions)).order_by(Streamer.id.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=StreamerResponse, status_code=status.HTTP_201_CREATED)
async def create_streamer(
    payload: StreamerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    # Check for existing channel_id on same platform
    stmt = select(Streamer).where(
        (Streamer.platform == payload.platform.value) & (Streamer.channel_id == payload.channel_id)
    )
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Streamer channel already registered")

    streamer = Streamer(
        platform=payload.platform.value,
        channel_id=payload.channel_id,
        channel_url=payload.channel_url,
        display_name=payload.display_name,
        avatar_url=payload.avatar_url,
        is_monitored=payload.is_monitored,
        live_status=StreamerStatus.OFFLINE.value,
    )
    db.add(streamer)
    await db.flush()

    # Create associated permission record
    perm_status = payload.permission.permission_status.value if payload.permission else PermissionStatus.PENDING.value
    auth_by = payload.permission.authorized_by if payload.permission else None
    lic_url = payload.permission.license_url if payload.permission else None
    notes = payload.permission.notes if payload.permission else None
    valid_until = payload.permission.valid_until if payload.permission else None

    permission = CreatorPermission(
        streamer_id=streamer.id,
        permission_status=perm_status,
        authorized_by=auth_by,
        license_url=lic_url,
        notes=notes,
        valid_until=valid_until,
    )
    db.add(permission)

    # Log audit event
    audit = AuditEvent(
        actor=user.username,
        action="create_streamer",
        target_type="streamer",
        target_id=str(streamer.id),
        details_json={
            "display_name": streamer.display_name,
            "platform": streamer.platform,
            "channel_id": streamer.channel_id,
            "permission_status": perm_status,
        }
    )
    db.add(audit)

    await db.commit()
    # Reload with permissions relationship
    stmt = select(Streamer).options(selectinload(Streamer.permissions)).where(Streamer.id == streamer.id)
    streamer_reloaded = (await db.execute(stmt)).scalar_one()
    return streamer_reloaded


@router.get("/{streamer_id}", response_model=StreamerResponse)
async def get_streamer(
    streamer_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(Streamer).options(selectinload(Streamer.permissions)).where(Streamer.id == streamer_id)
    streamer = (await db.execute(stmt)).scalar_one_or_none()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")
    return streamer


@router.patch("/{streamer_id}", response_model=StreamerResponse)
async def update_streamer(
    streamer_id: int,
    payload: StreamerUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(Streamer).options(selectinload(Streamer.permissions)).where(Streamer.id == streamer_id)
    streamer = (await db.execute(stmt)).scalar_one_or_none()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    if payload.display_name is not None:
        streamer.display_name = payload.display_name
    if payload.channel_url is not None:
        streamer.channel_url = payload.channel_url
    if payload.avatar_url is not None:
        streamer.avatar_url = payload.avatar_url
    if payload.is_monitored is not None:
        streamer.is_monitored = payload.is_monitored

    await db.commit()
    await db.refresh(streamer)
    return streamer


@router.delete("/{streamer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_streamer(
    streamer_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(Streamer).where(Streamer.id == streamer_id)
    streamer = (await db.execute(stmt)).scalar_one_or_none()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    db.add(AuditEvent(
        actor=user.username,
        action="delete_streamer",
        target_type="streamer",
        target_id=str(streamer_id),
        details_json={"display_name": streamer.display_name}
    ))
    await db.delete(streamer)
    await db.commit()


@router.post("/{streamer_id}/check-live", response_model=StreamerResponse)
async def trigger_live_check(
    streamer_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(Streamer).options(selectinload(Streamer.permissions)).where(Streamer.id == streamer_id)
    streamer = (await db.execute(stmt)).scalar_one_or_none()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    live_info = await check_streamer_live(
        platform=streamer.platform,
        channel_id=streamer.channel_id,
        channel_url=streamer.channel_url
    )

    streamer.live_status = StreamerStatus.LIVE.value if live_info["is_live"] else StreamerStatus.OFFLINE.value
    streamer.stream_title = live_info.get("title")
    streamer.game_name = live_info.get("game")
    streamer.viewer_count = live_info.get("viewers", 0)
    streamer.last_checked_at = datetime.now(timezone.utc)

    # If stream is live, ensure capture session is started
    if live_info["is_live"]:
        from workers.capture_worker import capture_worker
        if streamer.id not in capture_worker.active_processes:
            await capture_worker.start_capture_session(db, streamer)

    await db.commit()
    await db.refresh(streamer)
    return streamer


@router.post("/{streamer_id}/capture-now")
async def trigger_instant_capture(
    streamer_id: int,
    duration: int = 60,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    """
    On-demand capture test: records an immediate slice (default 60s) of the live stream,
    transcribes it, runs the strict virality filter, and renders a split-screen vertical clip.
    """
    stmt = select(Streamer).where(Streamer.id == streamer_id)
    streamer = (await db.execute(stmt)).scalar_one_or_none()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    from workers.capture_worker import capture_worker
    from workers.transcription_worker import transcription_worker
    from workers.candidate_worker import candidate_worker
    from workers.render_worker import render_worker
    from workers.storage_worker import storage_worker
    from packages.shared.config import settings

    # 1. Capture slice
    segment = await capture_worker.capture_sample_now(db, streamer, duration_seconds=duration)
    if not segment:
        raise HTTPException(status_code=500, detail="Failed to capture stream slice. Please verify stream is live.")

    # 2. Transcribe
    transcript = await transcription_worker.process_segment(segment.id)
    if not transcript:
        raise HTTPException(status_code=500, detail="Audio transcription failed.")

    # 3. Score for virality (filtered by settings.VIRAL_SCORE_THRESHOLD)
    candidates = await candidate_worker.process_segment_candidates(segment.id)

    # 4. Render viral clips
    rendered_clips = []
    for cand in candidates:
        if cand.score >= settings.VIRAL_SCORE_THRESHOLD:
            clip = await render_worker.render_candidate_to_clip(cand.id)
            if clip:
                await storage_worker.upload_clip_to_r2(clip.id)
                rendered_clips.append(clip.id)

    return {
        "status": "success",
        "streamer": streamer.display_name,
        "segment_id": segment.id,
        "duration_seconds": duration,
        "transcribed_text_preview": transcript.text[:120],
        "viral_candidates_count": len(candidates),
        "clips_rendered_count": len(rendered_clips),
        "clip_ids": rendered_clips,
        "viral_threshold_used": settings.VIRAL_SCORE_THRESHOLD
    }
