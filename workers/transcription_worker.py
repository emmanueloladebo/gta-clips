"""
Transcription Worker: Deepgram audio transcription pipeline.
Handles audio chunking, timestamp alignment, 429/5xx backoff retries,
and mock fallback.
"""
import asyncio
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import Segment, Transcript, UsageRecord
from packages.shared.enums import SegmentStatus, MetricType


class DeepgramTranscriptionWorker:
    def __init__(self):
        self.api_key = settings.DEEPGRAM_API_KEY
        self.base_url = settings.DEEPGRAM_BASE_URL.rstrip("/")
        self.model = settings.DEEPGRAM_MODEL
        self.mock_mode = not bool(self.api_key)
        self.max_retries = 3
        self.scratch_audio_dir = Path(settings.SCRATCH_DIR) / "audio"
        self.scratch_audio_dir.mkdir(parents=True, exist_ok=True)

    def extract_audio(self, video_path: str, output_path: str) -> bool:
        """Extract 16kHz mono audio from video segment with vocal isolation filter."""
        try:
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vn",
                "-af", "highpass=f=80,lowpass=f=7500,volume=1.4",
                "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                output_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
            return res.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 1000
        except Exception:
            return False

    async def transcribe_audio_file(self, audio_path: str, duration_seconds: float = 600.0) -> Dict[str, Any]:
        """
        Call Deepgram API with exponential backoff on 429 / 5xx errors.
        Uses Nova-3 model with keyterm domain boosting and speaker diarization.
        """
        if self.mock_mode:
            # Generate realistic timestamp-aligned transcript for GTA 6
            return self._generate_mock_transcript(duration_seconds)

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav"
        }
        params = [
            ("model", self.model or "nova-3"),
            ("smart_format", "true"),
            ("punctuate", "true"),
            ("diarize", "true"),
            ("utterances", "true"),
            ("filler_words", "true"),
            ("keyterm", "Lucia"),
            ("keyterm", "Jason"),
            ("keyterm", "Vice City"),
            ("keyterm", "GTA 6"),
            ("keyterm", "Leonida"),
            ("keyterm", "military base"),
            ("keyterm", "five star"),
            ("keyterm", "heist"),
            ("keyterm", "cops"),
            ("keyterm", "opps"),
            ("keyterm", "busted"),
            ("keyterm", "wasted"),
        ]

        audio_bytes = Path(audio_path).read_bytes()
        delay = 1.0

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/listen",
                        headers=headers,
                        params=params,
                        content=audio_bytes
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return self._parse_deepgram_response(data)
                    elif resp.status_code in [429, 500, 502, 503, 504]:
                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        resp.raise_for_status()
            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"Deepgram transcription request failed after retries: {e}")
                await asyncio.sleep(delay)
                delay *= 2

        raise RuntimeError("Deepgram transcription failed: max retries exceeded.")

    def _parse_deepgram_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text, word-level timestamps, and speaker utterances from Deepgram Nova-3 response."""
        channels = data.get("results", {}).get("channels", [])
        if not channels:
            return {"text": "", "words": [], "utterances": [], "sound_events": []}

        alt = channels[0].get("alternatives", [{}])[0]
        text = alt.get("transcript", "")
        words = alt.get("words", [])

        # Format words with speaker and confidence
        formatted_words = [
            {
                "word": w.get("word", ""),
                "start": float(w.get("start", 0.0)),
                "end": float(w.get("end", 0.0)),
                "confidence": float(w.get("confidence", 0.0)),
                "speaker": int(w.get("speaker", 0)) if "speaker" in w else 0,
            }
            for w in words
        ]

        # Extract timestamped utterances from Deepgram Nova-3
        raw_utterances = data.get("results", {}).get("utterances", [])
        if not raw_utterances and "paragraphs" in alt:
            paragraphs = alt.get("paragraphs", {}).get("paragraphs", [])
            for p in paragraphs:
                for sent in p.get("sentences", []):
                    raw_utterances.append({
                        "start": sent.get("start", 0.0),
                        "end": sent.get("end", 0.0),
                        "transcript": sent.get("text", ""),
                        "speaker": p.get("speaker", 0)
                    })

        formatted_utterances = [
            {
                "start": float(u.get("start", 0.0)),
                "end": float(u.get("end", 0.0)),
                "speaker": int(u.get("speaker", 0)),
                "text": str(u.get("transcript", "")).strip()
            }
            for u in raw_utterances
            if str(u.get("transcript", "")).strip()
        ]

        return {
            "text": text,
            "words": formatted_words,
            "utterances": formatted_utterances,
            "sound_events": []
        }

    def _generate_mock_transcript(self, duration_seconds: float) -> Dict[str, Any]:
        """Realistic mock transcript with gaming action cues and word timestamps."""
        phrases = [
            (5.0, 15.0, "Yo look at that Vice City skyline, the graphics are unreal! We're grabbing that sports car right now."),
            (25.0, 38.0, "Wait wait wait, five-star police chase already?! No way the helicopter just flew under the bridge!"),
            (60.0, 75.0, "Lucia, shoot the tires! Oh my god, the car flipped twice and landed on the roof! Did you see that?!"),
            (120.0, 135.0, "Bro that was the craziest heist escape I have ever seen in Grand Theft Auto!"),
            (200.0, 215.0, "Chat, is this mission impossible or what? Let's go!"),
            (350.0, 370.0, "Speeding down the highway at 180 mph, avoiding every roadblock, clean getaway baby!")
        ]

        all_words = []
        full_text_list = []
        for start, end, phrase in phrases:
            if start < duration_seconds:
                full_text_list.append(phrase)
                tokens = phrase.split()
                time_step = (end - start) / max(len(tokens), 1)
                for i, token in enumerate(tokens):
                    all_words.append({
                        "word": token,
                        "start": round(start + i * time_step, 2),
                        "end": round(start + (i + 1) * time_step, 2),
                        "confidence": 0.98
                    })

        sound_events = [
            {"event": "explosion", "start": 32.5, "end": 34.0, "confidence": 0.95},
            {"event": "car_screech", "start": 62.0, "end": 64.0, "confidence": 0.92},
            {"event": "cheering", "start": 122.0, "end": 125.0, "confidence": 0.89}
        ]

        mock_utterances = [
            {"start": start, "end": end, "speaker": 0, "text": phrase}
            for start, end, phrase in phrases
            if start < duration_seconds
        ]

        return {
            "text": " ".join(full_text_list),
            "words": all_words,
            "utterances": mock_utterances,
            "sound_events": sound_events
        }

    async def process_segment(self, segment_id: int) -> Optional[Transcript]:
        """Transcribe an un-transcribed segment and persist result."""
        async with AsyncSessionLocal() as db:
            stmt = select(Segment).where(Segment.id == segment_id)
            segment = (await db.execute(stmt)).scalar_one_or_none()
            if not segment:
                return None

            segment.status = SegmentStatus.TRANSCRIBING.value
            await db.commit()

            audio_file = str(self.scratch_audio_dir / f"seg_{segment.id}.wav")
            extracted = self.extract_audio(segment.file_path, audio_file)
            if not extracted or not Path(audio_file).exists() or Path(audio_file).stat().st_size < 1000:
                segment.status = SegmentStatus.FAILED.value
                segment.error_message = "Audio extraction failed or audio stream absent"
                await db.commit()
                return None

            try:
                result = await self.transcribe_audio_file(audio_file, segment.duration_seconds)
                transcript = Transcript(
                    segment_id=segment.id,
                    text=result["text"],
                    words_json=result["words"],
                    sound_events_json=result.get("utterances", []),
                    provider="deepgram" if not self.mock_mode else "deepgram_mock"
                )
                segment.status = SegmentStatus.TRANSCRIBED.value
                db.add(transcript)

                # Record transcription usage
                db.add(UsageRecord(
                    metric_type=MetricType.TRANSCRIPTION_SECONDS.value,
                    count_or_value=segment.duration_seconds,
                    metadata_json={"segment_id": segment.id, "provider": transcript.provider}
                ))

                await db.commit()
                await db.refresh(transcript)
                return transcript
            except Exception as e:
                segment.status = SegmentStatus.FAILED.value
                segment.error_message = f"Transcription error: {str(e)}"
                await db.commit()
                return None
            finally:
                if Path(audio_file).exists():
                    try:
                        Path(audio_file).unlink()
                    except Exception:
                        pass


transcription_worker = DeepgramTranscriptionWorker()
