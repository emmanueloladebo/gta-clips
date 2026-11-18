"""
System health check and credentials blocker tracking.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import get_db
from packages.shared.schemas import HealthStatusResponse
from packages.shared.storage import storage_manager

router = APIRouter(prefix="/api/health", tags=["health"])


def get_credentials_blockers() -> List[str]:
    """Returns list of pending external credentials required for live production."""
    blockers = []
    if not (settings.TWITCH_CLIENT_ID and settings.TWITCH_CLIENT_SECRET):
        blockers.append("Twitch Helix API: TWITCH_CLIENT_ID or TWITCH_CLIENT_SECRET missing (fallback Streamlink probe active)")
    if not settings.YOUTUBE_API_KEY:
        blockers.append("YouTube Data API: YOUTUBE_API_KEY missing (fallback Streamlink probe active)")
    if not settings.DEEPGRAM_API_KEY:
        blockers.append("Deepgram Speech-to-Text: DEEPGRAM_API_KEY missing (mock audio intelligence active)")
    if not settings.GROQ_API_KEY:
        blockers.append("Groq LLM Highlights: GROQ_API_KEY missing (mock JSON highlights active)")
    if not (settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY and settings.R2_ENDPOINT_URL):
        blockers.append("Cloudflare R2: S3 API credentials missing (mock cloud storage active)")
    if not settings.ZERNIO_API_KEY:
        blockers.append("Zernio Social Publishing: ZERNIO_API_KEY missing (mock publisher active)")
    return blockers


@router.get("", response_model=HealthStatusResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    scratch_ok = storage_manager.scratch_dir.exists()
    r2_ok = not storage_manager.mock_mode or storage_manager.mock_r2_dir.exists()
    blockers = get_credentials_blockers()

    return HealthStatusResponse(
        status="healthy" if db_ok and scratch_ok else "degraded",
        environment=settings.APP_ENV,
        database_connected=db_ok,
        storage_r2_healthy=r2_ok,
        scratch_disk_healthy=scratch_ok,
        workers_active=1,
        auto_post_enabled=settings.AUTO_POST_ENABLED,
        blockers=blockers
    )


@router.get("/blockers")
async def list_blockers():
    """Detailed blocker status for setup guidance."""
    return {
        "total_blockers": len(get_credentials_blockers()),
        "blockers": get_credentials_blockers(),
        "ready_for_production": len(get_credentials_blockers()) == 0,
        "instructions": "Add required credentials in cloud .env to switch from mock mode to live production."
    }
