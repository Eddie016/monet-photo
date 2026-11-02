"""Gemini image-editing backend ("Nano Banana" family)."""
from __future__ import annotations

import io
import logging
import os
import re

from google import genai
from google.genai import errors, types
from PIL import Image

from ..imaging import nearest_aspect_ratio
from ..presets import Preset
from .base import BackendError

log = logging.getLogger("uvicorn.error")

DEFAULT_MODEL = "gemini-2.5-flash-image"
MAX_REFS = 3


class GeminiBackend:
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise BackendError("No Gemini API key. Paste one in the UI or set GEMINI_API_KEY "
                               "(get one free at https://aistudio.google.com/apikey).", 401)
        self.model = model or os.getenv("MONET_GEMINI_MODEL") or DEFAULT_MODEL
        self.client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=180_000))

    def stylize(self, image: Image.Image, preset: Preset, *, strength: str = "medium",
                extra: str = "") -> Image.Image:
        contents: list = ["Photograph to repaint:", image]
        refs = preset.reference_paths()[:MAX_REFS]
        if refs:
            contents.append("Genuine Monet paintings — use ONLY for brushwork, palette and texture, "
                            "never copy their subject or composition:")
            contents += [Image.open(p).convert("RGB") for p in refs]
        contents.append(preset.build_prompt(strength, extra))

        config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=nearest_aspect_ratio(image)),
        )
        try:
            resp = self.client.models.generate_content(model=self.model, contents=contents, config=config)
        except errors.APIError as e:
            raise _friendly(e) from e

        return _extract_image(resp)

    def list_image_models(self) -> list[str]:
        try:
            return sorted(m.name.removeprefix("models/") for m in self.client.models.list()
                          if "image" in (m.name or ""))
        except errors.APIError as e:
            raise _friendly(e) from e


def _extract_image(resp) -> Image.Image:
    texts = []
    for cand in resp.candidates or []:
        for part in (cand.content.parts if cand.content else None) or []:
            if part.inline_data and part.inline_data.data:
                return Image.open(io.BytesIO(part.inline_data.data))
            if part.text:
                texts.append(part.text)
    reason = getattr(resp.prompt_feedback, "block_reason", None) if resp.prompt_feedback else None
    if not reason and resp.candidates:
        reason = resp.candidates[0].finish_reason
    detail = " ".join(texts).strip() or (f"finish reason: {reason}" if reason else "empty response")
    raise BackendError(f"Gemini returned no image ({detail}). Try another photo or preset.", 502)


def _friendly(e: errors.APIError) -> BackendError:
    # Never let a key reach logs or the browser, even if Google echoes one back.
    msg = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "AIza…(redacted)", e.message or str(e))
    log.warning("Gemini API error %s: %s", e.code, msg)
    if e.code == 429:
        if re.search(r"limit:\s*0\b", msg):
            return BackendError("This model has no free quota on your key (limit 0) — Gemini image models are "
                                "paid-only on the API. Enable billing for the key's project in AI Studio, then retry.", 429)
        return BackendError(f"Gemini rate limit hit (429) — wait a minute and retry. Google says: {msg[:300]}", 429)
    if e.code in (400, 401, 403) and "key" in msg.lower():
        return BackendError("Gemini rejected the API key. Check it at https://aistudio.google.com/apikey.", 401)
    if e.code == 404:
        return BackendError(f"Model not found: {msg}. Pick another model.", 400)
    return BackendError(f"Gemini error {e.code}: {msg}", 502)
