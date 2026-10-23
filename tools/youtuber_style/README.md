# Youtuberstle native animation rebuilds

These 20 C++ entrypoints redraw and animate their scenes with Blend2D through the existing ChrononTemplate rendering setup. The supplied PNG references are used only for visual comparison; the generators never load reference frames. Generated stills are written to `C:/Users/pater/OneDrive/Documenti/Chronomotion/MP4/Youtuberstle/Final/<animation>/frame_####.png`.

## Build and render

Run `build_and_render.ps1` in Windows PowerShell. It compiles each numbered `.cpp` source against the configured Blend2D package and executes the generator. Output frames use the same frame numbers and gaps as the corresponding capture run, at **1920×1080**.

The 20 ordered capture runs map to the 20 same-numbered recipes. Scene geometry and typography are authored as C++ vector shapes and text. Eight new image assets were generated for photographic and illustration elements: `generated_archival_meeting_v1.png`, `generated_creator_portrait_v1.png`, `generated_witness_interview_v1.png`, `generated_neon_figure_v1.png`, `generated_cyan_evidence_figure_v1.png`, `generated_amber_archive_chair_v1.png`, `generated_red_archive_figure_v1.png`, and `generated_stargate_globe_v1.png`. They are independent assets, not crops of reference PNGs.

## PowerPoint-style typewriter with scramble + glow

`powerpoint_typewriter_glow.cpp` is a standalone, unnumbered tool. It reveals a
sentence left to right the way a PowerPoint typewriter does, but every slot that
has not settled yet flickers through random keyboard characters. Each settled
glyph pops in oversized, springs back to its final size and keeps a soft cyan
glow; a block cursor blinks while the sentence decodes. Text is centered, wrapped to the frame and scaled
to fit, so any phrase can be passed in.

```powershell
.\build_typewriter_glow.ps1
.\build_typewriter_glow.ps1 --text "La verita non e mai troppo tardi" --seconds 4 --fps 60
.\build_typewriter_glow.ps1 --text "CIAO" --out C:\renders\ciao_typewriter
```

Options are `--text`, `--seconds` (default 3.2), `--fps` (default 30) and `--out`
(default `out/powerpoint_typewriter_glow`). Frames are 1920x1080 and named
`frame_0001.png`, ready for `ffmpeg -framerate <fps> -i frame_%04d.png ...`.

## Review artifacts

Reference and generated opening, middle, and ending frames are compared in `artifacts/youtuberstle_rebuild_v1/`. The render manifest records output dimensions, counts, and asset origin.

## Fidelity note

The reference folder contains rendered video captures, not the original project layers, newspaper source scans, channel screen captures, or production footage. The render is a native C++ reconstruction of their visible designs and timing. Photo elements are newly generated, and fine source details therefore cannot be pixel-identical to the unavailable original layers.
