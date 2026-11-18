"""
Highlight candidate API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.database import get_db
from packages.shared.models import Candidate, Segment, Clip, User
from packages.shared.schemas import CandidateResponse
from apps.api.auth import require_current_user

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("", response_model=List[CandidateResponse])
async def list_candidates(
    segment_id: Optional[int] = None,
    min_score: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(Candidate).order_by(Candidate.score.desc(), Candidate.id.desc())
    if segment_id:
        stmt = stmt.where(Candidate.segment_id == segment_id)
    if min_score is not None:
        stmt = stmt.where(Candidate.score >= min_score)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_current_user)
):
    stmt = select(Candidate).where(Candidate.id == candidate_id)
    candidate = (await db.execute(stmt)).scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate
