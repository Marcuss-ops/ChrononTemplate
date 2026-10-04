# Documentary Map V1

Three reusable 5-second Chronon RenderPlan V3 scenes demonstrate the core map
explainer workflow: a country outline reveal, a transatlantic route draw, and a
wide-to-country camera move with geographic labels.

## Build and render

From the VeloxEditing workspace root:

```bash
python3 ChrononTemplate/tools/build_documentary_map_v1.py --plans
python3 ChrononTemplate/tools/build_documentary_map_v1.py --render
```

The generator creates a warm toned Natural Earth relief plate, writes the plans
in this folder, then renders MP4 previews in
`ChrononTemplate/out/documentary_map_v1/`. It tries Vulkan by default and
retries a failed Vulkan example with software compositing. Set
`CHRONON_MAP_BACKEND=software` to select software directly.

## Native scene parts

- `relief-map` is the registered Natural Earth 1:10m shaded relief raster.
- Country outlines and routes are converted to registered rounded-rectangle
  segments. Each native Chronon shape fades on in sequence to reveal the
  geometry. Segment direction uses Z rotation in the XY map plane.
- The route bends across the Atlantic, uses a restrained teal line and ends in
  two native arrow arms.
- Pins and place names use native shape and text layers. Camera pans and zooms
  are shared scale and position tracks on the plate and its geographic paths.
- Labels follow their geographic point and inverse scale during camera moves.

The image layer uses Chronon's centered world coordinates while vector
coordinates are authored in canvas space; the generator resolves that origin
difference and the 3D Y-up convention for rotated segments.

The registration uses the equirectangular crop documented in
`ChrononTemplate/catalog/MAP_DATA_SOURCES.md` (longitude -100..50, latitude
8..72). The bundled Natural Earth countries file supplies contemporary Admin 0
boundaries. Historical boundary change and thematic data are not represented.

## Local render status

All three plans pass the Chronon CLI plan validation. All three five-second
MP4 examples were rendered with the Vulkan backend at 1920 × 1080 and 30 fps;
H.264 encoding uses libx264. An earlier Vulkan attempt lost the device at frame
81, but the isolated rerun and final exports completed. The generator retries a
failed Vulkan example with software compositing. Set `CHRONON_CLI` to use
another build, or `CHRONON_MAP_BACKEND=vulkan` / `software` to choose a backend.

## Examples

- `documentary_map_country_focus_v1.plan.json` — focuses mainland France and
  Corsica, traces the border, then marks Paris.
- `documentary_map_route_draw_v1.plan.json` — draws New York to London with a
  curved route, arrowhead, and staggered labels.
- `documentary_map_camera_shots_v1.plan.json` — makes a wide-to-France move,
  traces the boundary, then brings in France and Paris labels.
