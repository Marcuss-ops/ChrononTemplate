# Web bounded box

## Scene contract

- **Preset:** `web.bounded_box`, exposed as `BoundedBoxSpec` / `addBoundedBox` in ChrononTemplate.
- **Composition:** 1920×1080 at 30 fps. A square-corner white rectangle, 920×300 px, centered on a charcoal background. One editable centered text layer uses dark ink.
- **Sample text and font:** `Il tuo testo qui`, Inter Bold fixture from Chronon3D.
- **Motion and timing:** 10 seconds total. The rectangle expands horizontally and fades in over 3 seconds; the text follows with a slight delay and fades in over the same interval. Both hold through the final 7 seconds.
- **Layers:** background, rectangle, text. All remain separate plan layers.
- **Must not appear:** images, browser controls, extra labels, border, icons, or rounded corners.
- **Coordinate convention:** screen-space pixel coordinates, origin at top-left; center at (960, 540). This overlay has no camera.

## Render evidence

- Plan validates at 1920×1080, 30 fps, 300 frames.
- Full output: `out/web_bounded_box/web_bounded_box_1080p.mp4` (1920×1080, H.264, 30 fps, 10 seconds).
- Preview: `out/web_bounded_box/preview_854x480.png`, extracted from frame 90 of the final MP4 and inspected. Contact sheet `out/web_bounded_box/contact_sheet.png` shows frames 0, 30, 60, 90, 150, and 299 across reveal and hold.
- Render backend: Vulkan (DZN); video encoding: H.264 via x264.
- The sample plan is emitted directly as a 2D `chronon.render-plan.v3` plan so the video exporter receives a screen-space overlay. The reusable TemplateScene element remains available for composing the bounded box into other ChrononTemplate scenes.
- The sample uses `tests/fixtures/Inter-Bold.ttf` from Chronon3D, resolved with Chronon3D as the assets root. The preset defaults to `assets/fonts/Inter-Bold.ttf` and accepts another font path through `BoundedBoxSpec::font`.
