"""
Streamer Platform Adapters for Twitch, YouTube, and Streamlink fallback.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import httpx
import streamlink
from packages.shared.config import settings
from packages.shared.enums import StreamerStatus, PlatformType


class TwitchAdapter:
    def __init__(self):
        self.client_id = settings.TWITCH_CLIENT_ID
        self.client_secret = settings.TWITCH_CLIENT_SECRET
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def _get_app_token(self) -> Optional[str]:
        if not self.client_id or not self.client_secret:
            return None
        if self._access_token and self._token_expires_at and datetime.now(timezone.utc) < self._token_expires_at:
            return self._access_token

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://id.twitch.tv/oauth2/token",
                    params={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "client_credentials"
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    self._access_token = data["access_token"]
                    self._token_expires_at = datetime.now(timezone.utc)
                    return self._access_token
        except Exception:
            return None
        return None

    async def check_live_status(self, channel_login: str) -> Dict[str, Any]:
        """
        Check live status using Twitch Helix API (if app keys present)
        or high-speed Twitch GQL metadata endpoint (real-time viewers, title, game without developer keys).
        """
        clean_login = channel_login.lower().strip().replace("https://twitch.tv/", "").replace("twitch.tv/", "").rstrip("/")
        token = await self._get_app_token()
        if token:
            try:
                headers = {
                    "Client-ID": self.client_id,
                    "Authorization": f"Bearer {token}"
                }
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.get(
                        "https://api.twitch.tv/helix/streams",
                        headers=headers,
                        params={"user_login": clean_login}
                    )
                    if res.status_code == 200:
                        data = res.json()
                        streams = data.get("data", [])
                        if streams:
                            s = streams[0]
                            return {
                                "is_live": True,
                                "title": s.get("title", ""),
                                "game": s.get("game_name", ""),
                                "viewers": s.get("viewer_count", 0),
                                "session_id": s.get("id")
                            }
                        return {"is_live": False, "title": None, "game": None, "viewers": 0, "session_id": None}
            except Exception:
                pass

        # High-speed public Twitch GQL metadata endpoint
        try:
            gql_headers = {
                "Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            gql_payload = [
                {
                    "operationName": "StreamMetadata",
                    "variables": {"channelLogin": clean_login},
                    "query": "query StreamMetadata($channelLogin: String!) { user(login: $channelLogin) { stream { id title viewersCount game { name } } } }"
                }
            ]
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post("https://gql.twitch.tv/gql", headers=gql_headers, json=gql_payload)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        stream = data[0].get("data", {}).get("user", {}).get("stream")
                        if stream:
                            return {
                                "is_live": True,
                                "title": stream.get("title") or "GTA 6 Livestream",
                                "game": (stream.get("game") or {}).get("name") or "Grand Theft Auto VI",
                                "viewers": stream.get("viewersCount", 0),
                                "session_id": str(stream.get("id") or "")
                            }
                        return {"is_live": False, "title": None, "game": None, "viewers": 0, "session_id": None}
        except Exception:
            pass

        return await check_streamlink_live(f"https://twitch.tv/{clean_login}")


class YouTubeAdapter:
    def __init__(self):
        self.api_key = settings.YOUTUBE_API_KEY

    async def check_live_status(self, channel_id_or_url: str) -> Dict[str, Any]:
        """Check live status using YouTube Data API or streamlink fallback."""
        if not self.api_key:
            return await check_streamlink_live(channel_id_or_url)

        try:
            # If channel ID, search for live event
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "channelId": channel_id_or_url,
                        "eventType": "live",
                        "type": "video",
                        "key": self.api_key
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("items", [])
                    if items:
                        item = items[0]
                        return {
                            "is_live": True,
                            "title": item["snippet"].get("title", ""),
                            "game": "Grand Theft Auto VI",
                            "viewers": 0,
                            "session_id": item["id"].get("videoId")
                        }
                    return {"is_live": False, "title": None, "game": None, "viewers": 0, "session_id": None}
        except Exception:
            pass

        return await check_streamlink_live(channel_id_or_url)


async def check_streamlink_live(channel_url: str) -> Dict[str, Any]:
    """
    Fallback probe using streamlink CLI.
    Checks whether live streams are discoverable without requiring platform API keys.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "streamlink", "--json", channel_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=12.0)
        if proc.returncode == 0 and stdout:
            import json
            data = json.loads(stdout.decode())
            meta = data.get("metadata", {})
            return {
                "is_live": True,
                "title": meta.get("title") or "Live Stream",
                "game": meta.get("category") or "Grand Theft Auto VI",
                "viewers": 0,
                "session_id": str(meta.get("id") or f"sl_{int(datetime.now(timezone.utc).timestamp())}")
            }
    except Exception:
        pass

    return {
        "is_live": False,
        "title": None,
        "game": None,
        "viewers": 0,
        "session_id": None
    }


twitch_adapter = TwitchAdapter()
youtube_adapter = YouTubeAdapter()


async def check_streamer_live(platform: str, channel_id: str, channel_url: str) -> Dict[str, Any]:
    if platform.lower() == PlatformType.TWITCH.value:
        return await twitch_adapter.check_live_status(channel_id)
    elif platform.lower() == PlatformType.YOUTUBE.value:
        return await youtube_adapter.check_live_status(channel_id or channel_url)
    else:
        return await check_streamlink_live(channel_url)
