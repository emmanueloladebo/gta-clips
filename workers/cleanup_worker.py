"""
Cleanup Worker: 24-Hour Strict Retention Enforcer & Orphan Reconciler.
Deletes all raw scratch segments, temp audio, and R2 media older than 24 hours.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import StorageObject, Clip, Segment, AuditEvent
from packages.shared.enums import StorageType
from packages.shared.storage import storage_manager


class MediaRetentionWorker:
    def __init__(self):
        self.storage = storage_manager
        self.ttl_hours = settings.MEDIA_TTL_HOURS

    async def execute_retention_sweep(self) -> Dict[str, Any]:
        """
        Execute scheduled 24-hour TTL purge across R2 cloud storage
        and local scratch disks.
        """
        now = datetime.now(timezone.utc)
        r2_deleted_count = 0
        r2_freed_bytes = 0
        scratch_deleted_count = 0

        async with AsyncSessionLocal() as db:
            # 1. Purge expired R2 storage objects (older than 24h)
            stmt = select(StorageObject).where(
                (StorageObject.storage_type == StorageType.R2.value) &
                (StorageObject.expires_at <= now) &
                (StorageObject.deleted_at.is_(None))
            )
            expired_objects = (await db.execute(stmt)).scalars().all()

            for obj in expired_objects:
                try:
                    success = self.storage.delete_from_r2(obj.file_path_or_key)
                    if success:
                        obj.deleted_at = now
                        r2_deleted_count += 1
                        r2_freed_bytes += obj.size_bytes
                except Exception:
                    pass

            # 2. Reconcile expired Clips
            clip_stmt = select(Clip).where(Clip.expires_at <= now)
            expired_clips = (await db.execute(clip_stmt)).scalars().all()
            for clip in expired_clips:
                # Remove scratch copies if lingering
                if clip.portrait_video_path and Path(clip.portrait_video_path).exists():
                    try:
                        Path(clip.portrait_video_path).unlink()
                    except OSError:
                        pass
                if clip.thumbnail_path and Path(clip.thumbnail_path).exists():
                    try:
                        Path(clip.thumbnail_path).unlink()
                    except OSError:
                        pass

            # 3. Purge scratch files older than TTL
            scratch_deleted_count = self.storage.cleanup_expired_scratch_files(ttl_hours=self.ttl_hours)

            # 4. Log audit event
            db.add(AuditEvent(
                actor="cleanup_worker",
                action="24h_retention_purge",
                target_type="storage",
                details_json={
                    "r2_deleted_count": r2_deleted_count,
                    "r2_freed_bytes": r2_freed_bytes,
                    "scratch_deleted_count": scratch_deleted_count,
                    "ttl_hours": self.ttl_hours
                }
            ))

            await db.commit()

        return {
            "r2_deleted_count": r2_deleted_count,
            "r2_freed_bytes": r2_freed_bytes,
            "scratch_deleted_count": scratch_deleted_count,
            "ttl_hours": self.ttl_hours
        }

    async def orphan_reconciliation(self) -> int:
        """
        Scan scratch directory and delete unindexed / orphaned files.
        """
        async with AsyncSessionLocal() as db:
            active_segs = await db.scalars(select(Segment.file_path))
            active_clips = await db.scalars(select(Clip.portrait_video_path))
            known_paths = set(active_segs.all()) | set(active_clips.all())

        orphans_removed = 0
        scratch_path = Path(settings.SCRATCH_DIR)
        mock_r2_path = str(scratch_path / "mock_r2")

        if scratch_path.exists():
            for p in scratch_path.rglob("*"):
                if p.is_file() and not str(p).startswith(mock_r2_path):
                    if str(p) not in known_paths:
                        # Orphan candidate: check if older than 1 hour to prevent race with active writes
                        mtime = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                        if (datetime.now(timezone.utc) - mtime).total_seconds() > 3600:
                            try:
                                p.unlink()
                                orphans_removed += 1
                            except OSError:
                                pass

        return orphans_removed


cleanup_worker = MediaRetentionWorker()
