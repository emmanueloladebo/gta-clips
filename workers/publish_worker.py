"""
Publish Worker: Auto-post evaluator and Zernio distribution orchestrator.
Enforces review-before-post by default, creator licensing checks,
and asynchronous status polling.
"""
import asyncio
from datetime import datetime, timezone
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import Clip, CreatorPermission, DestinationAccount, PublishJob, AuditEvent
from packages.shared.enums import ApprovalStatus, PermissionStatus, PublishStatus
from packages.shared.zernio import zernio_adapter


class AutoPublishWorker:
    def __init__(self):
        self.adapter = zernio_adapter
        self.auto_post_enabled = settings.AUTO_POST_ENABLED

    async def evaluate_auto_post_queue(self) -> int:
        """
        If auto-post is enabled, queues approved clips from authorized creators.
        If auto-post is disabled (default), clips remain in pending_review.
        """
        if not self.auto_post_enabled:
            return 0

        queued_count = 0
        async with AsyncSessionLocal() as db:
            # Find approved clips not yet published
            stmt = select(Clip).where(
                (Clip.approval_status == ApprovalStatus.APPROVED.value) &
                (Clip.auto_post_eligible == True)
            )
            clips = (await db.execute(stmt)).scalars().all()

            # Find active destination accounts
            dest_stmt = select(DestinationAccount).where(
                (DestinationAccount.is_active == True) &
                (DestinationAccount.auto_post_enabled == True)
            )
            destinations = (await db.execute(dest_stmt)).scalars().all()

            if not destinations:
                return 0

            for clip in clips:
                # Double-check creator permission
                perm_stmt = select(CreatorPermission).where(
                    (CreatorPermission.streamer_id == clip.streamer_id) &
                    (CreatorPermission.permission_status == PermissionStatus.GRANTED.value)
                )
                perm = (await db.execute(perm_stmt)).scalars().first()
                if not perm:
                    continue

                for dest in destinations:
                    # Check if already queued
                    job_stmt = select(PublishJob).where(
                        (PublishJob.clip_id == clip.id) &
                        (PublishJob.destination_account_id == dest.id)
                    )
                    existing_job = (await db.execute(job_stmt)).scalars().first()
                    if not existing_job:
                        idempotency_key = f"auto_{clip.id}_{dest.id}_{int(datetime.now(timezone.utc).timestamp())}"
                        job = PublishJob(
                            clip_id=clip.id,
                            destination_account_id=dest.id,
                            platform=dest.platform,
                            status=PublishStatus.QUEUED.value,
                            idempotency_key=idempotency_key,
                        )
                        db.add(job)
                        queued_count += 1

            await db.commit()
        return queued_count

    async def process_queued_jobs(self) -> int:
        """Process all queued publishing jobs."""
        processed = 0
        async with AsyncSessionLocal() as db:
            stmt = select(PublishJob).where(
                PublishJob.status.in_([PublishStatus.QUEUED.value, PublishStatus.PENDING.value])
            )
            jobs = (await db.execute(stmt)).scalars().all()

            for job in jobs:
                clip_stmt = select(Clip).where(Clip.id == job.clip_id)
                clip = (await db.execute(clip_stmt)).scalar_one_or_none()

                dest_stmt = select(DestinationAccount).where(DestinationAccount.id == job.destination_account_id)
                dest = (await db.execute(dest_stmt)).scalar_one_or_none()

                if not clip or not dest:
                    job.status = PublishStatus.FAILED.value
                    job.error_message = "Clip or Destination not found"
                    continue

                # Strict check: clip must be approved
                if clip.approval_status != ApprovalStatus.APPROVED.value:
                    job.status = PublishStatus.FAILED.value
                    job.error_message = "Clip is not approved"
                    continue

                # Strict check: creator permission must be granted
                perm_stmt = select(CreatorPermission).where(
                    (CreatorPermission.streamer_id == clip.streamer_id) &
                    (CreatorPermission.permission_status == PermissionStatus.GRANTED.value)
                )
                perm = (await db.execute(perm_stmt)).scalars().first()
                if not perm:
                    job.status = PublishStatus.FAILED.value
                    job.error_message = "Creator permission revoked or not granted"
                    continue

                try:
                    media_url = clip.r2_url or f"{settings.PUBLIC_BASE_URL}/api/clips/mock-media/{clip.r2_key}"
                    res = await self.adapter.submit_publish_job(
                        media_url=media_url,
                        caption=f"{clip.title}\n\n{clip.tags or ''}",
                        platforms=[dest.platform],
                        idempotency_key=job.idempotency_key,
                        scheduled_at=job.scheduled_at
                    )
                    job.external_post_id = res.get("id")
                    job.status = PublishStatus.PUBLISHED.value if not job.scheduled_at else PublishStatus.QUEUED.value
                    job.published_at = datetime.now(timezone.utc) if not job.scheduled_at else None
                    processed += 1
                except Exception as e:
                    job.status = PublishStatus.FAILED.value
                    job.error_message = str(e)
                    job.retry_count += 1

            await db.commit()
        return processed


publish_worker = AutoPublishWorker()
