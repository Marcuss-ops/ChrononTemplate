# Procedural backgrounds and documentary highlighting V2

## Ownership and audit

- Chronon3D owns `graphics::Field2D` (Perlin, Simplex, fBm, cellular,
  domain warp, scalar operators), `VectorField2D`, brush profiles, gradient
  mesh, path rasterization, text shaping and `PlacedGlyphRun` cluster IDs.
- ChrononMotion3D owns offline curve integration and timing. It consumes a
  scalar/vector sampling callback, not a second Perlin implementation.
- ChrononTemplate owns configurations lowered to canonical RenderPlan V3.
  No new renderer, registry, cache or runtime executor is introduced.
- Existing noise effects accept pixel size and seed; stacked noise effects
  provide independent bands without extending the effect ABI.
- Existing text span highlights follow shaping/wrapping. External documents
  require explicit trustworthy source-image regions; no OCR inference.

## Contracts

The mathematical contract is `chronon.field2d.v1`: normalized coordinates,
float32 samples in [0,1], integer seed, absolute seconds, deterministic access
independent of frame order. Drift translates coordinates continuously; it
never changes the seed at frame boundaries. Flow integration consumes that
same field through a callback. No cross-backend bitwise equality is promised.

Composition APIs validate inputs before emitting `chronon.render-plan.v3`.
Grain band sizes are logical canvas pixels (reference 1920x1080), not analog
film-grain measurements. Each band has its own seed, size and amplitude.
Text targets use native spans; region targets are source-image pixels mapped
onto the displayed rectangle. Stroke widths may be absolute or font-relative.

## Artifact acceptance

Output root: `ChrononTemplate/out/procedural_documentary_v2/`.

Backgrounds: `grain_cinematic.mp4`, `noise_clouds.mp4`,
`topographic_flow.mp4`, `liquid_warp.mp4`, `technical_grid.mp4`,
`light_fibers.mp4`, `modern_dark_flow.mp4`.
Every background: 1920x1080, 30/1 FPS, 150 decoded frames, 5 seconds, seed 12045.
The user's final duration requirement supersedes the initial 8/6-second proposal.

Highlights: `01_marker_quality.mp4`, `02_underline_various.mp4`,
`03_web_article_focus.mp4`, `04_newspaper_investigation.mp4`,
`05_multi_line_highlight.mp4`, `06_tracking_focus.mp4`,
`07_glow_outline.mp4`, `08_data_highlight.mp4`,
`09_mask_spotlight.mp4`, `10_documentary_master.mp4`.
Every highlight: 1920x1080, 30/1 FPS, 150 decoded frames, 5 seconds.
Vulkan must be selected explicitly; GPU-native admission is checked separately
from Vulkan rendering with any internal CPU preparation.

Plans and PNG golden frames live alongside the videos; measured timings and
quality checks live in `metrics.json`. A valid schema/build alone is not video
certification. Check decoded frame count, dimensions, rate and duration with
ffprobe. Repeat raw PNG renders at the same frame/seed/backend and compare
hashes; compare another seed for variation. Measure software and Vulkan
separately. Inspect temporal frame differences, grain mean/variance, thin
stroke coverage and dark gradient quantization. Report unsupported GPU lanes
or missing artifacts as NOT RUN, never PASS.

## Resource policy

Before builds inspect MemAvailable, cgroup limits and existing jobs. Use
ccache and mold, at most 16 compiler workers, conservative memory reserve.
Render one video at a time with bounded worker counts; do not stop unrelated
jobs. Keep generated artifacts out of version control. No production changes,
remote publishing or pushes are part of this task.
