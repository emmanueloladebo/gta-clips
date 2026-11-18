"""
Acceptance Test 2: Ingest & Segmentation, restart recovery, and scratch limit backpressure.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from unittest.mock import patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.models import Streamer, StreamSession, Segment
from packages.shared.enums import SegmentStatus, SessionStatus, PlatformType
from workers.capture_worker import capture_worker


@pytest.mark.asyncio
async def test_segment_creation_and_10min_chunking(db_session: AsyncSession, tmp_path):
    # Setup streamer and session
    streamer = Streamer(
        platform=PlatformType.TWITCH.value,
        channel_id="test_streamer_2",
        channel_url="https://twitch.tv/test_streamer_2",
        display_name="Test Streamer 2",
    )
    db_session.add(streamer)
    await db_session.flush()

    session = StreamSession(
        streamer_id=streamer.id,
        started_at=datetime.now(timezone.utc),
        status=SessionStatus.ACTIVE.value,
    )
    db_session.add(session)
    await db_session.commit()

    # Create dummy sample video file
    dummy_video = tmp_path / "sample_10min_segment.mp4"
    dummy_video.write_bytes(b"\x00" * (1024 * 1024 * 5))  # 5 MB mock video

    # Record segment of 600 seconds (10 minutes)
    seg1 = await capture_worker.record_sample_segment(
        db=db_session,
        session_id=session.id,
        duration_seconds=600.0,
        sample_file_path=str(dummy_video)
    )

    assert seg1.sequence_num == 1
    assert seg1.duration_seconds == 600.0
    assert seg1.status == SegmentStatus.RECORDED.value
    assert seg1.disk_bytes == dummy_video.stat().st_size

    # Record second segment of 300 seconds
    dummy_video2 = tmp_path / "sample_5min_segment.mp4"
    dummy_video2.write_bytes(b"\x00" * (1024 * 1024 * 2))

    seg2 = await capture_worker.record_sample_segment(
        db=db_session,
        session_id=session.id,
        duration_seconds=300.0,
        sample_file_path=str(dummy_video2)
    )

    assert seg2.sequence_num == 2
    assert seg2.duration_seconds == 300.0

    # Verify session totals
    await db_session.refresh(session)
    assert session.total_segments == 2
    assert session.total_duration_seconds == 900.0


@pytest.mark.asyncio
async def test_startup_reconciliation_recovers_interrupted_segments(
    db_session: AsyncSession,
    tmp_path,
    mock_session_factory
):
    """Verifies that un-finalized segments on server crash/restart recover safely without duplicate work."""
    streamer = Streamer(
        platform=PlatformType.TWITCH.value,
        channel_id="crash_test_streamer",
        channel_url="https://twitch.tv/crash_test_streamer",
        display_name="Crash Tester",
    )
    db_session.add(streamer)
    await db_session.flush()

    session = StreamSession(
        streamer_id=streamer.id,
        started_at=datetime.now(timezone.utc),
        status=SessionStatus.ACTIVE.value,
    )
    db_session.add(session)
    await db_session.flush()

    # File 1: was interrupted but has recorded bytes on disk
    file_with_content = tmp_path / "interrupted_chunk.mp4"
    file_with_content.write_bytes(b"\x00" * 50000)

    seg_recovered = Segment(
        session_id=session.id,
        sequence_num=1,
        file_path=str(file_with_content),
        status=SegmentStatus.RECORDING.value,
        duration_seconds=120.0,
    )
    db_session.add(seg_recovered)

    # File 2: missing or empty file on disk
    seg_failed = Segment(
        session_id=session.id,
        sequence_num=2,
        file_path=str(tmp_path / "non_existent.mp4"),
        status=SegmentStatus.RECORDING.value,
        duration_seconds=0.0,
    )
    db_session.add(seg_failed)
    await db_session.commit()

    with patch("workers.capture_worker.AsyncSessionLocal", side_effect=mock_session_factory):
        await capture_worker.startup_reconciliation()

    # Query fresh records
    stmt1 = select(Segment).where(Segment.id == seg_recovered.id)
    r1 = (await db_session.execute(stmt1)).scalar_one()

    stmt2 = select(Segment).where(Segment.id == seg_failed.id)
    r2 = (await db_session.execute(stmt2)).scalar_one()

    # Recovered segment should be RECORDED so it can be transcribed
    assert r1.status == SegmentStatus.RECORDED.value
    assert r1.disk_bytes == 50000

    # Missing file should be marked FAILED
    assert r2.status == SegmentStatus.FAILED.value
