#!/usr/bin/env python3
"""Kit contract test: the shared authoring helpers emit the canonical plan
shapes without needing the CLI or a GPU.

Guards the properties the first kit conversion (multi_image_trio_v1) was
byte-diff-verified against, so a later refactor of tools/kit cannot silently
change emitted plan bytes or the standard CLI arguments.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from kit import Canvas, Plan, Suite, SuiteItem, fade, track  # noqa: E402
from kit.plan import SCHEMA, SCHEMA_VERSION  # noqa: E402

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  [OK] {name}")
    else:
        failures.append(f"{name}{': ' + detail if detail else ''}")
        print(f"  [FAIL] {name} {detail}")


# ---------------------------------------------------------------------------
# 1. canvas -> canonical canvas dict
# ---------------------------------------------------------------------------
canvas = Canvas(width=1920, height=1080, fps=30, duration_frames=150)
check("canvas dict", canvas.to_dict() == {
    "width": 1920, "height": 1080, "fps_num": 30, "fps_den": 1,
    "duration_frames": 150,
})

# ---------------------------------------------------------------------------
# 2. track()/fade() -> canonical track dict
# ---------------------------------------------------------------------------
t = track("scale", "in_out_cubic", (0, 0.92), (24, 1.0))
check("track dict", t == {
    "property": "scale", "easing": "in_out_cubic",
    "keyframes": [{"frame": 0, "value": 0.92},
                  {"frame": 24, "value": 1.0}],
})
check("fade property", fade("out_cubic", (0, 0.0), (18, 1.0))["property"]
      == "opacity")

# ---------------------------------------------------------------------------
# 3. plan -> canonical RenderPlan V3 document (key order + defaults)
# ---------------------------------------------------------------------------
plan = Plan(job_id="kit_canary", canvas=canvas,
            output_path=Path("/tmp/kit_canary/kit_canary.mp4"))
bg = plan.color_layer("bg", (0.03, 0.04, 0.07, 1.0))
card = plan.image_card(
    "card", "assets/images/card_trio_1.png", (500, 680), [-540, 0],
    [track("position_x", "out_cubic", (0, 540), (24, 0)),
     fade("in_out_cubic", (0, 0.0), (18, 1.0))],
)
doc = plan.to_dict()

check("schema fields", doc["schema"] == SCHEMA and doc["version"] == SCHEMA_VERSION)
check("plan key order",
      list(doc.keys()) == ["schema", "version", "job_id", "canvas", "output",
                           "layers"])
check("output dict", doc["output"] == {
    "path": "/tmp/kit_canary/kit_canary.mp4", "format": "mp4", "codec": "h264"})
check("bg layer", bg == {
    "id": "bg", "type": "color", "color": [0.03, 0.04, 0.07, 1.0],
    "start_frame": 0, "duration_frames": 150})
check("card key order",
      list(card.keys()) == ["id", "type", "asset", "size", "position",
                            "radius", "fit", "enable_3d", "start_frame",
                            "duration_frames", "animation"])
check("card values", card["radius"] == 0.0 and card["fit"] == "cover"
      and card["enable_3d"] is True)

# serialized bytes are stable (no trailing newline, indent=2)
serialized = json.dumps(doc, indent=2)
check("serialization stable", serialized.endswith("}")
      and "\n  \"schema\"" in serialized)

# ---------------------------------------------------------------------------
# 4. text layer per the multi_phrase/entity_presentation contract
# ---------------------------------------------------------------------------
text = plan.text_card(
    "t", "HELLO", size=(900, 42), position=(960, 330),
    font="assets/fonts/Inter-Bold.ttf", font_size=22, fill="#B4A99B",
    fit_mode="shrink_only",
    glow={"color": "#38BDF8", "intensity": 0.55, "radius": 16},
)
check("text style block", text["style"] == {
    "font": "assets/fonts/Inter-Bold.ttf", "font_size": 22.0,
    "fill": "#B4A99B", "fit_mode": "shrink_only",
    "glow": {"color": "#38BDF8", "intensity": 0.55, "radius": 16}})
check("text has no color/align keys", "color" not in text and "align" not in text)

# ---------------------------------------------------------------------------
# 5. Suite wiring: one item per name, builders callable
# ---------------------------------------------------------------------------
suite = Suite(
    name="kit_contract", out_dir=Path("/tmp/kit_contract"),
    items=[SuiteItem("a", lambda: plan), SuiteItem("b", lambda: plan)],
)
check("suite items", [i.name for i in suite.items] == ["a", "b"]
      and all(callable(i.build) for i in suite.items))

# ---------------------------------------------------------------------------
print()
if failures:
    print(f"kit contract: {len(failures)} FAILURE(S)")
    raise SystemExit(1)
print("kit contract: PASS")
