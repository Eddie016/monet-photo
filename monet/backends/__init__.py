from __future__ import annotations

from .base import Backend, BackendError

BACKENDS = {
    "gemini": "Gemini (cloud, needs API key)",
    "preview": "Offline preview filter (no API, not real Monet)",
}


def get_backend(name: str, *, api_key: str | None = None, model: str | None = None) -> Backend:
    # Imports are lazy so the preview backend works without google-genai configured.
    if name == "gemini":
        from .gemini import GeminiBackend
        return GeminiBackend(api_key=api_key, model=model)
    if name == "preview":
        from .preview import PreviewBackend
        return PreviewBackend()
    raise BackendError(f"Unknown backend '{name}'. Available: {', '.join(BACKENDS)}", 400)


__all__ = ["Backend", "BackendError", "BACKENDS", "get_backend"]
