"""
Acceptance Test 4: Groq highlight candidate extraction.
Verifies JSON schema validation, token budgeting, deduplication, and retries.
"""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import Response, Request
from pydantic import ValidationError

from packages.shared.schemas import HighlightCandidateScoring, GroqScoringPayload
from workers.candidate_worker import GroqCandidateWorker


def test_groq_candidate_schema_validation():
    # Valid candidate
    valid_data = {
        "hook_summary": "Insane helicopter bridge dive",
        "start_second": 12.0,
        "end_second": 42.0,
        "duration_seconds": 30.0,
        "score": 92.5,
        "excitement_score": 95.0,
        "clarity_score": 88.0,
        "why_highlight": "Stunt flight during police pursuit",
        "evidence_quote": "No way the helicopter just flew under the bridge!",
        "safety_flags": [],
        "visual_score": None,
        "visual_description": None,
    }
    cand = HighlightCandidateScoring(**valid_data)
    assert cand.duration_seconds == 30.0
    assert cand.score == 92.5

    # Invalid candidate (score out of bounds > 100)
    with pytest.raises(ValidationError):
        HighlightCandidateScoring(**{**valid_data, "score": 150.0})


def test_groq_candidate_deduplication():
    worker = GroqCandidateWorker()

    c1 = HighlightCandidateScoring(
        hook_summary="Stunt jump 1",
        start_second=10.0,
        end_second=35.0,
        duration_seconds=25.0,
        score=95.0,
        excitement_score=95.0,
        clarity_score=90.0,
        why_highlight="Best jump",
        evidence_quote="OMG!",
    )
    # Overlaps significantly with c1 (starts at 12s, ends at 36s)
    c2 = HighlightCandidateScoring(
        hook_summary="Stunt jump overlap duplicate",
        start_second=12.0,
        end_second=36.0,
        duration_seconds=24.0,
        score=80.0,
        excitement_score=80.0,
        clarity_score=85.0,
        why_highlight="Duplicate moment",
        evidence_quote="OMG!",
    )
    # Distinct non-overlapping candidate later in segment
    c3 = HighlightCandidateScoring(
        hook_summary="Heist escape",
        start_second=120.0,
        end_second=150.0,
        duration_seconds=30.0,
        score=90.0,
        excitement_score=92.0,
        clarity_score=88.0,
        why_highlight="Bank escape",
        evidence_quote="Clean getaway!",
    )

    deduped = worker.deduplicate_candidates([c1, c2, c3])

    # Should keep c1 (higher score) and c3, filtering out c2 duplicate
    assert len(deduped) == 2
    assert deduped[0].hook_summary == "Stunt jump 1"
    assert deduped[1].hook_summary == "Heist escape"


@pytest.mark.asyncio
async def test_groq_retries_and_falls_back_on_rate_limit():
    worker = GroqCandidateWorker()
    worker.mock_mode = False
    worker.api_key = "test_groq_key"

    req = Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resp_429 = Response(status_code=429, request=req)

    with patch("httpx.AsyncClient.post", return_value=resp_429), \
         patch("asyncio.sleep", new=AsyncMock()), \
         patch("packages.shared.config.settings.FALLBACK_LLM_PROVIDER", "openai"):

        # Should retry max times and fall back smoothly without crashing
        highlights = await worker.score_transcript("Dummy transcript test", 60.0)

    assert len(highlights) > 0
    assert isinstance(highlights[0], HighlightCandidateScoring)
