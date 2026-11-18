# Product requirements

## User journeys
- Owner signs in to web dashboard, adds authorized streamer channel URL and platform, enables monitoring, sees online/offline state.
- When channel goes live, cloud worker captures in ~10-minute segments with timestamps and resumes safely after failure.
- Deepgram transcribes audio, diarization when available; sound-energy and speech cues identify candidate windows. Groq scores bounded transcript snippets, optionally enriched by sampled frames through a verified vision-capable adapter.
- Candidate highlights include 5–15 seconds of lead-in and a configurable 15–60 second total length. Rank and avoid duplicates; provide explanations and confidence.
- Generate vertical 1080x1920 H.264/AAC MP4, readable burned captions, correct audio sync, watermark/source attribution as configured; preserve gameplay and facecam when possible.
- Upload final clips to R2, expose time-limited preview links, review/approve/reject, queue for Zernio publishing. Auto-post disabled by default; opt-in requires confirmation.
- Maintain provenance and permission status, errors, retry controls, clip and upload states, and usage/cost counters.

## Defaults
- 3–5 concurrent streamers; configurable concurrency and bitrate.
- 10-minute capture segments, shorter API-bound chunks if required.
- 24-hour hard TTL for all media, including R2 and VPS scratch, with hourly cleanup and startup reconciliation.
- 10 GiB max R2 storage budget with 8 GiB soft limit; stop uploads before hard cap. Disk scratch budget also configurable.
- Publish only approved clips from authorized creators; do not repost copyrighted music without rights.
- Fully cloud-hosted: browser UI only on user's local device.

## Nonfunctional
- Least-privilege secrets, encrypted HTTPS, authentication, rate limiting, CORS allowlist, signed preview URLs, logs without secrets.
- Idempotent jobs, retries with exponential backoff, distributed locking, graceful shutdown, no duplicate publications.
- Queue backpressure when storage, provider quota, or processing capacity exhausted.
- Track streaming bandwidth, compute time, transcription minutes, AI tokens, R2 usage and social publishing errors.
- Document limitations: API pricing/free tiers change; content rights; livestream platform support may vary; no guarantee of viral performance.
