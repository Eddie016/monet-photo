"""Command line: monet photo.jpg --preset water_lilies -o painting.jpg"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from . import paint
from .backends import BACKENDS, BackendError
from .presets import STRENGTHS, load_presets


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(prog="monet", description="Turn a photo into a Monet-style painting.")
    ap.add_argument("photo", nargs="?", type=Path)
    ap.add_argument("-p", "--preset", default="impression", choices=list(load_presets()))
    ap.add_argument("-s", "--strength", default="medium", choices=list(STRENGTHS))
    ap.add_argument("-x", "--extra", default="", help="extra instruction appended to the prompt")
    ap.add_argument("-b", "--backend", default="gemini", choices=list(BACKENDS))
    ap.add_argument("-m", "--model", help="Gemini model id (default: $MONET_GEMINI_MODEL or gemini-2.5-flash-image)")
    ap.add_argument("-o", "--out", type=Path, help="output path (default: <photo>_<preset>.jpg)")
    ap.add_argument("--list-presets", action="store_true")
    args = ap.parse_args(argv)

    if args.list_presets:
        for p in load_presets().values():
            print(f"{p.id:16} {p.name:22} best for: {', '.join(p.best_for)}")
        return 0
    if not args.photo:
        ap.error("photo is required")

    out = args.out or args.photo.with_name(f"{args.photo.stem}_{args.preset}.jpg")
    try:
        result = paint(args.photo.read_bytes(), args.preset, strength=args.strength, extra=args.extra,
                       backend=args.backend, model=args.model)
    except BackendError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    result.painting.save(out, quality=92)
    print(f"{out}  ({result.backend}, {result.seconds:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
