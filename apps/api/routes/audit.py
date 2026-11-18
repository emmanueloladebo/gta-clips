"""
Audit event log endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.database import get_db
from packages.shared.models import AuditEvent, User
from packages.shared.schemas import AuditEventResponse
from apps.api.auth import require_current_user

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=List[AuditEventResponse])
async def list_audit_events(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()
