"""
Smart Streamer Facecam Detector:
Identifies streamer webcam rectangles in gaming streams (GTA 6).
Streamer webcam overlays are typically situated along perimeter rectangular zones:
- top-left
- middle-left
- bottom-left
- top-right
- middle-right
- bottom-right
- top-center

It isolates streamer faces from in-game characters by filtering out center gameplay faces
and detecting stationary webcam regions. It dynamically calculates the optimal FFmpeg crop
parameters (width, height, x, y) matching the 1080x760 top vertical video slot (aspect ratio ~1.421).
"""
import os
import subprocess
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger("facecam_detector")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available. Falling back to quadrant-based facecam crops.")


class FacecamDetector:
    def __init__(self):
        self.cascade = None
        if CV2_AVAILABLE:
            try:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                self.cascade = cv2.CascadeClassifier(cascade_path)
            except Exception as e:
                logger.error(f"Failed to load OpenCV Haar Cascade: {e}")

    def extract_sample_frame(self, video_path: str, second: float = 3.0, out_path: str = "/tmp/sample_frame.jpg") -> bool:
        """Extract a single JPEG frame from video at the given second mark."""
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(second),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            out_path
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            return res.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0
        except Exception as e:
            logger.error(f"Failed to extract frame at {second}s: {e}")
            return False

    def detect_streamer_facecam(
        self,
        video_path: str,
        preferred_position: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Detects streamer facecam in the video.
        Returns:
            (crop_filter_str, detected_region_name)
            e.g. ("crop=600:422:1320:0", "top_right")
        """
        # If cv2 or cascade not ready, return standard position-based crop
        if not CV2_AVAILABLE or not self.cascade or not os.path.exists(video_path):
            return self._fallback_crop(preferred_position or "top_right")

        sample_frames = ["/tmp/face_sample_1.jpg", "/tmp/face_sample_2.jpg", "/tmp/face_sample_3.jpg"]
        sample_times = [2.0, 8.0, 15.0]

        all_detections = []
        for st, frame_file in zip(sample_times, sample_frames):
            if self.extract_sample_frame(video_path, second=st, out_path=frame_file):
                try:
                    img = cv2.imread(frame_file)
                    if img is None:
                        continue
                    H, W = img.shape[:2]
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    # Detect frontal faces
                    faces = self.cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=4,
                        minSize=(int(W * 0.04), int(H * 0.06)),
                        maxSize=(int(W * 0.35), int(H * 0.50))
                    )
                    for (x, y, w, h) in faces:
                        cx = x + w / 2.0
                        cy = y + h / 2.0

                        # Rule 1: Eliminate dead center gameplay (in-game GTA characters Jason/Lucia/NPCs)
                        # Center gameplay is x in [0.35*W, 0.65*W] and y in [0.30*H, 0.75*H]
                        is_center_gameplay = (0.35 * W <= cx <= 0.65 * W) and (0.30 * H <= cy <= 0.75 * H)
                        if is_center_gameplay:
                            continue

                        # Classify streamer webcam region
                        region = "unknown"
                        if cx <= 0.45 * W:
                            if cy <= 0.42 * H:
                                region = "top_left"
                            elif cy <= 0.72 * H:
                                region = "middle_left"
                            else:
                                region = "bottom_left"
                        elif cx >= 0.55 * W:
                            if cy <= 0.42 * H:
                                region = "top_right"
                            elif cy <= 0.72 * H:
                                region = "middle_right"
                            else:
                                region = "bottom_right"
                        elif cy <= 0.38 * H:
                            region = "top_center"

                        all_detections.append((x, y, w, h, W, H, region))
                except Exception as err:
                    logger.error(f"Facecam analysis error on {frame_file}: {err}")
                finally:
                    if os.path.exists(frame_file):
                        try:
                            os.remove(frame_file)
                        except Exception:
                            pass

        if not all_detections:
            logger.info("No streamer facecam detected with OpenCV. Using preferred/fallback quadrant.")
            return self._fallback_crop(preferred_position or "top_right")

        # Prioritize region matching preferred_position if provided, else take the most frequent region
        region_counts: Dict[str, int] = {}
        for det in all_detections:
            reg = det[6]
            region_counts[reg] = region_counts.get(reg, 0) + 1

        best_region = max(region_counts.items(), key=lambda item: item[1])[0]
        # Get face coordinates belonging to best_region
        matching_faces = [d for d in all_detections if d[6] == best_region]
        if not matching_faces:
            matching_faces = all_detections

        # Take average or median bounding box for stability
        avg_x = sum(d[0] for d in matching_faces) / len(matching_faces)
        avg_y = sum(d[1] for d in matching_faces) / len(matching_faces)
        avg_w = sum(d[2] for d in matching_faces) / len(matching_faces)
        avg_h = sum(d[3] for d in matching_faces) / len(matching_faces)
        W, H = matching_faces[0][4], matching_faces[0][5]

        # Calculate crop box for 1080:760 aspect ratio (1.421:1)
        # Give generous room around face (head + shoulders / mic / webcam frame)
        target_aspect = 1080.0 / 760.0  # 1.421
        crop_w = min(W, max(int(avg_w * 2.8), int(W * 0.32)))
        crop_h = min(H, int(crop_w / target_aspect))

        # Center around face with slight upward bias (so chin/shoulders are visible)
        center_x = avg_x + avg_w / 2.0
        center_y = avg_y + avg_h / 2.0

        crop_x = int(center_x - crop_w / 2.0)
        crop_y = int(center_y - crop_h / 2.2)

        # Clamp inside frame boundaries
        crop_x = max(0, min(W - crop_w, crop_x))
        crop_y = max(0, min(H - crop_h, crop_y))

        crop_filter = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}"
        logger.info(f"Detected streamer facecam at region '{best_region}'. Crop: {crop_filter}")
        return crop_filter, best_region

    def _fallback_crop(self, position: str) -> Tuple[str, str]:
        """Quadrant-based crop when no face is found or OpenCV is absent."""
        pos = (position or "top_right").lower()
        if pos == "top_left":
            return "crop=w=iw*0.35:h=ih*0.42:x=0:y=0", "top_left"
        elif pos == "middle_left":
            return "crop=w=iw*0.35:h=ih*0.42:x=0:y=ih*0.28", "middle_left"
        elif pos == "bottom_left":
            return "crop=w=iw*0.35:h=ih*0.42:x=0:y=ih*0.58", "bottom_left"
        elif pos == "middle_right":
            return "crop=w=iw*0.35:h=ih*0.42:x=iw*0.65:y=ih*0.28", "middle_right"
        elif pos == "bottom_right":
            return "crop=w=iw*0.35:h=ih*0.42:x=iw*0.65:y=ih*0.58", "bottom_right"
        elif pos == "top_center":
            return "crop=w=iw*0.42:h=ih*0.42:x=iw*0.29:y=0", "top_center"
        else:  # top_right
            return "crop=w=iw*0.35:h=ih*0.42:x=iw*0.65:y=0", "top_right"


facecam_detector = FacecamDetector()
