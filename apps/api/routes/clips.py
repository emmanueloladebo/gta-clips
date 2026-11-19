"""
Clip review, approval, and streaming endpoints.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import get_db
from packages.shared.models import Clip, Streamer, CreatorPermission, AuditEvent, User
from packages.shared.enums import ApprovalStatus, PermissionStatus
from packages.shared.schemas import ClipResponse, ClipUpdate, ClipApprovalRequest, ClipReRenderRequest
from packages.shared.storage import storage_manager
from apps.api.auth import require_current_user

router = APIRouter(prefix="/api/clips", tags=["clips"])


def enrich_clip_urls(clip: Clip) -> Clip:
    """Populate fresh presigned URLs for video and thumbnail preview."""
    if clip.r2_key:
        try:
            clip.r2_url = storage_manager.generate_presigned_url(clip.r2_key, expires_in_seconds=3600)
        except Exception:
            pass
    if clip.r2_thumbnail_key:
        try:
            clip.r2_thumbnail_url = storage_manager.generate_presigned_url(clip.r2_thumbnail_key, expires_in_seconds=3600)
        except Exception:
            pass
    return clip


@router.get("", response_model=List[ClipResponse])
async def list_clips(
    approval_status: Optional[str] = None,
    streamer_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(Clip).order_by(Clip.id.desc())
    if approval_status:
        stmt = stmt.where(Clip.approval_status == approval_status)
    if streamer_id:
        stmt = stmt.where(Clip.streamer_id == streamer_id)

    result = await db.execute(stmt)
    clips = result.scalars().all()
    return [enrich_clip_urls(c) for c in clips]


@router.get("/{clip_id}", response_model=ClipResponse)
async def get_clip(
    clip_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(Clip).where(Clip.id == clip_id)
    clip = (await db.execute(stmt)).scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    return enrich_clip_urls(clip)


@router.patch("/{clip_id}", response_model=ClipResponse)
async def update_clip(
    clip_id: int,
    payload: ClipUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(Clip).where(Clip.id == clip_id)
    clip = (await db.execute(stmt)).scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    if payload.title is not None:
        clip.title = payload.title
    if payload.description is not None:
        clip.description = payload.description
    if payload.tags is not None:
        clip.tags = payload.tags
    if payload.approval_status is not None:
        clip.approval_status = payload.approval_status.value

    await db.commit()
    await db.refresh(clip)
    return enrich_clip_urls(clip)


@router.post("/{clip_id}/review", response_model=ClipResponse)
async def review_clip(
    clip_id: int,
    payload: ClipApprovalRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    """
    Approve or reject a clip.
    Strict copyright check: if approved, verifies creator permission is granted.
    """
    stmt = select(Clip).where(Clip.id == clip_id)
    clip = (await db.execute(stmt)).scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    if payload.action == "approve":
        # Check creator permission
        perm_stmt = select(CreatorPermission).where(
            (CreatorPermission.streamer_id == clip.streamer_id) &
            (CreatorPermission.permission_status == PermissionStatus.GRANTED.value)
        )
        permission = (await db.execute(perm_stmt)).scalars().first()
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot approve clip: Creator permission is not granted for this streamer."
            )

        clip.approval_status = ApprovalStatus.APPROVED.value
        if payload.custom_title:
            clip.title = payload.custom_title
        if payload.custom_description:
            clip.description = payload.custom_description
        if payload.custom_tags:
            clip.tags = payload.custom_tags

        db.add(AuditEvent(
            actor=user.username,
            action="approve_clip",
            target_type="clip",
            target_id=str(clip.id),
            details_json={"title": clip.title, "streamer_id": clip.streamer_id}
        ))
    elif payload.action == "reject":
        clip.approval_status = ApprovalStatus.REJECTED.value
        db.add(AuditEvent(
            actor=user.username,
            action="reject_clip",
            target_type="clip",
            target_id=str(clip.id),
            details_json={"title": clip.title, "streamer_id": clip.streamer_id}
        ))

    await db.commit()
    await db.refresh(clip)
    return enrich_clip_urls(clip)


@router.post("/{clip_id}/re-render", response_model=ClipResponse)
async def re_render_clip_endpoint(
    clip_id: int,
    payload: ClipReRenderRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    """
    Re-render a clip with an edited headline burned onto the middle white card.
    Updates local scratch video, uploads fresh MP4 to Cloudflare R2, and refreshes preview URL.
    """
    from workers.render_worker import render_worker
    re_rendered = await render_worker.re_render_clip(clip_id, payload.headline)
    if not re_rendered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to re-render clip. Source video or segment may have expired or is missing."
        )

    # Re-query clip in the current route session to prevent detached session error
    stmt = select(Clip).where(Clip.id == clip_id)
    clip = (await db.execute(stmt)).scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    if payload.caption is not None:
        clip.description = payload.caption
    if payload.tags is not None:
        clip.tags = payload.tags

    db.add(AuditEvent(
        actor=user.username,
        action="re_render_clip_headline",
        target_type="clip",
        target_id=str(clip.id),
        details_json={"headline": payload.headline}
    ))

    await db.commit()
    await db.refresh(clip)
    return enrich_clip_urls(clip)


@router.api_route("/{clip_id}/stream", methods=["GET", "HEAD"])
async def stream_clip_video(
    clip_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Stream clip video directly from local scratch disk (with HTTP 206 Partial Content range support)
    or redirect to Cloudflare R2 if local copy was purged.
    """
    stmt = select(Clip).where(Clip.id == clip_id)
    clip = (await db.execute(stmt)).scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    # 1. Check if local scratch video file exists at recorded path
    if clip.portrait_video_path:
        local_path = Path(clip.portrait_video_path)
        if local_path.exists():
            return FileResponse(
                path=str(local_path),
                media_type="video/mp4",
                content_disposition_type="inline"
            )

    # 2. Check fallback in settings.SCRATCH_DIR / "clips"
    scratch_clips_dir = Path(settings.SCRATCH_DIR) / "clips"
    if clip.candidate_id:
        matching_files = sorted(list(scratch_clips_dir.glob(f"clip_cand_{clip.candidate_id}_*.mp4")), reverse=True)
        if matching_files and matching_files[0].exists():
            return FileResponse(
                path=str(matching_files[0]),
                media_type="video/mp4",
                content_disposition_type="inline"
            )

    # 3. If local file not found, redirect to fresh presigned R2 URL
    if clip.r2_key:
        try:
            r2_url = storage_manager.generate_presigned_url(clip.r2_key, expires_in_seconds=3600)
            return RedirectResponse(url=r2_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate video stream: {e}")

    raise HTTPException(status_code=404, detail="Clip video file not found")


@router.api_route("/{clip_id}/thumbnail", methods=["GET", "HEAD"])
async def stream_clip_thumbnail(
    clip_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Serve thumbnail image directly from local scratch disk or redirect to R2.
    """
    stmt = select(Clip).where(Clip.id == clip_id)
    clip = (await db.execute(stmt)).scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    if clip.thumbnail_path:
        local_path = Path(clip.thumbnail_path)
        if local_path.exists():
            return FileResponse(path=str(local_path), media_type="image/jpeg", content_disposition_type="inline")

    scratch_clips_dir = Path(settings.SCRATCH_DIR) / "clips"
    if clip.candidate_id:
        matching_files = sorted(list(scratch_clips_dir.glob(f"thumb_cand_{clip.candidate_id}_*.jpg")), reverse=True)
        if matching_files and matching_files[0].exists():
            return FileResponse(path=str(matching_files[0]), media_type="image/jpeg", content_disposition_type="inline")

    if clip.r2_thumbnail_key:
        try:
            r2_url = storage_manager.generate_presigned_url(clip.r2_thumbnail_key, expires_in_seconds=3600)
            return RedirectResponse(url=r2_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        except Exception:
            pass

    raise HTTPException(status_code=404, detail="Thumbnail not found")


@router.get("/mock-media/{file_path:path}")
async def serve_mock_media(file_path: str):
    """Serve mock media files locally when R2 credentials are not set."""
    base_dir = Path(settings.SCRATCH_DIR) / "mock_r2"
    target = (base_dir / file_path).resolve()
    if not target.is_relative_to(base_dir.resolve()) or not target.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    media_type = "video/mp4" if target.suffix == ".mp4" else "image/jpeg"
    return FileResponse(path=str(target), media_type=media_type)
