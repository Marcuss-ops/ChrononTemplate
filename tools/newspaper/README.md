# Linux newspaper scenes

Linux replacement for the Windows/Blend2D newspaper beats in
`tools/youtuber_style` (front page, dossier close-up, highlighter sweep,
declassified memo). No Blend2D, no browser, no `C:/` paths.

## Run everything

```bash
bash tools/newspaper/render_newspaper_pages.sh
```

Outputs land in `out/newspaper_pages/`:

- `newspaper_front_page.mp4` — 1920×1080, 30 fps, 180 frames
- `newspaper_dossier.mp4` — 1920×1080, 30 fps, 150 frames
- `newspaper_highlighter.mp4` — 1920×1080, 30 fps, 150 frames
- `newspaper_memo.mp4` — 1920×1080, 30 fps, 150 frames
- `plans/*.plan.json` — the RenderPlan V3 documents
- `verification.tsv` — codec / resolution / frame-count manifest
- `renders/` — temporary NV12 streams (removed after successful encode)

Render a single scene while iterating:

```bash
SCENE=newspaper_dossier bash tools/newspaper/render_newspaper_pages.sh
```

Useful environment overrides:

- `CHRONON3D_CLI=/path/to/chronon3d_cli`
- `CHRONON_BACKEND=software` (default) or `vulkan`
- `CHRONON_PROFILE=preview` (default), `draft`, `production`, `maximum`

Requirements: `g++` (C++20) + stb headers (Chronon3d vcpkg), `ffmpeg`,
`ffprobe`, and the canonical `chronon3d_cli`. Python3 is only needed for the
plan emitter; Pillow/numpy only for the legacy fallback composer.

## Pipeline

1. `make_newspaper_pages.cpp` composes the four 1920×1080 pages in C++
   (stb_image/stb_truetype/stb_image_write; same layout/copy as the former
   Python composer, which is kept as `make_newspaper_pages.py` fallback):
   masthead, headlines, columns, photo, rules, stamp, notes. It also measures
   the highlighter/redaction rectangles and writes
   `assets/newspaper/pages/meta.json`, so the art and the live overlays cannot
   drift apart.
2. `emit_newspaper_plans.py` turns each page + overlay metadata into a
   `chronon.render-plan.v3` document: one screen-space image layer with a
   fade/settle, plus animated marker and redaction shape layers.
3. `render_newspaper_pages.sh` validates every plan, rasterizes with the
   Chronon3D CLI, encodes H.264/yuv420p with ffmpeg, and checks the result with
   ffprobe.

## Why the pages are baked

In this CLI build the text layer path has two quirks that make a fully native
text layout unreliable for a newspaper page:

- text composites **below** shape/image layers, so paper and photo layers can
  cover it;
- text `position` is the **absolute centre of its box**, while shape/image
  `position` is an **offset from the canvas centre**.

Keeping editorial type in the page PNG avoids both issues and gives exact
typography with the bundled Playfair Display/Inter fonts. Chronon still owns
the motion: the page is an animated image layer, and the yellow marker bands
and black redaction bars are native shape layers driven by RenderPlan tracks.

## Coordinate conventions

- Canvas: 1920×1080.
- Image/shape `position` is an offset from the canvas centre. A full-frame
  layer at `[0, 0]` is centred.
- `position_x` / `position_y` animation tracks are **additive offsets** from
  the layer position, not absolute coordinates. A marker sweep therefore ends
  at `0`, not at its final screen coordinate.
- Page coordinates in `meta.json` are ordinary top-left pixels; the plan emitter
  converts each rectangle to the centred shape position.

## Editing

- Change copy/layout in `make_newspaper_pages.cpp` (and mirror it in the
  fallback `make_newspaper_pages.py`); overlay rectangles are re-measured
  from the actual text boxes.
- Change timing, marker delay/span/opacity in the returned `meta` dicts, or in
  `emit_newspaper_plans.py` for shared behavior.
- Re-run the render script; it regenerates pages and plans automatically.
