"""
Configuration module loading environment variables with strict typing.
"""
import os
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "GTA 6 Cloud Clipping Platform"
    APP_ENV: str = "production"
    DEBUG: bool = False
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Database & Cache
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/clips.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SESSION_SECRET: str = "super-secret-production-key-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Streamer Platforms
    TWITCH_CLIENT_ID: str = ""
    TWITCH_CLIENT_SECRET: str = ""
    YOUTUBE_API_KEY: str = ""

    # Audio Transcription (Deepgram)
    DEEPGRAM_API_KEY: str = ""
    DEEPGRAM_MODEL: str = "nova-3"
    DEEPGRAM_BASE_URL: str = "https://api.deepgram.com/v1"

    # AI Highlight Scorer (Groq LLM)
    GROQ_API_KEY: str = ""
    GROQ_MODEL_ID: str = "openai/gpt-oss-120b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # Fallback LLM Provider
    FALLBACK_LLM_PROVIDER: str = "disabled"  # disabled | openai | anthropic
    FALLBACK_LLM_MODEL_ID: str = ""
    FALLBACK_LLM_API_KEY: str = ""

    # Optional Vision Model Gating
    VISION_MODEL_ENABLED: bool = False
    VISION_MODEL_ID: str = "llama-3.2-11b-vision-preview"

    # Cloudflare R2 Storage
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = "clips"
    R2_ENDPOINT_URL: str = ""
    R2_PUBLIC_URL_PREFIX: str = ""  # If public CDN or custom domain enabled
    R2_SOFT_LIMIT_BYTES: int = 8 * 1024 * 1024 * 1024  # 8 GiB
    R2_HARD_LIMIT_BYTES: int = 10 * 1024 * 1024 * 1024  # 10 GiB

    # Scratch Media Storage (VPS local storage)
    SCRATCH_DIR: str = str(Path(__file__).parent.parent.parent / "scratch")
    SCRATCH_LIMIT_BYTES: int = 55 * 1024 * 1024 * 1024  # 55 GiB (matching ~60 GiB EBS volume)

    # Retention & Capture Rules
    MEDIA_TTL_HOURS: int = 24  # Hard 24h retention policy
    SEGMENT_SECONDS: int = 600  # 10 minutes per segment
    MAX_CONCURRENT_STREAMS: int = 3
    AUTO_POST_ENABLED: bool = False  # Review-before-post default
    VIRAL_SCORE_THRESHOLD: float = 65.0  # Captures viral moments, missions, unhinged NPCs, and gameplay chaos (0-100)

    # Social Publishing (Zernio)
    ZERNIO_API_KEY: str = ""
    ZERNIO_BASE_URL: str = "https://api.zernio.com/v1"
    ZERNIO_ACCOUNT_IDS: str = ""

    # Video Rendering Options
    WATERMARK_TEXT: str = "GTA 6 CLIPS"
    DEFAULT_FONT: str = "Arial"
    RENDER_FPS: int = 30
    RENDER_BITRATE: str = "4500k"

    # Security
    CORS_ORIGINS: List[str] = ["*"]


settings = Settings()

# Ensure scratch directory exists
os.makedirs(settings.SCRATCH_DIR, exist_ok=True)
os.makedirs(Path(__file__).parent.parent.parent / "data", exist_ok=True)
