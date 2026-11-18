"""
Creator permissions management API endpoints.
Ensures strict copyright compliance and creator consent.
"""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.database import get_db
from packages.shared.models import CreatorPermission, Streamer, AuditEvent, User
from packages.shared.schemas import CreatorPermissionUpdate, CreatorPermissionResponse
from apps.api.auth import require_current_user

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


@router.get("", response_model=List[CreatorPermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(CreatorPermission).order_by(CreatorPermission.id.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/{permission_id}", response_model=CreatorPermissionResponse)
async def update_permission(
    permission_id: int,
    payload: CreatorPermissionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(CreatorPermission).where(CreatorPermission.id == permission_id)
    perm = (await db.execute(stmt)).scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission record not found")

    old_status = perm.permission_status

    if payload.permission_status is not None:
        perm.permission_status = payload.permission_status.value
    if payload.authorized_by is not None:
        perm.authorized_by = payload.authorized_by
    if payload.license_url is not None:
        perm.license_url = payload.license_url
    if payload.notes is not None:
        perm.notes = payload.notes
    if payload.valid_until is not None:
        perm.valid_until = payload.valid_until

    perm.updated_at = datetime.now(timezone.utc)

    # Add audit log
    db.add(AuditEvent(
        actor=user.username,
        action="update_permission",
        target_type="creator_permission",
        target_id=str(perm.id),
        details_json={
            "streamer_id": perm.streamer_id,
            "old_status": old_status,
            "new_status": perm.permission_status,
            "authorized_by": perm.authorized_by,
        }
    ))

    await db.commit()
    await db.refresh(perm)
    return perm
