# Geo documentary runtime

The runtime entry point is `python3 tools/map/geo_runtime.py`. Existing free-text tours remain supported. Single-place documentary shots are reproducible with `--place`, `--shot-preset`, and `--out`:

## Offline geography lookup

`geo_runtime.py` resolves place names from the checked-in `catalog/geographic_catalog.v1.sqlite` by default; it does not call Nominatim for missing names. Both `--place` and names extracted from free-text tours use this catalog. Use `--geographic-catalog PATH` to select another catalog. A lookup that cannot be resolved offline remains unresolved, so rendering fails rather than silently selecting an unrelated location. `--online-geocoding` explicitly enables Nominatim fallback for unknown names; ambiguous city/region/country names remain unresolved rather than being guessed. `--offline-geocoding` makes the no-network behavior explicit. The Python `GeoRuntime` API defaults to offline lookup too; callers can opt into fallback with `offline_geocoding=False`. The lower-level `geo_places.geocode()` function supports `offline_only=True` and the `CHRONON_GEOCODE_OFFLINE=1` environment variable.

The catalog is a curated global gazetteer, not a complete gazetteer or a live geocoding service. The checked-in snapshot has 7 continents, 252 country/territory records, 3,865 ADM1 regions and 225,581 city/locality records. City records come from GeoNames `cities500`: generally settlements with population above 500 plus administrative seats down to PPLA4. They include alternate/localized names, but do not cover every settlement, neighborhood or named feature. Administrative boundaries are less complete: 3,183 of the 3,865 ADM1 records have a Natural Earth geometry linked by a unique GeoNames ID. A region without matched geometry cannot be centered by the offline map resolver.

Lookup is conservative: a unique exact city name/alternate name resolves to its catalog coordinates; a city name shared by multiple places is not guessed (except a unique national capital match). A unique ADM1 name with stored geometry resolves to the center of its boundary bounding box, which is a framing point rather than a surveyed city or guaranteed interior point. A recognized ADM1 region with no matched boundary remains unresolved by this coordinate resolver. Region names found in more than one country, or colliding with a country name (for example, Georgia), remain unresolved without country context. Country names resolve to their catalog capital when that capital is present as a city record. Substring city search through `GeographicCatalog.cities()` is useful for browsing candidates, but automatic place resolution deliberately requires an exact, unambiguous match.

Catalog data sources, licensing, refresh procedure and required GeoNames/Natural Earth attribution are documented in [`../../catalog/MAP_DATA_SOURCES.md`](../../catalog/MAP_DATA_SOURCES.md). Include “GeoNames (www.geonames.org)” and “Natural Earth (www.naturalearthdata.com)” in project/video credits when using catalog-derived geography.

```bash
python3 tools/map/geo_runtime.py --place "Roma, Italia" \
  --shot-preset earthrise --out out/rome-rise.mp4
python3 tools/map/geo_runtime.py --place "Roma, Italia" \
  --shot-preset space_to_street --strict-native --out out/rome-space-to-street.mp4
```

`--strict-native` fails closed unless OpenCV activates an NVIDIA OpenCL device and FFmpeg lists `h264_nvenc`. Sampler misses fail closed; there is no engine-renderer fallback path. Encoder telemetry retains the `engine_fallback_frames` compatibility field and it is always zero on successful renders. A Wayback tile request must specify a positive Esri release number (`--wayback-release N`); no version is guessed. The implementation uses Esri's release-addressed World Imagery tile path. Release availability and coverage are service-dependent. Optional Drive uploads use the `RenderingGen/bin/drive-upload` content-addressed publisher; `CHRONON_DRIVE_CREDENTIALS` and `CHRONON_DRIVE_TOKEN` may override the existing local OAuth file defaults. Upload telemetry reports the verified file id, link, parent folder, SHA-256, and byte count.

## Production dynamic map overlays

