# Green screen actor head and bust rig V1

## Scene contract

- **Subject and source:** AI-generated photorealistic chest-up portrait of Keanu Reeves, 1672×941 landscape, front-facing, RGB, no alpha, uniform green background. Key the green to alpha before it enters the ChrononMotion scene. Source image: `assets/social_rig_keanu_v1/keanu_chroma_source.png`.
- **Composition:** 1920×1080, centered head and shoulders, full green-screen output. Camera is fixed, front-facing, 45° FOV, 30 fps. Keep the entire head and shoulders in frame.
- **Motion and timing:** 4-second seamless loop (121 frames including both endpoints). Head moves slightly right and then left, returning to neutral; bust follows with a smaller lateral sway and gentle tilt. No unrelated gestures, camera movement, or breathing exaggeration.
- **Layers:** Green background plane and transparent actor image plane. A ChrononMotion PinWarp rig provides separate left/right head controls and a low-amplitude torso control; anchors hold the lower bust stable.
- **Must not appear:** Original green plate texture, key fringes, cropping, face replacement, text, extra props, cinematic background, or sharp jitter.
- **Review evidence:** Inspect the keyed cutout and rendered frames at the beginning, middle, and end. Verify the MP4 is 1920×1080, 30 fps, 121 frames, and confirm motion differs between those frames while the first and final frames match.

## Asset inspection

The generated source is 1672×941 (RGB, landscape, no alpha). Its green plate is uniformly lit and there are no external media assets or third-party attribution requirements. The working cutout is derived with an FFmpeg chroma key; the source remains preserved unchanged.
