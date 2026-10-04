# tools/kit — shared library for showcase suite scripts

One place for the scaffolding that every suite script used to copy-paste:
workspace/CLI discovery, render-plan authoring, the validate → render →
manifest → upload pipeline and the Drive upload helpers. A converted suite
script contains **only its creative content** (presets, timing, camera).

## Why

Measured on `tools/` (83 scripts, ~31k lines): 15 identical copies of
`refresh_drive_token`, 4 different CLI build directories hardcoded per script,
and a ~200-line main() per script for the same three-phase flow. A new suite
cost 500–1400 lines, of which ~60% was scaffold. The kit removes the scaffold.

## Modules

| Module | Replaces | Notes |
|---|---|---|
| `paths.py` | per-file `BASE_DIR` + CLI fallback chains | `VELOX_WORKSPACE` / `CHRONON_CLI` overrides; one candidate chain |
| `plan.py` | hand-rolled plan dicts | `Canvas`, `Plan`, `track()`, `fade()`; emits canonical `chronon.render-plan.v3` dicts, key order included |
| `pipeline.py` | the per-script three-phase `main()` | validate → parallel render (`--jobs`) → posters → manifest (with render timings) → Drive upload; resume with `--from PLAN`; `--validate-only` / `--plans-only` / `--render-only` / `--upload-only` / `--skip-upload` |
| `drive.py` | 15 copies of token refresh + upload | `refresh_token`, `upload_file`, `upload_many` (parallel) |

## Usage

```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from kit import Canvas, Plan, Suite, SuiteItem, fade, track

CANVAS = Canvas(width=1920, height=1080, fps=30, duration_frames=150)
OUT_DIR = Path(__file__).resolve().parents[1] / "out" / "my_suite_v1"

def build_hero() -> Plan:
    plan = Plan(job_id="hero", canvas=CANVAS,
                output_path=OUT_DIR / "hero.mp4")
    plan.color_layer("bg", (0.03, 0.04, 0.07, 1.0))
    plan.image_card("card", "assets/images/card_trio_1.png", (500, 680),
                    [-540, 0], [track("scale", "in_out_cubic",
                                      (0, 0.92), (24, 1.0), (149, 1.0))])
    return plan

SUITE = Suite(
    name="my_suite_v1",
    out_dir=OUT_DIR,
    drive_folder="<drive folder id>",   # optional; omit to never upload
    items=[SuiteItem("hero", build_hero)],
)

if __name__ == "__main__":
    from kit import run_suite
    raise SystemExit(run_suite(SUITE))
```

Run it:

```shell
python3 tools/render_my_suite_v1.py --plans-only          # write plans, no CLI
python3 tools/render_my_suite_v1.py --validate-only --cli ../Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli
python3 tools/render_my_suite_v1.py --jobs 2              # render + manifest
python3 tools/render_my_suite_v1.py --from hero --jobs 2  # resume after a plan
python3 tools/render_my_suite_v1.py --upload-only         # re-upload only
```

## Guarantees

- **Plan bytes are stable.** The first conversion (`multi_image_trio_v1`) was
  diff-verified byte-for-byte against the plans the handwritten script
  produced; `test_kit_contract.py` (registered in CTest) pins the shapes.
- **No renderer semantics here.** Validate/render are `chronon3d_cli`
  subprocesses; the kit only orchestrates them.
- **`--out` wins over the baked output path.** The runner redirects the
  plan's `output.path` when writing, so scratch/`--out` renders never leak
  into the suite's own directory.

## Converted suites

- `render_multi_image_trio_v1.py` (711 → 257 lines, presets unchanged)

Next candidates (same scaffold, different presets): `render_multi_image_quad_v1`,
`render_multi_image_penta_v1`, `render_image_frame_premium_v1`,
`render_multi_phrase_v1`.
