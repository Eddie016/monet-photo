"""Monet sub-style presets, loaded from the YAML files in monet/presets/."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

PRESET_DIR = Path(__file__).parent / "presets"
REFS_DIR = Path(__file__).parent / "refs"

# How far the painting may drift from the photo.
STRENGTHS = {
    "subtle": "Stay very close to the photograph: keep shapes, edges and proportions precise; the painting is a faithful translation with visible brushwork.",
    "medium": "Keep the composition, perspective and every major shape where it is, but let small details dissolve into brushwork.",
    "bold": "Keep only the overall composition and main masses; be loose and expressive, as in Monet's late work where forms nearly dissolve.",
}

BASE_PROMPT = """Repaint the photograph as an original oil painting on canvas by Claude Monet.

Composition: {strength}
Do not add or remove objects, people or buildings. Keep the same framing and camera angle.

Style:
{style}

The result must look like a photograph of a real 19th-century oil painting: visible bristle marks, paint ridges and canvas weave, no digital smoothness, no photographic detail left over.
Do not add a frame, signature, text or watermark. The painting fills the entire image.{extra}"""


@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    works: str
    prompt: str
    best_for: list[str] = field(default_factory=list)

    def build_prompt(self, strength: str = "medium", extra: str = "") -> str:
        extra = extra.strip()
        return BASE_PROMPT.format(
            strength=STRENGTHS.get(strength, STRENGTHS["medium"]),
            style=self.prompt.strip(),
            extra=f"\n\nAdditional instruction from the user: {extra}" if extra else "",
        )

    def reference_paths(self) -> list[Path]:
        """Optional public-domain Monet images in monet/refs/<preset id>/ used as style references."""
        d = REFS_DIR / self.id
        if not d.is_dir():
            return []
        return sorted(p for p in d.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "works": self.works, "best_for": self.best_for,
                "has_refs": bool(self.reference_paths())}


@lru_cache(maxsize=1)
def load_presets() -> dict[str, Preset]:
    presets = {}
    for path in sorted(PRESET_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        presets[data["id"]] = Preset(**data)
    # Put the general-purpose preset first.
    return dict(sorted(presets.items(), key=lambda kv: kv[0] != "impression"))


def get_preset(preset_id: str) -> Preset:
    presets = load_presets()
    if preset_id not in presets:
        raise KeyError(f"Unknown preset '{preset_id}'. Available: {', '.join(presets)}")
    return presets[preset_id]
