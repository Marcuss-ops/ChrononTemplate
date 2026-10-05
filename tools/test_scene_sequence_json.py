#!/usr/bin/env python3
"""scene_sequence_json contract test.

The pre-configured camera maps are data (`scene_camera_sequences_v1/*.json`),
authored by `chronontemplate_sequence_from_json`. This test pins the tool's
contract without needing the CLI or a GPU:

  1.  a good map parses and emits `id total` plus exactly `total` pose rows;
  2.  the rows are the camera grammar: the first hold rests on the phrase
      framing (fov 50, aimed at the centre), the travel moves the pose, the
      final hold rests on the text framing (fov 44);
  3.  the catalog maps in scene_camera_sequences_v1/ all parse;
  4.  the loud failures: unknown schema, unknown transition, unknown kind,
      one beat, hold below six frames, non-finite geometry, malformed JSON —
      each exits non-zero with a message on stderr.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
CATALOG = TOOLS.parent / "catalog/scene_camera_sequences_v1"

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  [OK] {name}")
    else:
        failures.append(f"{name}{': ' + detail if detail else ''}")
        print(f"  [FAIL] {name} {detail}")


def run_tool(tool: Path, document: dict | None, json_text: str | None = None,
             extra_id: str | None = None) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        handle.write(json_text if json_text is not None else json.dumps(document))
        path = handle.name
    command = [str(tool), path]
    if extra_id:
        command += ["--id", extra_id]
    return subprocess.run(command, capture_output=True, text=True)


def parse_rows(stdout: str) -> tuple[str, int, list[list[float]]]:
    lines = stdout.strip().splitlines()
    seq_id, total = lines[0].split()
    rows = [[float(v) for v in line.split()] for line in lines[1:]]
    return seq_id, int(total), rows


GOOD_MAP = {
    "schema": "chronontemplate.scene-camera-sequence.v1",
    "name": "json_canary",
    "transition": "scene_camera_arc_carry",
    "intensity": 1.0,
    "travel_frames": 24,
    "in_frame": 0,
    "beats": [
        {"kind": "phrase", "center": [960, 540, 0], "half_width": 520, "half_height": 110,
         "hold": 60},
        {"kind": "image", "center": [960, 540, -80], "half_width": 460, "half_height": 260,
         "hold": 60},
        {"kind": "text", "center": [960, 540, 0], "half_width": 620, "half_height": 150,
         "hold": 60},
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True, help="sequence_from_json binary path")
    args = parser.parse_args()
    tool = Path(args.tool)
    if not tool.is_file():
        print(f"FAIL: missing tool binary {tool}")
        return 1

    print("== a good map parses and emits the row contract")
    result = run_tool(tool, GOOD_MAP)
    check("tool exits 0", result.returncode == 0, result.stderr.strip())
    if result.returncode == 0:
        seq_id, total, rows = parse_rows(result.stdout)
        check("sequence id", seq_id == "json_canary", seq_id)
        check("total frames", total == 3 * 60 + 2 * 24, str(total))
        check("one row per frame", len(rows) == total, str(len(rows)))
        first = rows[0]
        check("first row is frame 0", first[0] == 0.0)
        check("first hold on the phrase lens (fov 50)", first[7] == 50.0, str(first[7]))
        check("first hold aims along +Z from the centre",
              abs(first[1] - 960.0) < 1e-3 and abs(first[2] - 540.0) < 1e-3 and first[3] > 0,
              str(first[1:4]))
        mid = rows[72]
        check("mid-travel leaves the first rest",
              abs(mid[3] - first[3]) > 1.0 or abs(mid[1] - first[1]) > 1.0)
        last = rows[total - 1]
        check("final hold on the text lens (fov 44)", last[7] == 44.0, str(last[7]))

    print("== --id overrides the sequence id")
    result = run_tool(tool, GOOD_MAP, extra_id="override_name")
    check("id override", result.returncode == 0 and result.stdout.startswith("override_name "),
          result.stdout.splitlines()[0] if result.stdout else "")

    print("== every catalog map parses")
    maps = sorted(CATALOG.glob("*.json"))
    check("three catalog maps exist", len(maps) == 3, str(len(maps)))
    for path in maps:
        result = run_tool(tool, None, json_text=path.read_text())
        ok = result.returncode == 0
        rows_ok = ok and len(result.stdout.strip().splitlines()) > 1
        check(f"{path.name} parses", rows_ok, result.stderr.strip())

    print("== the loud failures")
    bad_cases = {
        "unknown schema": lambda doc: {**doc, "schema": "something.else.v9"},
        "unknown transition": lambda doc: {**doc, "transition": "scene_camera_bogus"},
        "unknown kind": lambda doc: {**doc,
                                     "beats": [{**doc["beats"][0], "kind": "mascot"},
                                               *doc["beats"][1:]]},
        "one beat": lambda doc: {**doc, "beats": doc["beats"][:1]},
        "tiny hold": lambda doc: {**doc, "beats": [{**doc["beats"][0], "hold": 2},
                                                   *doc["beats"][1:]]},
        "non-finite centre": None,  # handled below via raw JSON text
    }
    for name, mutate in bad_cases.items():
        if mutate is None:
            continue
        result = run_tool(tool, mutate(GOOD_MAP))
        check(f"{name} exits 1", result.returncode == 1, str(result.returncode))
        check(f"{name} reports on stderr", "sequence_from_json:" in result.stderr)
    raw = GOOD_MAP.__str__().replace("'", '"').replace("True", "true").replace("960", "1e999", 1)
    result = run_tool(tool, None, json_text=raw)
    check("non-finite centre exits 1", result.returncode == 1, str(result.returncode))
    result = run_tool(tool, None, json_text="{not json")
    check("malformed json exits 1", result.returncode == 1, str(result.returncode))

    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall scene_sequence_json contract checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
