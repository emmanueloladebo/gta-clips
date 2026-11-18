"""
Storage Worker: Uploads rendered clips & thumbnails to Cloudflare R2.
Enforces 10 GiB hard limit, 8 GiB soft limit, and tracks StorageObjects.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import Clip, StorageObject, UsageRecord
from packages.shared.enums import StorageType, StorageCategory, MetricType
from packages.shared.storage import storage_manager, QuotaExceededError


class CloudStorageWorker:
    def __init__(self):
        self.storage = storage_manager

    async def upload_clip_to_r2(self, clip_id: int) -> Optional[Clip]:
        """Upload clip video and thumbnail to R2 with quota checks."""
        async with AsyncSessionLocal() as db:
            stmt = select(Clip).where(Clip.id == clip_id)
            clip = (await db.execute(stmt)).scalar_one_or_none()
            if not clip or not clip.portrait_video_path:
                return None

            video_path = Path(clip.portrait_video_path)
            thumb_path = Path(clip.thumbnail_path) if clip.thumbnail_path else None

            if not video_path.exists():
                return None

            # Keys in R2
            video_key = f"clips/{video_path.name}"
            thumb_key = f"thumbnails/{thumb_path.name}" if thumb_path and thumb_path.exists() else None

            # Upload video to R2 (will raise QuotaExceededError if hard limit hit)
            self.storage.upload_to_r2(str(video_path), video_key, content_type="video/mp4")
            clip.r2_key = video_key
            clip.r2_url = self.storage.generate_presigned_url(video_key, expires_in_seconds=3600)

            # Record storage object
            v_size = video_path.stat().st_size
            db.add(StorageObject(
                storage_type=StorageType.R2.value,
                file_path_or_key=video_key,
                size_bytes=v_size,
                category=StorageCategory.CLIP.value,
                created_at=clip.created_at,
                expires_at=clip.expires_at,
            ))

            # Upload thumbnail if present
            if thumb_path and thumb_path.exists():
                self.storage.upload_to_r2(str(thumb_path), thumb_key, content_type="image/jpeg")
                clip.r2_thumbnail_key = thumb_key
                clip.r2_thumbnail_url = self.storage.generate_presigned_url(thumb_key, expires_in_seconds=3600)

                t_size = thumb_path.stat().st_size
                db.add(StorageObject(
                    storage_type=StorageType.R2.value,
                    file_path_or_key=thumb_key,
                    size_bytes=t_size,
                    category=StorageCategory.THUMBNAIL.value,
                    created_at=clip.created_at,
                    expires_at=clip.expires_at,
                ))

            # Log R2 storage metric
            db.add(UsageRecord(
                metric_type=MetricType.R2_STORAGE_BYTES.value,
                count_or_value=float(v_size),
                streamer_id=clip.streamer_id,
                metadata_json={"r2_key": video_key}
            ))

            await db.commit()
            await db.refresh(clip)
            return clip


storage_worker = CloudStorageWorker()
