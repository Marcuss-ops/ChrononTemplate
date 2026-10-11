# Astronaut camera transition v3

Full-screen reconstruction at 1920×1080, 30 fps, 6.2 seconds. The sequence uses a perspective camera, separate background and title planes, transparent astronaut PNGs, a photographic foreground cloud layer, and a Z move on the astronaut independent of the camera. The scene changes happen at the peak of the camera movement; temporal motion blur is enabled in the render.

The title planes sit behind the astronaut cutouts. The foreground clouds sit closer to the camera and cross in front of the subject in the HUMANITY shots. The ending fades to white without adding a new title.

## Files

- `astronaut_camera_transition_v3.plan.json` — full 186-frame composition.
- `astronaut_camera_transition_v3_gate.plan.json` — 30-frame first-transition check.
- `../../output/astronaut_camera_transition_v1/astronaut_camera_transition_v3.mp4` — final 1920×1080 render.
- `../../output/astronaut_camera_transition_v1/astronaut_camera_transition_v3_contact.png` — sampled frames across the full duration.
- `../../output/astronaut_camera_transition_v1/astronaut_camera_transition_v3_gate_contact.png` — five frames around the first scene change.

## Assets

The plates and transparent astronaut cutouts are derived from the two existing photographic references. `foreground-clouds-v2.png` is a photorealistic transparent layer used in front of the HUMANITY scene. All assets are under `../../assets/astronaut_camera_transition_v1/`.

## Render command

From the workspace root:

```sh
Chronon3d/build/chronon/linux-video-test/apps/chronon3d_cli/chronon3d_cli render \
  --plan ChrononTemplate/golden_plans/astronaut_camera_transition_v1/astronaut_camera_transition_v3.plan.json \
  --assets-root "$PWD" --backend software \
  --output ChrononTemplate/output/astronaut_camera_transition_v1/astronaut_camera_transition_v3.mp4 \
  --fps 30 --motion-blur --motion-blur-mode 1 --motion-blur-samples 8 --shutter-angle 210
```

## Camera choreography v1

`astronaut_camera_choreography_v1.plan.json` is the full-screen camera-driven variant. It keeps the 1920×1080 composition and the photographic PNG assets while layering independent camera push/pull, horizontal and vertical tracking, restrained orbit, and astronaut/cloud motion. These moves overlap in time: the camera keeps pushing as the track begins, and the character and foreground clouds continue on their own depth planes. The plate is enlarged to maintain full-bleed coverage during the camera travel.

The renderer requires component tracks for a single position or rotation to share keyframe times and easing. The plan follows that contract for camera and layer transform channels.

Rendered output:

- `../../output/astronaut_camera_transition_v1/astronaut_camera_choreography_v1.mp4` — H.264, 1920×1080, 30 fps, 186 frames (6.2 s).
- `../../output/astronaut_camera_transition_v1/astronaut_camera_choreography_v1_contact.png` — sampled full-sequence review sheet.
