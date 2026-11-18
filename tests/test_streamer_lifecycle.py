"""
Acceptance Test 1: Streamer offline -> live -> offline transition lifecycle.
Verifies recording starts once and terminates cleanly.
"""
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.models import Streamer, StreamSession, CreatorPermission
from packages.shared.enums import StreamerStatus, SessionStatus, PlatformType, PermissionStatus
from workers.capture_worker import capture_worker


@pytest.mark.asyncio
async def test_streamer_offline_to_live_to_offline(db_session: AsyncSession, mock_session_factory):
    # 1. Register a test streamer
    streamer = Streamer(
        platform=PlatformType.TWITCH.value,
        channel_id="test_streamer_1",
        channel_url="https://twitch.tv/test_streamer_1",
        display_name="Test Streamer",
        is_monitored=True,
        live_status=StreamerStatus.OFFLINE.value,
    )
    db_session.add(streamer)
    await db_session.flush()

    permission = CreatorPermission(
        streamer_id=streamer.id,
        permission_status=PermissionStatus.GRANTED.value,
        authorized_by="Direct contract",
    )
    db_session.add(permission)
    await db_session.commit()

    # 2. Mock live check to return LIVE
    mock_live_info = {
        "is_live": True,
        "title": "GTA 6 Story Mode First Playthrough",
        "game": "Grand Theft Auto VI",
        "viewers": 15000,
        "session_id": "twitch_live_123"
    }

    with patch("workers.capture_worker.check_streamer_live", new=AsyncMock(return_value=mock_live_info)), \
         patch("workers.capture_worker.AsyncSessionLocal", side_effect=mock_session_factory):

        # First cycle: Stream goes live -> starts capture session
        await capture_worker.check_and_capture_streamers()

        # Re-fetch streamer from DB
        stmt = select(Streamer).where(Streamer.id == streamer.id)
        current_streamer = (await db_session.execute(stmt)).scalar_one()
        assert current_streamer.live_status == StreamerStatus.LIVE.value
        assert current_streamer.stream_title == "GTA 6 Story Mode First Playthrough"

        # Verify one active session was created
        sess_stmt = select(StreamSession).where(
            (StreamSession.streamer_id == streamer.id) &
            (StreamSession.status == SessionStatus.ACTIVE.value)
        )
        active_sessions = (await db_session.execute(sess_stmt)).scalars().all()
        assert len(active_sessions) == 1

        # Second cycle while still live: should NOT duplicate active session
        await capture_worker.check_and_capture_streamers()
        active_sessions_second = (await db_session.execute(sess_stmt)).scalars().all()
        assert len(active_sessions_second) == 1

    # 3. Mock live check to return OFFLINE
    mock_offline_info = {
        "is_live": False,
        "title": None,
        "game": None,
        "viewers": 0,
        "session_id": None
    }

    with patch("workers.capture_worker.check_streamer_live", new=AsyncMock(return_value=mock_offline_info)), \
         patch("workers.capture_worker.AsyncSessionLocal", side_effect=mock_session_factory):

        # Third cycle: Stream goes offline -> ends capture session
        await capture_worker.check_and_capture_streamers()

        stmt = select(Streamer).where(Streamer.id == streamer.id)
        current_streamer = (await db_session.execute(stmt)).scalar_one()
        assert current_streamer.live_status == StreamerStatus.OFFLINE.value

        # Verify session marked as ended
        ended_sess_stmt = select(StreamSession).where(
            (StreamSession.streamer_id == streamer.id) &
            (StreamSession.status == SessionStatus.ENDED.value)
        )
        ended_sessions = (await db_session.execute(ended_sess_stmt)).scalars().all()
        assert len(ended_sessions) == 1
        assert ended_sessions[0].ended_at is not None
