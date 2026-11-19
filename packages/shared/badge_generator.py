"""
Viral Headline Badge Generator:
Creates high-contrast, bold multiline pill badges for 9:16 vertical short videos.
Features:
- Individual rounded pills per line: background hugs the edges of the words with zero empty gaps at sides.
- Big, punchy bold font (size 50-54px) for high mobile readability.
- Real full-color emoji support (Twemoji) with local scratch caching.
- Soft drop-shadow for separation against busy gameplay.
"""
import os
import re
import urllib.request
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("badge_generator")

# Common emoji regex and Unicode ranges
EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF]|"  # Misc Symbols, Emoticons, Transport, Supplemental
    r"[\U00002600-\U000027BF]|"  # Misc Symbols, Dingbats
    r"[\U0001F600-\U0001F64F]|"  # Emoticons
    r"[\U0001F680-\U0001F6FF]|"  # Transport and Map Symbols
    r"[\U00002300-\U000023FF]|"  # Misc Technical
    r"[\U00002B50-\U00002B55]"   # Stars
)


def emoji_to_hex(char: str) -> str:
    """Convert Unicode emoji to lowercase hex string for Twemoji CDN."""
    chars = [c for c in char if ord(c) != 0xFE0F]
    return "-".join(f"{ord(c):x}" for c in chars)


def get_emoji_image(emoji_char: str, size: int = 54, cache_dir: Path = Path("/scratch/emojis")) -> Image.Image:
    """Fetch and cache Twemoji 72x72 PNG for authentic full-color keyboard emojis."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    hex_code = emoji_to_hex(emoji_char)
    cached_file = cache_dir / f"{hex_code}.png"

    if not cached_file.exists():
        url = f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{hex_code}.png"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                cached_file.write_bytes(resp.read())
        except Exception as e:
            logger.debug(f"Could not download emoji {emoji_char} ({hex_code}): {e}")
            return Image.new("RGBA", (size, size), (0, 0, 0, 0))

    try:
        img = Image.open(cached_file).convert("RGBA")
        return img.resize((size, size), Image.Resampling.LANCZOS)
    except Exception:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def format_balanced_headline_lines(headline: str, max_chars_per_line: int = 24) -> List[str]:
    """Break long headlines into 1-3 balanced lines hugging words naturally."""
    clean = headline.strip()
    if "\n" in clean:
        lines = [l.strip() for l in clean.split("\n") if l.strip()]
        return lines[:3]

    words = clean.split()
    if not words:
        return ["GTA 6 HIGHLIGHT"]

    lines = []
    curr = []
    curr_len = 0
    for w in words:
        w_len = len(w)
        if curr_len + w_len + (1 if curr else 0) <= max_chars_per_line:
            curr.append(w)
            curr_len += w_len + (1 if len(curr) > 1 else 0)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
            curr_len = w_len
    if curr:
        lines.append(" ".join(curr))

    return lines[:3]


def generate_headline_badge_png(
    headline: str,
    output_png_path: str,
    canvas_w: int = 1080,
    font_size: int = 52,
    padding_x: int = 26,
    padding_y: int = 14,
    corner_radius: int = 16,
    line_gap: int = 10
) -> Tuple[bool, int]:
    """
    Render a transparent PNG badge with per-line rounded pills hugging text,
    big bold font, and vibrant real-color emojis.
    Returns: (success: bool, total_height: int)
    """
    # 1. Select best bold font available
    font = None
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/seguiemj.ttf",
    ]
    for fc in font_candidates:
        if os.path.exists(fc):
            try:
                font = ImageFont.truetype(fc, font_size)
                break
            except Exception:
                pass
    if not font:
        font = ImageFont.load_default()

    # 2. Split into balanced lines
    lines = format_balanced_headline_lines(headline, max_chars_per_line=24)
    emoji_size = int(font_size * 1.08)

    # 3. Parse tokens and measure metrics per line
    line_metrics: List[Dict[str, Any]] = []
    for line in lines:
        tokens = []
        words = line.split(" ")
        for w_idx, word in enumerate(words):
            if w_idx > 0:
                tokens.append({"type": "space", "val": " "})

            curr_str = ""
            for ch in word:
                if EMOJI_PATTERN.match(ch):
                    if curr_str:
                        tokens.append({"type": "text", "val": curr_str})
                        curr_str = ""
                    tokens.append({"type": "emoji", "val": ch})
                else:
                    curr_str += ch
            if curr_str:
                tokens.append({"type": "text", "val": curr_str})

        # Calculate line width and heights
        line_w = 0
        max_h = font_size
        for t in tokens:
            if t["type"] == "text":
                bbox = font.getbbox(t["val"])
                t["w"] = bbox[2] - bbox[0]
                t["h"] = bbox[3] - bbox[1]
                line_w += t["w"]
            elif t["type"] == "space":
                bbox = font.getbbox(" ")
                t["w"] = bbox[2] - bbox[0]
                t["h"] = bbox[3] - bbox[1]
                line_w += t["w"]
            elif t["type"] == "emoji":
                t["w"] = emoji_size
                t["h"] = emoji_size
                line_w += t["w"]
                max_h = max(max_h, emoji_size)

        pill_w = line_w + padding_x * 2
        pill_h = max_h + padding_y * 2
        line_metrics.append({
            "pill_w": pill_w,
            "pill_h": pill_h,
            "line_w": line_w,
            "max_h": max_h,
            "tokens": tokens
        })

    total_h = sum(m["pill_h"] for m in line_metrics) + line_gap * (len(line_metrics) - 1) + 24
    img = Image.new("RGBA", (canvas_w, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    curr_y = 12
    for m in line_metrics:
        pw = m["pill_w"]
        ph = m["pill_h"]
        px = (canvas_w - pw) / 2

        # 1. Soft drop shadow (dark translucent pill underneath)
        shadow_rect = [px, curr_y + 4, px + pw, curr_y + ph + 4]
        draw.rounded_rectangle(shadow_rect, radius=corner_radius, fill=(0, 0, 0, 110))

        # 2. Solid white pill background wrapping this specific line tightly
        pill_rect = [px, curr_y, px + pw, curr_y + ph]
        draw.rounded_rectangle(pill_rect, radius=corner_radius, fill=(255, 255, 255, 255))

        # 3. Draw text and full-color emojis inside the pill
        tx = px + padding_x
        for t in m["tokens"]:
            if t["type"] in ("text", "space"):
                ty = curr_y + (ph - t["h"]) / 2 - 2
                draw.text((tx, ty), t["val"], font=font, fill=(12, 12, 12, 255))
                tx += t["w"]
            elif t["type"] == "emoji":
                emoji_img = get_emoji_image(t["val"], size=emoji_size)
                ey = int(curr_y + (ph - emoji_size) / 2)
                img.alpha_composite(emoji_img, dest=(int(tx), ey))
                tx += t["w"]

        curr_y += ph + line_gap

    Path(output_png_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_png_path, "PNG")
    return True, total_h
