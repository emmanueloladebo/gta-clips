"""
Acceptance Test 5: Text-only model safety guardrails.
Verifies that text models never receive raw video uploads and visual scores
are gated strictly behind verified multimodal vision models.
"""
import pytest
from workers.candidate_worker import GroqCandidateWorker
from packages.shared.config import settings


def test_text_only_model_never_has_visual_scores():
    worker = GroqCandidateWorker()
    worker.vision_enabled = False  # Default text-only mode

    highlights = worker._generate_mock_highlights(duration_seconds=120.0)

    for h in highlights:
        # Crucial check: Visual scores and descriptions must be None in text-only mode!
        assert h.visual_score is None
        assert h.visual_description is None


def test_groq_prompt_is_pure_text_never_video_blob():
    worker = GroqCandidateWorker()
    transcript = "Car crash at the intersection, police sirens in the background."

    prompt = worker.build_prompt(transcript, 60.0)

    # Prompt must contain plain text instructions and transcript
    assert isinstance(prompt, str)
    assert transcript in prompt
    assert "JSON Schema" in prompt

    # Must never contain binary markers or video stream references
    assert "\x00" not in prompt
    assert "video/mp4" not in prompt