`render_dynamic_map_overlay.py` uses the prepared OpenCL plate sampler for every composition by default (`DYNAMIC_MAP_GPU_SAMPLER=0` is the rollback). Classic compositions (`region_zoom`, `pulse_marker`, `spotlight`) still run their marker/label drawing on the host, so their sampled frame crosses GPU→host once; editorial compositions keep their all-GPU layer compositor until host readback. NVENC remains the required production encoder. GPU rendering queues up to 16 frames before ordered host readback. The sampler reuses two GPU resize surfaces and retains a separate GPU output surface for each queued frame; this avoids per-frame GPU allocation without overwriting frames still waiting for readback. Completed pixels still cross to FFmpeg's host pipe; this is not a zero-copy Vulkan/CUDA path. Both paths fail on sampler fallback, and telemetry reports the actual frame renderer separately from the video encoder.

For `chronon_editorial`, the retained map compositions use a cropped PIL patch
for the pin, leader and label. Their old implementation allocated, composited
and blurred full-canvas RGBA images for each pin on every frame. The ROI path
was checked against that implementation at center and edge positions and at
four animation phases: all 12 raw-frame comparisons were byte-identical.
Host-composed classic frames now stay in host memory for the FFmpeg pipe; they
are not uploaded to UMat just to be read back immediately.

## Documentary JSON

Pass an object with `--documentary layer.json`. Geometry is standard WGS84 GeoJSON `FeatureCollection`; values are numeric and keyed by feature `id`, falling back to `properties.name`. Polygons/MultiPolygons support holes, fill, numeric labels, and perimeter draw-on; route overlays accept GeoJSON LineString/MultiLineString. For a two-source epoch comparison, specify `epoch_before_provider` and optionally `epoch_before_release`, alongside `provider`/`wayback_release` for the current source. Wayback requires an explicit positive release. The epoch plates are sampled and the diagonal wipe is composited on OpenCL UMat; this enables the GPU map path even without `--strict-native`. NVIDIA/NVENC requirements remain enforced when `--strict-native` is requested.

```json
{
  "regions": {"type":"FeatureCollection","features":[]},
  "values": {"region-a": 42.5},
  "value_range": [0, 100],
  "fill_alpha": 0.32,
  "hotspots": [{"latitude":41.89,"longitude":12.49,"color_bgr":[40,80,255]}],
  "route_geojson": {"type":"FeatureCollection","features":[]},
  "hillshade_path": "assets/rome-relief.png",
  "hillshade_alpha": 0.25,
  "provider": "esri_wayback",
  "wayback_release": 56102,
  "epoch_before_provider": "esri_wayback",
  "epoch_before_release": 37000
}
```

`project` and `pose_project` are Python-only API hooks, not JSON fields. The defaults use a simple local degree-to-screen approximation; pass `project(lon, lat)` for accurate map projection. Supply `pose_project(lat, lon, pose)` when using `camera_labels`; it projects anchors against the full per-frame camera pose. Hillshade remains caller-supplied as a raster image; there is no implicit DEM download. Provider-based epoch comparison prepares isolated tile samplers and keeps each provider/release in a distinct disk cache namespace.

Beat times can be supplied as a JSON array of seconds:

```bash
python3 tools/map/geo_runtime.py --place "Roma" --shot-preset dive \
  --beat-times beats.json --out out/rome.mp4
```

Events snap to the closest supplied beat and convert to integer frames at the runtime FPS. `--beats-offset` aligns the beat file to the shot timeline. Route/pin events are annotations separate from the camera phase schedule, so they do not perturb camera continuity.

## Offline checks

```bash
PYTHONPATH=/usr/lib/python3/dist-packages python3 -m unittest \
  tools.map.test_geo_documentary tools.map.test_geo_places
python3 tools/map/geo_runtime.py --self-test
```

Tests use local arrays, synthetic tiles, and mocked geocoding; they do not contact Nominatim, Esri, Wayback, or fetch DEM imagery.
