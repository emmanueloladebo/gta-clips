#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# GTA 6 Cloud Clipping Platform - Deployment & Verification Script
# Target: Ubuntu 22.04 / 24.04 LTS Cloud Linux VPS
# ==============================================================================

echo "=== [1/6] Validating Environment & Prerequisites ==="
if [ ! -f ".env" ]; then
    echo "ERROR: .env file missing in root directory! Please copy docs/ENVIRONMENT.example to .env and configure secrets."
    exit 1
fi

command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker is required. Please install Docker Engine."; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "ERROR: Docker Compose is required."; exit 1; }

echo "=== [2/6] Building Production Container Images ==="
cd infra
docker compose build

echo "=== [3/6] Starting Cloud Services (Postgres, Redis, API, Worker, Web, Caddy) ==="
docker compose up -d

echo "=== [4/6] Waiting for Database & Backend to become Healthy ==="
sleep 8

echo "=== [5/6] Verifying API Health Endpoint ==="
MAX_RETRIES=10
COUNT=0
HEALTHY=false

while [ $COUNT -lt $MAX_RETRIES ]; do
    if curl -s -f http://localhost:8000/api/health >/dev/null 2>&1; then
        HEALTHY=true
        break
    fi
    echo "Waiting for API to respond... ($((COUNT+1))/$MAX_RETRIES)"
    sleep 3
    COUNT=$((COUNT+1))
done

if [ "$HEALTHY" = true ]; then
    echo "SUCCESS: API is responding and healthy!"
    curl -s http://localhost:8000/api/health | python3 -m json.tool || true
else
    echo "WARNING: Health endpoint check timed out. Inspecting logs:"
    docker compose logs --tail=50 api
fi

echo "=== [6/6] Deployment Complete ==="
echo "Access Dashboard at: http://localhost or https://${PUBLIC_DOMAIN:-your-domain}"
echo "Default Admin: admin / GTA6ClipsPass!2026"
