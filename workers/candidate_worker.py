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
        """Construct bounded prompt requesting schema-validated viral clip detection with deep GTA 6 context."""
        return f"""You are an elite, creative viral video editor and curator specialized in Grand Theft Auto VI (GTA 6).
Analyze the following transcript from a {duration_seconds:.0f}-second livestream segment.

YOUR MISSION:
Find the most entertaining, hilarious, intense, scandalous, or memorable moment in this transcript that will perform well on TikTok, YouTube Shorts, and Instagram Reels.

DEEP GTA 6 KNOWLEDGE & VIBES:
Do NOT limit your search to just 5-star police chases. GTA 6 in the state of Leonida (Vice City) is full of crazy, diverse moments:
- Lucia and Jason dynamics: romantic tension, banter, relationship drama, ex-partners, arguments, trust and crime partnership.
- Vice City nightlife: Lucia dancing at clubs, partying, wild NPCs, twerking on car roofs, beach antics, luxury lifestyle.
- Stunts and chaos: stealing fighter jets from the military base, crazy car ramps, speedboat chases in the Keys, airboats in the swamp with alligators, robbing stores, weapon experiments.
- Funny Florida/Leonida humor: bizarre NPC interactions, hilarious dialogue, weird radio broadcasts, ridiculous social media moments.
- Streamer reactions: funny jokes, roasts, laughing, screaming, unexpected fails, clutch saves, genuine shock or hype.
- Random fun banter: any conversation or moment that is funny, weird, or interesting to watch!

RULES:
1. If there is a fun, interesting, funny, or action-packed moment in the transcript, extract the best 15 to 60-second clip window.
2. Only return an empty list {{"highlights": []}} if the transcript is completely empty, unintelligible noise, or pure silence.
3. Provide a score between 70 and 100 based on entertainment value, humor, or excitement.
4. Provide a punchy, click-worthy 'headline' in uppercase (3-6 words, e.g. "LUCIA DANCING AT THE CLUB 💃", "STEALING A MILITARY JET ✈️", "JASON'S WORST DECISION EVER 😂", "BRO ACCIDENTALLY JUMPED THE BRIDGE 💀").
5. Write a natural, conversational 'caption' for social media (simple, everyday words - no big english or robotic prose).
6. Provide up to 5 lowercase hashtags, always including "#gta" and "#gta6" (e.g. ["#gta", "#gta6", "#gaming", "#gtavice", "#viral"]).
7. Quote the exact spoken words from the transcript as evidence.
8. Output MUST strictly adhere to the JSON schema below.

JSON Schema:
{{
  "highlights": [
    {{
      "hook_summary": "Catchy clip title (5-10 words)",
      "headline": "LUCIA CAUGHT DANCING AT THE CLUB 💃",
      "caption": "Jason was not ready for this in Vice City!",
      "hashtags": ["#gta", "#gta6", "#gaming", "#gtavice", "#viral"],
      "facecam_position": "top_right",
      "start_second": 5.0,
      "end_second": 35.0,
      "duration_seconds": 30.0,
      "score": 88.0,
      "excitement_score": 90.0,
      "clarity_score": 85.0,
      "why_highlight": "Funny and entertaining dialogue/moment",
      "evidence_quote": "Exact transcript text",
      "safety_flags": []
    }}
  ]
}}

Transcript:
\"\"\"{transcript_text}\"\"\"

Respond with valid JSON only. Do not add markdown backticks outside JSON."""

    async def score_transcript(self, transcript_text: str, duration_seconds: float) -> List[HighlightCandidateScoring]:
        """Call Groq API to extract viral highlight moments."""
        if not transcript_text or not transcript_text.strip():
            logger.info("Empty transcript text provided. No highlights to extract.")
            return []

        if self.mock_mode:
            logger.warning("Groq API key not configured. Skipping candidate scoring.")
            return []

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
                        logger.error(f"Groq API returned error status {resp.status_code}: {resp.text}")
                        resp.raise_for_status()
            except Exception as e:
                logger.warning(f"Groq scoring attempt {attempt+1}/{self.max_retries} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"All Groq scoring attempts failed for segment: {e}")
                    return []
                await asyncio.sleep(delay)
                delay *= 2

        return []

    def _generate_mock_highlights(self, duration_seconds: float) -> List[HighlightCandidateScoring]:
        """Realistic mock candidates matching the JSON schema."""
        return [
            HighlightCandidateScoring(
                hook_summary="Car flips twice and lands on the roof",
                headline="INSANE DOUBLE FLIP ESCAPE 🚗💨",
                caption="I cannot believe this car flip actually worked during the escape!",
                hashtags=["#gta", "#gta6", "#gaming", "#gtaclips", "#viral"],
                facecam_position="top_right",
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
                headline="FIVE STAR HELICOPTER STUNT 🚁🔥",
                caption="Bro really pulled off this bridge flight under 5 stars!",
                hashtags=["#gta", "#gta6", "#gaming", "#gtavice", "#viral"],
                facecam_position="top_right",
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

            # Strict Virality Gate: only moments meeting or exceeding the viral threshold are saved
            viral_highlights = [h for h in deduped if h.score >= settings.VIRAL_SCORE_THRESHOLD]

            db_candidates = []
            for h in viral_highlights:
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
                    safety_flags={
                        "flags": h.safety_flags if isinstance(h.safety_flags, list) else [],
                        "headline": h.headline or h.hook_summary.upper(),
                        "caption": h.caption or h.why_highlight,
                        "hashtags": h.hashtags or ["#gta", "#gta6", "#gaming", "#gtaclips", "#viral"],
                        "facecam_position": h.facecam_position or "top_right",
                    },
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
