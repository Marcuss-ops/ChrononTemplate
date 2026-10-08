# ChrononTemplate

Separate C++ composition presets for ChrononMotion. This module does not belong
inside the ChrononMotion core: it consumes the core's `MotionScene`, `Layer`,
`ContentRef`, camera, lighting, material and preset APIs.

## Contents

```text
CMakeLists.txt                            the module build (library + tests)
CMakePresets.json                         dev / dev-fast / release / release-fast
include/chronontemplate/chronontemplate.hpp     Presets + the orchestration API
include/chronontemplate/core/Presets.hpp
src/chronontemplate/core/Presets.cpp
include/chronontemplate/core/ContentHost.hpp         what this module asks Chronon for
include/chronontemplate/core/ContentBinding.hpp      layer -> content
include/chronontemplate/core/FrameSubmission.hpp     what the renderer is handed
include/chronontemplate/core/MotionBridge.hpp        the conversion, one direction
include/chronontemplate/core/TemplateScene.hpp       the authoring API a template sees
include/chronontemplate/core/UiPrimitives.hpp        validated web composition primitives
src/chronontemplate/{ContentBinding,MotionBridge,TemplateScene}.cpp
include/chrononmotion/templates/Templates.hpp   moved out of the motion core
src/chrononmotion/templates/Templates.cpp
tests/motion_check.hpp                    the module's own test harness
tests/fake_content_host.hpp               the shared Chronon-side double
tests/motion_templates.cpp
tests/presets.cpp
tests/template_scene.cpp                  the orchestration contract
tests/youtube_subscribe.cpp               the pack's composition and timing
```

## Pack layout (by animation category)

The pack sources are grouped by the kind of animation they author. Headers and
sources mirror each other under `include/chronontemplate/` and
`src/chronontemplate/`, so a pack is found by category first, family second.
The retired map-beat API was replaced by `ModernMapPack`; callers should use
`ModernMapSpec` and `composeModernMap()` for styled labels and authored camera
moves. `MapTextRole` exposes title, primary/secondary location, data-value,
legend, and attribution typography presets. `ModernMapSpec` can add independently
revealed subtitle/attribution, data cards, legend rows, and multi-segment callout
leaders. Geographic projection and provider attribution metadata remain owned
by RenderingGen; ChrononTemplate accepts already-positioned editorial elements
and does not implement geographic projection.

```text
important_phrases/          phrasing and titling, one subdir per family
  ImportantPhrasePack            shared look + plan data types
  classic/                       fourteen "normal" phrase animations
  typewriter/                    fifteen typed animations, `_` cursor
  typewriter_3d/                 3D typewriter + neon glow / web cards
  apple/                         modern restrained phrase presets
  highlight/                     long phrases with animated under-phrase accents
  didone/                        editorial Didone title pack
short_phrases/              ShortPhrasePack — 12 archetypes for phrases of 1–7 words
                            (+ short_phrase.decor.star_bumper, semantic emphasis, exit modes)
single_images/              ImageAnimationPack — one-image 2.5D entrances
multiple_images/            MultiImagePack — duo/trio/quad/penta boards with captions
backgrounds/                BackgroundPack — editorial documentary/grid/scan/dust looks from shape layers
entities_with_text/         DocumentarySnapshotPack + YouTubeSubscribe
map/                        ModernMapPack — styled plate, labels and camera beat
camera_roll/                TitleCameraPack + SceneCameraPack — camera-only motion
transitions/                TransitionPack — twelve legacy + eight rapid looks
captions_dataviz/           CaptionsDataVizPack — PCM beat grid, beat-timed captions, bar + step-line charts
composers/                  LayoutComposer — flex row/column/grid boards plus FLIP moves
```

## Tools layout

The `tools/` scripts follow the same categories, so a generator is found the way
its pack is. Shared scaffolding (`kit/`, `emit_catalog`, the cursor/envato/drive
utilities) stays at the root of `tools/`.

```text
tools/
  important_phrases/   render_/build_/test_ phrase, title and kinetic-typography suites
  short_phrases/       the short-phrase catalog emitter + its contract test
  single_images/       image-frame, photo-motion and 2.5D image suites
  multiple_images/     duo/trio/quad/penta and named multi-entity boards
  backgrounds/         cinematic light-leak, bloom, rgb, aura, tech-background suites
  entities_with_text/  entity cards, captions and documentary snapshots
  map/                 map plates, geo-camera flights, location and route suites
  camera_roll/         title-camera, scene-camera and camera-motion suites
  kit/, emit_*         shared scaffolding and the catalog emitters (root)
```

## Clean editorial short phrases

The original twelve recipes are preserved; ten append-only
`short_phrase_editorial_*` choices add Baseline Rise, Side Glide, Tracking Close,
Focus Resolve, Underline Draw, Rule Handoff, Glyph Curtain, Contrast Sweep,
Quiet Zoom and Lift And Rule. They use plain ink/ivory backgrounds, restrained
motion, shrink-only text fitting and a stationary reading hold. Accent rules
are native V3 shapes; focus blur is a native text animator, not a layer effect.
All ten are available through `shortPhraseAnimations()` and the word-count
suggestion table, with their style and accent tracks in the generated catalog.

Generate just the new preview set (1920×1080, 30 fps, 150 frames each):

```shell
cmake --build build/dev --target chronontemplate_emit_short_phrase_plans chronontemplate_emit_short_phrase_catalog
build/dev/chronontemplate_emit_short_phrase_catalog > catalog/short_phrase_motion.v1.json
build/dev/chronontemplate_emit_short_phrase_plans out/short_phrase_editorial_v1 --editorial-only
```

Render the emitted plans through Chronon3D's Vulkan/native NVENC path, using
absolute plan and asset-root paths, then verify the actual encoded frames:

```shell
python3 tools/short_phrases/verify_editorial_short_phrases.py out/short_phrase_editorial_v1
DRIVE_FOLDER_ID=12uXxT3uTNlLFclxsDxndq9U8KhF98CN_ \\
  tools/short_phrases/upload_short_phrases_drive.sh out/short_phrase_editorial_v1
```

The verifier checks the exact ten-file set, H.264, resolution, frame count,
five-second duration, visible foreground inside the safe area, a moving entrance,
a stable hold and fully disappeared first/last frames. It writes
`verification.json` with pixel measurements and SHA-256 evidence. Upload sends
only MP4s via the existing configured Drive uploader.

## Short-phrase catalog

`catalog/short_phrase_motion.v1.json` holds the short-phrase archetypes (the
twelve originals plus the append-only editorial and product-video families),
the five exit modes, the decor bumper and the selection table RenderingGen uses
to pick a recipe by word count. It is **generated from the C++ pack**, not
hand-maintained:

```shell
cmake --build build/dev --target chronontemplate_emit_short_phrase_catalog
./build/dev/chronontemplate_emit_short_phrase_catalog > catalog/short_phrase_motion.v1.json
```

The emitter is fail-closed (a malformed pack aborts the emit instead of shipping
a catalog the consumer would reject), and
`tools/short_phrases/test_short_phrase_catalog.py` (CTest:
`chronontemplate_short_phrase_catalog_contract`) pins the document and fails when
the committed file drifts from what the C++ pack emits today.

### React text-effect adaptations

