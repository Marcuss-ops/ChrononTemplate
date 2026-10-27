# Chronon SVG animation collection

The collection contains **100 MP4 animations**: 20 downloaded vector subjects
crossed with five palettes. Every variation is an independently rendered
four-second video.

## Files

- `001_*.mp4` through `100_*.mp4`: 1280×720, 30 unique frames per second,
  120 frames, H.264 NVENC/yuv420p.
- `contact_sheet_100_variations.jpg`: overview of all 100 videos.
- `previews/`: one editable SVG and one PNG preview per MP4.
- `manifest.json`: mapping of each MP4 to its vector, palette and primitives.
- `sources/`: downloaded SVG sources and the Lucide license text.

## Vector subjects

mountain, sun, moon, tree-pine, compass, map-pin, bike, train-front,
bus-front, rocket, lightbulb, flask-conical, atom, heart-pulse, footprints,
waves, cloud-sun, telescope, ship, and orbit. Each appears in arctic cyan,
solar amber, ultraviolet, verdant, and rose neon. The MP4 filename includes
the variation number, subject, and palette.

## Primitive coverage

Every video animates an SVG polyline reveal and a marker sampled by distance
along that same path. It layers neon strokes and gradients, pulses three red
checkpoints, transforms the icon/path/marker together with a moving camera,
adds soft radial bokeh for stylized depth, and composites deterministic dust
points over the scene. The bokeh is a stylized depth cue, not a calibrated
optical DoF pass.

The SVG frames are rasterized with ImageMagick/Librsvg, then encoded with
FFmpeg's NVIDIA `h264_nvenc` encoder. The generator fails if NVENC is
unavailable rather than falling back to software encoding. The videos
demonstrate the visual primitives but are not output from Chronon3D's
RenderPlan renderer.

## Regenerate

From `C:\Users\pater\Pyt` on Windows, with PowerShell, ImageMagick and FFmpeg
on `PATH`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  ChrononTemplate\tools\vector_diagram\generate_vector_animation_collection.ps1
```

Pass `-Resume` to keep completed MP4s and render missing variations. Run the
separate verifier with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  ChrononTemplate\tools\vector_diagram\verify_vector_animation_collection.ps1
```

## Sources and licenses

The 20 scene icons were downloaded from the [Iconify Lucide API](https://api.iconify.design/lucide/{icon}.svg)
from the [Lucide project](https://github.com/lucide-icons/lucide). Lucide is
ISC licensed; `sources/Lucide-LICENSE.txt` is included.

`sources/Wikimedia_Mountains.svg` is an additional vector downloaded from
[Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Mountains.svg),
dedicated to the public domain by Herzi Pinki. It is retained as an input
asset and is not embedded in these scene renders.
