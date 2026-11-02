"""Turn photos into Claude Monet–style paintings."""
from __future__ import annotations

import time
from dataclasses import dataclass

from PIL import Image

from .backends import get_backend
from .imaging import load_image, match_frame
from .presets import get_preset

__version__ = "0.1.0"


@dataclass
class Result:
    source: Image.Image
    painting: Image.Image
    seconds: float
    backend: str


def paint(photo: bytes, preset: str = "impression", *, strength: str = "medium", extra: str = "",
          backend: str = "gemini", api_key: str | None = None, model: str | None = None) -> Result:
    """Single-shot pipeline used by both the CLI and the web server."""
    source = load_image(photo)
    engine = get_backend(backend, api_key=api_key, model=model)
    t0 = time.perf_counter()
    out = engine.stylize(source, get_preset(preset), strength=strength, extra=extra)
    label = f"{engine.name}:{engine.model}" if hasattr(engine, "model") else engine.name
    return Result(source, match_frame(out, source), time.perf_counter() - t0, label)