Seven supplied React components have deterministic native short-phrase recipes:
`short_phrase_product_masked_heading`, `short_phrase_product_split_flap_text`,
`short_phrase_product_warp_text`, `short_phrase_product_fold_text`,
`short_phrase_product_decrypted_text`, `short_phrase_product_scroll_reveal`,
and `short_phrase_product_scrambled_text`. Their `adaptation_note` appears in
the catalog and generated manifest. The video/image text fill and pointer
parallax in MaskedHeading, live randomized split-flap tiles, WarpText's WebGL
shader and pointer response, per-unit FoldText hinges/crease, DecryptedText's
interactive triggers, viewport-driven ScrollReveal scrub, and pointer-distance
ScrambledText are not capabilities of these offline RenderPlans. The C++ pack
uses native glyph/word transforms, frame-based reveals, perspective at phrase
level, and fixed encoded-text stages where appropriate; it does not claim those
browser-only interactions are preserved.

Build the emitters, regenerate the canonical catalog and emit only the seven
React-derived V3 plans (1920×1080, 30 fps, 210 frames):

```shell
cmake --build build/dev --target chronontemplate_emit_short_phrase_catalog chronontemplate_emit_short_phrase_plans
build/dev/chronontemplate_emit_short_phrase_catalog > catalog/short_phrase_motion.v1.json
build/dev/chronontemplate_emit_short_phrase_plans out/short_phrase_react_text_v1 --react-text-only

CLI=../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli
for plan in out/short_phrase_react_text_v1/*.plan.json; do
  "$CLI" validate --plan "$PWD/$plan" --assets-root "$PWD/../Chronon3d"
  "$CLI" render --plan "$PWD/$plan" --output "$PWD/${plan%.plan.json}.mp4" \\
    --assets-root "$PWD/../Chronon3d" --backend vulkan --profile preview \\
    --hardware nvenc --fps 30
done
```

The renders are H.264 at 1920×1080, 30 fps, seven seconds each; Chronon3D
writes a per-frame timing sidecar beside each MP4. The short-phrase pack and Python catalog contract pin all seven stable IDs,
well-formed native tracks/overlay text, explicit fidelity notes, deterministic
catalog bytes and selection-table references.

## Packs

### `blackboard_torture_v1`

`include/chronontemplate/core/NativePrimitives.hpp` exposes reusable C++ `Geometry`,
`Material`, `Effects`, `Paths`, `Camera`, `Motion`, `Particles`, `Text`, and
`TemplateComposition` builders. They produce ordinary V3 RenderPlan data,
validate authoring-time dimensions and timing, and leave evaluation and
rendering with Chronon3D. The canary emitter composes these builders instead
of carrying its own mesh, stroke, camera, or particle encoders.

This ten-second RenderPlan V3 canary composes six procedural inline meshes for
the green board slab, four wooden rails and chalk tray. It writes `CHRONON` as
sixteen native path strokes revealed by the V3 Trim operator, emits seeded chalk
dust, draws an underline/arrow/circle, erases the right-hand strokes while
keeping low-opacity residue, then writes `NEXT`. A perspective camera pushes
in and drifts across the same interval. No browser, external model, or JS
renderer is involved.

Build and generate the plan in C++, then run the primitive contract and live
RenderPlan validation:

```shell
cmake --build build/dev --target chronontemplate_emit_blackboard_torture_v1 chronontemplate_native_primitives_test
build/dev/chronontemplate_emit_blackboard_torture_v1 golden_plans/blackboard_torture_v1.plan.json
ctest --test-dir build/dev -R chronontemplate_native_primitives_test --output-on-failure
../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli \
  validate --plan golden_plans/blackboard_torture_v1.plan.json
```

The CLI check validates all 47 layers against the live RenderPlan contract. To
render a frame or the full clip, pass
`golden_plans/blackboard_torture_v1.plan.json` to `chronon3d_cli render --plan`.
The existing RenderPlan material contract currently gives inline meshes a
lit base color and basic specular parameters. `Effects::noise` is available on
layer types that accept post effects; inline mesh plans currently reject layer
effects. Per-pixel roughness maps and a world-space chalk-head-follow emitter
are not representable yet. Dust therefore uses the engine's
deterministic bounded emitter over the writing interval.

A pack is composition and timing on top of `TemplateScene`; it owns no bytes, no
font and no matrix. The subscribe card is the first one: avatar, channel name,
subscriber count, button with its label, and the bell.

```cpp
TemplateScene scene("youtube_subscribe", 30.f, host);
YouTubeSubscribePack card = buildYouTubeSubscribe(scene, {
    .avatarPath = "avatar.png",
    .channelName = "Wrestling Discovery",
    .subscriberCount = "1.2M subscribers",
});

FrameSubmission frame = scene.submit(card.clickFrame);
```

The whole card is parented to one controller, so the entrance and the exit are
authored once: `worldOpacity` is the product down the hierarchy. The controller
scales 0.7 -> 1 with the motion core's overshoot (peak ~1.08) while it fades in,
and one `FadeOut` on it exits everything.

Two details the pack had to solve against the real motion core:

- a preset **appends** keys, so a second `ScalePop` on one layer would ramp from
the entrance's last key into the punch instead of pulsing. The click holds a key
one frame before it lands, then pokes to 1.12 and settles;
- `Track::add` replaces a key at an equal time, which is what makes the punch
land on the click frame instead of next to it.

## Documentary backgrounds

`BackgroundPack` exposes twenty append-only stable IDs. The original ten remain
unchanged; six native editorial looks were added (`bg_documentary_grid`,
`bg_radar_sweep`, `bg_archive_dust`, `bg_mesh_gradient`, `bg_grid_pattern`,
and `bg_particles`). Nine React-inspired effects are available as bounded native
approximations: `bg_aurora` (GradientMesh + drifting color field), `bg_dark_veil`
(warped field with optional scan/grain), `bg_dot_grid` and `bg_dot_field`
(native dot grids, seeded wave/glow accents), `bg_gradient_waves` (fractal field
and optional grain), `bg_grainient` (seeded three-color field and noise),
`bg_ripple_grid` (native grid and stroked ring), `bg_shape_grid` (moving
square/hexagon/circle/triangle cells), and `bg_silk` (drifting folded-field
approximation). The existing `bg_particles` is the tenth React port; its stable
ID is reused rather than duplicated. Canvas pointer/mouse actions are represented
by deterministic offline motion, not live interaction or pixel-identical shaders.

The looks use Chronon's native shape, ellipse, Grid, DotGrid, Field2D,
GradientMesh, and gradient fills plus ChrononMotion tracks. Field transforms not
present in RenderPlan remain un-authored; bounded field operators, seeded drift,
and temporal position tracks provide repeatable approximations. DotGrid adapts
spacing to stay within the renderer's 4,096-dot ceiling, and compositions stay
within a bounded layer budget. Color, timing, density, and effect-specific
controls are checked by `addBackground`; animated looks require at least 24
frames. `BackgroundSpec::gridSquares` selects highlighted GridPattern cells;
`particleQuantity`, `particleColors`, `particleSpeed`, and related particle
options tune deterministic particles.

The native field/mesh contract is emitted by `chronontemplate_background_canary_v1`
(one V3 plan per look) and checked through the renderer CLI; unit contracts are
`chronontemplate_background_pack_test` and `chronontemplate_plan_lowering_test`.

```cpp
TemplateScene scene("doc_grid", 30.f, host, 1920.f, 1080.f);
BackgroundSpec spec;
spec.look = BackgroundLook::DocumentaryGrid;
spec.ground = "#080D16";
spec.accent = "#233247";
spec.seam = "#62C8D6";
spec.gridSpacing = 120.f;
spec.majorEvery = 4;
spec.inFrame = 0;
spec.duration = 150;
const BackgroundComposition plate = addBackground(scene, spec);
FrameSubmission frame = scene.submit(48);
```

Use `BackgroundLook::RadarSweep` for technical scan motion,
`BackgroundLook::ArchiveDust` for the quieter archival plate (`particleCount`
0–256), `BackgroundLook::MeshGradient` for soft color drift, or the distinct
`GridPattern` and `Particles` looks for a configurable coordinate grid and
mouse-free deterministic particles. Contract:
`chronontemplate_background_pack_test`.

