"""
Acceptance Test 8: Strict 24-hour retention purge and orphan sweep.
Verifies all raw and finished media older than 24h is permanently removed.
"""
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from unittest.mock import patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.models import StorageObject, Clip, Streamer
from packages.shared.enums import StorageType, StorageCategory, ApprovalStatus
from workers.cleanup_worker import cleanup_worker


@pytest.mark.asyncio
async def test_24h_media_retention_purge(db_session: AsyncSession, tmp_path):
    cleanup_worker.storage.mock_mode = True
    cleanup_worker.storage.mock_r2_dir = tmp_path / "mock_r2"
    cleanup_worker.storage.mock_r2_dir.mkdir(parents=True, exist_ok=True)
    cleanup_worker.storage.scratch_dir = tmp_path / "scratch"
    cleanup_worker.storage.scratch_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create a dummy file in mock R2 that is expired
    expired_r2_file = cleanup_worker.storage.mock_r2_dir / "clips" / "expired_clip.mp4"
    expired_r2_file.parent.mkdir(parents=True, exist_ok=True)
    expired_r2_file.write_bytes(b"\x00" * 1000)

    # DB record for this expired R2 object
    past_time = datetime.now(timezone.utc) - timedelta(hours=25)
    storage_obj = StorageObject(
        storage_type=StorageType.R2.value,
        file_path_or_key="clips/expired_clip.mp4",
        size_bytes=1000,
        category=StorageCategory.CLIP.value,
        created_at=past_time,
        expires_at=past_time,
    )
    db_session.add(storage_obj)

    # 2. Create an expired scratch file on disk (set mtime 26 hours ago)
    scratch_file = cleanup_worker.storage.scratch_dir / "old_raw_seg.mp4"
    scratch_file.write_bytes(b"\x00" * 2000)
    old_timestamp = time.time() - (26 * 3600)
    os.utime(str(scratch_file), (old_timestamp, old_timestamp))

    # 3. Create a fresh scratch file (< 24 hours old) that should NOT be deleted
    fresh_file = cleanup_worker.storage.scratch_dir / "fresh_raw_seg.mp4"
    fresh_file.write_bytes(b"\x00" * 3000)

    await db_session.commit()

    with patch("workers.cleanup_worker.AsyncSessionLocal", return_value=db_session):
        res = await cleanup_worker.execute_retention_sweep()

    # Verify R2 object was deleted
    assert not expired_r2_file.exists()
    assert res["r2_deleted_count"] >= 1

    # Verify expired scratch file was deleted
    assert not scratch_file.exists()

    # Verify fresh file is retained
    assert fresh_file.exists()
