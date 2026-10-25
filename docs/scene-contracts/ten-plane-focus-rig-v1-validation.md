# Ten Plane Focus Rig V1 — Validation

## Rendered result

- Ten ChatGPT Image green-screen sources are preserved at `assets/focus_plane_stack_v1/source_green/` (1672×941 RGB); ten keyed and despilled layers are at `assets/focus_plane_stack_v1/layers_rgba/` (854×480 RGBA).
- The keyed source overview is `out/focus_plane_stack_v1/keyed_layers_contact_sheet.png`. The inspected 854×480 renderer output overview is `out/focus_plane_stack_v1/focus_states_contact_sheet.png`.
- Ten static RenderPlan v2 files represent the ten native CameraRig focus-track samples: 450, 650, …, 2250 units. Each plan has ten editable image layers, the same camera pose and framing, near/far 10/3000, focal length 22.723370 mm, f-stop 0.7 and max blur 24 px at 854×480.
- Ten matching 1920×1080 renders were saved to `C:\Users\pater\OneDrive\Documenti\Chronomotion\MP4\Camera\`; their contact sheet and validated plans are in that folder too. The output is raw RGBA from Chronon CLI's software backend converted losslessly to PNG. Each raw frame is 8,294,400 bytes (1920×1080×4). These are stills, one frame per focus state; there is no video frame rate or duration.
- The raw-pixel path needs plans to declare MP4 output so plan preparation creates its full composition compatibility view. The render command overrides that encoder path with the raw RGBA sink; no MP4 was generated.

## CameraRig and focus checks

ChrononMotion3D was built from current source in Release mode with tests, benchmarks and render targets disabled. A native sampler linked against that fresh library evaluated `CameraRig` at seconds 0–9. The resulting CSV records focus distances 450, 650, …, 2250, constant camera position `(0,0,0)`, FOV 48°, focal length 22.723370 mm, sensor width 36 mm, f-stop 0.7 and max blur 24 px. The C++ sampler source is `tools/focus_plane_stack/sample_camera_rig_focus_track.cpp`.

All ten pixel-truth focus states rendered successfully and were visually inspected, including the 1920×1080 contact sheet. The target group's Laplacian-variance sharpness score ranked first in all ten states at both 854×480 and 1920×1080 when compared with the other nine groups. At 854×480, target-to-runner-up score ratios ranged from 7.9× to 250×. Switching focus from state 01 to state 02 changed 50,345 RGB pixels (mean absolute difference 2.0981, maximum 178); switching 02 to 03 changed 75,487 pixels (mean absolute difference 2.0923, maximum 163). The visible sharp group moves from kettle/mug to compass/watch, then vase/stem. This verifies that focus and DOF affect actual Chronon output.

| State | Focus distance | Target sharpness | Rank among groups | Strongest other / target |
|---:|---:|---:|---:|---:|
| 01 | 450 | 640.515 | 1 | 0.072 |
| 02 | 650 | 1459.424 | 1 | 0.032 |
| 03 | 850 | 1097.514 | 1 | 0.023 |
| 04 | 1050 | 1435.917 | 1 | 0.004 |
| 05 | 1250 | 2979.235 | 1 | 0.007 |
| 06 | 1450 | 2644.192 | 1 | 0.011 |
| 07 | 1650 | 2586.861 | 1 | 0.021 |
| 08 | 1850 | 1644.188 | 1 | 0.085 |
| 09 | 2050 | 2393.477 | 1 | 0.127 |
| 10 | 2250 | 3578.492 | 1 | 0.056 |

Sharpness uses Laplacian variance in a crop around each expected group location. The rank comparison is within each rendered frame and is a relative focus check, not a calibrated optical measurement. The v2 CLI cannot render animated `camera_samples`; the ten states are individual samples of the native CameraRig track.

## Reproduction

Build the ten plans from the recorded CameraRig samples and validate a plan:

```sh
python3 ChrononTemplate/tools/focus_plane_stack/build_focus_plane_stack_v1.py
Chronon3d/.tmp/cli/apps/chronon3d_cli/chronon3d_cli validate \
  --plan ChrononTemplate/out/focus_plane_stack_v1/focus_01.plan.json \
  --assets-root /mnt/c/Users/pater/dev/projects
```

The pixel-truth render command is:

```sh
Chronon3d/.tmp/cli/apps/chronon3d_cli/chronon3d_cli render \
  --plan ChrononTemplate/out/focus_plane_stack_v1/focus_01.plan.json \
  --assets-root /mnt/c/Users/pater/dev/projects \
  --backend software --video-sink raw --pipe-pixfmt rgba \
  --start-frame 0 --end-frame 0 \
  -o ChrononTemplate/out/focus_plane_stack_v1/focus_01.rgba
```

`out/focus_plane_stack_v1/still_lane_diagnostic_854x480.png` is retained only as a historical diagnostic: the legacy PNG still lane ignores the authored camera for this plan and is not camera-truth evidence. No renderer source was changed for this scene.