## Declarative transitions (BACKLOG item 4)

`include/chronontemplate/transitions/TransitionPack.hpp` exposes eight legacy
looks and eight rapid light-transition presets. The rapid IDs are
`lightleak_flash_sweep` (6–10f), `lightleak_corner_burn` (8–12f),
`lightleak_whiteout` (5–8f), `lightleak_diagonal_cut` (6–9f),
`lightleak_double_pass` (10–14f), `lightleak_film_burn` (8–12f),
`lightleak_center_burst` (5–8f), and `lightleak_horizontal_whip` (4–7f).
`recommendedTransitionDuration()` provides the midpoint default; rapid durations
outside their published range fail closed. `transitionTimingClass()` classifies
the recommendation as MICRO (4–6), NORMAL (7–10), or HERO (11–16). The
suggested weighted selector distribution is available as data only; this pack
does not create or claim an existing random selector.

The transition catalog is published under `transitions` in
`catalog/motion_catalog.v1.json`, and validated by `chronontemplate_emit_catalog`;
the generated `catalog/chronontemplate_catalog.v1.json` embeds the same rows.
The optional offline `chronontemplate_transition_canary_v1 <out-dir>` target
writes one native V3 plan per rapid look; the plans are suitable for
`chronon3d_cli validate --plan`.
The native C++ pack's light looks are deterministic shape plates/tracks; they
are practical shape approximations, not optical light-leak shaders. The separate
RGB RenderPlan authoring tool (`tools/backgrounds/render_rgb_motion_v1.py`)
now publishes ten fast presets from the proposal: `rgb_split_whip` (5–8f),
`rgb_snap` (4–6f), `rgb_zoom_punch` (6–10f), `rgb_horizontal_tear` (6–10f),
`rgb_glitch_cut` (4–8f), `rgb_lens_snap` (6–9f), `rgb_spin_blur` (6–10f),
`prismatic_flash` (6–10f), `lightleak_rgb_combo` (8–12f), and `film_burn_rgb`
(8–12f). These compose existing channel-transform, deterministic slice,
analytic velocity and blur operators without introducing another renderer or
registry. The first seven RGB IDs and frame limits match the proposal; the
three hybrid looks round out the same documented library.

Emit and validate the short plans through the same CLI used for rendering:

```shell
python3 tools/backgrounds/render_rgb_motion_v1.py --transitions --validate
python3 tools/backgrounds/render_rgb_motion_v1.py --transitions --render
```

Plans are written under `out/rgb_motion_v1/transitions/`; metadata and frame
limits are published under `rgb_motion.rapid_transitions` in
`catalog/rgb_motion_v1.json` and embedded by `chronontemplate_emit_catalog`.
These presets are authored recipes, not a video cut-point selector or native
`TransitionPack` enum entries. They use existing operators; native
`WarpedLightLeak`, `ChannelSplit`, `ChannelTrail` frame-history sampling, and
`SliceDisplace` renderer primitives remain explicit gaps rather than being
claimed as implemented.

```cpp
TemplateScene scene("cut", 30.f, host, 1920.f, 1080.f);
TransitionSpec spec;
spec.look = TransitionLook::LightLeakFlashSweep;
spec.inFrame = 30;
spec.duration = recommendedTransitionDuration(spec.look); // 8 frames
const TransitionComposition cut = addTransition(scene, spec);
```

When requested, scene temporal motion blur remains an opt-in declaration.


```cpp
TemplateScene scene("cut", 30.f, host, 1920.f, 1080.f);
TransitionSpec spec;
spec.look = TransitionLook::GlitchSlices;
spec.travel = chrononmotion::motion::presets::Direction::Left;
spec.inFrame = 30;
spec.duration = 20;
spec.enableMotionBlur = true;
const TransitionComposition cut = addTransition(scene, spec);
```

`transitionId` names each look (`transition_wipe`, `transition_push_through`,
`transition_dip_to_black`, `transition_dip_to_color`, `transition_blinds`,
`transition_iris_circle`, `transition_glitch_slices`,
`transition_light_leak`, `transition_barn_doors`, `transition_curtain_lift`,
`transition_diamond_iris`, `transition_four_way_doors`, `lightleak_flash_sweep`, `lightleak_corner_burn`,
`lightleak_whiteout`, `lightleak_diagonal_cut`, `lightleak_double_pass`,
`lightleak_film_burn`, `lightleak_center_burst`, and
`lightleak_horizontal_whip`); `coverFrame` is the authored peak/cover point.
Scale never reaches an exact zero (the plan lowering fails closed on singular
transforms) and the glitch slices are deterministic by index, never by an RNG,
so every cut is a pure function of (scene, frame). Contract:
`chronontemplate_transitions_pack_test`.

## Captions and data-viz (BACKLOG item 5)

`include/chronontemplate/captions_dataviz/CaptionsDataVizPack.hpp` wires the
two halves the backlog item asked for:

- `buildBeatGrid` runs the motion core's certified PCM analyzer
  (`analyzePcmAudio` — no decoder, no file I/O) and reduces its onsets to a
  frame-space grid with a minimum gap between beats; deterministic by
  construction.
- `addCaptionTrack` authors one band + one caption per beat, each layer alive
  exactly on its own beat interval.
- `addDataVizChart` authors a bar chart that grows bottom-up from its anchored
  scale (staggered, all landed by `peakFrame`), per-bar value labels that fade
  in when their bar lands, a pulsing halo on the highlighted bar, a trend rule
  that draws itself left-to-right and a two-pulse `radarPing` on the peak bar.

Everything keys plain transform channels — no effect tracks — so the chart
lowers through the ordinary RenderPlan path. Contract:
`chronontemplate_captions_dataviz_pack_test`.

## Orchestration

This module is where the two engines meet, and it converts in one direction:

```text
Chronon            creates and measures content  ->  ContentHandle + metrics
ChrononTemplate    binds layer -> content, authors the intent
ChrononMotion      owns space and time           ->  CompiledScene
ChrononTemplate    resolves the frame            ->  FrameSubmission
Chronon            draws the content with those matrices
```

A template writes one sentence per intent. Text, image and video are the same
layer: the only difference is the `ContentRef` the content side measured.

```cpp
TemplateScene scene("youtube_subscribe", 30.f, host);

LayerHandle& title = scene.text({.text = "SUBSCRIBE", .font = "Inter-Bold.ttf", .fontSize = 180.f});
title.position(960.f, 540.f)
     .animate(ScalePop{.inFrame = 0, .duration = 15, .from = 0.6f})
     .animate(FadeIn{.inFrame = 0, .duration = 10});

LayerHandle& logo = scene.image({.path = "youtube.png"});
logo.position(750.f, 540.f, 20.f).animate(SpinXYZ{.inFrame = 10, .duration = 25});

scene.camera().orbit(-0.35f, 0.05f).between(0, 90);
scene.camera().setFov(42.f).horizon(4.f);

FrameSubmission frame = scene.submit(12);
```

`ContentHost` is the whole Chronon-side dependency: create text/image/video/shape and
measure them. It is abstract on purpose, so this module keeps compiling without
the renderer and the real host can be the Chronon engine, the C ABI or a test
double. `FrameSubmission` is the whole render-side output: per layer, the matrix
and the content it draws, already resolved.

`CameraHandle::fov(from, to).between(start, end)` animates field of view;
`setFov(degrees)` sets a static field of view and `horizon(rollDegrees)` sets
camera roll around the view axis. The latter two are validated at the template
boundary.

