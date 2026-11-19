"""
Publishing and destination account endpoints.
Guards against unauthorized or unapproved distribution.
"""
from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import get_db
from packages.shared.models import (
    Clip, Streamer, CreatorPermission, DestinationAccount,
    PublishJob, AuditEvent, User
)
from packages.shared.enums import ApprovalStatus, PermissionStatus, PublishStatus
from packages.shared.schemas import (
    DestinationAccountCreate, DestinationAccountResponse,
    PublishJobCreate, PublishJobResponse
)
from packages.shared.zernio import zernio_adapter
from packages.shared.storage import storage_manager
from apps.api.auth import require_current_user

router = APIRouter(prefix="/api/publishing", tags=["publishing"])


@router.get("/destinations", response_model=List[DestinationAccountResponse])
async def list_destinations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(DestinationAccount).order_by(DestinationAccount.id.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/destinations/sync", response_model=List[DestinationAccountResponse])
async def sync_zernio_destinations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    """
    Fetch all connected social accounts from Zernio and sync them into destination accounts.
    Removes any old stale or mock accounts not present in Zernio.
    """
    remote_accounts = await zernio_adapter.get_connected_accounts()
    synced: List[DestinationAccount] = []

    if remote_accounts:
        remote_ext_ids = {str(item["external_account_id"]) for item in remote_accounts}
        # Remove old accounts that don't belong to the user's real Zernio connections
        existing_res = await db.execute(select(DestinationAccount))
        for old_acc in existing_res.scalars().all():
            if str(old_acc.external_account_id) not in remote_ext_ids:
                await db.delete(old_acc)
        await db.flush()

    for item in remote_accounts:
        stmt = select(DestinationAccount).where(
            (DestinationAccount.platform == item["platform"]) &
            (DestinationAccount.external_account_id == item["external_account_id"])
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.account_name = item["account_name"]
            existing.is_active = item.get("is_active", True)
            synced.append(existing)
        else:
            new_acc = DestinationAccount(
                platform=item["platform"],
                account_name=item["account_name"],
                external_account_id=item["external_account_id"],
                is_active=item.get("is_active", True),
                auto_post_enabled=False,
            )
            db.add(new_acc)
            synced.append(new_acc)

    await db.commit()
    for acc in synced:
        await db.refresh(acc)

    db.add(AuditEvent(
        actor=user.username,
        action="sync_zernio_accounts",
        target_type="destination_account",
        target_id=str(len(synced)),
        details_json={"count": len(synced)}
    ))
    await db.commit()

    all_stmt = select(DestinationAccount).order_by(DestinationAccount.id.asc())
    return (await db.execute(all_stmt)).scalars().all()


@router.post("/destinations", response_model=DestinationAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_destination(
    payload: DestinationAccountCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    account = DestinationAccount(
        platform=payload.platform.value,
        account_name=payload.account_name,
        external_account_id=payload.external_account_id,
        is_active=payload.is_active,
        auto_post_enabled=payload.auto_post_enabled,
        auth_metadata=payload.auth_metadata,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/destinations/{dest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_destination(
    dest_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(DestinationAccount).where(DestinationAccount.id == dest_id)
    account = (await db.execute(stmt)).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Destination account not found")

    await db.delete(account)
    await db.commit()


@router.get("/jobs", response_model=List[PublishJobResponse])
async def list_publish_jobs(
    clip_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(PublishJob).order_by(PublishJob.id.desc())
    if clip_id:
        stmt = stmt.where(PublishJob.clip_id == clip_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/publish", response_model=PublishJobResponse)
async def publish_clip(
    payload: PublishJobCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    """
    Submits an approved clip to Zernio for multi-platform publishing.
    Verifies creator permission and approval status.
    """
    # 1. Fetch clip
    clip_stmt = select(Clip).where(Clip.id == payload.clip_id)
    clip = (await db.execute(clip_stmt)).scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    # 2. Strict Check: Approval Status
    if clip.approval_status != ApprovalStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clip cannot be published because its status is '{clip.approval_status}'. Approval is required."
        )

    # 3. Strict Check: Creator Permission
    perm_stmt = select(CreatorPermission).where(
        (CreatorPermission.streamer_id == clip.streamer_id) &
        (CreatorPermission.permission_status == PermissionStatus.GRANTED.value)
    )
    permission = (await db.execute(perm_stmt)).scalars().first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Publishing blocked: The creator has not granted permission for this channel."
        )

    # 4. Fetch destination account
    dest_stmt = select(DestinationAccount).where(DestinationAccount.id == payload.destination_account_id)
    dest = (await db.execute(dest_stmt)).scalar_one_or_none()
    if not dest or not dest.is_active:
        raise HTTPException(status_code=400, detail="Destination account not found or inactive")

    # 5. Build idempotency key
    idempotency_key = f"pub_{clip.id}_{dest.id}_{int(datetime.now(timezone.utc).timestamp())}"

    # Create job in database
    job = PublishJob(
        clip_id=clip.id,
        destination_account_id=dest.id,
        platform=dest.platform,
        status=PublishStatus.SUBMITTED.value,
        idempotency_key=idempotency_key,
        scheduled_at=payload.scheduled_at,
    )
    db.add(job)
    await db.flush()

    try:
        # Submit to Zernio
        media_url = clip.r2_url or f"{settings.PUBLIC_BASE_URL}/api/clips/mock-media/{clip.r2_key}"
        zernio_res = await zernio_adapter.submit_publish_job(
            media_url=media_url,
            caption=f"{clip.title}\n\n{clip.tags or ''}",
            platforms=[dest.platform],
            idempotency_key=idempotency_key,
            account_id=dest.external_account_id,
            title=clip.title,
            scheduled_at=payload.scheduled_at
        )

        job.external_post_id = zernio_res.get("id")
        job.status = PublishStatus.PUBLISHED.value if not payload.scheduled_at else PublishStatus.QUEUED.value
        job.published_at = datetime.now(timezone.utc) if not payload.scheduled_at else None

        # Once confirmed published, clean up media files from scratch disk and Cloudflare R2
        if job.status == PublishStatus.PUBLISHED.value:
            clip.approval_status = ApprovalStatus.PUBLISHED.value
            try:
                storage_manager.cleanup_clip_media(clip)
            except Exception:
                pass

        db.add(AuditEvent(
            actor=user.username,
            action="publish_clip",
            target_type="clip",
            target_id=str(clip.id),
            details_json={
                "job_id": job.id,
                "platform": dest.platform,
                "account": dest.account_name,
                "external_id": job.external_post_id
            }
        ))
    except Exception as e:
        job.status = PublishStatus.FAILED.value
        job.error_message = str(e)
        job.retry_count += 1

    await db.commit()
    await db.refresh(job)
    return job


@router.post("/jobs/{job_id}/retry", response_model=PublishJobResponse)
async def retry_publish_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(PublishJob).where(PublishJob.id == job_id)
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Publish job not found")

    clip = (await db.execute(select(Clip).where(Clip.id == job.clip_id))).scalar_one_or_none()
    dest = (await db.execute(select(DestinationAccount).where(DestinationAccount.id == job.destination_account_id))).scalar_one_or_none()

    if not clip or not dest:
        raise HTTPException(status_code=400, detail="Associated clip or destination missing")

    try:
        media_url = clip.r2_url or f"{settings.PUBLIC_BASE_URL}/api/clips/mock-media/{clip.r2_key}"
        zernio_res = await zernio_adapter.submit_publish_job(
            media_url=media_url,
            caption=f"{clip.title}\n\n{clip.tags or ''}",
            platforms=[dest.platform],
            idempotency_key=job.idempotency_key,
            account_id=dest.external_account_id,
            title=clip.title,
            scheduled_at=job.scheduled_at
        )
        job.external_post_id = zernio_res.get("id")
        job.status = PublishStatus.PUBLISHED.value if not job.scheduled_at else PublishStatus.QUEUED.value
        job.error_message = None
        job.retry_count += 1
        if job.status == PublishStatus.PUBLISHED.value:
            clip.approval_status = ApprovalStatus.PUBLISHED.value
            try:
                storage_manager.cleanup_clip_media(clip)
            except Exception:
                pass
    except Exception as e:
        job.status = PublishStatus.FAILED.value
        job.error_message = str(e)
        job.retry_count += 1

    await db.commit()
    await db.refresh(job)
    return job


@router.get("/auto-post-status")
async def get_auto_post_status(user: User = Depends(require_current_user)):
    return {
        "auto_post_enabled": settings.AUTO_POST_ENABLED,
        "mode": "review_before_post" if not settings.AUTO_POST_ENABLED else "automatic",
        "description": "When OFF, every clip requires human review and explicit approval before posting."
    }
