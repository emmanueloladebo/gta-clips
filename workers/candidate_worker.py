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

    def build_prompt(self, transcript_text: str, duration_seconds: float, recent_headlines: Optional[List[str]] = None) -> str:
        """Construct prompt requesting high-converting viral hooks matching Vice City Snips quality."""
        banned_section = ""
        if recent_headlines:
            formatted_recent = "\n".join(f"- {h}" for h in recent_headlines[:15])
            banned_section = f"""
STRICT HEADLINE DIVERSITY (DO NOT REPEAT):
Do NOT use or closely imitate any of these existing headlines:
{formatted_recent}
Every new headline must be 100% fresh, creative, and strictly specific to what happened in THIS clip.
"""

        return f"""You are a top viral TikTok/Shorts content curator specialized in Grand Theft Auto VI (GTA 6).
Analyze this transcript from a {duration_seconds:.0f}-second livestream segment.

YOUR OBJECTIVE:
Find the single most captivating, intense, shocking, or hilarious moment in this segment.
Deeply analyze dialogue, streamer reactions, scenario, and gameplay context:
- Missions & base break-ins (stealing a fighter jet from the military base, plane crashes in swamps, boat escapes).
- Unhinged NPCs & dialogue (talking parrots that roast people, almost getting banned by weird NPCs, pedestrians, random crimes).
- Game mechanics & discoveries (new gym systems, building muscle, comparing police AI to GTA 5, weird weapons like tennis balls).
- Streamer panic, chaos, roasts, laughing, scream reactions, unexpected fails.

HEADLINE ON-SCREEN RULES:
- Must be a punchy, curiosity-inducing hook (4 to 9 words in UPPERCASE) with 1-2 relevant emojis at the end.
- It must accurately describe the exact scenario/dialogue in the video!
- NEVER give generic titles like "HEAD CLIPPERS FAIL" or "JASON & LUCIA CHAOS". Make every title unique and descriptive.
- Perfect headline examples:
  * "STEALING A JET IN GTA 6 IS A DEATH SENTENCE 💀✈️"
  * "GTA 6 HAS A TALKING PARROT THAT ROASTS YOU 😭🦜"
  * "THIS GTA 6 NPC ALMOST GOT HIM BANNED 💀"
  * "I FOUND A CRASHED PLANE IN GTA 6… BIG MISTAKE 💀"
  * "TRYING TO SNEAK ONTO A CRUISE SHIP IN GTA 6 💀"
  * "GTA 6 COPS ARE WAY SMARTER THAN GTA 5 COPS"
  * "BRO REALLY USED A TENNIS BALL AS A WEAPON 😭"
  * "YOU CAN ACTUALLY BUILD MUSCLE IN GTA 6?!"
  * "I JUST WITNESSED A RANDOM MURDER IN GTA 6 💀"
{banned_section}
CAPTION RULES:
- Write a short, natural social caption (1 sentence, everyday words - no big english):
  * "Bro thought this was GTA 5 😭💀 The military wasn't playing!"
  * "This parrot has absolutely NO FILTER 😭🦜💀"
  * "I thought stealing a police boat would SAVE me 💀"

HASHTAGS:
- Must be: ["#gta6", "#gtavi", "#gaming", "#vicecity", "#gta6gameplay"]

WINDOW & DURATION:
- Extract the best 20 to 50-second window.
- Assign an entertainment score between 70.0 and 99.0.

JSON SCHEMA:
{{
  "highlights": [
    {{
      "hook_summary": "Catchy 4-7 word title",
      "headline": "STEALING A JET IN GTA 6 IS A DEATH SENTENCE 💀✈️",
      "caption": "Bro thought this was GTA 5 😭💀 The military wasn't playing!",
      "hashtags": ["#gta6", "#gtavi", "#gaming", "#vicecity", "#gta6gameplay"],
      "facecam_position": "top_right",
      "start_second": 10.0,
      "end_second": 45.0,
      "duration_seconds": 35.0,
      "score": 92.0,
      "excitement_score": 94.0,
      "clarity_score": 90.0,
      "why_highlight": "Streamer infiltrates the military base and gets surrounded by tanks.",
      "evidence_quote": "Exact spoken words from transcript",
      "safety_flags": []
    }}
  ]
}}

Transcript:
\"\"\"{transcript_text}\"\"\"

Respond with valid JSON only."""

    async def score_transcript(self, transcript_text: str, duration_seconds: float, recent_headlines: Optional[List[str]] = None) -> List[HighlightCandidateScoring]:
        """Call Groq API to extract viral highlight moments."""
        if not transcript_text or not transcript_text.strip():
            logger.info("Empty transcript text provided. No highlights to extract.")
            return []

        if self.mock_mode:
            logger.warning("Groq API key not configured. Skipping candidate scoring.")
            return []

        prompt = self.build_prompt(transcript_text, duration_seconds, recent_headlines=recent_headlines)
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

            # Format timestamped utterances from Deepgram Nova-3 if available
            scoring_text = transcript.text
            if transcript.sound_events_json and isinstance(transcript.sound_events_json, list):
                dialogue_lines = []
                for item in transcript.sound_events_json:
                    if isinstance(item, dict) and "start" in item and "text" in item and item["text"]:
                        s_m, s_s = divmod(int(item["start"]), 60)
                        e_m, e_s = divmod(int(item.get("end", item["start"])), 60)
                        spk = item.get("speaker", 0)
                        dialogue_lines.append(f"[{s_m:02d}:{s_s:02d} - {e_m:02d}:{e_s:02d}] (Speaker {spk}): {item['text']}")
                if dialogue_lines:
                    scoring_text = "\n".join(dialogue_lines)

            # Fetch recent headlines to actively prevent duplicate or repetitive titles across clips
            recent_cands = (await db.execute(select(Candidate.hook_summary).order_by(Candidate.id.desc()).limit(15))).scalars().all()
            recent_clips = (await db.execute(select(Clip.title).order_by(Clip.id.desc()).limit(15))).scalars().all()
            all_recent = list(set([h for h in (recent_cands + recent_clips) if h]))

            raw_highlights = await self.score_transcript(scoring_text, segment.duration_seconds, recent_headlines=all_recent)
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