The bridge refuses two defects instead of drawing the wrong thing: a content
layer with no binding row, and a binding whose measurement is no longer the
digest its host currently holds (`ContentRef::metrics.fingerprint`). The second
is the one that fails silently otherwise: a re-measured asset keeps the old
rectangle and the anchor drifts.

## Public API

```cpp
#include "chronontemplate/chronontemplate.hpp"

chronontemplate::Final3DData data;
data.title = "GLOW 3D";
data.subtitle = "FINAL ANIMATION";
data.assetId = "product.asset";

auto composition = chronontemplate::build(
    chronontemplate::Final3DPreset::LogoReveal, data);

composition.scene.evaluate(30);
auto compiled = composition.scene.compile();
```

Final 3D presets:

- `LogoReveal`
- `ProductOrbit`
- `TitleCard3D`
- `CameraPush`
- `LightPulse`
- `MacBookProduct` — a product card on a title, then a quarter turn under an orbit
- `Typewriter3DGlow` — one complete text content request with typewriter intent; Chronon3D owns cluster/glyph reveal and fixed layout
- `CleanRed` — the headline slides in flat while the key light keys from dim to red
- `YouTubeCanary` — the production `CHRONON` composition intent: red glow, typewriter style, XYZ motion and camera orbit on one content id
- `TextStatic` — isolated white `CHRONON` text, no glow and no animation, used as the first text-path gate
- `TextDollyOrbitGlow` — a restrained 2.5D title/subtitle card with depth-separated text, camera dolly, light orbit and the shared Gaussian Glow

Web-style presets are exposed through the existing template catalog:

- `YouTubeSubscribe`
- `InstagramLike`
- `FollowPrompt`
- `LowerThird`
- `QuoteCard`
- `BreakingNews`
- `EpisodeTag`

### Image animation starter pack

`ImageAnimationPack` keeps the five original image motions (`Fade`, `Rise`,
`ScalePop`, `Slide`, and `Spin`) and adds the `image_25d_clean_v1` set as C++
choices on the same `ImageAnimation` enum:

- `DepthFloatIn`, `YawFlipIn`, `PitchLift`, `PopZBounce`, `Swipe3D`, `CardSwing`
- `DollySettle`, `OrbitArc`, `CounterTilt`, `DollyBreath`, `ParallaxDrift`, `HeroPullExit`

Each recipe authors its image transform and opacity on ChrononMotion3D tracks.
The six camera-driven recipes use the existing ChrononMotion3D camera rig and
camera presets; the other six keep the camera static. All 12 can be selected
through the regular scene submission and render path:

```cpp
TemplateScene scene("image_25d_orbit", 30.f, host, 1920.f, 1080.f);
LayerHandle& product = addImageAnimation(
    scene, ImageAnimation::OrbitArc, "assets/test/square_bottle_test.png", "Product",
    ImageFrameStyle{.cornerRadius = 64.f, .borderWidth = 0.f},
    ImageCameraMove::None);
product.position(960.f, 540.f);
FrameSubmission frame = scene.submit(48);
```

The 2.5D recipes control their own camera where needed; the `cameraMove` argument
is retained for compatibility and only applies to the original five motions.
They stay visibly in motion through most of a 150-frame,
30 fps sample, then fade out at frame 132. The starter style uses a 64 px
corner radius and disables the outline stroke. `ImageFrameStyle` lets a caller
change the radius or opt into a border. `ImageCameraMove` offers a stationary
camera, a dolly, an orbit, or a combined dolly and orbit. The default is the
combined move; it goes through `CameraHandle` and the existing ChrononMotion3D
camera presets, so this pack adds no camera math of its own.

`ImageFrameStyle` also exposes composable editorial effects: `lightLeak` adds
warm light rays and glow, `channelSplit` adds radial RGB separation,
`channelTrail` adds temporal echoes, and `sliceDisplace` adds alternating
mesh-warp bands. These are CPU/render-plan approximations and remain bounded by
the native effect contracts; they are not optical light-leak simulation.

```cpp
#include "chronontemplate/chronontemplate.hpp"

TemplateScene scene("image_rise", 30.f, host, 1920.f, 1080.f);
LayerHandle& product = addImageAnimation(
    scene, ImageAnimation::Rise, "assets/test/square_bottle_test.png", "Product",
    ImageFrameStyle{.cornerRadius = 64.f, .borderWidth = 0.f},
    ImageCameraMove::DollyOrbit);
product.position(0.f, 0.f);
FrameSubmission frame = scene.submit(12);
```

The original generated image is preserved as
`assets/test/square_bottle_source_original.png`; the clean source and its
rounded-alpha test version are `square_bottle_clean_source.png` and
`square_bottle_test.png` in that directory. The test asset avoids the render
plan renderer's dark edge halo; Chronon's content host still applies the
configurable rounded-corner mask from `ImageFrameStyle`. A C++ test submits all five scenes
through the content binding, checks the rounded-corner request and disabled
stroke, and confirms camera projection changes through the ongoing motion.

### Pack vs preset

The two catalogs answer different questions, and keeping them apart is what
stops an overlay from existing in two places:

- a **pack** (`chrononmotion::templates::TemplateId`) is a *recipe*: it authors
  its own scene graph, layer ids and timing in its own builder;
- a **preset** (`Final3DPreset`) is a *parameter set over a recipe*: every one
  goes through `baseComposition` — shared root, title layer, key and fill
  lights, camera rig, lifetime — and then appends motion with the `presets::`
  primitives. A preset never re-authors the base scene.

Both are published by `chronontemplate_emit_catalog` under separate sections
(`templates` and `final3d_presets`), and the emitter fails if an id is listed
twice or appears in both: an id in both lists is the same overlay described
twice, with two timings free to drift apart. If an overlay should also be
reachable as a preset, the preset must be parameters over the pack's recipe —
never a second recipe.

The three style presets are ordinary `Final3DPreset`s: they build through the
same `baseComposition` as the rest, so the key/fill lights, the camera rig, the
lifetime and the validation are shared rather than re-authored. `CleanRed` keys
the key light's intensity track. `Typewriter3DGlow` keeps the phrase as one
content request; Chronon3D may animate its stable clusters internally, but
Template never computes per-glyph positions or creates character layers.

Glow is declared here and rendered by Chronon3D. `Composition::material` is the
module's only statement about how a composition should be lit — an emissive
descriptor means "this lights its own colour", and its `emissiveStrength` says how
much. `Typewriter3DGlow` declares an emissive material because its halo is the point.
A consumer that ignores the descriptor still gets a correct, if flat,
composition; the preview consumer does not interpret it at all, because it draws
motion rather than pixels and a local halo there would be a second glow
authority.

The text face and native phrase glow are declared with the style and consumed
by Chronon3D. Glow has one implementation and no preview/final quality selector
or stacked-lobe settings; a native phrase carries only its radius, intensity
and tint. `Composition::textStyles` maps every text layer to a `TextStyleDeclaration`:
an asset-relative font path (the defaults are the canonical Inter assets,
`assets/fonts/Inter-Bold.ttf` / `Inter-Regular.ttf`, resolved by the content
side through its own resolver — never the process CWD) plus the authored px
size. The gate covers every text layer, including one whose opacity is animated
up from zero, so a recipe cannot add text that draws with the consumer's default
face. `Final3DData` exposes `titleFont` / `subtitleFont` so callers can re-face a
preset without editing it, and `Typewriter3DGlow` declares its title's face,
sized against the same 900-unit reference box the recipe lays the run out in.

Chronon3D therefore renders the real text: the host receives the complete
content request, resolves the face, shapes the run, owns stable clusters and
renders the glow. Template only carries style intent and Motion3D metrics;
there is no default-font or flat-text fallback in the production contract.

