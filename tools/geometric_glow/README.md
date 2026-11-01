# geometric_glow — native C++ / Blend2D rebuild of the neon minimalist animation

Recreates the 16-second motion-graphics sequence captured in
`visual_venture_channel_archive/02_Disturbing_Webpages_Deleted_From_Internet/frames/frame_0051..0066.png`
(640x360, sampled at 1 fps) as a pure C++ / Blend2D emitter.
No Python in the render path.

## What it renders

Keyframed state machine: 16 measured keyframes (one per reference frame), each
holding the exact geometry/color/alpha measured from the PNGs. Keyframe `k`
lands exactly at `t = k` seconds; between keyframes the state is interpolated
with ease-in-out cubic, so the motion is real, not a crossfade:

| t (s) | ref  | content |
|-------|------|---------|
| 0-1   | f51  | dashed flowchart box, 3 outlined blocks + connectors |
| 1     | f52  | blocks turn solid white, box shrinks |
| 2     | f53  | rounded square outline + two spheres (large/small) |
| 3-4   | f54/55 | box elongates into a pill, spheres travel down |
| 5     | f56  | box breaks: top bar detaches, right rail, spheres separate |
| 6-7   | f57/58 | bar widens, conical beam lights the spheres, row fades in |
| 8     | f59  | box returns with a top-edge gap, sphere turns pink, 10-dot row |
| 9-11  | f60-62 | sphere rises and saturates to pure red, row glows brighter |
| 12    | f63  | box dissolves to a rail, row bends into a smile arc |
| 13    | f64  | red core + 10-dot orbit ring (R = 58) |
| 14    | f65  | constellation shrinks (ring R = 44) |
| 15    | f66  | cut to the dark slab device with amber LED |

Post per frame: procedural star dust, soft halo, radial vignette, film grain.
Rendering happens at 2x device scale → 1280x720 PNGs.

## Build and render

```powershell
powershell -ExecutionPolicy Bypass -File .build_and_render.ps1
```

- MSVC (`vcvars64.bat`, VS 18 Community) + `blend2d.lib` from the vcpkg pkgs
  under `C:\Users\pater\dev\projects\Chronon3d\vcpkg_installed\win-release\vcpkg\pkgs`.
- Writes `out/frame_0000..0479.png` plus `out/_keyframes_sheet.png` (4x4 sheet
  of the keyframes for side-by-side review against the reference).
- Encodes `geometric_glow.mp4` (30 fps, H.264 CRF 16) with `C:\Ffmpeg\ffmpeg.exe`.

`geometric_glow.exe [outDir]` can be run directly; the argument defaults to `out`.

## Review artifacts

- `out/_keyframes_sheet.png` — the 16 keyframes, in order, for direct
  comparison with `frame_0051..0066.png`.
- `geometric_glow.mp4` — final animation.

## Fidelity note

Positions/radii/colors were measured per frame with a connected-component
analysis of the reference PNGs; the in-between frames are interpolated, since
the reference is only sampled at 1 fps.
