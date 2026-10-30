# Fast Intro v2 contract

Replaces the four diverging v1 one-offs (ivory `fast_intro_v1`, dual-source
`retro_stat_collage`, 24s `build_match_cut_plan.py`, hard-coded
`emit_disaster_chapter_intro`) with one spec + one recipe enum.

## Recipes

| id | recipe | duration | layers |
|---|---|---|---|
| `fast_intro_v2_opening` | `OpeningPlate` | 120f (4.0s) | 12 |
| `fast_intro_v2_punch` | `PunchStat` | 150f (5.0s) | 10 |
| `fast_intro_v2_whip` | `WhipMatch` | 180f (6.0s) | 10 |
| `fast_intro_v2_chapter` | `ChapterCard` | 150f (5.0s) | 17 |

All at 1920x1080 @ 30fps, `Inter-Black` default, camera push on every recipe,
hook motion in frames 0-12, scales clamped to [0.02, 3.5].

## What v2 fixes vs v1

- **Single source.** `addFastIntroV2()` in
  `src/chronontemplate/fast_intro/FastIntroPack.cpp` owns all four recipes.
  `tools/fast_intro/build_fast_intro_v2.py` mirrors the same math for
  Windows/no-build verification; `tools/fast_intro/emit_fast_intro_v2.cpp`
  lowers through the real `TemplateScene` path on Linux CI.
- **Hook first.** Kicker/title/scale-punch all start at frame 0 and read by
  frame 10-12. No dead 2-second openings.
- **Camera always moves.** Every recipe pushes (`160-200` units over the clip).
- **No singularities, no spikes.** Rail/band start at `0.02`, punch stat caps
  at `3.4` (was `8.2`), collage at `3.2` (was `6.5`).
- **Typography.** `Inter-Black` everywhere text exists; `Inter-Regular` fails
  the contract. Chips are real pills (rounded-rect + stroke + text), not bare
  text. Topics are 0-4 flexible (was exactly 3).
- **Punch background unified.** The Python ring-tunnel look is now 5 native
  stroked rings expanding `1.0 -> 1.12` + the 11-stop radial gradient + light
  noise — no CPU texture, no baked PNG.
- **Whip is parametric.** 4-16 plates via spec, full-bleed `Cover` fit, no
  pillarbox, vignette as one radial disc (was baked `_vignette.png`), <= 20
  layers (was 70+ for 24s).
- **Chapter is parametric.** Title/label/subtitle via spec, single
  `TextGlowStyle` declaration (was 3 duplicated text layers), 12 drifting dust
  motes (was 24 hard-coded LCG particles), correct
  `ChrononTemplate/assets/fonts/` paths.

## Files

```text
include/chronontemplate/fast_intro/FastIntroPack.hpp  v1 (compat) + v2 API
src/chronontemplate/fast_intro/FastIntroPack.cpp       single-source recipes
tools/fast_intro/build_fast_intro_v2.py               no-build mirror emitter
tools/fast_intro/emit_fast_intro_v2.cpp               Linux C++ emitter
tools/fast_intro/test_fast_intro_v2.py                fail-closed contract
catalog/fast_intro_motion.v1.json                     4-recipe catalog
golden_plans/fast_intro_v2/*.plan.json                committed reference plans
```

## Regenerate

```sh
python3 ChrononTemplate/tools/fast_intro/build_fast_intro_v2.py \
  --out ChrononTemplate/out/fast_intro_v2 [--vertical]
python3 ChrononTemplate/tools/fast_intro/test_fast_intro_v2.py \
  --dir ChrononTemplate/out/fast_intro_v2
```

V1 (`fast_intro_v1`, `retro_stat_collage_v1`) is kept for compatibility but
frozen: new work uses v2 only.

## Renderer conventions learned while validating (Windows CLI, 2026-10-30)

Hand-written plans must follow the dialect the native CLI decodes, confirmed
by probe renders against `chronon3d_cli.exe` (software backend):

- **Positions are per-kind.** Text/shape positions are canvas pixels with the
  layer center at the point (e.g. title at `[960, 540]`). Image/color
  positions are **center-relative** (canvas center is `[0, 0]`): a fullscreen
  plate is `position [0, 0]`, a left duo card is `[-480, -55]`. Writing an
  image at `[960, 540]` renders it in the bottom-right quadrant. This matches
  `tools/entities_with_text/build_entity_presentation_v1.py`
  (`renderer_center_position` / `canvas_position`).
- **Text must lock its size.** `fit_mode: shrink_only` without
  `min_font_size == max_font_size == font_size` collapsed a 200px probe glyph
  to ~8px; locking the range renders the authored size exactly.
- **Easing vocabulary** is `linear | out_cubic | in_out_cubic | smoothstep |`
  … — `ease_out_cubic` / `ease_out` are rejected by the schema.
- **Fills** are bare values, never `{enabled, …}` wrappers: solid
  `fill: [r, g, b, a]`, gradient
  `fill: {type: radial, spread: pad, center, radius, color_stops: [...]}`,
  stroke `{color: "#RRGGBB", width}`. Shape types are `rect` /
  `rounded_rect` (never `round_rect`).
- **Keyframe frames must be strictly sorted** (`keyframes must be sorted by
  frame`); duplicate/out-of-order frames fail validation. The punch  collage
  scale track uses `min(140, duration-1)` before the final key.
- **Transform tracks are offsets** (`position_x/y`) except `scale` (absolute
  scalar) and `opacity` (absolute). Base positions above already encode the
  resting place.

## Renders (Windows, software backend)

```sh
python3 ChrononTemplate/tools/fast_intro/build_fast_intro_v2.py --out ChrononTemplate/out/fast_intro_v2
# validate (structural + native CLI):
python3 ChrononTemplate/tools/fast_intro/test_fast_intro_v2.py --dir ChrononTemplate/out/fast_intro_v2 --native
# render raw + encode (raw .yuv deleted after encode):
chronon3d_cli render --plan <plan> --assets-root <repo-root> --backend software \
  --video-sink raw --pipe-pixfmt yuv420p -o render/<name>.yuv
ffmpeg -f rawvideo -pixel_format yuv420p -video_size 1920x1080 -framerate 30 -i render/<name>.yuv <name>.mp4
```

Deliverables in `ChrononTemplate/out/fast_intro_v2/render/`: four MP4s
(opening 120f, punch 150f, whip 180f, chapter 150f), per-frame timing
sidecars and `thumbs/*_strip.png` contact strips. Verified pixel-side: era
and stat text present with sharp glyph edges, whip plates fullscreen,
chapter band + label legible, collage centered.
