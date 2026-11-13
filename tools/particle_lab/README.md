# Particle Lab

Nine native `chronon.render-plan.v3` experiments for the Chronon3D particle
emitter. The first six are pure particle studies; the last three are 6-second
YouTube bumpers that combine a resolved 3D camera, baked transparent title/light
plates and two depth-separated particle planes. The base algorithm lives in
[`Chronon3d/include/chronon3d/scene/model/shape/particles.hpp`](../../../Chronon3d/include/chronon3d/scene/model/shape/particles.hpp)
and these plans exercise it through the canonical `particle_emitter` contract.

## Base algorithm (Chronon3D)

`sample_particles()` remains a stateless pure function of the emitter, the
particle index and absolute time. Two opt-in fields extend it without changing
any existing render:

| Field | Meaning |
|---|---|
| `flow_strength` | Peak curl-flow displacement in canvas units. `0` disables the field and keeps the old ballistic motion bit-identical. |
| `flow_scale` | Spatial frequency of the flow (1/units). Larger values make finer swirls. |
| `flow_speed` | Temporal frequency in rad/s. |
| `twinkle` | Alpha shimmer depth in `[0, 1]`; `0` keeps the color ramp untouched. |
| `twinkle_speed` | Shimmer cycles per second. |

The flow is the curl of a scalar potential (three sine waves), so it is
divergence-free: density is preserved and a particle stays within
`strength * 1.13` of its ballistic path. It is sampled from the spawn position,
the particle age and a deterministic phase, which keeps warm/cold, random-access
and distributed renders identical. `environment` emitters additionally scale the
flow by depth (far motes drift less), so the same field reads as parallax.

`EffectsPack`'s `floating_dust` now uses this base directly: 44 motes in three
depth bands, curved keyframes and a per-mote twinkle instead of 24 straight
lines.

## Experiments

| Plan | Look |
|---|---|
| `01_cinematic_dust` | 320 environment motes, cool far / warm near, screen blend, bokeh |
| `02_embers` | 180 rising embers, negative gravity, fast warm twinkle, add blend |
| `03_ash_fall` | 240 slow cool flakes, lateral curl, screen blend |
| `04_bokeh_orbs` | 48 large defocused discs with a very slow field |
| `05_chalk_burst` | 160 classroom motes, gravity and a short expansion |
| `06_light_motes` | 90 tiny additive sparks with a strong shimmer |
| `07_youtube_light_intro` | 6 s, 30 fps: cyan light sweep, dust/bokeh, push-in title card |
| `08_youtube_particle_reveal` | 6 s, 30 fps: magenta/cyan bokeh, lateral camera orbit |
| `09_youtube_light_outro` | 6 s, 30 fps: warm light pull-back, outro title card |

The YouTube FX plans use a resolved `camera_samples` array (one perspective
camera per frame), a baked transparent title card, a glow/beam light plate, and
3D environment particles at two depths. Only the color plate is screen-space.
They are 1920×1080, 30 fps, 180 frames. The title and light assets are generated
from `assets/fonts/` by `make_youtube_fx_assets.py`; rerun it after editing the
copy in that script to change the typography.

## Build and run

```bash
python3 tools/particle_lab/make_youtube_fx_assets.py
cmake --build build/dev-fast --target chronontemplate_emit_particle_lab
./build/dev-fast/chronontemplate_emit_particle_lab tools/particle_lab/plans
```

Each experiment is written as `<name>.plan.json`; the emitter prints its size,
layer count and frame count. Validate the plans with the renderer CLI:

```bash
CLI=../Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli
for plan in tools/particle_lab/plans/*.plan.json; do
  "$CLI" validate --plan "$plan" --assets-root "$PWD"
done
```

Render one YouTube FX bumper from the repository root:

```bash
"$CLI" render --plan tools/particle_lab/plans/07_youtube_light_intro.plan.json \
  --assets-root "$PWD" --backend vulkan --gpu-hot-path-mode require_gpu_native \
  --tone-map aces --exposure 1.0 --rate-control qp --qp 18 \
  -o out/youtube_fx/07_youtube_light_intro.mp4
```

## Tuning notes

- Use `blend_mode: "add"` for sparks and embers and `"screen"` for dust; normal
  blend keeps chalk opaque.
- `bokeh: true` scales the particle size and alpha by `depth_range`, so keep
  large discs in a narrow far band and tiny sparks near the camera.
- The flow phase is derived from the emitter seed, so changing `seed` reshuffles
  every swirl without changing the look's amplitude or density.
