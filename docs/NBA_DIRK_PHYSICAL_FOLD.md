# NBA Dirk physical fold

## Scene contract

- **Subject:** The headline `2011 Dirk Nowitzki Was A GOD`, appearing on a textured sports archive sheet.
- **Composition:** A warm, worn sheet floats over black. It has a main panel and a hinged side panel, a pronounced paper crease, deckled outer edges, paper fibers, faded print and a subtle drop shadow. The right panel folds relative to the main panel.
- **Coordinate and camera convention:** Chronon's existing 1920×1080 perspective camera; world X is horizontal, Y is up, and the proven project camera placement is negative Z, looking toward the planes at Z≈0. Image panel centers use world coordinates in pixel-like units. The camera starts near frontal and moves to a three-quarter view.
- **Motion and timing:** Eight seconds at 30 fps. The sheet begins partly folded, opens as the camera moves closer, and folds again while the camera arcs to show its edge. Chronon text layers write the two headline lines forward, one grapheme at a time, then hold for the final camera move.
- **Layers and source:** The paper is a textured SVG plate split into two image assets. The main panel and right flap are distinct 3D Chronon image layers. The two headline lines are native 3D Chronon text layers with character selectors. A separate black vignette plate sits behind them.
- **Must not appear:** Browser controls, a clean black title card, red pin, unrelated player photos, or a flat page that does not fold.
- **Preview acceptance:** Opening and ending frames show the sheet and its visible fold; the camera change exposes thickness at the end; intermediate frames show the title writing from left to right; the complete final title is readable and inside the page.

## Delivery

- Replace `NBA_Article_and_Title_Chronon.mp4` in `OneDrive/Documenti/Chronomotion/MP4/MP4/Altri_video`.
- H.264, 1920×1080, 30 fps, 8 seconds. Chronon Vulkan produces the frames; FFmpeg encodes the final MP4 from Chronon's raw pre-encode frames.
- `tools/web_presets/build_nba_dirk_physical_fold.mjs` regenerates the SVG-derived paper assets and the editable Chronon render plan.
