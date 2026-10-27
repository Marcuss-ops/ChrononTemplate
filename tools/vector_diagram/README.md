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

## Verification scope

Older notes in this section described failures from a previous software build.
They are not current guarantees. The raw software sink was manually checked
against `vector_documentary_diagram.native_v3.plan.json` at frames 12–60: the
yellow marker moves and its measured centroid follows the path sampler within
0.8 px. `test_vector_diagram.py` remains a geometry/composition test and does
not claim renderer pixel truth.

`svg_peak_pixel_gate.py` is the focused automated pixel gate for imported SVG
pixels, rendered marker alignment, moving-marker glow halo/residue, and repeat
determinism. Run it against an SVG-enabled CLI build:

```sh
python3 tools/vector_diagram/svg_peak_pixel_gate.py --cli /path/to/chronon3d_cli
```

This synthetic 320×180 gate does not certify the supplied 19.63-second video,
target-scene glow, vehicle pivots, footage compositing, GPU parity, or reference fidelity.
The original footage is not stored in this repository, so those checks need
the source video and an approved scene contract.

## Documentary SVG graph study

`assets/documentary_svg_peak_v1.svg` and
`render_documentary_svg_peak_v1.py` produce a five-second 854×480 animation
using Chronon3D's software renderer, including imported-SVG Trim Paths and a
marker following the same path geometry. Generate it with:

```sh
python3 tools/vector_diagram/render_documentary_svg_peak_v1.py \
  --cli /path/to/chronon3d_cli
```

The preset lives in `catalog/documentary_svg_peak_v1.json`; edit its canvas,
trim timing, marker, optional glow, or framing values and rerun the renderer.
The follow-path points are resolved from `#peak_line` in the SVG, so the chart
geometry is not duplicated in the generator. The resolver currently accepts
explicit `M`/`L` path data and fails closed on other path commands.

The H.264 MP4, editable RenderPlan, sampled PNGs and contact sheet are in
`artifacts/documentary_svg_peak_v1/`. The sequential path loss was traced to
the compiler treating `Composite` nodes as static bake candidates even though
the executor bypasses inter-frame caching for them. The compiler now excludes
composites from static bakes, and `svg_peak_pixel_gate.py` requires path pixels
to remain visible in an unguarded sequence with a moving marker. The preset's
constant-opacity workaround has been removed; its encoded artifacts are being
rerendered against the fixed source. This graph study is not a recreation of
the complete reference video. The registered preset is defined in
`catalog/documentary_svg_peak_v1.json` and lowered by
`documentary_svg_peak_registry.py`; its catalog controls cover geometry derived
from the SVG, timing, marker styling/glow, and framing. The synthetic glow
pixel gate passes; target-scene glow remains open.

## Rigging 2D + Anims

`rig_2d_anims/` contains a reusable SVG puppet rig split into torso, head,
upper/lower arms, hands, thighs and shins, with composite arm and leg controls.
Its four 4-second clips exercise breathing, a shoulder-pivot wave, an
alternating walk cycle, and a jump with anticipation and landing. The
`shape.element_animations` tracks address SVG group IDs; rotations pair with
translation tracks calculated from each shoulder or hip pivot, keeping the
composite limbs connected during motion.

Generate and render the four MP4s plus a contact sheet through Chronon3D's SVG
enabled software renderer:

```sh
CHRONON_CLI=/path/to/svg-enabled/chronon3d_cli \
  tools/vector_diagram/rig_2d_anims/render_rig_2d_anims.sh
```

Outputs and editable plans are written to `artifacts/rig_2d_anims_v1/`.
The source SVG and plan emitter stay in the `rig_2d_anims/` section; the
renderer executes the SVG and keyframes as native Chronon RenderPlan data.

The showcase renders headlessly with Chronon3D's software renderer; no GPU is
required. Edge-TTS voiceover and footage pixels are outside this SVG-rigging
example.
