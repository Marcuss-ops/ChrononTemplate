# Screen recording camera recreation

## Scene contract

- **Source:** `Screen Recording 2026-10-17 170934.mp4`, supplied by the user (1772×1002, H.264, 30 fps, 8.7 s). It is the sole visual asset; no substitute illustration, model, or title is introduced.
- **Subject:** the source footage itself, displayed on one 3D video plane. This preserves its tabletop, torn illustrated sheet, ceramic bowl, figurine, and photograph exactly as captured.
- **Composition:** 1920×1080, 16:9, plane centered at `(960, 540, 0)` in RenderPlan coordinates. A perspective ChrononMotion `CameraRig` looks toward the plane from negative RenderPlan Z (Motion camera forward is local `-Z`; lowering converts that to the plan convention).
- **Motion and timing:** 261 frames at 30 fps. Camera pose is authored and sampled in C++ by `CameraRig`; a restrained dolly and pan add a real perspective-camera pass over the source footage.
- **Layers:** one video plane and one perspective camera. No added text, effects, or fabricated props.
- **Must not appear:** replacement artwork, invented text, additional objects, or a second renderer.
- **Delivery acceptance:** H.264 MP4 at 1920×1080, 30 fps, approximately 8.7 s, rendered through Chronon3D; inspect opening, middle, transition, and ending frames for a visible source subject and camera change.

## Limitation

The supplied file is a screen recording, so its captured framing and any visible playback controls/cursor are part of the source. The 3D camera moves the video plane as a whole; the source does not provide separate tabletop, paper, and photograph assets for independent parallax.
