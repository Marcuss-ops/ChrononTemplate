# Three Plane Camera Focus V1 — Validation

## Scene and assets

- Layer 0: generated vintage camera repair studio at focus distance 900 units.
- Layer 1: native editable Chronon text `FOCUS TEST` at 650 units.
- Layer 2: generated transparent brass lens at 450 units. It overlaps the title to make the front-to-back compositing order visible.
- Background source: 1672×941 RGB. Lens cutout: 1374×1145 RGBA with alpha range 0–255. Both sources and image generation prompts are recorded in `assets/three_plane_focus_v1/README.md`.
- The 854×480 composition preview is `out/three_plane_focus_v1/preview_text_focus_854x480.png`. It was inspected before making the 1920×1080 states.

## Render result

Three RenderPlan v2 stills were rendered with the Chronon3D CLI, software backend and raw RGBA pixel-truth sink, then converted losslessly to PNG. The 1920×1080 outputs and validated plans are in `C:\Users\pater\OneDrive\Documenti\Chronomotion\MP4\Camera\three_plane_focus_v1\`.

| File | Focus plane | Focus distance |
|---|---|---:|
| `focus_background_1920x1080.png` | Layer 0 background | 900 |
| `focus_text_1920x1080.png` | Layer 1 text | 650 |
| `focus_foreground_1920x1080.png` | Layer 2 foreground lens | 450 |

All three layers remain present in every render. Visual inspection of the contact sheet confirms that the requested plane sharpens in each state while layers at other depths blur; the foreground lens stays in front and partially occludes the title. All three states are distinct: focus changes 1→2 altered 1,943,689 RGB pixels (MAE 7.2876), and 2→3 altered 1,980,200 pixels (MAE 9.8815). Each PNG is 1920×1080.

The v2 CLI does not accept this CameraRig focus sequence as an animated camera track, so the three track samples are represented by three static plans. No engine source was changed.

## Reproduction

```sh
python3 ChrononTemplate/tools/three_plane_focus/build_three_plane_focus_v1.py \
  --width 1920 --height 1080 \
  --out '/mnt/c/Users/pater/OneDrive/Documenti/Chronomotion/MP4/Camera/three_plane_focus_v1/plans_1920x1080'
```

The builder and source assets are in `tools/three_plane_focus/` and `assets/three_plane_focus_v1/`.
