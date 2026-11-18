# Deployment contract

Target: cloud Linux VPS with Docker Engine/Compose, persistent PostgreSQL volume, Redis, HTTPS reverse proxy, separate scratch media volume, domain and DNS. No local workstation processes.

1. Provision VPS with enough CPU, RAM, scratch disk, bandwidth and monthly transfer for chosen concurrent streams. Start with 1–2 streams and measure before scaling to 3–5.
2. Install Docker, configure firewall, SSH keys, unattended security patches, backup policy, monitoring and disk alerts.
3. Create R2 bucket and least-privilege API token, set lifecycle rules where feasible; use application cleanup to guarantee <=24h retention (lifecycle rules alone may not be exact-hour).
4. Create Deepgram, Groq, Twitch/YouTube and Zernio credentials and social account connections. Verify current provider limits and API docs.
5. Put secrets in cloud-side environment/secret manager. Deploy Compose, run DB migrations, configure TLS and smoke tests.
6. Test with licensed sample footage and one authorized streamer; review clips and test Zernio drafts before enabling publishing.
7. Monitor CPU, disk, network, provider bills and storage. Apply budget alerts and stop recording when storage is critically low.

Cost caveat: 10 GiB R2 does not mean total system footage stays within 10 GiB; capture scratch is separate. Deepgram/Groq and Zernio free/paid tiers must be confirmed. Bandwidth and compute may dominate costs.

The agent must not claim a deployment happened unless it has actually deployed and verified a public URL. Never expose secrets in logs or generated files.
