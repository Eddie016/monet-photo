from __future__ import annotations

from typing import Protocol

from PIL import Image

from ..presets import Preset


class BackendError(Exception):
    """An error whose message is safe to show to the end user."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


class Backend(Protocol):
    name: str

    def stylize(self, image: Image.Image, preset: Preset, *, strength: str = "medium",
                extra: str = "") -> Image.Image: ...
