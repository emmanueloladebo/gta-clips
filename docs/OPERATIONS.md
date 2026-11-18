# Operations & Runbook Guide — GTA 6 Cloud Clipping Platform

This runbook documents production operations, provider API configurations, quota monitoring, and disaster recovery for the GTA 6 Automated Cloud Clipping Platform.

---

## 1. Cloud Architecture & Zero-Local-PC Contract

The platform is designed exclusively for cloud VPS hosting (e.g., Ubuntu 22.04/24.04 LTS on AWS, DigitalOcean, Hetzner, or GCP).
- **All livestream recording, FFmpeg portrait editing, Deepgram audio extraction, Groq scoring, and publishing run in Docker containers on the cloud server.**
- **The operator's personal workstation is never required** for recording, processing, storage, or background worker tasks. The dashboard is accessed via standard web browser over HTTPS.

---

## 2. External Provider Configurations & APIs

### 2.1 Twitch Helix API
- **Purpose**: Low-latency polling of monitored Twitch channels.
- **Official API**: `POST https://id.twitch.tv/oauth2/token` for App Access Tokens, followed by `GET https://api.twitch.tv/helix/streams?user_login={channel}`.
- **Fallback**: When `TWITCH_CLIENT_ID` or `TWITCH_CLIENT_SECRET` is omitted, the capture worker falls back to local Streamlink discovery probes (`streamlink.streams(url)`).
- **Rate Limits**: 800 requests/minute per Client ID (more than sufficient for 3–5 concurrent streamers polled every 30s).

### 2.2 Deepgram Speech Intelligence
- **Purpose**: Fast speech transcription, diarization, and sound event cues (cheering, explosions, gunshots, screams).
- **Official API**: `POST https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&diarize=true&punctuate=true`.
- **Audio Extraction**: Audio is extracted on the VPS scratch disk using FFmpeg to 16kHz mono PCM (`.wav`), cutting upload bandwidth by over 90%.
- **Error Handling**: Implements exponential backoff on HTTP 429 and 5xx errors with up to 3 retries.
- **Fallback / Mock**: Generates realistic game dialogue transcripts with word-level timestamps when `DEEPGRAM_API_KEY` is not configured.

### 2.3 Groq LLM Highlight Inference
- **Purpose**: Fast extraction of high-energy gaming moments, reactions, and clip boundaries (15–60s length with 5–15s lead-in).
- **Official API**: `POST https://api.groq.com/openai/v1/chat/completions` using JSON mode (`response_format: {"type": "json_object"}`).
- **Recommended Model**: `llama-3.3-70b-versatile` or `llama-3.1-8b-instant`.
- **Text-Only Guard**: Groq LLMs are text models. Video is never uploaded to text LLMs. Prompts are strictly bounded transcripts.
- **Vision Model Gating**: Visual scoring is disabled by default (`VISION_MODEL_ENABLED=false`). When disabled, `visual_score` is strictly set to `null` to avoid hallucinated visual commentary.
- **Deduplication**: Automatic time-window intersection analysis filters out overlapping candidates (>40% overlap), keeping the highest scoring clip.

### 2.4 Cloudflare R2 Cloud Storage
- **Purpose**: Storage of final 1080x1920 MP4 clips, JPEG thumbnails, and time-limited presigned URLs.
- **S3 Compatibility**: Connects via `boto3` to `https://{ACCOUNT_ID}.r2.cloudflarestorage.com`.
- **10 GiB Storage Ceiling**:
  - Soft threshold: **8 GiB** (`R2_SOFT_LIMIT_BYTES = 8589934592`). Emits warning alerts and prioritizes cleanup.
  - Hard limit: **10 GiB** (`R2_HARD_LIMIT_BYTES = 10737418240`). Blocks any new uploads with `QuotaExceededError`.
- **Presigned URLs**: Clips are served via secure time-limited URLs (1 hour expiration) to prevent unauthorized public hotlinking.

### 2.5 Zernio Social Publishing
- **Purpose**: Multi-platform distribution to YouTube Shorts, TikTok, Instagram Reels, and X.
- **Official API**: `POST https://api.zernio.com/v1/posts` with `Idempotency-Key` header and Bearer token auth.
- **Idempotency Guarantee**: Every publication job uses a deterministic idempotency key (`pub_{clip_id}_{dest_id}_{timestamp}`) preventing duplicate posts during network retries.
- **Guardrails**:
  - **Review-Before-Post**: Auto-post is disabled by default (`AUTO_POST_ENABLED=false`). Every clip requires manual review and approval in the dashboard.
  - **Creator Rights Check**: Clips cannot be approved or published without a confirmed `CreatorPermission` record (`permission_status = 'granted'`) for the streamer.

---

## 3. Strict 24-Hour Media Retention Policy

To comply with streaming platform guidelines and eliminate runaway storage costs:
1. **Every media file is tagged with an expiration timestamp (`expires_at = created_at + 24 hours`) upon creation.**
2. **Automated Sweep**:
   - The cleanup worker runs an hourly automated purge.
   - Deletes expired R2 objects (`expires_at <= now`).
   - Deletes expired scratch files and temporary audio extractions on the VPS.
3. **Startup Reconciliation**:
   - Whenever the worker container starts or restarts, it sweeps the scratch folder and database to remove orphaned or dangling files from previous runs.
4. **Manual Purge**:
   - Operators can trigger an immediate retention cleanup anytime via the dashboard or `POST /api/storage/cleanup`.

---

## 4. Emergency Procedures & Troubleshooting

| Symptom | Cause | Resolution |
| :--- | :--- | :--- |
| **R2 Hard Quota Error** | Storage usage approached 10 GiB | Trigger manual 24h purge in dashboard (`Storage & Retention -> Run 24h Purge Now`). Old clips will be deleted. |
| **Scratch Disk Warning** | Multiple concurrent streams filled VPS scratch | Worker automatically pauses new captures. Check `docker volume inspect infra_scratch_data`. |
| **Streamer Not Recording** | Streamer is offline or Streamlink probe failed | Click **Check Live** in the Streamers tab. Ensure streamer URL is valid and public. |
| **Clip Approval Denied (403)** | Streamer permission is Pending or Denied | Open Streamers tab -> Click on **Pending Consent** -> Switch status to **Granted** if you have creator rights. |
| **Zernio Publish Failed** | Invalid social account auth or API key | Check **Settings** for credentials status. Retry failed job from the Publishing Hub. |
