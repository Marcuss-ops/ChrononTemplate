# Ten Plane Focus and CameraRig Check V1

## Scene contract

- **Subject and assets:** ten independently generated still-life groups with distinct materials and silhouettes. Each source is a uniform chroma-green plate preserved beside its keyed RGBA output. The groups are: enamel kettle and mug; compass and pocket watch; blue ceramic vase and dried stem; unmarked burgundy books and reading glasses; toy robot and gears; terracotta pot with burgundy succulent leaves and stones; film camera and canister; citrus bowl and spoon; globe and wooden telescope; hourglass, key and medallion. No overlay text or logos.
- **Composition:** 16:9, authored at 854×480 and delivered at 1920×1080. One perspective camera at `(0, 0, 0)` aimed at `(0, 0, -1)`, FOV 48°, focal length 22.723370 mm, 36 mm sensor width, near 10 and far 3000 render units. The camera has f-stop 0.7; max blur is 24 px at 854×480 and scaled to 54 px at 1920×1080. Ten image planes sit at camera-space distances 450 through 2250 units in increments of 200; their transforms compensate for perspective so the groups stay separated and legible.
- **Motion and timing:** position, aim, FOV and exposure remain fixed. A native ChrononMotion3D `CameraRig` focus-distance track contains ten keys at seconds 0–9 with distances 450–2250. The keys are sampled through `CameraRig` into `tools/focus_plane_stack/camera_rig_focus_samples.csv`. The current v2 RenderPlan CLI does not accept animated `camera_samples`, so each sample is lowered to a static one-frame plan for pixel-truth rendering.
- **Required layers:** ten separate editable RGBA image planes. Preserve the original green-screen sources and keyed outputs. Do not flatten the scene before rendering.
- **Must not appear:** green matte or spill, cut-off subjects, overlay text, logos, unsupported bokeh shapes, changing FOV, unrelated props, or focus values derived from world-Z instead of camera-space distance.
- **Preview acceptance:** inspect the actual 854×480 Chronon output, including focus states 01 and 02, then inspect the contact sheet for all ten states. Each target group must be the sharpest of the ten; near and far groups must remain visible while out of focus.

## Coordinate and lens convention

ChrononMotion3D `CameraRig` aims along local `-Z`; its `+Z` axis is backward. The RenderPlan 2.5D camera view follows that backward-axis convention, so the static plans use a 180° Y rotation to keep the optical direction along world `-Z`. Focus distance is positive camera-space distance along the optical axis, not a world-Z coordinate or Euclidean distance. Focal length 22.723370 mm with a 36 mm sensor gives the authored 48° vertical FOV. Distances use renderer world units; the image planes are sized at a 100:1 scene-unit scale.

## Source and attribution

All ten source plates were generated with ChatGPT Image for this focus test. There are no external image sources. The source filenames and keyed-layer mapping are recorded in `assets/focus_plane_stack_v1/README.md` and `tools/focus_plane_stack/build_focus_plane_stack_v1.py`.
