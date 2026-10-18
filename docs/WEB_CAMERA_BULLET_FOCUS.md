# Web camera bullet focus

## Scene contract

- **Preset:** `web.camera_bullet_focus`, emitted by `chronontemplate_emit_camera_bullet_focus`.
- **Subject and content:** four editable sample headings: `1ST ERA — THE RISE`, `2ND ERA — THE EARLY GAME`, `3RD ERA — SHOT CHUCKING ERA`, and `4TH ERA — MODERN BASKETBALL`.
- **Composition:** 1920×1080, light gray monochrome field. Four rows are spaced 200 px apart and centered as a vertical list. A cyan-blue triangle marks the active heading. The active era/title are dark and sharp with a cyan glow; a warm yellow marker wipes left-to-right behind each active heading. Inactive text is hidden on the sharp layer and shown only as unreadable 40 px mosaic pixels until focus arrives.
- **Camera and coordinates:** ChrononMotion3D `CameraRig`, perspective camera forward +Z in motion coordinates, plan camera Z negated for Chronon3D. XY positions use canvas pixels from top-left, +Y down. Camera tracks down through rows while keeping the selected row in the central reading band. FOV 55°, near 1, far 5000.
- **Motion and timing:** 4 headings, 2.5 seconds per heading (10 seconds total, 30 fps). Camera, pointer, marker, and text focus share the same 35-frame in-out move/arrival timing. The marker wipes as the pixelated layer fades and sharp glowing text resolves at arrival. The last row holds to the end.
- **Layers and source:** editable era and heading text planes, soft-focus duplicate text layers, pointer polygon, and full-frame gray color. Font is Chronon3D's Inter Bold fixture. Screenshots guide composition only and are not included as source footage or textures.
- **Must not appear:** copied YouTube UI, video footage, playback controls, channel marks, narration, or unrelated imagery.
- **Preview acceptance:** at opening `THE RISE` is dark and selected; in the middle the active row has moved down and a different heading is dark; at the end the camera has reached `MODERN BASKETBALL`. Titles remain in frame, the pointer aligns with the active row, and frames change over time.

## Render record

- Plan: `out/web_camera_bullet_focus/plan.json`.
- Final: `Web_Camera_Bullet_Focus_1080p.mp4` (1920×1080, H.264, 30 fps, 300 frames / 10 s).
- Preview: `out/web_camera_bullet_focus/preview_854x480.png`; contact sheet: `out/web_camera_bullet_focus/contact_sheet.png` (frames 0, 75, 150, 225, 299).
- Backend: Vulkan (DZN); video encoding: H.264 via x264.
- Focus treatment uses Chronon3D's per-layer mosaic effect (40 px blocks) on inactive title layers, cyan glow/shadow on active text, and a left-to-right animated marker bar under each heading. The mosaic layer shares the exact text position. Camera DOF is omitted because it produced blank frames in the DZN video path. Dense CRT scanlines are also omitted.
- Build emitter: `cmake --build build/web-preset --target chronontemplate_emit_camera_bullet_focus`. It accepts four optional `era title` pairs after the plan path, so the same move can be reused with new headings.
