"""Image pre/post-processing shared by all backends."""
from __future__ import annotations

import io

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()  # iPhone photos are HEIC by default

MAX_SIDE = 1536  # Image models output ~1–2K anyway; sending more only adds latency.

# Aspect ratios accepted by Gemini image models.
ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]


def load_image(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)  # phone photos store rotation in EXIF
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    return img


def nearest_aspect_ratio(img: Image.Image) -> str:
    r = img.width / img.height
    return min(ASPECT_RATIOS, key=lambda s: abs(r - _ratio(s)))


def match_frame(result: Image.Image, source: Image.Image) -> Image.Image:
    """Crop/resize the result to the source's exact size so before/after line up."""
    result = result.convert("RGB")
    if result.size == source.size:
        return result
    return ImageOps.fit(result, source.size, Image.LANCZOS)


def to_bytes(img: Image.Image, fmt: str = "JPEG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt, quality=92) if fmt == "JPEG" else img.save(buf, fmt)
    return buf.getvalue()


def _ratio(s: str) -> float:
    w, h = s.split(":")
    return int(w) / int(h)
