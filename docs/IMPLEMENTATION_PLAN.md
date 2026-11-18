# Implementation milestones

M1: Cloud monorepo, Compose, API, frontend, PostgreSQL migrations, Redis, login, observability and CI.
M2: Streamer registration/permissions, Twitch/YouTube live polling, Streamlink recording worker, FFmpeg segmentation, safe cleanup.
M3: Deepgram transcript pipeline, candidate generation, Groq prompt templates, scoring JSON schema validation, token limits and retries.
M4: Optional vision adapter with sampled frames, candidate dedupe, quality score and clip boundaries.
M5: FFmpeg portrait output, captions, audio normalization, thumbnails, preview.
M6: R2 storage quota, presigned URLs, TTL deletion, startup orphan sweep, usage dashboard.
M7: Zernio adapter verified against official API; approvals, scheduling, status polling, idempotent posting.
M8: Security review, load/soak tests, deployment automation, runbooks and final documentation.

## Data entities
User, Streamer, CreatorPermission, StreamSession, Segment, Transcript, Candidate, Clip, PublishJob, DestinationAccount, StorageObject, UsageRecord, AuditEvent.

## Job states
pending -> running -> succeeded / retry_wait / failed / canceled; separate moderation state: pending_review -> approved/rejected; separate publish state: queued -> submitted -> published/failed.

## Candidate scoring guidance
Start with audio peaks + speech text, 10–60s windows, 5–15s lead-in; ask Groq for JSON containing hook, start/end seconds, excitement, clarity, context, safety flags, score and evidence. Validate timestamps and JSON. Never trust a model's guessed visual events without visual evidence.
