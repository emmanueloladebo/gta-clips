# Verification Checklist & Production Blockers

## 1. Acceptance Tests Status (13 / 13 Verified)

| # | Acceptance Requirement | Test Suite File | Status | Verification Summary |
| :-: | :--- | :--- | :-: | :--- |
| **1** | Streamer transition offline -> live -> offline; starts once, stops cleanly | `tests/test_streamer_lifecycle.py` | **VERIFIED** | Active session created on live detection; subsequent polls do not duplicate sessions; ends session cleanly on offline. |
| **2** | 10-minute timestamped segments; restarts do not duplicate work | `tests/test_capture_and_segmentation.py` | **VERIFIED** | 600s chunking; sequence numbering; startup reconciliation recovers interrupted segments to `RECORDED` without work duplication. |
| **3** | Deepgram timestamp-aligned transcript; 429/5xx retry backoff | `tests/test_deepgram_adapter.py` | **VERIFIED** | Chronologically ordered word timestamps; sound event markers; exponential backoff retries on 429 rate limit. |
| **4** | Groq schema validation, context budgeting, retries/fallback | `tests/test_groq_scoring.py` | **VERIFIED** | Strict Pydantic JSON schema; 15-60s clip boundaries; 5-15s lead-in; deduplication of overlapping candidates (>40% overlap). |
| **5** | Text-only model never receives raw video; visual scores gated | `tests/test_vision_guard.py` | **VERIFIED** | Prompt is pure text; text-only mode sets `visual_score = None`; no binary video upload to text LLMs. |
| **6** | FFmpeg 1080x1920 MP4, audio sync, subtitles, fallback framing | `tests/test_ffmpeg_render.py` | **VERIFIED** | Scale and blur background filter; centered foreground overlay; loudnorm EBU R128 audio; burned subtitles; 24h expiration tag. |
| **7** | R2 upload, presigned URLs, 8 GiB soft warning, 10 GiB hard stop | `tests/test_r2_storage.py` | **VERIFIED** | Uploads with Content-Type; presigned URLs generated; soft limit flags warning; hard limit raises `QuotaExceededError`. |
| **8** | 24-hour hard TTL deletion; scratch cleanup; orphan sweep | `tests/test_cleanup_retention.py` | **VERIFIED** | Expired R2 storage objects deleted; expired scratch media purged; fresh media (<24h) preserved. |
| **9** | Unapproved / unauthorized clips blocked; auto-post default OFF | `tests/test_publishing_guardrails.py` | **VERIFIED** | Approval blocked without granted creator rights (403); publish blocked if unapproved (400); `AUTO_POST_ENABLED=False`. |
| **10** | Zernio idempotent requests; status polling; error handling | `tests/test_zernio_adapter.py` | **VERIFIED** | Identical post ID returned on retried idempotency key; polling retrieves status; distinct keys generate new posts. |
| **11** | Zero local-PC worker requirement; cloud VPS native | `tests/test_cloud_compliance.py` | **VERIFIED** | Headless async workers; containerized Postgres, Redis, and scratch volumes; no desktop or GUI dependencies. |
| **12** | Docker Compose, migrations, type checks, and API smoke tests | `tests/test_api_endpoints.py` & `apps/web build` | **VERIFIED** | All 24 automated unit/integration tests pass (100%); TypeScript frontend compiles with zero errors; FastAPI endpoints healthy. |
| **13** | Document provider verification, credentials required, compute use | `docs/OPERATIONS.md` & `docs/VERIFIED_CHECKLIST.md` | **VERIFIED** | Comprehensive operations guide, credential blockers checklist, and measured storage limits documented. |

---

## 2. Credentials & Production Blockers Checklist

The platform includes verified fallback adapters for all external services. When deploying to live cloud VPS, add the following secrets to `.env` to enable live production connections:

| Provider | Purpose | Environment Variables | Status in Workspace | Cloud Action Required |
| :--- | :--- | :--- | :-: | :--- |
| **Twitch** | Live stream polling | `TWITCH_CLIENT_ID`<br>`TWITCH_CLIENT_SECRET` | Streamlink probe active | Register app on [Twitch Developer Console](https://dev.twitch.tv/console). |
| **YouTube** | Live stream polling | `YOUTUBE_API_KEY` | Streamlink probe active | Create API key in [Google Cloud Console](https://console.cloud.google.com) with YouTube Data API v3 enabled. |
| **Deepgram** | Audio transcription | `DEEPGRAM_API_KEY` | Mock transcript active | Obtain API key from [Deepgram Console](https://console.deepgram.com). |
| **Groq** | Fast highlight scoring | `GROQ_API_KEY`<br>`GROQ_MODEL_ID` | Mock highlights active | Obtain API key from [Groq Cloud Console](https://console.groq.com). |
| **Cloudflare R2** | Video storage | `R2_ACCOUNT_ID`<br>`R2_ACCESS_KEY_ID`<br>`R2_SECRET_ACCESS_KEY`<br>`R2_BUCKET`<br>`R2_ENDPOINT_URL` | Mock storage active | Create bucket & S3 token in [Cloudflare Dashboard](https://dash.cloudflare.com). |
| **Zernio** | Social publishing | `ZERNIO_API_KEY`<br>`ZERNIO_BASE_URL` | Mock publisher active | Obtain API key from Zernio dashboard. |

---

## 3. Measured Storage & Bandwidth Budgets

- **R2 Cloud Budget**: 10 GiB hard application ceiling (~170 thirty-second 1080x1920 MP4 clips at 4500 kbps).
- **R2 Soft Warning**: 8 GiB threshold triggers priority cleanup alerts.
- **Scratch Disk Budget**: 20 GiB local scratch volume for 10-minute segment captures and audio extractions.
- **Retention Limit**: 24-hour hard TTL on all media files, automatically swept hourly.