## Build

Linux only, CMake 3.20+ and a C++20 compiler, exactly like the motion core:

```shell
cmake --preset dev-fast
cmake --build --preset dev-fast
ctest --preset dev-fast
```

By default the build compiles the ChrononMotion core it finds in
`../ChrononMotion3D` (`CHRONONTEMPLATE_CHRONONMOTION_DIR`). When the core is
already built somewhere, point the module at that archive instead and it will
not recompile it — useful when the machine is busy:

```shell
cmake -S . -B build/verify -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DCHRONONTEMPLATE_CHRONONMOTION_PREBUILT_LIBRARY="$PWD/../ChrononMotion3D/build/dev/libchrononmotion.a" \
  -DCHRONONTEMPLATE_CHRONONMOTION_INCLUDE_DIR="$PWD/../ChrononMotion3D/include"
cmake --build build/verify -j 2
ctest --test-dir build/verify
```

The archive and the headers must come from the same core revision: a stale
`libchrononmotion.a` fails at link time, not at configure time.

### Canonical catalog

This module owns the phrase/motion/preset vocabulary, so it also ships the tool
that publishes it as data instead of letting every consumer restate it:

```shell
cmake --build build/verify --target chronontemplate_emit_catalog
./build/verify/chronontemplate_emit_catalog > catalog/chronontemplate_catalog.v1.json
```

`catalog/motion_catalog.v1.json` is the authored data (motion ids, their
tracks/selectors, the phrase and image selections and the overlay preset
families); the tool validates it and merges the lists that are genuinely
expressed in C++ — the template catalog (`TemplateId`) and the composition
presets (`Final3DPreset`, named by `chronontemplate::name`, so a new enumerator
cannot reach the artifact without a stable id). Preset rows publish material
facts (`material.kind` and `material.emissive_strength`) but do not carry a
parallel Glow-quality policy. The native phrase style carries its single
`radius`/`intensity`/`color` Glow block. Consumers embed the emitted document:
RenderingGen reads it through
`renderinggen/internal/motion/catalog/chronontemplate_catalog.v1.json` and
refreshes it with `RenderingGen/scripts/sync_motion_catalog.sh`.

### Entity presentation V1 — the registry flow

`catalog/entity_presentation.v1.json` is the single motion source of truth for
the three certified editorial families — `metric_v1` and `date_v1` with 20
distinct presets each, and `entity_card_v1` with 10. Nothing else republishes those lists: the
legacy `catalog/entity_motion_families.v1.json` is marked legacy and feeds only
the exploratory people/location render scripts.

```text
ChrononTemplate/catalog/entity_presentation.v1.json   authored 20/20/10 vocabulary
ChrononTemplate/tools/emit_catalog.cpp                validation + merge
                 │  chronontemplate_emit_catalog
                 ▼
catalog/chronontemplate_catalog.v1.json   (entity_presentation + 50 motions)
                 │  RenderingGen/scripts/sync_motion_catalog.sh
                 ▼
RenderingGen/renderinggen/internal/motion/catalog/   embedded, fail-closed
                 │  internal/motion Registry.Resolve(preset_id)
                 ▼
Chronon3D  chronon.render-plan.v2/v3
```

Every preset carries its certification metadata in the emitted motions:
`id`, `family` (category), `supported_template`, `duration_bounds`,
`required_properties` (one per track, in track order), `requires_3d`,
`requires_camera`, `seeded` and `render_safe`. The gates that keep it honest:

- `ChrononTemplate/tools/entities_with_text/test_entity_presentation_v1.py` — catalog contract,
  deterministic golden plans, layout/Unicode/safe-area, multi-entity duo
- `RenderingGen .../internal/motion/presentation_catalog_test.go` — catalog
  parity, 20/20/10 presets, unknown-preset fail-closed, exact final pose
- `RenderingGen .../internal/motion/presentation_pose_certification_test.go`
  — start/mid/end poses for all 50 presets, the `entity_yaw_caption`
  scenario, counter no-overshoot, sampling determinism
- `RenderingGen .../internal/motion/presentation_multi_entity_test.go` — one
  scene for two entities, captions remain visible, focus A→B, no overlap

`tools/entities_with_text/build_entity_presentation_v1.py` regenerates seven golden plans (metric
five-value canary, metric 4×5 gallery, metric 20-preset timeline, date 4×5 gallery,
date 20-preset gallery, entity gallery and entity duo) into
`golden_plans/entity_presentation_v1/`; `--cli` additionally validates each
plan through `chronon3d_cli validate --plan` when the Chronon3D CLI is built.

The certified individual metric/date preview videos can be published from
ChrononTemplate with the same verified `RenderingGen/bin/drive-upload` CLI used
by the other packs. The upload is opt-in, requires a Drive parent folder ID,
probes the complete 40-file H.264 set before touching Drive, uploads MP4s only
directly into the requested Drive folder, and records provider confirmations,
SHA-256 hashes and byte sizes in the preview directory's upload manifest:

```shell
python3 tools/entities_with_text/build_entity_presentation_v1.py \\
  --upload-only \\
  --preview-dir out/entity_presentation_v1_gpu_certified \\
  --drive-folder <drive-folder-id> \\
  --drive-credentials ~/.config/velox/credentials.json \\
  --drive-token ~/.config/velox/token.json
```

Use `--upload` instead of `--upload-only` to regenerate the seven plans first.
This Drive folder is a human-review/preview delivery, not a runtime dependency:
RenderingGen consumes motion IDs and tracks from the embedded catalog, refreshed
with `RenderingGen/scripts/sync_motion_catalog.sh`; it does not fetch preview
MP4s from Drive to animate metric/date text.

## SaaS Kinetic Typography V1

`tools/important_phrases/build_saas_kinetic_typography_v1.py` authors six renderer-native
reference-inspired beats: per-grapheme vertical drop with velocity blur, staggered
word reveal with tracking stretch, a split-mask decapitation, spring-drawn
underline, glossy gradient/shimmer, and a rotation snap. It writes six 3-second
canaries plus a 18-second `saas_kinetic_typography_gallery_v1` plan. The text
remains a single renderer-owned run per phrase; there is no manually positioned
glyph mesh or custom shader. Linear/gloss gradients use native shape fills
clipped by a text mask, while motion and per-glyph treatment use V3 layer tracks
and text animators.

```shell
python3 tools/important_phrases/test_saas_kinetic_typography_v1.py
python3 tools/important_phrases/build_saas_kinetic_typography_v1.py \\
  --out out/saas_kinetic_typography_v1
python3 tools/important_phrases/build_saas_kinetic_typography_v1.py --validate-only \\
  --cli ../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli
```

Each canary is 1920×1080 at 30 fps. Native plan validation and deterministic
contract tests are included in the module's Python CTest suite.

## Kinetic Type Editorial V1

`tools/important_phrases/build_kinetic_type_editorial_v1.py` authors the reference-inspired
editorial type family from reusable Chronon3D render-plan primitives. It emits a
single manifest plus 10 text-motion canaries, eight seeded aurora look canaries,
five compositional scene-recipe canaries and the 13-scene
`editorial_typography_gallery_v1`. The authored tokens define a near-black
canvas, magenta/purple/red/coral aurora colors, bright text and three editorial
accents. Presets cover a hero scale burst and zoom exit, phrase rise, accented
word swap, semantic keyword emphasis, luminous underline, same-line slide
replacement, hero-to-statement handoff, staggered segments, trailing-word
reveal and scale/blur phrase transitions.

