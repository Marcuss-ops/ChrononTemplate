# David Carpenter Archive Timeline Recreation

## Scene contract

- **Subject and assets:** Warm aged-paper timeline with two distinct David Carpenter mugshots: an August 1960 San Francisco mugshot and a July 1981 Marin County Sheriff's Department mugshot.
- **Composition:** 1197×658 board, archive caption at upper left, two photographs above a full-width horizontal timeline, and decade labels below. The 1960s portrait is narrower and taller; the 1980s mugshot is compact and nearly square.
- **Line and markers:** Continuous vivid red rule across the canvas at y=470, with two red circular markers aligned to the photographs and labels. The timeline also exists as a standalone transparent SVG layer.
- **Motion and timing:** Static composition held for 8 seconds at 30 fps.
- **Layers and source:** `timeline_recreation.svg` contains the composition; `timeline_line.svg` contains the red rule and markers. The images are embedded from the two credited public-record sources listed below. Vector text, timeline, paper texture, and light aged softness are SVG effects.
- **Must not appear:** Browser chrome, controls, invented dates, extra labels, generated faces, or a broken/dashed timeline.
- **Preview acceptance:** At 854×470 both different mugshots are visible and distinct, the red line is uninterrupted edge-to-edge, and the red markers align with the two decade labels.

## Image sources

- 1960 mugshot: [DavidCarpenter-1970.jpg, Wikimedia Commons](https://commons.wikimedia.org/wiki/File:DavidCarpenter-1970.jpg). The file summary dates the photo to August 1960 and identifies it as a California public record.
- 1981 mugshot: [David Carpenter alternate mugshot.jpg, Wikimedia Commons](https://commons.wikimedia.org/wiki/File:David_Carpenter_alternate_mugshot.jpg). The file summary dates it to July 1981 and identifies it as a California public record.

## Delivery

- Final MP4: `C:\Users\pater\OneDrive\Documenti\Chronomotion\MP4\MP4\Altri_video\David_Carpenter_Timeline_Recreation.mp4`.
- Editable SVG, embedded photo assets, and review previews: `out/david_carpenter_timeline/`.
- Video: H.264, 1920×1056, 30 fps, 8 seconds. SVG rasterized through FFmpeg `svg_pipe`; MP4 encoded with FFmpeg/libx264.
- Review: inspected the 854×470 SVG render. Both mugshots are visible, the red line is continuous, and markers and labels align. Mild global Gaussian softness and stronger photographic softness give an aged print appearance while retaining the line's readability.
