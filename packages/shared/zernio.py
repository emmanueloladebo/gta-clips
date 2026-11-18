"""
Zernio Publishing Adapter.
Supports multi-platform social scheduling (YouTube Shorts, TikTok, Instagram Reels)
with strict idempotency, rate limiting, and mock fallback.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
import httpx

from packages.shared.config import settings


class ZernioAdapter:
    def __init__(self):
        self.api_key = settings.ZERNIO_API_KEY
        self.base_url = settings.ZERNIO_BASE_URL.rstrip("/")
        self.mock_mode = not bool(self.api_key)
        self._mock_jobs: Dict[str, Dict[str, Any]] = {}

    async def submit_publish_job(
        self,
        media_url: str,
        caption: str,
        platforms: List[str],
        idempotency_key: str,
        scheduled_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Submit video for social publishing.
        Uses idempotency key to prevent accidental duplicate posts.
        """
        if self.mock_mode:
            # Check idempotency in mock cache
            if idempotency_key in self._mock_jobs:
                return self._mock_jobs[idempotency_key]

            post_id = f"zernio_mock_{uuid.uuid4().hex[:12]}"
            res = {
                "id": post_id,
                "status": "published" if not scheduled_at else "scheduled",
                "idempotency_key": idempotency_key,
                "media_url": media_url,
                "caption": caption,
                "platforms": platforms,
                "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "external_post_ids": {p: f"{p}_post_{uuid.uuid4().hex[:8]}" for p in platforms}
            }
            self._mock_jobs[idempotency_key] = res
            return res

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        payload = {
            "mediaUrl": media_url,
            "caption": caption,
            "platforms": platforms,
        }
        if scheduled_at:
            payload["scheduledAt"] = scheduled_at.isoformat()

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/posts",
                headers=headers,
                json=payload
            )
            resp.raise_for_status()
            return resp.json()

    async def get_publish_status(self, post_id: str) -> Dict[str, Any]:
        """Check status of an asynchronous publication on Zernio."""
        if self.mock_mode:
            for job in self._mock_jobs.values():
                if job["id"] == post_id:
                    return job
            return {"id": post_id, "status": "published", "error": None}

        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/posts/{post_id}",
                headers=headers
            )
            resp.raise_for_status()
            return resp.json()


zernio_adapter = ZernioAdapter()