The producer lowers them to ordinary `chronon.render-plan.v3` documents:
ChrononTemplate owns composition and recipe vocabulary; Chronon3D still owns
semantic-span layout, text shaping and rasterization. The aurora fields use
six broad, irregular soft-alpha emitters as moving native image layers.
`tools/important_phrases/generate_kinetic_type_editorial_textures.py` recreates the deterministic
palette and accent-light textures. Native per-glyph animators combine scale,
blur, tracking and fill color; semantic accent spans drive a synchronized
colored light layer. The `Design` gallery beat uses three animated color spans
to approximate a red-to-magenta gradient while staying on the Vulkan text
path. Underlines use a Vulkan-native rounded stroke with an overshoot draw and
soft afterglow. Hero words may crop intentionally, while sentence lines retain
the native shrink-only fit contract.

Generate plans and run the deterministic/safe-area contract tests:

```shell
python3 tools/important_phrases/generate_kinetic_type_editorial_textures.py
python3 tools/important_phrases/build_kinetic_type_editorial_v1.py --out build/kinetic_type_editorial_v1
python3 tools/important_phrases/test_kinetic_type_editorial_v1.py
```

Validate all generated plans with the local Chronon3D CLI, or render a single
scene with Vulkan to raw NV12 frames, then encode the final MP4 with NVIDIA
NVENC (preview profile and a 512 MiB framebuffer-pool retention budget):

```shell
python3 tools/important_phrases/build_kinetic_type_editorial_v1.py \
  --out build/kinetic_type_editorial_v1 --validate-only \
  --cli ../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli
python3 tools/important_phrases/build_kinetic_type_editorial_v1.py \
  --out build/kinetic_type_editorial_v1 --render --scene canary_text_word_pop_focus \
  --cli ../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli
```

Use `--render-all` for the complete 24-plan canary set. Vulkan exports start in
sequential bounded-frame renderer processes; a failed range is bisected until
it passes. Raw frame ranges are joined and encoded once with NVENC at constant
30 fps. Use `--render-from <plan>`
to resume a stopped batch after the last verified plan. The
pack's contract verifies stable ids, finite bounded
parameters, keyframe/lifetime integrity, UTF-8 semantic spans, safe-area bounds,
scene handoff overlap, palette/type/background coverage and renderer-native
plan schemas. A renderer validation or canary establishes contract support,
not pixel equivalence to an unprovided reference-video frame.

## Boundary

This module owns recipes. The motion core owns space/time evaluation, and
Chronon3d owns rasterization, content bytes and font layout. A file belongs here
when it is a composition recipe over `MotionScene`; a file belongs in the core
when it is the primitive the recipe is written with.

Two rules keep the move out of Chronon3d possible without breaking its SDK:

- installed header paths and public signatures stay frozen — a recipe may move
  behind a registry, but `chronon3d::presets::MotionParameters` (referenced by
  `LayerBuilder::motion()`) cannot move out of the engine's public surface;
- the dependency points one way: this module consumes the core and the engine,
  the engine does not link this module;
- the module owns no font, no glyph, no raster and no matrix maths: text shaping
  and content bytes are `ContentHost`'s answer, the matrix is the motion core's.

## Canonical ownership

```text
RenderingGen owns editorial intent.
ChrononTemplate owns composition.
ChrononMotion owns space and time.
Chronon3D owns content and pixels.
```

`scene.text()` is an orchestration facade only: it delegates to
`ContentHost::createText()`. It is not a font, shaping, glyph or raster API.
The `ContentHandle` returned by Chronon carries an opaque identity, measured
metrics and a fingerprint. Motion3D never interprets the text or recomputes its
layout. Stable element/cluster animation is a Chronon3D capability; the current
ADR-032 layer record carries the complete content identity, while a future
additive element-state record must be implemented by Chronon3D before Template
can expose per-cluster motion.

## Chronon ABI handoff

`FrameSubmission` now exposes the final `projection × view × world` matrix for
each layer, and `ChrononMotionContract.hpp` converts it to the existing
`chronon_layer_state` records. A connected `ContentHost` supplies the numeric
opaque content id minted by Chronon; missing ids fail closed instead of being
hashed. The Chronon side consumes the records through the existing
`chronon_render_frame_with_layers` entry point in
`Chronon3d/include/chronon/abi.h`.

The module intentionally does not own an engine or plan handle. The host that
owns `chronon_engine`/`chronon_plan` can use the thin `ChrononRenderAdapter`, which
borrows both handles, packs the states and calls `chronon_render_frame_with_layers`.
The returned `chronon_frame_buffer` remains owned by Chronon3D and is released
through the adapter; no second renderer or upload path is introduced.

The preview consumer has an explicit `--clean` mode for motion-only inspection.
It omits HUD, labels, pivots, bounds, strokes and progress indicators. Its strict
ownership gate also prevents local font/glyph/raster/glow APIs. It does not render
text pixels; a production canary must be submitted to Chronon3D with a live
ContentHost and the ADR-032 layer states.

The runtime library remains the only owner of space/time evaluation. Chronon
still owns content bytes, text layout and rasterization; ChrononTemplate only
orchestrates the handoff and declares intent. No browser, renderer,
font system or Windows toolchain is required.

## Important-phrase style families (Classic)

RenderingGen names the editorial kind (IMPORTANT_PHRASE);
`include/chronontemplate/important_phrases/ImportantPhrasePack.hpp` owns how such a phrase looks
and moves. `Classic` is the first family: white Montserrat Bold face with a
soft white glow and a slight black stroke on the black canvas, fourteen
animations — seven layer entrances, three staggered glyph windows, two
whole-run focuses and two full-run word emphases. The second family,
`Typewriter`, types the phrase glyph by glyph while the `_` underscore cursor
trails, blinks, leads or holds: fifteen animations with `typewriter_*` ids.
One file per family (`ClassicPhrasePack.*`, `TypewriterPhrasePack.*`) on the
shared look and motion vocabulary of `ImportantPhrasePack.*`, so a pipeline
can render one family while the other stays ready.

The pack is data; `tools/important_phrases/emit_important_phrase_classic.cpp` lowers it to
`chronon.render-plan.v2` and `tools/important_phrases/render_important_phrase_classic.sh` renders
the showcase MP4s on the Vulkan lane (GPU-native text, `require_gpu_native`).
The GPU lane samples animator properties per run — per-glyph effect is always
`property(t) * weight(glyph, t)` — so unit-level staging lives in the selector
window: `reveal` holds the property at its hidden value and sweeps the window
edge as the reveal frontier (typewriter, assembly), `band` sweeps a narrow
window that pulses the held value through the run (lift, wave), and `full`
selects the whole run at once. Every definition stays inside Chronon3D's
canonical GPU text contract (glyph windows and single-word run emphasis), which
is what keeps the whole pack on the GPU instead of the software text fallback.

### Title-camera documentary family — `camera_title_documentary_v1`

Twenty editorial title moves as recipes over six camera primitives (dolly, pan,
orbit, tilt, roll, FOV plus target lock and focus distance). The family exists
for one grammar: **the title never animates**. The layer keeps an empty
transform — no position, scale, rotation or opacity keys — and the camera is
the only thing that tells the story. That separation is a tested contract, not
a convention.

Every preset receives a `TitleShotAnchor` (the title's optical centre and a
conservative bound) plus `TitleFraming` (Hero / Medium / Wide / ExtremeClose)
and `TitleCameraIntensity` (Subtle / Editorial / Cinematic), so the same move
frames "ROME", "2008", "$4.5 BILLION" or "THE STORY OF APPLE" without any of
them carrying coordinates. Framings share one optical law
(`titleCameraDistance`): a 900-unit reference subject fills the framing's
coverage fraction of the frame width at the delivery aspect.

