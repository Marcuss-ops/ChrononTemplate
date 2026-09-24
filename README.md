# ChrononTemplate

Separate C++ composition presets for ChrononMotion. This module does not belong
inside the ChrononMotion core: it consumes the core's `MotionScene`, `Layer`,
`ContentRef`, camera, lighting, material and preset APIs.

## Contents

```text
CMakeLists.txt                            the module build (library + tests)
CMakePresets.json                         dev / dev-fast / release / release-fast
include/chronontemplate/chronontemplate.hpp     Presets + the orchestration API
include/chronontemplate/Presets.hpp
src/chronontemplate/Presets.cpp
include/chronontemplate/ContentHost.hpp         what this module asks Chronon for
include/chronontemplate/ContentBinding.hpp      layer -> content
include/chronontemplate/FrameSubmission.hpp     what the renderer is handed
include/chronontemplate/MotionBridge.hpp        the conversion, one direction
include/chronontemplate/TemplateScene.hpp       the authoring API a template sees
include/chronontemplate/UiPrimitives.hpp        validated web composition primitives
src/chronontemplate/{ContentBinding,MotionBridge,TemplateScene}.cpp
include/chronontemplate/templates/YouTubeSubscribe.hpp   the first pack
src/chronontemplate/templates/YouTubeSubscribe.cpp
include/chrononmotion/templates/Templates.hpp   moved out of the motion core
src/chrononmotion/templates/Templates.cpp
tests/motion_check.hpp                    the module's own test harness
tests/fake_content_host.hpp               the shared Chronon-side double
tests/motion_templates.cpp
tests/presets.cpp
tests/template_scene.cpp                  the orchestration contract
tests/youtube_subscribe.cpp               the pack's composition and timing
```

## Packs

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

FrameSubmission frame = scene.submit(12);
```

`ContentHost` is the whole Chronon-side dependency: create text/image/video and
measure them. It is abstract on purpose, so this module keeps compiling without
the renderer and the real host can be the Chronon engine, the C ABI or a test
double. `FrameSubmission` is the whole render-side output: per layer, the matrix
and the content it draws, already resolved.

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
./build/verify/chronontemplate_emit_catalog > catalog/emitted.json
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
`include/chronontemplate/ImportantPhrasePack.hpp` owns how such a phrase looks
and moves. `Classic` is the first family: white Montserrat Bold face with a
soft white glow and a slight black stroke on the black canvas, fourteen
animations — seven layer entrances, three staggered glyph windows, two
whole-run focuses and two full-run word emphases. The second family,
`Typewriter`, types the phrase glyph by glyph while the `_` underscore cursor
trails, blinks, leads or holds: fifteen animations with `typewriter_*` ids.
One file per family (`ClassicPhrasePack.*`, `TypewriterPhrasePack.*`) on the
shared look and motion vocabulary of `ImportantPhrasePack.*`, so a pipeline
can render one family while the other stays ready.

The pack is data; `tools/emit_important_phrase_classic.cpp` lowers it to
`chronon.render-plan.v2` and `tools/render_important_phrase_classic.sh` renders
the showcase MP4s on the Vulkan lane (GPU-native text, `require_gpu_native`).
The GPU lane samples animator properties per run — per-glyph effect is always
`property(t) * weight(glyph, t)` — so unit-level staging lives in the selector
window: `reveal` holds the property at its hidden value and sweeps the window
edge as the reveal frontier (typewriter, assembly), `band` sweeps a narrow
window that pulses the held value through the run (lift, wave), and `full`
selects the whole run at once. Every definition stays inside Chronon3D's
canonical GPU text contract (glyph windows and single-word run emphasis), which
is what keeps the whole pack on the GPU instead of the software text fallback.
