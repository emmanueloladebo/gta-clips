# Cloud architecture

Browser -> HTTPS reverse proxy -> React dashboard + FastAPI API -> PostgreSQL
                                                        -> Redis job queue
Scheduler -> platform live-status adapter -> recorder worker (Streamlink -> FFmpeg 10-min files on VPS scratch)
                                        -> Deepgram audio transcription -> event candidate extractor
                                        -> Groq text scorer + optional sampled-frame vision adapter
                                        -> FFmpeg clip editor -> Cloudflare R2
                                        -> moderation/approval queue -> Zernio publish adapter
Cleanup scheduler -> scratch and R2 deletion, storage quotas, orphan reconciliation

## Design notes
- Keep recordings on VPS scratch only until processed and at most 24 hours; do not store all raw video in R2.
- R2 stores final MP4, optional thumbnail and short-lived manifests. Signed URLs for dashboard preview.
- A six-hour 5 Mbps stream is about 13.5 GB; multiple concurrent streams can exceed a small VPS disk. Enforce scratch quotas and process/delete segments promptly.
- Text-only Groq scoring cannot see visual events: sampled keyframes must use a supported vision model or explicitly mark visual scoring unavailable.
- Use official Twitch/YouTube live-state methods where available; use Streamlink plugin support as a capture capability, not guaranteed support for all sites.
- Use per-streamer authorization records and source links for attribution.

## Suggested repository layout
apps/api/ (FastAPI, auth, CRUD, provider adapters)
apps/web/ (React TS dashboard)
workers/ (capture, transcription, scoring, render, publish, cleanup)
packages/shared/ (schemas, configs, job states)
infra/ (compose, nginx/caddy, provisioning, backups)
tests/ (unit, integration, end-to-end)
docs/ (operations, provider setup, troubleshooting)
