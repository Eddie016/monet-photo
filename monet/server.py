"""FastAPI server: JSON API + the static web UI in monet/web/."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__, paint
from .backends import BACKENDS, BackendError, get_backend
from .backends.gemini import DEFAULT_MODEL
from .imaging import load_image, to_bytes
from .presets import STRENGTHS, load_presets

load_dotenv()

MAX_UPLOAD = 20 * 1024 * 1024
WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(title="Monet Agent", version=__version__)


@app.exception_handler(BackendError)
async def _backend_error(_, e: BackendError):
    return JSONResponse({"detail": str(e)}, status_code=e.status)


@app.get("/api/config")
def config():
    return {
        "version": __version__,
        "presets": [p.to_dict() for p in load_presets().values()],
        "strengths": list(STRENGTHS),
        "backends": BACKENDS,
        "default_model": os.getenv("MONET_GEMINI_MODEL") or DEFAULT_MODEL,
        "server_has_key": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
    }


@app.get("/api/models")
def models(x_gemini_key: str | None = Header(default=None)):
    return {"models": get_backend("gemini", api_key=x_gemini_key).list_image_models()}


@app.post("/api/convert")
def convert(image: UploadFile = File(...)):
    """Decode formats browsers can't show (HEIC) into the same JPEG the painter will see."""
    try:
        img = load_image(_read_upload(image))
    except OSError:
        raise HTTPException(400, "Could not read that file as an image.")
    return Response(to_bytes(img), media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.post("/api/paint")
def paint_endpoint(
    image: UploadFile = File(...),
    preset: str = Form("impression"),
    strength: str = Form("medium"),
    extra: str = Form(""),
    backend: str = Form("gemini"),
    model: str = Form(""),
    x_gemini_key: str | None = Header(default=None),
):
    # Sync def → FastAPI runs it in a worker thread, so slow API calls don't block other requests.
    data = _read_upload(image)
    if preset not in load_presets():
        raise HTTPException(400, f"Unknown preset '{preset}'.")
    try:
        result = paint(data, preset, strength=strength, extra=extra[:500], backend=backend,
                       api_key=x_gemini_key or None, model=model or None)
    except BackendError:
        raise
    except OSError:
        raise HTTPException(400, "Could not read that file as an image.")
    return Response(to_bytes(result.painting), media_type="image/jpeg", headers={
        "X-Seconds": f"{result.seconds:.1f}",
        "X-Backend": result.backend,
        "Cache-Control": "no-store",
    })


def _read_upload(image: UploadFile) -> bytes:
    data = image.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Image larger than 20 MB.")
    return data


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


def main():
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "7860"))
    print(f"Monet Agent → http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
