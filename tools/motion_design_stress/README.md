# Motion-design stress suite (20 cases, 4 modules)

C++ contract suite for the documentary motion-design pipeline. Each case authors
a `chronon.render-plan.v3` document, checks the invariant a renderer bug would
break, and writes the plan to `out/motion_design_stress/plans/`. The plans are
then validated and rendered by the Chronon3D CLI; the C++ checks keep the
authoring contract pinned without a GPU in CTest.

## Layout

| Path | Purpose |
|---|---|
| `tests/motion_design_stress.cpp` | 20 cases, 403 assertions, plan emitter |
| `tools/motion_design_stress/generate_assets.py` | deterministic paper, cutout, bokeh and logo assets |
| `out/motion_design_stress/plans/` | 24 emitted plans (some cases emit two/three) |
| `out/motion_design_stress/frames/` | representative single-frame renders + contact sheet |
| `out/motion_design_stress/assets/` | generated PNGs and `manifest.json` |

## Coverage

| # | Case | Contract |
|---|---|---|
| 01 | Multiply over paper grain | black stays 0, grain survives, linear vs gamma result differs |
| 02 | Off-centre anchor + asymmetric X scale | left edge pinned for 15 frames across three line lengths |
| 03 | 3D rack focus | ten planes, 60 camera samples, monotonic focus, constant f/1.4 and 28 px cap |
| 04 | Micro-typography pan | 12 px floor, sub-2 px/frame horizontal motion, no duplicate time key |
| 05 | Multi-highlight | crossing Multiply marks darken, channels stay in gamut |
| 06 | Alpha cutout | premultiply round-trip, no white/black fringe, soft hair edge |
| 07 | 2.5D parallax + dolly | near/mid/far displacement ordering, cubic ease-out deceleration |
| 08 | Background dimming + blur | `-2.5 EV` exact matte factor, 40 px gaussian, oversized blur plate |
| 09 | Add/Screen particles | 500 + 200 motes, Add may exceed alpha 1, Screen stays in [0,1] |
| 10 | Z-sorting | two non-overlapping depth bands crossing the subject plane |
| 11 | Logo 360° Y + lighting | 0→360 in 90° steps, key/ambient/rim rig |
| 12 | Spring overshoot | 112% peak → exactly 100% on frame 12, no residual rise |
| 13 | Motion blur 180/360 | shutter and sub-frame count both double |
| 14 | Parent-child non-uniform scale | uncompensated stretch and compensated uniform world scale |
| 15 | Drop shadow + glow | shadow follows the logo rotation curve, 80 px shadow, 90 px glow |
| 16 | Whip velocity continuity | analytic derivatives match at the cut; linear ramp visibly mismatches |
| 17 | Directional blur at 150% height | 1620 px kernel, 32 samples, clamp-vs-zero edge proof |
| 18 | 4K60 stress | 3840×2160, 600 frames, all layer families, 300 camera samples |
| 19 | Chromatic aberration | offsets proportional to velocity, exactly zero on landing |
| 20 | Multi-codec Rec.709 | H.264, H.265 and lossless PNG sequence share identical layers |

## Build and run

```bash
cd ChrononTemplate
python3 tools/motion_design_stress/generate_assets.py
cmake -S . -B build/dev-fast -DCHRONONTEMPLATE_BUILD_TESTS=ON
cmake --build build/dev-fast --target chronontemplate_motion_design_stress_test -j 8
./build/dev-fast/chronontemplate_motion_design_stress_test
ctest --test-dir build/dev-fast -R chronontemplate_motion_design_stress --output-on-failure
```

The asset generator needs a Python with `numpy` and `Pillow`; the CMake test
target only runs the compiled C++ suite, because the project Python found by
`find_package(Python3)` may not have those packages.

## Validate and render

```bash
CLI=../Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli
for plan in out/motion_design_stress/plans/*.plan.json; do
  "$CLI" validate --plan "$plan" --assets-root "$PWD"
done
```

Render one frame of a case (the MP4 route is pixel-truth, unlike the still/PNG
lane which warns that it does not compose text):

```bash
"$CLI" render --plan out/motion_design_stress/plans/01_multiply_paper_grain.plan.json \
  --assets-root "$PWD" --start-frame 30 --end-frame 30 --backend software \
  -o out/motion_design_stress/frames/01_video_frame.mp4
ffmpeg -y -i out/motion_design_stress/frames/01_video_frame.mp4 \
  -frames:v 1 out/motion_design_stress/frames/01_video_frame.png
```

The representative render set is in `out/motion_design_stress/frames/`; the
contact sheet is `contact_sheet.png`.

## Results (2026-11-14)

- C++ suite: **403 checks, 0 failures**; CTest target passes.
- Emitted plans: **24**; `chronon3d_cli validate`: **24/24 valid**.
- Assets: 6 deterministic PNGs, SHA-256 recorded in `assets/manifest.json`.
- Rendered and inspected: 01, 02, 03, 05, 06, 07 (partial 3D frame), 08,
  09, 10, 11, 12, 13, 14, 15 (edge-on frame), 16, 17, 19.
- Delivery formats: H.264/Rec.709, H.265/Rec.709, lossless PNG sequence.

### Engine fixes validated by the renders

