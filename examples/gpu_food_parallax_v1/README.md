# GPU Food Story Parallax

Three distinct 6-second video-essay compositions authored as native RenderPlan
V3 scenes, with separate background, title, portrait, food, and particle planes.
The plans are rendered by Chronon3D with Vulkan; the MP4s use NVENC.

## Scenes

1. **Humble Beginnings** — founder portrait over oversized type, with floating
   fries and amber dust against the night storefront.
2. **The Sandwich** — a two-line chapter title with food planes at foreground,
   hero, and background depths.
3. **The Long Game** — a second founder portrait and food arrangement over a
   warm restaurant interior.

Each plan has independent Z planes for the background, title, portrait, and food
cutouts. The food cutouts are transparent PNGs; the portrait and restaurant
plates are project assets. A restrained camera push-in plus per-layer scale,
float, and particle motion creates movement while keeping subjects in frame.

## Build and render

Build the plan emitter from the ChrononTemplate root:

```bash
cmake --preset release-fast \
  -DCHRONONTEMPLATE_CHRONON3D_DIR="$PWD/../Chronon3d-mainfix" \
  -DCHRONONTEMPLATE_CHRONONMOTION_DIR="$PWD/../ChrononMotion3D"
cmake --build --preset release-fast --target chronontemplate_emit_gpu_food_parallax_examples
```

Build the Chronon3D `linux-video-fast-dev` CLI with Vulkan enabled, then run:

```bash
tools/gpu_parallax/render_examples.sh
```

The script authors the plans under `plans/` and renders frames 0, 90, and 179 of
each scene at 1920×1080. It requests Vulkan explicitly and fails if timing
metadata reports software fallback. PNG previews go under
`ChrononTemplate/out/gpu_food_parallax_v1/png/`.

## MP4 export (Windows)

With the Windows Chronon3D CLI and NVENC available, render all three six-second
compositions as 1920×1080 H.264 MP4 files:

```powershell
.\tools\gpu_parallax\render_mp4_examples.ps1
```

The script requests Vulkan, NVENC, and temporal motion blur, then checks each
timing sidecar for 180 frames, Vulkan GPU nodes, and zero software fallback
nodes. The sandwich scene uses gently softened foreground cutouts; native
camera DOF currently breaks the renderer's NVENC surface handoff, so that pass
is disabled for this export. Chronon's receipt still labels the encode path
`software` when direct YUV handoff is rejected; the timing sidecar separately
confirms Vulkan rendering for all 180 frames, NVENC use, and zero software
fallback render nodes. MP4 files and their verification sidecars go under
`out/gpu_food_parallax_v1/mp4/`.

The compositions use 2.5D image planes and camera parallax. They do not claim
automatic roto/background reconstruction, light wrap, or a certified Vulkan
depth-of-field pass; those remain separate tools or renderer work.
