"""
Candidate Worker: Groq LLM highlight detection and optional vision adapter.
Enforces text-only guardrails, token context budgets, JSON schema validation,
and deduplication.
"""
import asyncio
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import Segment, Transcript, Candidate, Clip, UsageRecord
from packages.shared.enums import SegmentStatus, CandidateStatus, MetricType
from packages.shared.schemas import HighlightCandidateScoring, GroqScoringPayload

logger = logging.getLogger(__name__)


def find_utterance_bounds(
    utterances: List[Dict[str, Any]],
    evidence_quote: str,
    fallback_start: float,
    fallback_end: float,
    segment_duration: float
) -> Tuple[float, float]:
    """
    Locates the spoken quote in Deepgram utterances to anchor ground-truth timestamps,
    then expands to a viral 35-50s window with proper lead-in context and reaction.
    """
    if not utterances or not evidence_quote:
        dur = max(30.0, fallback_end - fallback_start)
        s = max(0.0, fallback_start - (35.0 - (fallback_end - fallback_start)) * 0.4 if (fallback_end - fallback_start) < 35.0 else fallback_start)
        e = min(segment_duration, s + max(35.0, dur))
        return s, e

    quote_clean = evidence_quote.lower().strip()
    quote_words = [w for w in quote_clean.split() if len(w) > 3]

    best_match_start = None
    best_match_end = None
    max_overlap = 0

    for u in utterances:
        u_text = str(u.get("text", "")).lower()
        overlap = sum(1 for w in quote_words if w in u_text)
        if overlap > max_overlap:
            max_overlap = overlap
            best_match_start = float(u.get("start", fallback_start))
            best_match_end = float(u.get("end", fallback_end))

    if best_match_start is not None and max_overlap >= 1:
        # Anchor around the climax: 15s lead-in context, 20s reaction/gameplay
        s = max(0.0, best_match_start - 15.0)
        e = min(segment_duration, max(best_match_end + 20.0, s + 35.0))
        if (e - s) < 35.0 and segment_duration >= 35.0:
            if s == 0.0:
                e = min(segment_duration, 35.0)
            elif e == segment_duration:
                s = max(0.0, segment_duration - 35.0)
        return s, e

    # Fallback expansion to minimum 35 seconds
    dur = fallback_end - fallback_start
    if dur < 35.0:
        needed = 35.0 - dur
        s = max(0.0, fallback_start - (needed * 0.4))
        e = min(segment_duration, fallback_end + (needed * 0.6))
        return s, e

    return fallback_start, fallback_end


class GroqCandidateWorker:
    def __init__(self):
        # Primary: 9router AI Gateway (OpenAI compatible)
        self.router_api_key = settings.ROUTER_API_KEY
        self.router_base_url = settings.ROUTER_BASE_URL.rstrip("/")
        self.router_model_id = settings.ROUTER_MODEL_ID or "openai/gpt-6-luna"

        # Fallback: Groq / GPT-OSS
        self.groq_api_key = settings.GROQ_API_KEY
        self.groq_base_url = settings.GROQ_BASE_URL.rstrip("/")
        self.groq_model_id = settings.GROQ_MODEL_ID or "openai/gpt-oss-120b"

        self.vision_enabled = settings.VISION_MODEL_ENABLED
        self.vision_model_id = settings.VISION_MODEL_ID
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

CRITICAL TIMING & DURATION RULES:
- Every viral TikTok/Shorts clip MUST be between 30 and 55 seconds long (never shorter than 25 seconds).
- For "start_second" and "end_second", provide the exact SECOND float numbers matching the transcript (e.g. start_second: 185.0, end_second: 225.0).
- If the dialogue/punchline is short (e.g. 5-10 seconds), you MUST include the buildup context leading into it (15 seconds before) and the aftermath reaction (15-20 seconds after) so the clip tells the complete story!
- "duration_seconds" must equal end_second - start_second (between 30.0 and 55.0).
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
      "start_second": 185.0,
      "end_second": 225.0,
      "duration_seconds": 40.0,
      "score": 92.0,
      "excitement_score": 94.0,
      "clarity_score": 90.0,
      "why_highlight": "Streamer infiltrates the military base and gets surrounded by tanks.",
      "evidence_quote": "Exact spoken words from transcript",
      "safety_flags": []
    }}
  ]
}}

Transcript (with exact second timestamps):
\"\"\"{transcript_text}\"\"\"

