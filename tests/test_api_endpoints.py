"""
Acceptance Test 12: FastAPI REST endpoints, auth, and health check tests.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "storage_r2_healthy" in data
    assert "scratch_disk_healthy" in data
    assert "blockers" in data


@pytest.mark.asyncio
async def test_auth_and_protected_routes(client: AsyncClient):
    # 1. Register a user
    reg_resp = await client.post(
        "/api/auth/register",
        json={"username": "newstreamer", "email": "streamer@example.com", "password": "SecurePassword123!"}
    )
    assert reg_resp.status_code == 200
    user_data = reg_resp.json()
    assert user_data["username"] == "newstreamer"

    # 2. Login
    login_resp = await client.post(
        "/api/auth/login",
        data={"username": "newstreamer", "password": "SecurePassword123!"}
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Access protected /api/auth/me
    me_resp = await client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "newstreamer"

    # 4. Create a streamer via API
    streamer_payload = {
        "platform": "twitch",
        "channel_id": "vice_city_king",
        "channel_url": "https://twitch.tv/vice_city_king",
        "display_name": "ViceCityKing",
        "is_monitored": True,
        "permission": {
            "permission_status": "granted",
            "notes": "Exclusive affiliate agreement"
        }
    }
    create_strm_resp = await client.post("/api/streamers", headers=headers, json=streamer_payload)
    assert create_strm_resp.status_code == 201
    strm = create_strm_resp.json()
    assert strm["channel_id"] == "vice_city_king"
    assert len(strm["permissions"]) == 1
    assert strm["permissions"][0]["permission_status"] == "granted"

    # 5. List streamers
    list_resp = await client.get("/api/streamers", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 6. Check storage usage endpoint
    storage_resp = await client.get("/api/storage/usage", headers=headers)
    assert storage_resp.status_code == 200
    storage_data = storage_resp.json()
    assert storage_data["r2_hard_limit_bytes"] == 10 * 1024 * 1024 * 1024
    assert storage_data["media_ttl_hours"] == 24

    # 7. Check metrics summary endpoint
    metrics_resp = await client.get("/api/metrics/summary", headers=headers)
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    assert "total_streamers_monitored" in metrics_data
    assert "r2_storage_gb" in metrics_data