```cpp
#include "chronontemplate/camera_roll/TitleCameraPack.hpp"

TemplateScene scene("title_card", 30.f, host, 1920.f, 1080.f);
LayerHandle& title = scene.text({.text = "THE STORY OF APPLE",
                                 .font = "Inter-Bold.ttf", .fontSize = 180.f});
title.position(960.f, 540.f);

applyTitleCameraShot(scene, TitleCameraMove::LowAnglePush,
                     TitleCameraShot{.anchor = {.center = chrononmotion::Vector3(960.f, 540.f, 0.f)},
                                     .framing = TitleFraming::Medium,
                                     .intensity = TitleCameraIntensity::Cinematic,
                                     .inFrame = 0, .duration = 135});
```

The twenty ids, in canonical order (`titleCameraMoveIds()`, stable and
append-only): `title_camera_slow_push`, `title_camera_slow_pull_out`,
`title_camera_left_drift`, `title_camera_right_drift`,
`title_camera_vertical_rise`, `title_camera_vertical_descend`,
`title_camera_micro_orbit_left`, `title_camera_micro_orbit_right`,
`title_camera_arc_push`, `title_camera_arc_pull`, `title_camera_low_angle_push`,
`title_camera_high_angle_settle`, `title_camera_roll_settle`,
`title_camera_roll_pass`, `title_camera_dolly_zoom_subtle`,
`title_camera_focus_push`, `title_camera_parallax_side`,
`title_camera_parallax_push`, `title_camera_whip_settle`,
`title_camera_corner_reveal`.

They are recipes, not implementations: `arc_push` is dolly + pan + target lock,
`dolly_zoom_subtle` is dolly + FOV compensation (the exact tan ratio, so the
projected title width stays constant while the background perspective changes),
`focus_push` is dolly + focus/aperture keys. The pure numeric plan each preset
lowers onto the rig is exposed by `titleCameraPlanFor` for catalogs and tests.

Every application ends with a settle beat (the last 6–12 frames decelerate into
the hold) and verifies the framing law — the projected anchor stays inside the
5%/8% safe area for the whole window — throwing instead of authoring an
unreadable title. The `whip_settle` acquisition is the declared loud exception:
fast but continuous.

The acceptance suite (`tests/title_camera_pack.cpp`, one scene per preset on a
fixed anchor — the `title_camera_documentary_gallery_v1` grammar, where only
the camera differs between shots) pins eight gates across all twenty presets:

1. **P0** — the title never animates: empty layer tracks, and
   `titleTransform(frame0) == titleTransform(frameEnd)`;
2. the camera really animates — no preset samples to a single pose;
3. the framing holds — the projected anchor stays in the safe area;
4. hero occupancy — a push grows the projected title width;
5. target lock — the projected centre tracks the frame centre during
   orbit/pan/whip;
6. quaternion continuity — `dot(q[n], q[n+1]) >= 0` between neighbors;
7. velocity continuity — no channel teleports between frames (whip exempted
   on loudness, not on continuity);
8. end settle — `velocity(end) < velocity(mid)`.

A torture-test composition (six consecutive title beats, each a static title
moved only by its camera) is authored by chaining `applyTitleCameraShot` over
adjacent frame windows on the same scene. A canary gallery
(`title_camera_documentary_gallery_v1`: 1920×1080, 30 fps, one title, one
background, twenty clips — one per camera) renders through the regular scene
submission path; the C++ contract above is the gate, the render is the exhibit.

### Documentary title-to-snapshot family — `documentary_title_snapshot_v1`

`DocumentarySnapshotPack` authors the title and photos as ordinary scene layers,
then resolves the selected story recipe onto the shared `CameraRig`. The twelve
recipes are `doc_title_snap_down`, `doc_title_pullback_photo_reveal`,
`doc_title_push_through_snapshot`, `doc_title_whip_to_photo`,
`doc_title_focus_drop`, `doc_title_90_reveal`, `doc_title_corner_turn`,
`doc_title_foreground_photo_pass`, `doc_title_photo_stack`,
`doc_title_filmstrip_handoff`, `doc_title_split_depth`, and
`doc_archive_crane_reveal`.

```cpp
#include "chronontemplate/entities_with_text/DocumentarySnapshotPack.hpp"

DocumentaryShot shot;
shot.title = {{960.f, 280.f, 0.f}, 520.f, 100.f};
shot.snapshots = {{.path = "archive/rome.jpg",
                   .anchor = {{960.f, 960.f, -60.f}, 620.f, 350.f},
                   .caption = "ROME, 1960",
                   .fit = SnapshotFit::Fill}};
shot.recipe = DocumentaryRecipe::SnapDown;
shot.style = SnapshotStyle::Archive;
shot.titleHoldFrames = 48;
shot.transitionFrames = 8;

addDocumentarySnapshot(scene,
    TextSpec{.text = "THE STORY OF ROME", .font = "Playfair Display Italic",
             .fontSize = 138.f, .color = "#F1EBDD"}, shot);
```

The seven catalogued looks are Clean, Archive, Polaroid, Filmstrip, Evidence,
Newspaper, and Black-and-white Documentary. `SnapshotFit::Fit`, `Fill`, and
`Crop` map to the existing image placement request; Crop carries an explicit
normalized rectangle. Frame, color grade, grain, vignette, and stable grain seed
travel through `ImageRequest`, so the connected `ContentHost` can route them to
Chronon3D's existing image and effect path. `doc_title_push_through_snapshot`
also adds a native `ShapeRequest` red portal as an ordinary animated scene
layer: it covers the photo at the push peak, then fades to reveal it. The host
maps `ShapeRequest` to a Chronon3D Shape LayerPlan. The C++ contracts verify the
requested values and camera geometry; rendered fit/style verification remains
part of the open canary checklist.

Render the title handoff or red portal with the native camera pose dumper and
Chronon3D CLI:

```sh
python3 tools/entities_with_text/render_documentary_snapshot_canary.py --render
python3 tools/entities_with_text/render_documentary_snapshot_canary.py \
  --recipe doc_title_push_through_snapshot --render
python3 tools/entities_with_text/render_documentary_snapshot_canary.py --style-gallery --render
```

### Scene-camera sequencer — `scene_camera_sequencer_v1`

Where the title-camera pack frames one title, the scene-camera pack frames the
whole edit: a chain of subjects — a phrase, an image, a text, a stat card —
each holding its own framing (the *stacco*), with the camera itself carrying
the audience from hold to hold. One call authors the chain; the subjects never
animate (the P0 contract), and every travel leg starts exactly on hold A's
rest and lands exactly on hold B's rest, so any length of sequence is
continuous at every boundary by construction. The rest framing of each beat is
derived from the beat's own half-extents through one framing law
(`sceneFramingDistance`) and the kind's lens (`sceneSubjectFov`: Phrase 50°,
Image 62°, Text 44°, Card 56°).

```cpp
#include "chronontemplate/camera_roll/SceneCameraPack.hpp"

applySceneCameraSequence(scene, SceneCameraSequence{
    .beats = {{{SubjectKind::Phrase, {960.f, 540.f, 0.f}, 520.f, 110.f}, 60},
              {{SubjectKind::Image,  {960.f, 540.f, -80.f}, 460.f, 260.f}, 60},
              {{SubjectKind::Text,   {960.f, 540.f, 0.f}, 620.f, 150.f}, 60}},
    .transition = SceneCameraTransition::ArcCarry,
    .intensity = 1.f,          // 0.55 subtle · 1 editorial · 1.9 cinematic
    .travelFrames = 24,
    .inFrame = 0});
```

