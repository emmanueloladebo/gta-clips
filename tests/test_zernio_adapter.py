"""
Acceptance Test 10: Zernio publish adapter.
Verifies idempotency guarantees, status polling, and error handling.
"""
import pytest
from packages.shared.zernio import ZernioAdapter


@pytest.mark.asyncio
async def test_zernio_idempotency_guarantee():
    adapter = ZernioAdapter()
    adapter.mock_mode = True

    idempotency_key = "test_key_unique_12345"
    media_url = "https://r2.example.com/clips/stunt.mp4"
    caption = "Insane GTA 6 stunt!"
    platforms = ["tiktok", "youtube_shorts"]

    # 1. First submission
    res1 = await adapter.submit_publish_job(
        media_url=media_url,
        caption=caption,
        platforms=platforms,
        idempotency_key=idempotency_key
    )

    assert "id" in res1
    first_post_id = res1["id"]
    assert res1["status"] == "published"
    assert "tiktok" in res1["external_post_ids"]

    # 2. Second submission with SAME idempotency key (simulating retry or network duplicate)
    res2 = await adapter.submit_publish_job(
        media_url=media_url,
        caption=caption,
        platforms=platforms,
        idempotency_key=idempotency_key
    )

    # Must return identical post ID and result (idempotent)
    assert res2["id"] == first_post_id
    assert res2 == res1

    # 3. Third submission with DIFFERENT idempotency key -> generates new post ID
    res3 = await adapter.submit_publish_job(
        media_url=media_url,
        caption=caption,
        platforms=platforms,
        idempotency_key="different_key_67890"
    )
    assert res3["id"] != first_post_id


@pytest.mark.asyncio
async def test_zernio_status_polling():
    adapter = ZernioAdapter()
    adapter.mock_mode = True

    post = await adapter.submit_publish_job(
        media_url="https://r2.example.com/clips/stunt.mp4",
        caption="Stunt",
        platforms=["tiktok"],
        idempotency_key="poll_key_111"
    )

    status_data = await adapter.get_publish_status(post["id"])
    assert status_data["id"] == post["id"]
    assert status_data["status"] in ["published", "scheduled", "processing"]


@pytest.mark.asyncio
async def test_zernio_get_connected_accounts():
    adapter = ZernioAdapter()
    adapter.mock_mode = True

    accounts = await adapter.get_connected_accounts()
    assert len(accounts) >= 2
    platforms = [a["platform"] for a in accounts]
    assert "tiktok" in platforms
    assert "youtube_shorts" in platforms