- Screen-space **Shape** positions are top-left in V3. The compiled lowering
  now adds `size/2` before making the sample canvas-relative: the callout badge
  lands at `[320,310]-[959,489]`, its centre is `[640,400]`, and `$10,000` is
  inside it. 02's highlight left edge is pinned at `x=360` for all three widths.
- Vector `scale`/`position` tracks are split into scalar component tracks in
  the typed lowering. 12's spring reaches **716x202** at frame 8 (1.12x) and
  settles to **640x180** at frame 12; 14's non-uniform parent is **840x144**.

## Post-review fixes (2026-11-14)

- **12 / Vulkan drop shadow:** native drop-shadow radius window raised from 32
  to 64; the plan's radius 36 now renders. Strict Vulkan parity test passes
  522/522. The MP4 is non-black in all 13 frames; the badge/text appear as
  the intro animation resolves.
- **03 / projected text:** the camera looks at the back of the 3D card, so the
  text is mirrored by construction. The fixture now flips the text layer X
  (`scale: [-1, 1, 1]`); the render reads `FOCUS PLANE` normally without
  changing camera, DoF or rack-focus.
- **02 / highlights:** each bar now uses the measured line bbox instead of one
  900 px bar at x=360: `810/543/465` and widths `300/840/990`. Frame 15 has the
  three bars aligned to their lines.
- **09/10 particles:** `normaliseScreenSpace()` no longer shifts particle layers
  from their centred basis to top-left. Frame 60 covers the full canvas
  (`09: 0..1919x0..1071`, `10: 0..1919x0..1079`).
- **12 text-vis:** the post-render audit now uses the draw's actual ink bbox and
  the real framebuffer clip, not the predicted box; frame 8 has zero
  `CLIP_DROPS_INK` / `NO_INK_RENDERED` warnings.
- Suite after the fixes: **403 checks, 0 failures**.

## Video delivery (2026-11-14)

- **22 MP4 at 1920x1080**, max 4.0 s, in
  `out/motion_design_stress/videos/`.
- **20 rendered with Vulkan**. 09 and 10 fall back to the software backend
  because Vulkan times out on their screen-space particle placement; see the
  particle ticket.
- **18 (UHD60) and 20c (lossless)** are excluded per the delivery request: no
  4K, no ProRes/lossless requirement.
- Uploaded to the supplied Drive folder:
  https://drive.google.com/drive/folders/1J_xUGo_bchzXDIGqSX04CU44c_Dm3SxS
  (`videos/drive_manifest.json` has the per-file links; 01 has one duplicate
  from the uploader smoke test).
- Corrected 02/03/12 also in subfolder **`fix_2026-11-14`**:
  https://drive.google.com/drive/folders/117ayvGXRgPy80fQ7lu-_vFyVqOxeciWJ
  (`videos/drive_fixes_manifest.json`).
- Local manifest: `out/motion_design_stress/videos/manifest.json` (dimensions,
  duration, codec, SHA-256).
- No suite tickets remain open after the 2026-11-14 closeout.

## Known limits / not reachable today

- **ProRes 4444** is not in the output codec enum (`auto`, `h264`, `h265`,
  `vp9`, `av1`). Case 20 uses a lossless PNG sequence as the reachable lossless
  proxy; it does not test a ProRes encoder.
- **Layer-level exposure** is not in the effect union. Case 08 uses the exact
  `1 - 2^-2.5 = 0.8232233` black matte, which is mathematically identical for
  a linear dim, plus the 40 px gaussian. The `color.exposure` identifier exists
  only in the effect-parameter track vocabulary.
- **Directional blur edge mode** is not exposed as an effect property. Case 17
  proves the clamp-vs-zero difference and supplies an oversized edge plate so
  the plan itself carries clamped pixels.
- **4K60 frame time** is not measured. Case 18 validates the UHD/600-frame
  authoring contract and construction time (< 5 s), not GPU frame stability;
  rendering 4K60 on the software backend is not practical here.
- **09/10 Vulkan performance**: placement is fixed and the software frames
  cover the full canvas, but Vulkan still times out on the 120-frame particle
  jobs. The delivered 09/10 MP4s remain on the software fallback; this is a
  performance limitation, not the old top-left placement bug.
- **DoF/backface pixel quality** is checked structurally (camera samples,
  rotation continuity, normal/backface authoring), not with a GPU pixel probe.

## Next steps

1. Re-render 09/10 with the corrected centre and measure Vulkan frame time;
   placement is fixed, performance is the remaining work.
2. Use Vulkan for 09/10 after the particle ticket closes; measure per-frame
   time and replace the structural 4K60 gate with a real budget assertion when
   4K is back in scope.
3. If ProRes 4444 is ever back in scope, add output support and extend case 20
   to compare the decoded ProRes and H.264 frames rather than only the authored
   layers.
4. Expose a layer-level exposure effect and a directional-blur `edge_mode`;
   cases 08 and 17 can then test the engine property instead of the workaround.
5. Add a pixel probe for DoF gradient continuity, premultiplied alpha edges and
   backface culling on the GPU backend.
6. Keep `videos/drive_manifest.json` in sync if the videos are re-rendered;
   the current 22 files are already uploaded to the supplied folder.
