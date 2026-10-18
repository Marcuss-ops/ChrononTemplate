# Centered bullet point camera animations

## Scene contract

- **Subject:** one centered, editable headline and supporting bullet sentence per clip; ten Italian editorial statements are authored in `emit_bullet_camera_10.cpp`.
- **Composition:** 1920×1080, centered title and supporting sentence on a restrained dark blue-gray field.
- **Camera:** ChrononMotion3D perspective `CameraRig`; canvas coordinates use pixel units, origin at canvas center for RenderPlan camera coordinates, +Y points down, and the camera looks toward the title at Z=0. The RenderPlan lowering mirrors camera Z.
- **Motion and timing:** ten distinct 5-second moves at 30 fps (150 frames): push in, pull out, left/right orbit, lateral track, crane down/up, dolly arc, roll reveal, and slow drift. Text remains centered in the view throughout.
- **Layers:** background, headline and supporting text. No stock imagery or extra objects.
- **Preview acceptance:** start, midpoint and ending frames show legible centered text and a visible camera pose change; each final MP4 is 1920×1080 H.264.

## Build and render

```sh
python3 tools/bulletpoints_3d/render_bullet_camera_10.py
```

The renderer compiles the C++ emitter against the existing ChrononMotion3D library when needed. Chronon3D renders RGBA video frames; FFmpeg encodes the H.264 files because this WSL CLI build has no MP4 encoder adapter. It writes ten MP4 files, a JSON manifest and a start/middle/end contact sheet to `C:\Users\pater\OneDrive\Documenti\Chronomotion\MP4\MP4\BulletPoints`. Plans and sampled frames are retained in `out/bullet_camera_10/`.
