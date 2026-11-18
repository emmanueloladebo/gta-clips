"""
Storage metrics, R2 budget tracking, and retention cleanup endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import get_db
from packages.shared.models import AuditEvent, User
from packages.shared.schemas import StorageUsageResponse
from packages.shared.storage import storage_manager
from apps.api.auth import require_current_user

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/usage", response_model=StorageUsageResponse)
async def get_storage_usage(user: User = Depends(require_current_user)):
    r2_used, r2_count = storage_manager.get_r2_usage()
    scratch_used, scratch_limit = storage_manager.get_scratch_usage()

    return StorageUsageResponse(
        r2_used_bytes=r2_used,
        r2_soft_limit_bytes=settings.R2_SOFT_LIMIT_BYTES,
        r2_hard_limit_bytes=settings.R2_HARD_LIMIT_BYTES,
        r2_soft_limit_exceeded=r2_used >= settings.R2_SOFT_LIMIT_BYTES,
        r2_hard_limit_exceeded=r2_used >= settings.R2_HARD_LIMIT_BYTES,
        r2_object_count=r2_count,
        scratch_used_bytes=scratch_used,
        scratch_limit_bytes=scratch_limit,
        scratch_limit_exceeded=scratch_used >= scratch_limit,
        media_ttl_hours=settings.MEDIA_TTL_HOURS
    )


@router.post("/cleanup")
async def trigger_cleanup(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    """Manually invoke the 24h retention cleanup cycle."""
    deleted_scratch = storage_manager.cleanup_expired_scratch_files()

    db.add(AuditEvent(
        actor=user.username,
        action="manual_cleanup",
        target_type="storage",
        details_json={"deleted_scratch_files": deleted_scratch}
    ))
    await db.commit()

    return {
        "status": "success",
        "deleted_scratch_files": deleted_scratch,
        "message": f"Cleaned up scratch files older than {settings.MEDIA_TTL_HOURS} hours."
    }
