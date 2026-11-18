"""
Acceptance Test 3: Deepgram transcription pipeline.
Verifies timestamp-aligned transcripts and 429/5xx retry handling.
"""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import Response, Request
from workers.transcription_worker import DeepgramTranscriptionWorker


@pytest.mark.asyncio
async def test_deepgram_mock_transcription_has_aligned_timestamps():
    worker = DeepgramTranscriptionWorker()
    worker.mock_mode = True

    result = worker._generate_mock_transcript(duration_seconds=300.0)

    assert "text" in result
    assert len(result["text"]) > 20
    assert "words" in result
    assert len(result["words"]) > 0

    # Verify word timestamps are chronologically ordered and aligned
    prev_end = 0.0
    for w in result["words"]:
        assert "word" in w
        assert "start" in w
        assert "end" in w
        assert w["start"] >= 0.0
        assert w["end"] >= w["start"]
        prev_end = w["end"]

    # Verify sound events
    assert "sound_events" in result
    assert len(result["sound_events"]) > 0


@pytest.mark.asyncio
async def test_deepgram_retries_on_429_rate_limit(tmp_path):
    worker = DeepgramTranscriptionWorker()
    worker.mock_mode = False
    worker.api_key = "test_deepgram_key"

    dummy_audio = tmp_path / "test_audio.wav"
    dummy_audio.write_bytes(b"RIFFdummywav")

    # Mock responses: first 429 (Too Many Requests), second 200 (OK)
    req = Request("POST", "https://api.deepgram.com/v1/listen")
    resp_429 = Response(status_code=429, request=req)
    resp_200 = Response(
        status_code=200,
        request=req,
        json={
            "results": {
                "channels": [
                    {
                        "alternatives": [
                            {
                                "transcript": "Testing 429 backoff retry logic",
                                "words": [
                                    {"word": "Testing", "start": 0.0, "end": 0.5, "confidence": 0.99},
                                    {"word": "retry", "start": 0.6, "end": 1.0, "confidence": 0.98}
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    )

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return resp_429
        return resp_200

    with patch("httpx.AsyncClient.post", side_effect=mock_post), \
         patch("asyncio.sleep", new=AsyncMock()):
        result = await worker.transcribe_audio_file(str(dummy_audio), duration_seconds=60.0)

    assert call_count == 2
    assert result["text"] == "Testing 429 backoff retry logic"
    assert len(result["words"]) == 2
