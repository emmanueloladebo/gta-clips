# Acceptance tests

1. With mocked Twitch live status, a streamer transitions offline -> live -> offline, recording starts once and stops cleanly.
2. Streamlink/FFmpeg capture of authorized sample input produces 10-minute-or-shorter timestamped chunks; restarts do not duplicate work.
3. Deepgram mocked response produces timestamp-aligned transcript and graceful retry on 429/5xx.
4. Groq mocked response is schema-validated, truncated/split to context budget, and retries/falls back on rate limits.
5. A text-only model never receives a raw video upload; visual scores only appear with verified vision output.
6. FFmpeg produces playable 1080x1920 MP4, synced audio, subtitles, and sensible fallback framing.
7. R2 mocked upload and presigned preview work; exceeding soft/hard quota triggers throttling and blocks uploads.
8. Objects and scratch media older than 24 hours are deleted; orphan cleanup and failed-delete alerts work.
9. Unauthorized or unapproved clips cannot be published; explicit auto-post setting defaults OFF.
10. Zernio mocked publish requests are idempotent; status polling handles delayed success and errors.
11. No local-PC worker requirement; all processing runs on cloud VPS.
12. Docker Compose startup, tests, lint/type checks, migration and basic browser smoke test pass.
13. Document actual provider API verification, credentials still required, and measured compute/storage use.
