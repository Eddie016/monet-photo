"""Offline filter backend: no API, no key. Only for trying the UI — it is NOT a Monet painting."""
from __future__ import annotations

import random

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from ..presets import Preset

STROKE = {"subtle": 3, "medium": 5, "bold": 8}


class PreviewBackend:
    name = "preview"

    def stylize(self, image: Image.Image, preset: Preset, *, strength: str = "medium",
                extra: str = "") -> Image.Image:
        size = STROKE.get(strength, 5)
        base = ImageEnhance.Color(image).enhance(1.35).filter(ImageFilter.ModeFilter(size))
        canvas = base.filter(ImageFilter.GaussianBlur(size / 2))
        draw = ImageDraw.Draw(canvas)
        rng = random.Random(0)
        w, h = image.size
        step = size * 2
        px = base.load()
        # Short tilted dabs sampled from the image colour underneath.
        for y in range(0, h, step):
            for x in range(0, w, step):
                cx, cy = min(w - 1, x + rng.randrange(step)), min(h - 1, y + rng.randrange(step))
                dx, dy = rng.choice([(1, 0), (1, 1), (0, 1), (1, -1)])
                L = size * rng.uniform(1.2, 2.2)
                draw.line([(cx - dx * L, cy - dy * L), (cx + dx * L, cy + dy * L)],
                          fill=px[cx, cy], width=max(2, size))
        return ImageEnhance.Contrast(canvas).enhance(0.92)
