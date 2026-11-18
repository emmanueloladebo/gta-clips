"""
Acceptance Test 9: Publishing guardrails, creator rights, and review gates.
Verifies unapproved or unauthorized clips are strictly blocked from publishing.
"""
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.models import Streamer, CreatorPermission, Clip, DestinationAccount
from packages.shared.enums import PlatformType, PermissionStatus, ApprovalStatus, PublishPlatform
from packages.shared.config import settings


@pytest.mark.asyncio
async def test_unauthorized_creator_blocks_clip_approval(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict
):
    # Streamer with PENDING (unauthorized) permission
    streamer = Streamer(
        platform=PlatformType.TWITCH.value,
        channel_id="unauthorized_streamer",
        channel_url="https://twitch.tv/unauthorized_streamer",
        display_name="NoRightsStreamer",
    )
    db_session.add(streamer)
    await db_session.flush()

    perm = CreatorPermission(
        streamer_id=streamer.id,
        permission_status=PermissionStatus.PENDING.value,
    )
    db_session.add(perm)

    clip = Clip(
        streamer_id=streamer.id,
        title="Epic GTA 6 Moment",
        duration_seconds=30.0,
        approval_status=ApprovalStatus.PENDING_REVIEW.value,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(clip)
    await db_session.commit()

    # Attempt to approve clip via API
    resp = await client.post(
        f"/api/clips/{clip.id}/review",
        headers=auth_headers,
        json={"action": "approve"}
    )

    # Must be rejected with 403 Forbidden!
    assert resp.status_code == 403
    assert "Creator permission is not granted" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_unapproved_clip_cannot_be_published(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict
):
    # Streamer WITH permission granted
    streamer = Streamer(
        platform=PlatformType.TWITCH.value,
        channel_id="authorized_streamer",
        channel_url="https://twitch.tv/authorized_streamer",
        display_name="RightsHolder",
    )
    db_session.add(streamer)
    await db_session.flush()

    perm = CreatorPermission(
        streamer_id=streamer.id,
        permission_status=PermissionStatus.GRANTED.value,
    )
    db_session.add(perm)

    # Destination account
    dest = DestinationAccount(
        platform=PublishPlatform.TIKTOK.value,
        account_name="@gtashorts",
        external_account_id="tiktok_123",
        is_active=True,
    )
    db_session.add(dest)

    # Clip still in PENDING_REVIEW
    clip = Clip(
        streamer_id=streamer.id,
        title="Unreviewed Clip",
        duration_seconds=20.0,
        approval_status=ApprovalStatus.PENDING_REVIEW.value,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add(clip)
    await db_session.commit()

    # Attempt to publish unapproved clip
    resp = await client.post(
        "/api/publishing/publish",
        headers=auth_headers,
        json={"clip_id": clip.id, "destination_account_id": dest.id}
    )

    # Must be rejected with 400 Bad Request!
    assert resp.status_code == 400
    assert "Approval is required" in resp.json()["detail"]


def test_auto_post_defaults_to_off():
    # Strict requirement: auto-post MUST default to OFF
    assert settings.AUTO_POST_ENABLED is False
