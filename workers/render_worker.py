"""
Render Worker: FFmpeg vertical (9:16) video editor.
Renders 1080x1920 MP4 with audio normalization, burned subtitles,
watermark attribution, thumbnail export, and 24h retention tag.
"""
import asyncio
import os
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.config import settings
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import Candidate, Segment, StreamSession, Streamer, Clip, UsageRecord
from packages.shared.enums import CandidateStatus, ApprovalStatus, MetricType
from workers.facecam_detector import facecam_detector


def format_headline_card_text(headline: str, max_chars_per_line: int = 26) -> str:
    """Format headline text into 1-2 balanced lines for the white center badge."""
    words = headline.strip().split()
    if not words:
        return "GTA 6 HIGHLIGHT"
    if "\n" in headline:
        return headline.strip()

    lines = []
    curr = []
    curr_len = 0
    for w in words:
        if curr_len + len(w) + (1 if curr else 0) <= max_chars_per_line:
            curr.append(w)
            curr_len += len(w) + (1 if len(curr) > 1 else 0)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
            curr_len = len(w)
    if curr:
        lines.append(" ".join(curr))
    return "\n".join(lines[:3])


class FFmpegRenderWorker:
    def __init__(self):
        self.output_dir = Path(settings.SCRATCH_DIR) / "clips"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.watermark_text = settings.WATERMARK_TEXT

    def build_ffmpeg_filter(
        self,
        streamer_name: str = "",
        quote_text: str = "",
        headline_text: str = "",
        facecam_pos: str = "top_right",
        crop_cam: Optional[str] = None
    ) -> str:
        """
        Creates an FFmpeg complex filter for viral split-screen vertical video:
        1. Top: Streamer facecam cropped and scaled to 1080x740.
        2. Bottom: Main GTA 6 gameplay cropped and scaled to 1080x1180.
        3. Middle: Centered white card badge with bold black headline text.
        """
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
            "[0:v]split=2[raw_cam][raw_game];"
            f"[raw_cam]{crop_cam},scale=1080:740:force_original_aspect_ratio=increase,crop=1080:740[facecam];"
            "[raw_game]scale=2062:1180:force_original_aspect_ratio=increase,crop=1080:1180[gameplay];"
            "[facecam][gameplay]vstack=inputs=2[stacked];"
            f"[stacked]drawtext=text='{headline_text}':fontsize=38:fontcolor=black:line_spacing=12:x=(w-text_w)/2:y=715:box=1:boxcolor=white@1.0:boxborderw=24[final_v]"
        )
        return filter_complex

    def render_vertical_clip(
        self,
        input_file: str,
        start_sec: float,
        duration_sec: float,
        output_file: str,
        streamer_name: str = "",
        quote_text: str = "",
        headline_text: str = "",
        facecam_pos: str = "top_right",
        crop_cam: Optional[str] = None
    ) -> bool:
        """Execute FFmpeg command to produce 1080x1920 H.264/AAC MP4 with clean white headline card."""
        temp_dir = self.output_dir / "tmp_text"
        temp_dir.mkdir(parents=True, exist_ok=True)
        unique_prefix = f"render_{int(datetime.now(timezone.utc).timestamp()*1000)}_{os.getpid()}"

        headline_file = temp_dir / f"{unique_prefix}_headline.txt"
        card_headline = format_headline_card_text(headline_text or "GTA 6 HIGHLIGHT")
        headline_file.write_text(card_headline, encoding="utf-8")

        # In FFmpeg, escape colon and backslash in textfile path
        h_path = str(headline_file).replace("\\", "/").replace(":", "\\:")

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
            f"[raw_cam]{crop_cam},scale=1080:740:force_original_aspect_ratio=increase,crop=1080:740[facecam];"
            "[raw_game]scale=2062:1180:force_original_aspect_ratio=increase,crop=1080:1180[gameplay];"
            "[facecam][gameplay]vstack=inputs=2[stacked];"
            f"[stacked]drawtext=textfile='{h_path}':fontsize=38:fontcolor=black:line_spacing=12:x=(w-text_w)/2:y=715:box=1:boxcolor=white@1.0:boxborderw=24[final_v]"
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
            if headline_file.exists():
                try:
                    headline_file.unlink()
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
            # Check if this candidate already has an existing clip to avoid duplicate titles/clips
            existing_clip = (await db.execute(select(Clip).where(Clip.candidate_id == candidate_id))).scalar_one_or_none()
            if existing_clip:
                return existing_clip

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

            # Enforce rich, full viral short duration (at least 30-50s) bounded by segment length
            start_sec = max(0.0, candidate.start_second)
            duration_sec = candidate.duration_seconds
            if duration_sec < 30.0 and segment.duration_seconds >= 30.0:
                duration_sec = 35.0
            if start_sec + duration_sec > segment.duration_seconds:
                duration_sec = max(10.0, segment.duration_seconds - start_sec)

            # Extract AI headline, caption, and hashtags from metadata if present
            meta = candidate.safety_flags if isinstance(candidate.safety_flags, dict) else {}
            headline = meta.get("headline") or candidate.hook_summary.upper()
            caption = meta.get("caption") or candidate.why_highlight
            facecam_pos = meta.get("facecam_position") or "top_right"

            # Post numbering: Post 1, Post 2, etc. matching user TikTok captions
            existing_count = (await db.execute(select(func.count(Clip.id)))).scalar() or 0
            post_num = existing_count + 1

            clean_caption = caption.strip()
            if not clean_caption.lower().startswith("post "):
                formatted_caption = f"Post {post_num}: {clean_caption}"
            else:
                formatted_caption = clean_caption

            clean_name = (streamer.display_name or "Player").strip()
            clean_upper = clean_name.upper()

            headline = re.sub(r'\bSTREAMER\b', clean_upper, headline, flags=re.IGNORECASE)
            headline = re.sub(r'\bStreamer\b', clean_name, headline)
            headline = re.sub(r'\bstreamer\b', clean_name, headline)

            formatted_caption = re.sub(r'\bSTREAMER\b', clean_upper, formatted_caption, flags=re.IGNORECASE)
            formatted_caption = re.sub(r'\bStreamer\b', clean_name, formatted_caption)
            formatted_caption = re.sub(r'\bstreamer\b', clean_name, formatted_caption)

            final_tags = "#gta6 #gtavi #gaming #vicecity #gta6gameplay"
            full_description = f"{formatted_caption}\n\n{final_tags}"

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
                streamer_name=clean_name,
                quote_text="",
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
                description=full_description,
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

            # Purge raw segment capture once all detected candidates for it have finished rendering
            all_cands = (await db.execute(select(Candidate).where(Candidate.segment_id == segment.id))).scalars().all()
            if all(c.status in (CandidateStatus.RENDERED.value, CandidateStatus.FAILED.value) for c in all_cands):
                raw_p = Path(segment.file_path)
                if raw_p.exists():
                    try:
                        raw_p.unlink()
                        segment.disk_bytes = 0
                        await db.commit()
                        logger.info(f"All candidates for segment {segment.id} rendered. Purged raw capture {segment.file_path} to save scratch disk.")
                    except Exception:
                        pass

            return clip

    async def re_render_clip(self, clip_id: int, new_headline: str) -> Optional[Clip]:
        """Re-render an existing clip with an updated headline on the white card."""
        async with AsyncSessionLocal() as db:
            clip = (await db.execute(select(Clip).where(Clip.id == clip_id))).scalar_one_or_none()
            if not clip:
                return None

            candidate = None
            if clip.candidate_id:
                candidate = (await db.execute(select(Candidate).where(Candidate.id == clip.candidate_id))).scalar_one_or_none()

            segment = None
            if candidate and candidate.segment_id:
                segment = (await db.execute(select(Segment).where(Segment.id == candidate.segment_id))).scalar_one_or_none()

            raw_seg_exists = segment and Path(segment.file_path).exists()
            old_clip_exists = clip.portrait_video_path and Path(clip.portrait_video_path).exists()

            ts = int(datetime.now(timezone.utc).timestamp())
            if not raw_seg_exists and not old_clip_exists and clip.r2_key:
                # If local file was purged, download from R2 to re-burn headline
                from packages.shared.storage import storage_manager
                temp_down = self.output_dir / f"r2_dl_{clip_id}_{ts}.mp4"
                try:
                    storage_manager.s3.download_file(
                        storage_manager.bucket,
                        clip.r2_key,
                        str(temp_down)
                    )
                    if temp_down.exists() and temp_down.stat().st_size > 50000:
                        clip.portrait_video_path = str(temp_down)
                        old_clip_exists = True
                except Exception as e:
                    logger.warning(f"Could not download clip {clip_id} from R2 for re-render: {e}")

            if not raw_seg_exists and not old_clip_exists:
                return None
            cand_id_tag = candidate.id if candidate else clip_id
            new_clip_filename = f"clip_cand_{cand_id_tag}_{ts}.mp4"
            new_thumb_filename = f"thumb_cand_{cand_id_tag}_{ts}.jpg"
            new_clip_path = str(self.output_dir / new_clip_filename)
            new_thumb_path = str(self.output_dir / new_thumb_filename)

            rendered = False
            duration_sec = clip.duration_seconds

            if raw_seg_exists and candidate:
                strm = (await db.execute(select(Streamer).where(Streamer.id == clip.streamer_id))).scalar_one_or_none()
                streamer_name = strm.display_name if strm else "Streamer"

                meta = candidate.safety_flags if isinstance(candidate.safety_flags, dict) else {}
                facecam_pos = meta.get("facecam_position") or "top_right"

                crop_cam, detected_region = facecam_detector.detect_streamer_facecam(
                    video_path=segment.file_path,
                    preferred_position=facecam_pos
                )

                start_sec = max(0.0, candidate.start_second - 3.0)
                duration_sec = candidate.duration_seconds + (candidate.start_second - start_sec)

                rendered = self.render_vertical_clip(
                    input_file=segment.file_path,
                    start_sec=start_sec,
                    duration_sec=duration_sec,
                    output_file=new_clip_path,
                    streamer_name=streamer_name,
                    quote_text="",
                    headline_text=new_headline,
                    facecam_pos=detected_region,
                    crop_cam=crop_cam
                )
            elif old_clip_exists:
                # Fast re-burn: Burn the new white card badge directly over the divider line on the existing 9:16 clip
                temp_dir = self.output_dir / "tmp_text"
                temp_dir.mkdir(parents=True, exist_ok=True)
                formatted_card = format_headline_card_text(new_headline)
                text_file = temp_dir / f"re_card_{clip_id}_{ts}.txt"
                text_file.write_text(formatted_card, encoding="utf-8")
                escaped_text_path = str(text_file).replace("\\", "/").replace(":", "\\:")
                card_filter = f"drawtext=textfile='{escaped_text_path}':fontsize=38:fontcolor=black:line_spacing=12:x=(w-text_w)/2:y=715:box=1:boxcolor=white@1.0:boxborderw=24"

                cmd = [
                    "ffmpeg", "-y",
                    "-i", clip.portrait_video_path,
                    "-vf", card_filter,
                    "-c:v", "libx264",
                    "-preset", "faster",
                    "-crf", "22",
                    "-c:a", "copy",
                    new_clip_path
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
                rendered = (res.returncode == 0 and Path(new_clip_path).exists() and Path(new_clip_path).stat().st_size > 50000)
                try:
                    text_file.unlink()
                except Exception:
                    pass

            if not rendered or not Path(new_clip_path).exists() or Path(new_clip_path).stat().st_size < 50000:
                return None

            self.generate_thumbnail(
                video_file=new_clip_path,
                output_thumb=new_thumb_path,
                at_second=min(2.0, duration_sec / 2)
            )

            # Clean up old local video and thumb if they exist
            if clip.portrait_video_path and Path(clip.portrait_video_path).exists():
                try:
                    Path(clip.portrait_video_path).unlink()
                except Exception:
                    pass
            if clip.thumbnail_path and Path(clip.thumbnail_path).exists():
                try:
                    Path(clip.thumbnail_path).unlink()
                except Exception:
                    pass

            clip.title = new_headline
            clip.portrait_video_path = new_clip_path
            clip.thumbnail_path = new_thumb_path
            clip.file_size_bytes = Path(new_clip_path).stat().st_size
            await db.commit()

            # Upload new files to R2
            from workers.storage_worker import storage_worker
            await storage_worker.upload_clip_to_r2(clip.id)
            await db.refresh(clip)
            return clip


render_worker = FFmpegRenderWorker()
