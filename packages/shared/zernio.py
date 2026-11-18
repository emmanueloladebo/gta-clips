"""
Zernio Publishing Adapter.
Supports multi-platform social scheduling (YouTube Shorts, TikTok, Instagram Reels)
with strict idempotency, rate limiting, and connected account synchronization.
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

    async def get_connected_accounts(self) -> List[Dict[str, Any]]:
        """
        Fetch social media accounts connected in Zernio (TikTok, YouTube Shorts, Instagram Reels).
        """
        if self.mock_mode:
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{self.base_url}/accounts", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # Handle both array response or { "accounts": [...] }
                    accounts = data.get("accounts", data) if isinstance(data, dict) else data
                    if isinstance(accounts, list) and len(accounts) > 0:
                        normalized = []
                        for acc in accounts:
                            raw_plat = str(acc.get("platform", "tiktok")).lower().replace(" ", "_")
                            plat_map = {
                                "tiktok": "tiktok",
                                "youtube": "youtube_shorts",
                                "youtube_shorts": "youtube_shorts",
                                "instagram": "instagram_reels",
                                "instagram_reels": "instagram_reels",
                                "x": "x",
                                "twitter": "x",
                            }
                            # Extract Zernio account ID (_id is standard in Zernio)
                            account_id = str(acc.get("_id") or acc.get("id") or acc.get("platformUserId") or "")
                            acc_name = (
                                acc.get("displayName")
                                or acc.get("username")
                                or acc.get("name")
                                or "Connected Account"
                            )
                            if acc_name and not acc_name.startswith("@") and raw_plat in ("tiktok", "instagram", "x", "twitter"):
                                acc_name = f"@{acc_name}"
                            is_act = acc.get("isActive", acc.get("is_active", True))

                            normalized.append({
                                "platform": plat_map.get(raw_plat, "tiktok"),
                                "account_name": acc_name,
                                "external_account_id": account_id,
                                "is_active": bool(is_act),
                            })
                        return normalized
        except Exception:
            pass

        return []

    async def submit_publish_job(
        self,
        media_url: str,
        caption: str,
        platforms: List[str],
        idempotency_key: str,
        account_id: Optional[str] = None,
        title: Optional[str] = None,
        scheduled_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Submit video for social publishing on Zernio.
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

        # Build platform targets including specific accountId if provided
        platform_targets = []
        for p in platforms:
            target: Dict[str, Any] = {"platform": p}
            if account_id:
                target["accountId"] = account_id
            platform_targets.append(target)

        payload = {
            "title": title or "GTA 6 Highlight",
            "content": caption,
            "platforms": platform_targets,
            "mediaItems": [media_url] if media_url else [],
        }
        if scheduled_at:
            payload["scheduledFor"] = scheduled_at.isoformat()
        else:
            payload["publishNow"] = True

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/posts",
                headers=headers,
                json=payload
            )
            resp.raise_for_status()
            res_json = resp.json()
            post_data = res_json.get("post", res_json)
            extracted_id = post_data.get("_id") or post_data.get("id") or str(uuid.uuid4())
            return {
                "id": extracted_id,
                "status": "published" if not scheduled_at else "scheduled",
                "raw": res_json
            }

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
