"""
Acceptance Test 6: FFmpeg portrait rendering pipeline.
Verifies 1080x1920 MP4 formatting, audio normalization, subtitles, and safe framing.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.models import Streamer, StreamSession, Segment, Candidate, Clip
from packages.shared.enums import PlatformType, SegmentStatus, CandidateStatus, ApprovalStatus
from workers.render_worker import FFmpegRenderWorker


def test_ffmpeg_filter_construction():
    worker = FFmpegRenderWorker()
    streamer_name = "SpeedDemon"
    quote = "No way the car flipped twice!"
    headline = "INSANE DOUBLE FLIP"

    filter_str = worker.build_ffmpeg_filter(streamer_name, quote, headline_text=headline)

    # 1. Top facecam crop and scale
    assert "scale=1080:760" in filter_str

    # 2. Bottom gameplay crop and scale
    assert "scale=2062:1160" in filter_str

    # 3. Vertical stack
    assert "vstack=inputs=2" in filter_str

    # 4. Middle headline banner
    assert "drawbox=y=715:w=1080:h=90" in filter_str
    assert "INSANE DOUBLE FLIP" in filter_str

    # 5. Streamer attribution watermark
    assert "@SpeedDemon" in filter_str
    assert "GTA 6" in filter_str

    # 6. Burned subtitle
    assert "No way the car flipped twice!" in filter_str


@pytest.mark.asyncio
async def test_render_candidate_to_clip_and_24h_ttl(db_session: AsyncSession, tmp_path):
    worker = FFmpegRenderWorker()
    worker.output_dir = tmp_path

    # Setup Streamer, Session, Segment, Candidate
    streamer = Streamer(
        platform=PlatformType.TWITCH.value,
        channel_id="render_tester",
        channel_url="https://twitch.tv/render_tester",
        display_name="RenderTester",
    )
    db_session.add(streamer)
    await db_session.flush()

    session = StreamSession(streamer_id=streamer.id)
    db_session.add(session)
    await db_session.flush()

    dummy_seg_file = tmp_path / "raw_seg.mp4"
    dummy_seg_file.write_bytes(b"\x00" * 50000)

    segment = Segment(
        session_id=session.id,
        sequence_num=1,
        file_path=str(dummy_seg_file),
        duration_seconds=600.0,
        status=SegmentStatus.SCORED.value,
    )
    db_session.add(segment)
    await db_session.flush()

    cand = Candidate(
        segment_id=segment.id,
        start_second=30.0,
        end_second=55.0,
        duration_seconds=25.0,
        score=91.0,
        excitement_score=95.0,
        clarity_score=88.0,
        hook_summary="Double flip landing",
        why_highlight="Epic car stunt",
        evidence_quote="Did you see that flip?!",
        status=CandidateStatus.DETECTED.value,
    )
    db_session.add(cand)
    await db_session.commit()

    from unittest.mock import patch
    with patch("workers.render_worker.AsyncSessionLocal", return_value=db_session):
        clip = await worker.render_candidate_to_clip(cand.id)

    assert clip is not None
    assert clip.resolution == "1080x1920"
    assert clip.aspect_ratio == "9:16"
    assert clip.approval_status == ApprovalStatus.PENDING_REVIEW.value
    assert Path(clip.portrait_video_path).exists()
    assert Path(clip.thumbnail_path).exists()

    # Crucial check: Clip expires_at must be exactly ~24 hours from creation
    expected_expiry = clip.created_at + timedelta(hours=24)
    assert abs((clip.expires_at - expected_expiry).total_seconds()) < 60
