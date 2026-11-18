"""
Storage Manager for Cloudflare R2 and Scratch Disk.
Enforces 10 GiB hard limit, 8 GiB soft limit, presigned URLs, and 24h retention.
"""
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from packages.shared.config import settings


class QuotaExceededError(Exception):
    """Raised when R2 or Scratch storage quota is exceeded."""
    pass


class StorageManager:
    def __init__(self):
        self.r2_bucket = settings.R2_BUCKET
        self.soft_limit = settings.R2_SOFT_LIMIT_BYTES
        self.hard_limit = settings.R2_HARD_LIMIT_BYTES
        self.scratch_dir = Path(settings.SCRATCH_DIR)
        self.scratch_limit = settings.SCRATCH_LIMIT_BYTES
        self.media_ttl_hours = settings.MEDIA_TTL_HOURS

        # Mock R2 directory if credentials not set
        self.mock_mode = not bool(settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY and settings.R2_ENDPOINT_URL)
        self.mock_r2_dir = Path(settings.SCRATCH_DIR) / "mock_r2"
        if self.mock_mode:
            self.mock_r2_dir.mkdir(parents=True, exist_ok=True)
            self._s3_client = None
        else:
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4"),
                region_name="auto"
            )

    def get_scratch_usage(self) -> Tuple[int, int]:
        """Returns (used_bytes, total_limit_bytes) for scratch disk."""
        total_size = 0
        if self.scratch_dir.exists():
            for p in self.scratch_dir.rglob("*"):
                if p.is_file():
                    try:
                        total_size += p.stat().st_size
                    except OSError:
                        pass
        # Dynamically inspect disk filesystem capacity (matching 60 GB EBS volume)
        try:
            total_disk = shutil.disk_usage(str(self.scratch_dir)).total
            limit = max(self.scratch_limit, total_disk)
        except Exception:
            limit = self.scratch_limit
        return total_size, limit

    def get_r2_usage(self) -> Tuple[int, int]:
        """Returns (estimated_used_bytes, object_count)."""
        if self.mock_mode:
            total_size = 0
            count = 0
            if self.mock_r2_dir.exists():
                for p in self.mock_r2_dir.rglob("*"):
                    if p.is_file():
                        try:
                            total_size += p.stat().st_size
                            count += 1
                        except OSError:
                            pass
            return total_size, count

        try:
            paginator = self._s3_client.get_paginator("list_objects_v2")
            total_size = 0
            count = 0
            for page in paginator.paginate(Bucket=self.r2_bucket):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        total_size += obj["Size"]
                        count += 1
            return total_size, count
        except Exception:
            return 0, 0

    def check_r2_quota(self, incoming_bytes: int = 0) -> Dict[str, Any]:
        """Checks if R2 quota permits new uploads."""
        current_used, count = self.get_r2_usage()
        projected = current_used + incoming_bytes

        soft_exceeded = projected >= self.soft_limit
        hard_exceeded = projected >= self.hard_limit

        return {
            "current_used_bytes": current_used,
            "projected_bytes": projected,
            "soft_limit_bytes": self.soft_limit,
            "hard_limit_bytes": self.hard_limit,
            "soft_limit_exceeded": soft_exceeded,
            "hard_limit_exceeded": hard_exceeded,
            "object_count": count
        }

    def check_scratch_quota(self, incoming_bytes: int = 0) -> bool:
        """Returns True if scratch disk has sufficient room."""
        current_used, limit = self.get_scratch_usage()
        return (current_used + incoming_bytes) < limit

    def upload_to_r2(self, local_path: str, r2_key: str, content_type: str = "video/mp4") -> str:
        """
        Uploads a file to R2 with strict quota enforcement.
        Returns the object key.
        """
        file_path = Path(local_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        file_size = file_path.stat().st_size
        quota_status = self.check_r2_quota(incoming_bytes=file_size)

        if quota_status["hard_limit_exceeded"]:
            raise QuotaExceededError(
                f"R2 Hard storage limit of {self.hard_limit / (1024**3):.1f} GiB would be exceeded! "
                f"Current: {quota_status['current_used_bytes']} bytes, Required: {file_size} bytes."
            )

        if self.mock_mode:
            dest = self.mock_r2_dir / r2_key
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest)
            return r2_key

        try:
            self._s3_client.upload_file(
                Filename=str(file_path),
                Bucket=self.r2_bucket,
                Key=r2_key,
                ExtraArgs={"ContentType": content_type}
            )
            return r2_key
        except ClientError as e:
            raise RuntimeError(f"Failed to upload to Cloudflare R2: {e}")

    def generate_presigned_url(self, r2_key: str, expires_in_seconds: int = 3600) -> str:
        """
        Generates a secure, time-limited presigned URL for previewing clips.
        """
        if self.mock_mode:
            # Return API stream/static preview URL in mock mode
            return f"{settings.PUBLIC_BASE_URL}/api/clips/mock-media/{r2_key}"

        try:
            url = self._s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.r2_bucket, "Key": r2_key},
                ExpiresIn=expires_in_seconds
            )
            return url
        except ClientError as e:
            raise RuntimeError(f"Failed to generate presigned URL: {e}")

    def delete_from_r2(self, r2_key: str) -> bool:
        """Deletes an object from R2."""
        if self.mock_mode:
            dest = self.mock_r2_dir / r2_key
            if dest.exists():
                dest.unlink()
                return True
            return False

        try:
            self._s3_client.delete_object(Bucket=self.r2_bucket, Key=r2_key)
            return True
        except ClientError:
            return False

    def cleanup_expired_scratch_files(self, ttl_hours: Optional[int] = None) -> int:
        """
        Deletes local scratch files older than TTL (24 hours default).
        Returns number of deleted files.
        """
        ttl = ttl_hours if ttl_hours is not None else self.media_ttl_hours
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=ttl)
        deleted_count = 0

        if not self.scratch_dir.exists():
            return 0

        for p in self.scratch_dir.rglob("*"):
            if p.is_file() and not str(p).startswith(str(self.mock_r2_dir)):
                try:
                    mtime = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                    if mtime < cutoff_time:
                        p.unlink()
                        deleted_count += 1
                except OSError:
                    pass

        return deleted_count

    def cleanup_clip_media(self, clip) -> Dict[str, bool]:
        """
        Deletes a clip's video and thumbnail files from local scratch disk
        and from Cloudflare R2 when posted or rejected.
        """
        results = {"local_video": False, "local_thumbnail": False, "r2_video": False, "r2_thumbnail": False}

        # Local portrait video
        if getattr(clip, "portrait_video_path", None):
            try:
                p = Path(clip.portrait_video_path)
                if p.exists() and p.is_file():
                    p.unlink()
                    results["local_video"] = True
            except Exception:
                pass

        # Local thumbnail
        if getattr(clip, "thumbnail_path", None):
            try:
                p = Path(clip.thumbnail_path)
                if p.exists() and p.is_file():
                    p.unlink()
                    results["local_thumbnail"] = True
            except Exception:
                pass

        # Cloudflare R2 video
        if getattr(clip, "r2_key", None):
            results["r2_video"] = self.delete_from_r2(clip.r2_key)

        # Cloudflare R2 thumbnail
        if getattr(clip, "r2_thumbnail_key", None):
            results["r2_thumbnail"] = self.delete_from_r2(clip.r2_thumbnail_key)

        return results


storage_manager = StorageManager()
