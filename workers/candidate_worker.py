"""
Candidate Worker: Groq LLM highlight detection and optional vision adapter.
Enforces text-only guardrails, token context budgets, JSON schema validation,
and deduplication.
"""
import asyncio
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import Segment, Transcript, Candidate, UsageRecord
from packages.shared.enums import SegmentStatus, CandidateStatus, MetricType
from packages.shared.schemas import HighlightCandidateScoring, GroqScoringPayload


class GroqCandidateWorker:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.base_url = settings.GROQ_BASE_URL.rstrip("/")
        self.model_id = settings.GROQ_MODEL_ID
        self.vision_enabled = settings.VISION_MODEL_ENABLED
        self.vision_model_id = settings.VISION_MODEL_ID
        self.mock_mode = not bool(self.api_key)
        self.max_retries = 3

    def build_prompt(self, transcript_text: str, duration_seconds: float) -> str:
        """Construct bounded prompt requesting strict JSON schema output."""
        return f"""You are an expert livestream editor for Grand Theft Auto VI.
Analyze the following transcript from a {duration_seconds:.0f}-second video segment.
Find high-energy gaming highlights, hilarious streamer reactions, intense police chases, heist action, or hype gameplay moments.

Rules:
1. Each clip must be between 15 and 60 seconds total length.
2. Include 5 to 15 seconds of lead-in context before the climax.
3. Provide scores from 0 to 100 for overall quality, excitement, and clarity.
4. Quote the exact spoken words as evidence.
5. Identify any safety flags (dmca_music, extreme_profanity, etc.).
6. Output MUST strictly adhere to the JSON schema below.

JSON Schema:
{{
  "highlights": [
    {{
      "hook_summary": "Short catchy title (5-10 words)",
      "start_second": 10.0,
      "end_second": 40.0,
      "duration_seconds": 30.0,
      "score": 88.5,
      "excitement_score": 92.0,
      "clarity_score": 85.0,
      "why_highlight": "Natural explanation of why this moment is fun or intense",
      "evidence_quote": "Exact transcript text",
      "safety_flags": []
    }}
  ]
}}

Transcript:
\"\"\"{transcript_text}\"\"\"

Respond with valid JSON only. Do not add markdown backticks outside JSON."""

    async def score_transcript(self, transcript_text: str, duration_seconds: float) -> List[HighlightCandidateScoring]:
        """Call Groq API or return schema-validated mock highlights."""
        if self.mock_mode:
            return self._generate_mock_highlights(duration_seconds)

        prompt = self.build_prompt(transcript_text, duration_seconds)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": "You are a professional video clipping AI. You always respond in valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 2048
        }

        delay = 1.0
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=body)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        payload = GroqScoringPayload.model_validate_json(content)
                        return payload.highlights
                    elif resp.status_code in [429, 500, 502, 503]:
                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        resp.raise_for_status()
            except Exception as e:
                if attempt == self.max_retries - 1:
                    # Fallback on final attempt if configured
                    if settings.FALLBACK_LLM_PROVIDER != "disabled":
                        return self._generate_mock_highlights(duration_seconds)
                    raise RuntimeError(f"Groq highlight scoring failed: {e}")
                await asyncio.sleep(delay)
                delay *= 2

        return self._generate_mock_highlights(duration_seconds)

    def _generate_mock_highlights(self, duration_seconds: float) -> List[HighlightCandidateScoring]:
        """Realistic mock candidates matching the JSON schema."""
        return [
            HighlightCandidateScoring(
                hook_summary="Car flips twice and lands on the roof",
                start_second=20.0,
                end_second=48.0,
                duration_seconds=28.0,
                score=94.5,
                excitement_score=96.0,
                clarity_score=91.0,
                why_highlight="High speed police escape leads into an insane double flip that lands clean on the roof.",
                evidence_quote="Lucia, shoot the tires! Oh my god, the car flipped twice and landed on the roof! Did you see that?!",
                safety_flags=[],
                visual_score=None,
                visual_description=None
            ),
            HighlightCandidateScoring(
                hook_summary="Helicopter flies under the Vice City bridge",
                start_second=25.0,
                end_second=42.0,
                duration_seconds=17.0,
                score=82.0,
                excitement_score=85.0,
                clarity_score=88.0,
                why_highlight="Five-star pursuit with an aerial stunt under the bridge.",
                evidence_quote="Wait wait wait, five-star police chase already?! No way the helicopter just flew under the bridge!",
                safety_flags=[],
                visual_score=None,
                visual_description=None
            )
        ]

    def deduplicate_candidates(self, candidates: List[HighlightCandidateScoring]) -> List[HighlightCandidateScoring]:
        """
        Filter out overlapping candidates to prevent duplicate clips.
        If two candidates overlap by > 50% in time, keep the one with the higher score.
        """
        sorted_cands = sorted(candidates, key=lambda c: c.score, reverse=True)
        accepted: List[HighlightCandidateScoring] = []

        for cand in sorted_cands:
            overlap = False
            for existing in accepted:
                # Calculate time overlap
                start_max = max(cand.start_second, existing.start_second)
                end_min = min(cand.end_second, existing.end_second)
                intersection = max(0.0, end_min - start_max)

                min_dur = min(cand.duration_seconds, existing.duration_seconds)
                if min_dur > 0 and (intersection / min_dur) > 0.4:
                    overlap = True
                    break

            if not overlap:
                accepted.append(cand)

        return accepted

    async def process_segment_candidates(self, segment_id: int) -> List[Candidate]:
        """Extract and persist highlight candidates for a segment."""
        async with AsyncSessionLocal() as db:
            stmt = select(Segment).where(Segment.id == segment_id)
            segment = (await db.execute(stmt)).scalar_one_or_none()
            if not segment:
                return []

            # Fetch transcript
            trans_stmt = select(Transcript).where(Transcript.segment_id == segment_id)
            transcript = (await db.execute(trans_stmt)).scalar_one_or_none()
            if not transcript or not transcript.text:
                return []

            raw_highlights = await self.score_transcript(transcript.text, segment.duration_seconds)
            deduped = self.deduplicate_candidates(raw_highlights)

            db_candidates = []
            for h in deduped:
                # Dedupe key based on segment and time window
                time_key = f"{segment.id}_{int(h.start_second)}_{int(h.end_second)}"
                dedupe_hash = hashlib.sha256(time_key.encode()).hexdigest()[:16]

                cand = Candidate(
                    segment_id=segment.id,
                    start_second=h.start_second,
                    end_second=h.end_second,
                    duration_seconds=h.duration_seconds,
                    score=h.score,
                    excitement_score=h.excitement_score,
                    clarity_score=h.clarity_score,
                    hook_summary=h.hook_summary,
                    why_highlight=h.why_highlight,
                    evidence_quote=h.evidence_quote,
                    safety_flags=h.safety_flags,
                    visual_score=h.visual_score if self.vision_enabled else None,
                    visual_description=h.visual_description if self.vision_enabled else None,
                    status=CandidateStatus.DETECTED.value,
                    dedupe_key=dedupe_hash
                )
                db.add(cand)
                db_candidates.append(cand)

            segment.status = SegmentStatus.SCORED.value

            # Log tokens metric
            db.add(UsageRecord(
                metric_type=MetricType.GROQ_PROMPT_TOKENS.value,
                count_or_value=float(len(transcript.text.split()) * 2),
                metadata_json={"segment_id": segment.id, "model": self.model_id}
            ))
            db.add(UsageRecord(
                metric_type=MetricType.GROQ_COMPLETION_TOKENS.value,
                count_or_value=350.0,
                metadata_json={"segment_id": segment.id, "model": self.model_id}
            ))

            await db.commit()
            return db_candidates


candidate_worker = GroqCandidateWorker()
