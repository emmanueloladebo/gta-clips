# GTA 6 Cloud Highlights — Automated Livestream Clipping Platform

A production-grade, cloud-native automated platform for monitoring GTA 6 livestreams, recording broadcasts in 10-minute segments, detecting hype moments with Deepgram and Groq, editing vertical 1080x1920 (9:16) clips with FFmpeg, storing finished clips in Cloudflare R2, enforcing strict 24-hour media retention, and publishing to social accounts via Zernio.

---

## Highlights & Features

- **Cloud-Only Architecture**: Runs entirely on a cloud Linux VPS using Docker Compose. The operator's personal computer is never needed for capture, video processing, or storage.
- **Automated Stream Ingest**: Monitors Twitch and YouTube channels, captures live broadcasts via Streamlink, and produces timestamped 10-minute segments on local scratch storage with restart recovery.
- **Deepgram Audio Intelligence**: Transcribes audio with word-level timestamps, diarization, and sound event cues (cheering, explosions, gunshots, screams) with 429/5xx exponential backoff retries.
- **Groq Highlight Scorer**: Prompts fast Groq LLMs (`llama-3.3-70b-versatile`) with strict JSON schemas, 5–15s context lead-in, confidence scoring, and deduplication.
- **FFmpeg 9:16 Vertical Video Editor**: Generates 1080x1920 portrait MP4s with centered gameplay, blurred background framing, burned subtitles, EBU R128 audio normalization, and watermark attribution.
- **Cloudflare R2 Storage with Quota Defense**: Enforces a strict 10 GiB hard storage ceiling and 8 GiB soft warning limit with secure presigned preview URLs.
- **Strict 24-Hour Media Retention**: Automatically purges all raw scratch segments, temporary audio, and R2 cloud objects older than 24 hours via an hourly background worker.
- **Content Rights & Review-Before-Post Guard**: Auto-posting defaults to **OFF**. Clips require confirmed creator permissions and operator approval before submission to social networks.
- **Zernio Publishing Adapter**: Multi-platform distribution (YouTube Shorts, TikTok, Instagram Reels) with idempotency guarantees and asynchronous status polling.
- **Modern Web Dashboard**: Fast React + TypeScript + Tailwind CSS UI for managing streamers, previewing vertical clips in a mobile frame, tracking storage quotas, and managing social queues.

---

## Repository Structure

```
gta-clips/
├── apps/
│   ├── api/                  # FastAPI backend (auth, streamers, clips, publishing, storage)
│   │   ├── routes/           # REST endpoints
│   │   ├── auth.py           # JWT & password hashing
│   │   └── main.py           # Application entrypoint
│   └── web/                  # React + TypeScript + Vite + Tailwind CSS dashboard
│       ├── src/components/   # Header, Sidebar, Review, Streamers, Publishing, Storage
│       └── dist/             # Production bundled frontend
├── packages/
│   └── shared/               # Shared schemas, models, config, and adapters
│       ├── config.py         # Pydantic Settings configuration
│       ├── database.py       # Async SQLAlchemy engine & session factory
│       ├── models.py         # Database models (Streamer, Clip, Candidate, etc.)
│       ├── schemas.py        # Pydantic v2 validation contracts
│       ├── storage.py        # Cloudflare R2 & scratch storage manager
│       ├── platforms.py      # Twitch & YouTube platform adapters
│       └── zernio.py         # Zernio publishing adapter
├── workers/                  # Cloud background worker pipeline
│   ├── capture_worker.py     # Streamlink ingest & FFmpeg segmentation
│   ├── transcription_worker.py # Deepgram audio transcription
│   ├── candidate_worker.py   # Groq LLM highlight detection & dedupe
│   ├── render_worker.py      # FFmpeg 1080x1920 portrait editor
│   ├── storage_worker.py     # Cloudflare R2 uploader & quota manager
│   ├── cleanup_worker.py     # 24-hour retention purge & orphan reconciler
│   ├── publish_worker.py     # Auto-post evaluator & Zernio publisher
│   └── runner.py             # Unified background worker loop
├── infra/                    # Cloud container infrastructure
│   ├── docker-compose.yml    # Multi-container setup (Postgres, Redis, API, Worker, Web, Caddy)
│   ├── Dockerfile.api        # Python 3.12 API container
│   ├── Dockerfile.worker     # Python 3.12 Worker container (with FFmpeg & Streamlink)
│   ├── Dockerfile.web        # Multi-stage Web container
│   ├── Caddyfile             # HTTPS reverse proxy configuration
│   └── deploy.sh             # Deployment and health check script
├── tests/                    # 24 Automated acceptance tests
├── docs/                     # Specifications, runbooks, and checklists
└── requirements.txt          # Python dependencies
```

---

## Quickstart & Local Testing

### 1. Run the Automated Test Suite (24 / 24 Tests Passing)
```bash
python -m pytest -v
```

### 2. Run Backend Locally
```bash
uvicorn apps.api.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`
- Default Admin Login: `admin` / `GTA6ClipsPass!2026`

### 3. Run Frontend Dashboard
```bash
cd apps/web
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Production Cloud Deployment (Linux VPS)

1. Provision an Ubuntu 22.04 or 24.04 LTS VPS with Docker and Docker Compose installed.
2. Clone this repository onto the cloud server:
   ```bash
   git clone <repo-url> /opt/gta-clips
   cd /opt/gta-clips
   ```
3. Copy environment configuration and configure secrets:
   ```bash
   cp docs/ENVIRONMENT.example .env
   nano .env
   ```
4. Run the automated deployment script:
   ```bash
   bash infra/deploy.sh
   ```
   Or launch directly via Docker Compose:
   ```bash
   cd infra
   docker compose up -d --build
   ```
5. Access your secure dashboard at `https://your-domain` or `http://server-ip`.

---

## Documentation

- [MASTER_PROMPT.md](file:///c:/Users/olade/Documents/GitHub/gta-clips/docs/MASTER_PROMPT.md) — Master build instructions and rules
- [OPERATIONS.md](file:///c:/Users/olade/Documents/GitHub/gta-clips/docs/OPERATIONS.md) — Production operations & runbook
- [VERIFIED_CHECKLIST.md](file:///c:/Users/olade/Documents/GitHub/gta-clips/docs/VERIFIED_CHECKLIST.md) — 13/13 acceptance test verification and credentials checklist
- [ARCHITECTURE.md](file:///c:/Users/olade/Documents/GitHub/gta-clips/docs/ARCHITECTURE.md) — Infrastructure design
- [REQUIREMENTS.md](file:///c:/Users/olade/Documents/GitHub/gta-clips/docs/REQUIREMENTS.md) — Product requirements and guardrails