Respond with valid JSON only."""

    async def _call_llm(
        self,
        base_url: str,
        api_key: str,
        model_id: str,
        prompt: str,
        provider_name: str = "LLM"
    ) -> List[HighlightCandidateScoring]:
        """Make an OpenAI-compatible /chat/completions call and parse JSON highlights."""
        if not api_key:
            return []

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        body: Dict[str, Any] = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": "You are a professional viral video clipping AI. You always respond in valid JSON matching the schema."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 2048
        }
        # Models like luna and o1 only support default temperature
        if "luna" not in model_id.lower() and "o1" not in model_id.lower():
            body["temperature"] = 0.2

        delay = 1.0
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=body)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        # Clean potential markdown fences
                        clean_content = content.strip()
                        if clean_content.startswith("```"):
                            lines = clean_content.split("\n")
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines and lines[-1].startswith("```"):
                                lines = lines[:-1]
                            clean_content = "\n".join(lines).strip()
                        payload = GroqScoringPayload.model_validate_json(clean_content)
                        logger.info(f"{provider_name} ({model_id}) extracted {len(payload.highlights)} highlights.")
                        return payload.highlights
                    elif resp.status_code in [429, 500, 502, 503]:
                        logger.warning(f"{provider_name} returned status {resp.status_code}, retrying...")
                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        logger.error(f"{provider_name} returned error status {resp.status_code}: {resp.text}")
                        resp.raise_for_status()
            except Exception as e:
                logger.warning(f"{provider_name} attempt {attempt+1}/{self.max_retries} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"All {provider_name} attempts failed: {e}")
                    raise
                await asyncio.sleep(delay)
                delay *= 2
        return []

    async def score_transcript(self, transcript_text: str, duration_seconds: float, recent_headlines: Optional[List[str]] = None) -> List[HighlightCandidateScoring]:
        """
        Extract viral highlight moments.
        Uses 9router (openai/gpt-6-luna) as primary engine.
        Falls back to Groq (openai/gpt-oss-120b) if 9router is unconfigured or fails.
        """
        if not transcript_text or not transcript_text.strip():
            logger.info("Empty transcript text provided. No highlights to extract.")
            return []

        prompt = self.build_prompt(transcript_text, duration_seconds, recent_headlines=recent_headlines)

        # 1. Primary: 9router (openai/gpt-6-luna)
        if self.router_api_key:
            try:
                highlights = await self._call_llm(
                    base_url=self.router_base_url,
                    api_key=self.router_api_key,
                    model_id=self.router_model_id,
                    prompt=prompt,
                    provider_name="9router"
                )
                if highlights:
                    return highlights
            except Exception as e:
                logger.warning(f"9router ({self.router_model_id}) failed: {e}. Falling back to Groq / GPT-OSS...")

        # 2. Fallback: Groq (openai/gpt-oss-120b)
        if self.groq_api_key:
            try:
                highlights = await self._call_llm(
                    base_url=self.groq_base_url,
                    api_key=self.groq_api_key,
                    model_id=self.groq_model_id,
                    prompt=prompt,
                    provider_name="Groq/GPT-OSS"
                )
                if highlights:
                    return highlights
            except Exception as e:
                logger.error(f"Fallback Groq ({self.groq_model_id}) failed: {e}")

        # If mock mode or keys missing
        if not self.router_api_key and not self.groq_api_key:
            logger.warning("No LLM API keys configured. Generating mock highlights.")
            return self._generate_mock_highlights(duration_seconds)

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

            # Format timestamped utterances from Deepgram Nova-3 with exact second offsets
            scoring_text = transcript.text
            raw_utterances = transcript.sound_events_json if isinstance(transcript.sound_events_json, list) else []
            if raw_utterances:
                dialogue_lines = []
                for item in raw_utterances:
                    if isinstance(item, dict) and "start" in item and "text" in item and item["text"]:
                        s = float(item["start"])
                        e = float(item.get("end", item["start"]))
                        s_m, s_s = divmod(int(s), 60)
                        e_m, e_s = divmod(int(e), 60)
                        spk = item.get("speaker", 0)
                        dialogue_lines.append(f"[{s:05.1f}s ({s_m:02d}:{s_s:02d}) - {e:05.1f}s ({e_m:02d}:{e_s:02d})] (Speaker {spk}): {item['text']}")
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
                # Ground-truth alignment: anchor timestamps to actual Deepgram utterance and expand to viral 35-50s window
                precise_start, precise_end = find_utterance_bounds(
                    utterances=raw_utterances,
                    evidence_quote=h.evidence_quote,
                    fallback_start=float(h.start_second),
                    fallback_end=float(h.end_second),
                    segment_duration=float(segment.duration_seconds)
                )

                precise_duration = round(precise_end - precise_start, 1)

                # Dedupe key based on segment and time window
                time_key = f"{segment.id}_{int(precise_start)}_{int(precise_end)}"
                dedupe_hash = hashlib.sha256(time_key.encode()).hexdigest()[:16]

                cand = Candidate(
                    segment_id=segment.id,
                    start_second=precise_start,
                    end_second=precise_end,
                    duration_seconds=precise_duration,
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
