"""
Render Worker: FFmpeg vertical (9:16) video editor.
Renders 1080x1920 MP4 with audio normalization, burned subtitles,
watermark attribution, thumbnail export, and 24h retention tag.
"""
import asyncio
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import Candidate, Segment, StreamSession, Streamer, Clip, UsageRecord
from packages.shared.enums import CandidateStatus, ApprovalStatus, MetricType
from workers.facecam_detector import facecam_detector


class FFmpegRenderWorker:
    def __init__(self):
        self.output_dir = Path(settings.SCRATCH_DIR) / "clips"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.watermark_text = settings.WATERMARK_TEXT

    def build_ffmpeg_filter(
        self,
        streamer_name: str,
        quote_text: str,
        headline_text: str = "",
        facecam_pos: str = "top_right",
        crop_cam: Optional[str] = None
    ) -> str:
        """
        Creates an FFmpeg complex filter for viral split-screen vertical video:
        1. Top: Streamer facecam cropped and scaled to 1080x760.
        2. Bottom: Main GTA 6 gameplay cropped and scaled to 1080x1160.
        3. Middle Divider: Dynamic AI headline banner with bold high-contrast text.
        4. Attribution watermark at top and spoken subtitles at bottom.
        """
        escaped_streamer = streamer_name.replace("'", "\\'").replace(":", "\\:")
        clean_headline = (headline_text or "GTA 6 HIGHLIGHT").upper().replace("'", "\\'").replace(":", "\\:")
        clean_quote = quote_text[:70].replace("'", "\\'").replace(":", "\\:")

        # If dynamic facecam crop coordinates provided from detection, use them
        if not crop_cam or not crop_cam.startswith("crop="):
            if facecam_pos == "top_left":
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=0:y=0"
            elif facecam_pos == "middle_left":
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=0:y=ih*0.28"
            elif facecam_pos == "bottom_right":
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=iw*0.65:y=ih*0.58"
            elif facecam_pos == "bottom_left":
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=0:y=ih*0.58"
            elif facecam_pos == "middle_right":
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=iw*0.65:y=ih*0.28"
            elif facecam_pos == "top_center" or facecam_pos == "center_zoom":
                crop_cam = "crop=w=iw*0.42:h=ih*0.45:x=iw*0.29:y=0"
            else:  # top_right default
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=iw*0.65:y=0"

        filter_complex = (
            # 1. Split stream into facecam feed and gameplay feed
            "[0:v]split=2[raw_cam][raw_game];"
            # 2. Crop streamer facecam and scale to 1080x760
            f"[raw_cam]{crop_cam},scale=1080:760:force_original_aspect_ratio=increase,crop=1080:760[facecam];"
            # 3. Scale & crop gameplay to 1080x1160
            "[raw_game]scale=2062:1160:force_original_aspect_ratio=increase,crop=1080:1160[gameplay];"
            # 4. Vertical stack: Facecam on top, gameplay on bottom (total 1080x1920)
            "[facecam][gameplay]vstack=inputs=2[stacked];"
            # 5. Middle headline banner dividing bar (y = 715 to 805)
            "[stacked]drawbox=y=715:w=1080:h=90:color=black@0.85:t=fill[bannered];"
            # 6. Headline text overlay
            f"[bannered]drawtext=text='{clean_headline}':fontsize=36:fontcolor=yellow:x=(w-text_w)/2:y=742:shadowcolor=black:shadowx=2:shadowy=2[headlined];"
            # 7. Watermark attribution banner at top
            f"[headlined]drawtext=text='@{escaped_streamer} | GTA 6':fontsize=28:fontcolor=white:x=(w-text_w)/2:y=24:box=1:boxcolor=black@0.6:boxborderw=6[watermarked];"
            # 8. Spoken caption/subtitle near bottom of gameplay
            f"[watermarked]drawtext=text='{clean_quote}':fontsize=36:fontcolor=white:x=(w-text_w)/2:y=1640:box=1:boxcolor=black@0.7:boxborderw=8[final_v]"
        )
        return filter_complex

    def render_vertical_clip(
        self,
        input_file: str,
        start_sec: float,
        duration_sec: float,
        output_file: str,
        streamer_name: str,
        quote_text: str,
        headline_text: str = "",
        facecam_pos: str = "top_right",
        crop_cam: Optional[str] = None
    ) -> bool:
        """Execute FFmpeg command to produce 1080x1920 H.264/AAC MP4 using external text files."""
        temp_dir = self.output_dir / "tmp_text"
        temp_dir.mkdir(parents=True, exist_ok=True)
        unique_prefix = f"render_{int(datetime.now(timezone.utc).timestamp()*1000)}_{os.getpid()}"

        headline_file = temp_dir / f"{unique_prefix}_headline.txt"
        watermark_file = temp_dir / f"{unique_prefix}_watermark.txt"
        sub_file = temp_dir / f"{unique_prefix}_sub.txt"

        clean_headline = (headline_text or "GTA 6 HIGHLIGHT").upper()
        clean_streamer = f"@{streamer_name} | GTA 6"
        clean_quote = (quote_text or "")[:80]

        headline_file.write_text(clean_headline, encoding="utf-8")
        watermark_file.write_text(clean_streamer, encoding="utf-8")
        sub_file.write_text(clean_quote, encoding="utf-8")

        # In FFmpeg, escape colon and backslash in textfile path
        h_path = str(headline_file).replace("\\", "/").replace(":", "\\:")
        w_path = str(watermark_file).replace("\\", "/").replace(":", "\\:")
        s_path = str(sub_file).replace("\\", "/").replace(":", "\\:")

        if not crop_cam or not crop_cam.startswith("crop="):
            if facecam_pos == "top_left":
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=0:y=0"
            elif facecam_pos == "middle_left":
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=0:y=ih*0.28"
            elif facecam_pos == "bottom_right":
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=iw*0.65:y=ih*0.58"
            elif facecam_pos == "bottom_left":
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=0:y=ih*0.58"
            elif facecam_pos == "middle_right":
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=iw*0.65:y=ih*0.28"
            elif facecam_pos == "top_center" or facecam_pos == "center_zoom":
                crop_cam = "crop=w=iw*0.42:h=ih*0.45:x=iw*0.29:y=0"
            else:  # top_right default
                crop_cam = "crop=w=iw*0.35:h=ih*0.42:x=iw*0.65:y=0"

        filter_str = (
            "[0:v]split=2[raw_cam][raw_game];"
            f"[raw_cam]{crop_cam},scale=1080:760:force_original_aspect_ratio=increase,crop=1080:760[facecam];"
            "[raw_game]scale=2062:1160:force_original_aspect_ratio=increase,crop=1080:1160[gameplay];"
            "[facecam][gameplay]vstack=inputs=2[stacked];"
            "[stacked]drawbox=y=715:w=1080:h=90:color=black@0.85:t=fill[bannered];"
            f"[bannered]drawtext=textfile='{h_path}':fontsize=36:fontcolor=yellow:x=(w-text_w)/2:y=742:shadowcolor=black:shadowx=2:shadowy=2[headlined];"
            f"[headlined]drawtext=textfile='{w_path}':fontsize=28:fontcolor=white:x=(w-text_w)/2:y=24:box=1:boxcolor=black@0.6:boxborderw=6[watermarked];"
            f"[watermarked]drawtext=textfile='{s_path}':fontsize=36:fontcolor=white:x=(w-text_w)/2:y=1640:box=1:boxcolor=black@0.7:boxborderw=8[final_v]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-t", str(duration_sec),
            "-i", input_file,
            "-filter_complex", filter_str,
            "-map", "[final_v]",
            "-map", "0:a?",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-b:v", settings.RENDER_BITRATE,
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            output_file
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240)
            if res.returncode == 0 and Path(output_file).exists() and Path(output_file).stat().st_size > 50000:
                return True
            return False
        except Exception:
            return False
        finally:
            for tf in (headline_file, watermark_file, sub_file):
                if tf.exists():
                    try:
                        tf.unlink()
                    except Exception:
                        pass

    def generate_thumbnail(self, video_file: str, output_thumb: str, at_second: float = 1.0) -> bool:
        """Extract high-resolution 1080x1920 thumbnail JPEG."""
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(at_second),
            "-i", video_file,
            "-vframes", "1",
            "-q:v", "2",
            output_thumb
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            if res.returncode == 0 and Path(output_thumb).exists() and Path(output_thumb).stat().st_size > 1000:
                return True
        except Exception:
            pass
        return False

    async def render_candidate_to_clip(self, candidate_id: int) -> Optional[Clip]:
        """Convert an approved candidate into a vertical 9:16 clip."""
        async with AsyncSessionLocal() as db:
            cand_stmt = select(Candidate).where(Candidate.id == candidate_id)
            candidate = (await db.execute(cand_stmt)).scalar_one_or_none()
            if not candidate:
                return None

            # Get segment and session
            seg_stmt = select(Segment).where(Segment.id == candidate.segment_id)
            segment = (await db.execute(seg_stmt)).scalar_one_or_none()
            if not segment:
                return None

            sess_stmt = select(StreamSession).where(StreamSession.id == segment.session_id)
            session = (await db.execute(sess_stmt)).scalar_one_or_none()
            if not session:
                return None

            strm_stmt = select(Streamer).where(Streamer.id == session.streamer_id)
            streamer = (await db.execute(strm_stmt)).scalar_one_or_none()
            streamer_name = streamer.display_name if streamer else "Streamer"

            clip_filename = f"clip_cand_{candidate.id}_{int(datetime.now(timezone.utc).timestamp())}.mp4"
            thumb_filename = f"thumb_cand_{candidate.id}_{int(datetime.now(timezone.utc).timestamp())}.jpg"

            clip_path = str(self.output_dir / clip_filename)
            thumb_path = str(self.output_dir / thumb_filename)

            # Lead-in adjustment: up to 5 seconds before climax if available
            start_sec = max(0.0, candidate.start_second - 3.0)
            duration_sec = candidate.duration_seconds + (candidate.start_second - start_sec)

            # Extract AI headline, caption, and hashtags from metadata if present
            meta = candidate.safety_flags if isinstance(candidate.safety_flags, dict) else {}
            headline = meta.get("headline") or candidate.hook_summary.upper()
            caption = meta.get("caption") or candidate.why_highlight
            raw_hashtags = meta.get("hashtags") or ["#gta", "#gta6", "#gaming", "#gtaclips", "#viral"]
            facecam_pos = meta.get("facecam_position") or "top_right"

            # Enforce maximum 5 hashtags in lowercase, guaranteeing #gta and #gta6
            tags_list = []
            for tag in raw_hashtags:
                t = tag.strip().lower()
                if not t.startswith("#"):
                    t = f"#{t}"
                if t not in tags_list:
                    tags_list.append(t)
            if "#gta" not in tags_list:
                tags_list.insert(0, "#gta")
            if "#gta6" not in tags_list:
                tags_list.insert(1, "#gta6")
            final_tags = " ".join(tags_list[:5])

            # Detect smart streamer facecam coordinates across candidate regions (left, middle-left, top-right, middle-right, top)
            crop_cam, detected_region = facecam_detector.detect_streamer_facecam(
                video_path=segment.file_path,
                preferred_position=facecam_pos
            )

            rendered = self.render_vertical_clip(
                input_file=segment.file_path,
                start_sec=start_sec,
                duration_sec=duration_sec,
                output_file=clip_path,
                streamer_name=streamer_name,
                quote_text=candidate.evidence_quote,
                headline_text=headline,
                facecam_pos=detected_region,
                crop_cam=crop_cam
            )

            if not rendered or not Path(clip_path).exists() or Path(clip_path).stat().st_size < 50000:
                return None

            self.generate_thumbnail(
                video_file=clip_path,
                output_thumb=thumb_path,
                at_second=min(2.0, duration_sec / 2)
            )

            file_size = Path(clip_path).stat().st_size if Path(clip_path).exists() else 0
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(hours=settings.MEDIA_TTL_HOURS)

            clip = Clip(
                candidate_id=candidate.id,
                streamer_id=session.streamer_id,
                title=headline,
                description=f"{caption}\n\nStreamed by {streamer_name}",
                tags=final_tags,
                portrait_video_path=clip_path,
                thumbnail_path=thumb_path,
                duration_seconds=duration_sec,
                file_size_bytes=file_size,
                resolution="1080x1920",
                aspect_ratio="9:16",
                approval_status=ApprovalStatus.PENDING_REVIEW.value,
                auto_post_eligible=False,
                created_at=now,
                expires_at=expires_at,
            )
            db.add(clip)
            candidate.status = CandidateStatus.RENDERED.value

            # Record render compute metric
            db.add(UsageRecord(
                metric_type=MetricType.RENDER_SECONDS.value,
                count_or_value=duration_sec * 1.5,
                streamer_id=session.streamer_id,
                metadata_json={"clip_title": clip.title}
            ))

            await db.commit()
            await db.refresh(clip)
            return clip


render_worker = FFmpegRenderWorker()
