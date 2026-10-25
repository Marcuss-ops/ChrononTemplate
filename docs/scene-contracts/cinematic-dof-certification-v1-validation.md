# Cinematic Depth of Field Certification V1 — Validation

Contract: `cinematic-dof-certification-v1.md`. All outputs are under `out/cinematic_dof_v1/`.

## Hardware and build

- CPU: AMD Ryzen 7 5800X, 8 cores / 16 threads.
- Chronon3d CLI rebuilt from current source (`Chronon3d/.tmp/cli`). `CHRONON3D_ENABLE_VULKAN=OFF`.
- Vulkan: not compiled into this build. Only the `llvmpipe` CPU driver is present on the host, so there is no hardware GPU.

## Results

| Item | Result |
| --- | --- |
| 150-frame 30 fps 1920×1080 animated focus, all ten layers | Rendered (`cinematic_dof_v1_150.rgba`, 1,244,160,000 bytes = 150 × 1920×1080×4), encoded to `cinematic_dof_v1_150.mp4` (H.264, 1920×1080, 30/1, 150 frames). |
| Linear focus across the ten distances | `camera_samples[0..149]`, focus 450 → 2250 (see `cinematic_dof_v1.plan.json`). |
| Deterministic random access | Frames 149, 37 and 0 rendered individually in shuffled order with `--video-sink raw`. Each is byte-identical (SHA-256) to the same frame in the chronological run. A full second render of the hero plan is also byte-identical to the first (full-file SHA-256 match). |
| Software vs Vulkan parity | **Not verified.** `--backend vulkan` (strict) fails with `no backend satisfies preference=gpu`. Reported as a limitation, not a software fallback. |
| Second scene: three overlapping transparent objects | Rendered 150 frames, focus 600 → 1800 (`cinematic_dof_overlap_v1.mp4`, 150 frames). |
| f-stop 0.7 / 2.8 / 8 at same focus and blur cap | Rendered 150 frames each (`fstop_0_7.mp4`, `fstop_2_8.mp4`, `fstop_8_0.mp4`). Frame 75 differs across the three; f/0.7 matches the hero render at frame 75 (same SHA-256). `fstop_compare_f75.png` shows the side-by-side. |

## Performance (CPU only, `/usr/bin/time`)

| Render | Frames | Wall time | Peak RSS |
| --- | --- | --- | --- |
| Hero, animated focus (rerun) | 150 | 41.2 s | 2.88 GB |
| Overlap scene | 150 | 17.9 s | 2.86 GB |
| f-stop 0.7 | 150 | 39.5 s | 2.89 GB |
| f-stop 2.8 | 150 | 25.6 s | 2.88 GB |
| f-stop 8 | 150 | 21.2 s | 3.01 GB |

GPU time and VRAM are not reported because there is no GPU backend. Allocation counts were not collected.

## Output files

- Plans: `cinematic_dof_v1.plan.json`, `cinematic_dof_overlap_v1.plan.json`, `fstop_0_7.plan.json`, `fstop_2_8.plan.json`, `fstop_8_0.plan.json`.
- MP4: `cinematic_dof_v1_150.mp4`, `cinematic_dof_overlap_v1.mp4`, `fstop_0_7.mp4`, `fstop_2_8.mp4`, `fstop_8_0.mp4`.
- Frames: `frames/frame_{000,030,060,090,120,149}.png`, `frames_overlap/frame_{000,075,149}.png`.
- Contact sheet: `contact_sheet.png` (every 25th frame of the hero MP4). F-stop comparison: `fstop_compare_f75.png`.
- Determinism logs: `determinism/`.

## Limitations

- **Vulkan parity is not verified.** Vulkan is OFF in the build and no GPU exists on the host. The strict backend selection fails as expected.
- **Encoding path.** The in-process FFmpeg sink fails to open for H.264 in this build, so the MP4s were encoded from the raw RGBA output with the system `ffmpeg` (libx264, CRF 18, yuv420p). `render_mp4.log` is from the failed in-process attempt.
- **Visual quality of the blur is not certified here.** Premultiplied-alpha edge handling, halo or colour bleed, bokeh shape and occlusion between overlapping transparent planes are not measured by this report. The contract leaves visual review to the user.
- **The `T16` reference plan** (`validate` on the existing reference plan) still fails schema validation. This is pre-existing and was not changed.
- **The f-stop test is a single frame check.** The determinism test covers three frames; the f-stop comparison is confirmed at frame 75 only.

## Reproduction

```bash
cd ChrononTemplate
python3 tools/focus_plane_stack/build_cinematic_dof_v1.py
CLI=../Chronon3d/.tmp/cli/apps/chronon3d_cli/chronon3d_cli
ROOT=$(realpath ..)
$CLI render --plan out/cinematic_dof_v1/cinematic_dof_v1.plan.json --start-frame 0 --end-frame 149 --video-sink raw --assets-root $ROOT -o out/cinematic_dof_v1/cinematic_dof_v1_150.rgba
ffmpeg -f rawvideo -pix_fmt rgba -s 1920x1080 -r 30 -i out/cinematic_dof_v1/cinematic_dof_v1_150.rgba -c:v libx264 -pix_fmt yuv420p -crf 18 out/cinematic_dof_v1/cinematic_dof_v1_150.mp4
```
