# Monet Agent

Turn a photo into a Claude Monet–style painting. Pick a Monet series (Water Lilies, Rouen Cathedral,
Haystacks, London fog, …), get a painting back, compare with a before/after slider.

No GPU needed — the painting is done by Google's Gemini image model through its API.

<!-- TODO: before/after gallery from examples/ -->

## Run it

```bash
git clone https://github.com/Eddie016/monet-photo.git && cd monet-photo
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
monet-web            # → http://127.0.0.1:7860
```

Paste a Gemini API key into the **Engine** section of the page (free at
[aistudio.google.com/apikey](https://aistudio.google.com/apikey)), or put it in `.env`:

```bash
cp .env.example .env   # then fill in GEMINI_API_KEY
```

Without a key you can still try the UI with the **Offline preview** backend (a simple local filter —
not a real Monet).

### Command line

```bash
monet photo.jpg --preset water_lilies --strength bold -o painting.jpg
monet --list-presets
```

## Presets

| id | Series | Best for |
|---|---|---|
| `impression` | Impression, Sunrise · Woman with a Parasol | anything, people, daylight |
| `water_lilies` | Water Lilies · Japanese Footbridge | ponds, lakes, gardens |
| `rouen_cathedral` | Rouen Cathedral | buildings, facades |
| `haystacks` | Grainstacks · Poppy Field | fields, countryside, golden hour |
| `london_fog` | Houses of Parliament · Charing Cross Bridge | fog, rivers, city, night |
| `the_magpie` | The Magpie · Snow at Argenteuil | snow, winter |

Presets are plain YAML in `monet/presets/` — add your own. For better style fidelity, drop 1–3
public-domain Monet paintings into `monet/refs/<preset id>/`; they are sent as style references.

**Strength**: `subtle` stays close to the photo, `bold` is loose like late Monet.

## How it works

```
browser ──multipart──▶ FastAPI /api/paint ──▶ preprocess (EXIF rotate, ≤1536px)
                                           ──▶ backend.stylize(photo, preset)   # Gemini / preview
                                           ──▶ crop result to the photo's frame ──▶ JPEG
```

- `monet/backends/` — pluggable backends behind one `stylize()` interface
- `monet/presets.py` — prompt template + per-series style descriptions
- `monet/server.py` — API + serves the static UI in `monet/web/` (no build step)

## API keys & privacy

- The key you paste is sent only to this server, which forwards it to Google; it is stored in your
  browser only if you tick "Remember".
- **Deploying publicly? Do not set `GEMINI_API_KEY` on the server** — anyone could spend your quota.
- Gemini's free tier may use your inputs to improve Google's products. Use a paid key for private photos.

## Roadmap

- [ ] `--agent` mode: analyze scene → pick preset → generate → critique → retry
- [ ] Auto preset selection from the photo
- [ ] Other backends (fal / Replicate Flux Kontext, local SDXL + ControlNet + Monet LoRA)
- [ ] Hugging Face Spaces deploy

## License

MIT. Monet's paintings are in the public domain.
