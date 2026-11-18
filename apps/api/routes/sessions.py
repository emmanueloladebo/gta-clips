"""
Stream session and segment API endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.database import get_db
from packages.shared.models import StreamSession, Segment, User
from packages.shared.schemas import StreamSessionResponse, SegmentResponse
from apps.api.auth import require_current_user

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=List[StreamSessionResponse])
async def list_sessions(
    streamer_id: int = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(StreamSession).options(selectinload(StreamSession.segments)).order_by(StreamSession.id.desc())
    if streamer_id:
        stmt = stmt.where(StreamSession.streamer_id == streamer_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{session_id}", response_model=StreamSessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(StreamSession).options(selectinload(StreamSession.segments)).where(StreamSession.id == session_id)
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Stream session not found")
    return session


@router.get("/{session_id}/segments", response_model=List[SegmentResponse])
async def list_session_segments(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(Segment).where(Segment.session_id == session_id).order_by(Segment.sequence_num.asc())
    result = await db.execute(stmt)
    return result.scalars().all()