The eight transition ids, in canonical order (`sceneCameraTransitionIds()`,
stable and append-only): `scene_camera_push_through`,
`scene_camera_lateral_swipe`, `scene_camera_arc_carry`,
`scene_camera_orbit_handoff`, `scene_camera_rise_and_land`,
`scene_camera_focus_rack`, `scene_camera_pull_back_reveal`,
`scene_camera_whip_reframe`.

The acceptance suite (`tests/scene_camera_pack.cpp`) pins eight gates across
all eight transitions on the fixed frase → immagine → testo canary: the
subjects never animate (empty tracks and a bit-identical transform at frame 0
and frame end); the camera really carries the frame; every leg departs and
lands exactly on the two rests it joins; every hold holds its rest for its
whole window; the end settles (landing slower than mid-travel); velocity
continuity with no channel teleports (the whip's loud acquisition is the
declared exception on loudness, not on continuity); the safe-area gate; and
loud authoring failures on empty, one-beat, short-travel, tiny-hold and
negative-intensity sequences.

Render the nine-clip gallery and the 14-second five-stacco master with the
native pose dumper and Chronon3D CLI:

```sh
cmake --build --preset dev --target chronontemplate_dump_scene_camera_poses
python3 tools/camera_roll/render_scene_camera_sequencer_v1.py            # plans + renders
python3 tools/camera_roll/render_scene_camera_sequencer_v1.py --generate-only
```

The renders land in `out/scene_camera_sequencer_v1/` (plans, MP4s and
per-frame timing sidecars); the Drive publication path is
`RenderingGen/UploadDrive/upload_scene_camera_sequencer_v1.sh`.

Pre-configured maps are data, not code:
`catalog/scene_camera_sequences_v1/*.json` names the beats and the transition
(one `chronontemplate.scene-camera-sequence.v1` document each), the
`chronontemplate_sequence_from_json` tool authors them fail-closed, and
`render_scene_camera_sequencer_v1.py --sequence-json <map.json>` renders one
end to end — camera keys from the rig, layers from each beat's `content`
block, which the lens never reads. See `docs/SCENE_CAMERA_PACK.md`.

### Multi-image duo v1

`catalog/multi_entity_layout.v1.json` and
`tools/multiple_images/render_multi_entity_layout_v1.py` define the two-image, one-scene pack.
It keeps both 620×720 cards in fixed left/right slots on a 1920×1080 canvas for
150 frames (5 seconds at 30 fps), and provides five motions:
`duo_split_reveal`, `duo_depth_stagger`, `duo_cross_focus`,
`duo_parallax_balance`, and `duo_compare_hold`. The authoring contract enforces
both cards in the same scene, a visible reveal by 45%, persistent opacity, a
maximum 1.05× focus scale, safe-area bounds, and a reciprocal left/right focus
exchange; the image cards have a six-pixel minimum center gap at peak scale.

The generator is repository-relative and local-only by default. It validates
and renders all five presets plus people, brand, and generic-image canaries;
Google Drive upload requires an explicit `--upload` opt-in and uses
RenderingGen's `drive-upload` CLI with the configured OAuth files. Use
`--upload-only` to revalidate the complete eight-video suite and publish its MP4s
without rerendering; only those eight MP4s are sent, not posters, plans, or the
verification manifest. With the repository Chronon CLI available, run:

```shell
python3 tools/multiple_images/render_multi_entity_layout_v1.py \
  --cli ../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli \
  --assets-root ../Chronon3d --validate-only
python3 tools/multiple_images/render_multi_entity_layout_v1.py \
  --cli ../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli \
  --assets-root ../Chronon3d
python3 tools/multiple_images/verify_multi_image_duo_v1.py out/multi_image_duo_v1 --canaries
# After the suite has been rendered and verified, upload the exact eight MP4s:
python3 tools/multiple_images/render_multi_entity_layout_v1.py \\
  --cli ../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli \\
  --assets-root ../Chronon3d --upload-only \\
  --drive-credentials /home/pierone/.config/velox/credentials.json \\
  --drive-token /home/pierone/.config/velox/token.json
```

The default upload destination is the configured multi-image-duo Google Drive
folder; override `--drive-folder`, `--drive-uploader`, `--drive-credentials`, or
`--drive-token` when needed. RenderingGen verifies each file's SHA-256 and byte
count and reports a `DRIVE_UPLOAD_PASS` line on success. The verifier checks
1920×1080, 30 fps, 150 frames, five-second duration,
left/right visibility in an encoded frame, and safe-area clipping; it writes
`out/multi_image_duo_v1/multi_image_duo_v1_manifest.json` with coverage and
SHA-256 evidence. Fast contract checks run as part of CTest when Python 3 is
available, and can also be run directly with
`python3 tools/multiple_images/test_multi_image_duo_v1.py`.

### Responsive Social Motion V1

`tools/important_phrases/build_social_motion_pack_v1.py` creates eighteen five-second, 30 fps
Chronon3D plans: five image-count layouts (one through five images) for each
1920×1080 landscape, 1080×1080 square and 1080×1920 vertical canvas, plus a
three-phrase English web/editorial reel in each format. Image cards animate
with staggered reveals, measured focus pulses and format-specific safe-area
slots; phrase cards use Inter Bold, shrink-only fitting and animated rise/fade
handoffs. Assets are the existing local Chronon3D image library and font.

Validate the complete plan set without rendering, or render and verify all MP4s
locally:

```shell
python3 tools/important_phrases/test_social_motion_pack_v1.py
python3 tools/important_phrases/build_social_motion_pack_v1.py --validate-only
python3 tools/important_phrases/build_social_motion_pack_v1.py --render
```

The render directory is `out/social_motion_pack_v1/`. When the host's standard
RenderingGen OAuth files are available, publish only the eighteen verified MP4s
to the requested Drive folder with explicit opt-in:

```shell
python3 tools/important_phrases/build_social_motion_pack_v1.py --upload \\
  --drive-credentials ~/.config/velox/credentials.json \\
  --drive-token ~/.config/velox/token.json \\
  --drive-folder 1ATL0bnJXijNqFlKkgWye3PEAdAuQa1HI
```

Upload validates every MP4's encoded dimensions, 30 fps and five-second
runtime and records provider-confirmed byte counts and SHA-256 hashes in
`out/social_motion_pack_v1/social_motion_pack_v1_upload_manifest.json`. It
does not upload plans, timing sidecars or source assets. The rounded-alpha PNG
cards retain their baked corner coverage (`radius: 0`) and remain flat
(`enable_3d: false`) so the renderer does not apply a second mask or 3D depth
grading at their edges.

### Text Depth Focus V1

`tools/important_phrases/build_text_depth_focus_v1.py` generates eight five-second 1920×1080,
30 fps word-focus plans from stable semantic word spans: static editorial
focus, continuous focus travel, near/far traversal, center-out and edges-in
travel, duo rack focus, and a true-Z depth cascade. The first seven use the
renderer-native per-word blur, opacity and scale animator; `text_focus_depth_cascade`
also places each word on a separate 3D plane and enables the existing camera
DOF path. RenderPlan currently exposes camera pose tracks but no animated
focus-distance track, so traveling focus is baked as deterministic linear
word-blur samples while true camera DOF is used on the static focus plane.

```shell
python3 tools/important_phrases/test_text_depth_focus_v1.py
python3 tools/important_phrases/build_text_depth_focus_v1.py --validate-only \\
  --cli ../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli
python3 tools/important_phrases/build_text_depth_focus_v1.py --render-all \\
  --mirror-output-dir ../RenderingGen/UploadDrive/text_depth_focus_v1
```

Plans, MP4s, frame timing sidecars and `manifest.json` are written under
`out/text_depth_focus_v1/`; only the plans/MP4s/timing files are mirrored into
the delivery staging directory.
