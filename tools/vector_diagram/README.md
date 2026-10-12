# Vector diagram composers (ChrononMotion3D -> RenderPlan bridge)

Five high-level, reusable behaviors over EXISTING native primitives
(no new renderer; SVG/Lottie stay compile-time inputs):

| Composer | Native primitive |
|---|---|
| `VectorDrawOn` | `shape.path` + `operators[trim + trim_animation]` |
| `FollowPath` | `layer.follow_path {path_commands, progress}`, SAME geometry object as the drawn path |
| `GlowMarker` | `shape.ellipse` + `effects[glow]` + opacity/start window |
| `ShapeMorphAnimation` | `operators[morph + morph_animation]`, matching topology or fail-closed |
| `AnimatedDiagram` | deterministic 90f/30fps `chronon.render-plan.v3` composition |

Recipe `vector_documentary_diagram` (90f): trajectory reveal [8,40],
traveling dot [12,60] + glow, peak marker [48,67] + glow, static camera.

## Artefacts (`out/`)

- `vector_documentary_diagram.plan.json` — conceptual recipe (agent-facing)
- `vector_documentary_diagram.native_v3.plan.json` — strict native v3,
  `chronon3d_cli validate` PASS (decoder+compiler accept trim/morph/follow/glow)
- `vector_documentary_diagram.baked_v3.plan.json` — sprite-chain bake of the
  same sampler data (renders on backends without path-stroke/follow; same
  vocabulary as ChrononMotion `authorGlowChain`), validate PASS + 90 software
  frames rendered (`baked_*.png`)
- `vector_morph_test.native_v3.plan.json` — morph fixture, validate PASS
- `vector_plus_footage.plan.json` — vector persists 0..90, video plate 60..90
  (compositing/timing at plan level)

## Coordinate convention (measured on `linux-video-test` software backend)

- color layers: `position` = top-left px (background must be `[0,0]`)
- shape layers: `position` = offset from canvas center (`px = pos + half`);
  `shape.path` points are relative to the layer origin
- `follow_path.path_commands` are absolute canvas coords
  (`world = point - half`, same center-offset space)

With trajectory `pos=[0,0]`, `rel=ABS-half`, follow commands `ABS`,
both describe world line `ABS`: `dot_on_path` holds by construction and is
checked per-frame by `test_vector_diagram.py` (<=1px).

## Backend limits found (this build, software lane, honest scope)

- path-stroke layers do not rasterize pixels here (rect/ellipse do);
  trim evaluation itself is covered by the Lottie L5 C-ABI/CLI gates.
- any `opacity` animation track on a shape ellipse hides it entirely here;
  visibility is therefore driven by `start_frame`/`duration_frames` windows.
- `follow_path` validates but the head renders at base position (progress
  ignored) in this lane; movement is certified by the shared-geometry gate
  plus the baked-variant pixel walk
  (head `(192,885)->(524,577)->(1140,157)->(1652,769)->(1688,842)`).

Vulkan/NVENC, Drive publication, Edge-TTS voiceover and footage pixels are
out of scope for this headless ticket (same boundary as TICKET-LOTTIE-ANIMATED:
software scene evaluation PASS, GPU capability separate).
