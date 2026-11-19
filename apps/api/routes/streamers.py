"""
Streamer management API endpoints.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.database import get_db, AsyncSessionLocal
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
        streamer.display_name = payload.display_name.strip()
    if payload.channel_id is not None:
        streamer.channel_id = payload.channel_id.strip()
    if payload.channel_url is not None:
        streamer.channel_url = payload.channel_url.strip()
    if payload.platform is not None:
        streamer.platform = payload.platform.strip()
    if payload.avatar_url is not None:
        streamer.avatar_url = payload.avatar_url.strip() if payload.avatar_url else None
    if payload.is_monitored is not None:
        streamer.is_monitored = payload.is_monitored

    db.add(AuditEvent(
        actor=user.username,
        action="update_streamer",
        target_type="streamer",
        target_id=str(streamer_id),
        details_json={
            "display_name": streamer.display_name,
            "channel_id": streamer.channel_id,
            "platform": streamer.platform
        }
    ))

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


@router.post("/{streamer_id}/toggle-recording", response_model=StreamerResponse)
async def toggle_streamer_recording(
    streamer_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    """Toggle auto-recording ON/OFF for a streamer. If toggled off, any running capture process is terminated immediately."""
    stmt = select(Streamer).options(selectinload(Streamer.permissions)).where(Streamer.id == streamer_id)
    streamer = (await db.execute(stmt)).scalar_one_or_none()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    streamer.is_monitored = not streamer.is_monitored

    from workers.capture_worker import capture_worker
    if not streamer.is_monitored:
        # Pause recording: stop active capture process and close session to save disk space
        await capture_worker.stop_capture_session(db, streamer)
    else:
        # Resume recording: check if streamer is live right now, and if so start capturing
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
        if live_info["is_live"]:
            await capture_worker.start_capture_session(db, streamer)

    db.add(AuditEvent(
        actor=user.username,
        action="toggle_streamer_recording",
        target_type="streamer",
        target_id=str(streamer_id),
        details_json={"display_name": streamer.display_name, "is_monitored": streamer.is_monitored}
    ))

    await db.commit()
    await db.refresh(streamer)
    return streamer


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


async def _run_capture_pipeline_bg(streamer_id: int, duration: int):
    """Background task to capture, transcribe, score, and render clip without blocking API response."""
    logging.info(f"Background capture started for streamer_id={streamer_id} (duration={duration}s)")
    async with AsyncSessionLocal() as db:
        stmt = select(Streamer).where(Streamer.id == streamer_id)
        streamer = (await db.execute(stmt)).scalar_one_or_none()
        if not streamer:
            logging.error(f"Streamer {streamer_id} not found in background capture")
            return

        from workers.capture_worker import capture_worker
        from workers.transcription_worker import transcription_worker
        from workers.candidate_worker import candidate_worker
        from workers.render_worker import render_worker
        from workers.storage_worker import storage_worker
        from packages.shared.config import settings

        try:
            # 1. Capture slice
            segment = await capture_worker.capture_sample_now(db, streamer, duration_seconds=duration)
            if not segment:
                logging.error(f"Failed to capture slice for {streamer.display_name}")
                return

            # 2. Transcribe
            transcript = await transcription_worker.process_segment(segment.id)
            if not transcript:
                logging.error(f"Audio transcription failed for segment {segment.id}")
                return

            # 3. Score for virality (strictly gated by settings.VIRAL_SCORE_THRESHOLD)
            candidates = await candidate_worker.process_segment_candidates(segment.id)
            logging.info(f"Groq evaluated segment {segment.id}: {len(candidates)} candidates scored >= {settings.VIRAL_SCORE_THRESHOLD}")

            # 4. Render viral clips
            for cand in candidates:
                if cand.score >= settings.VIRAL_SCORE_THRESHOLD:
                    clip = await render_worker.render_candidate_to_clip(cand.id)
                    if clip:
                        await storage_worker.upload_clip_to_r2(clip.id)
                        logging.info(f"Successfully rendered viral clip {clip.id}: '{clip.title}'")
        except Exception as e:
            logging.exception(f"Error in background capture for {streamer.display_name}: {e}")


@router.post("/{streamer_id}/capture-now", status_code=status.HTTP_202_ACCEPTED)
async def trigger_instant_capture(
    streamer_id: int,
    duration: int = 60,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    """
    On-demand capture test (Asynchronous): starts recording a live stream slice in the background,
    returning 202 Accepted immediately so reverse proxies (Caddy/Nginx) never timeout.
    """
    stmt = select(Streamer).where(Streamer.id == streamer_id)
    streamer = (await db.execute(stmt)).scalar_one_or_none()
    if not streamer:
        raise HTTPException(status_code=404, detail="Streamer not found")

    from packages.shared.config import settings

    # Launch background capture task
    asyncio.create_task(_run_capture_pipeline_bg(streamer.id, duration))

    return {
        "status": "processing",
        "message": f"Capture started for {streamer.display_name}. Recording {duration}s slice in background. Clip will appear in Review when done.",
        "streamer": streamer.display_name,
        "duration_seconds": duration,
        "viral_threshold_used": settings.VIRAL_SCORE_THRESHOLD
    }
