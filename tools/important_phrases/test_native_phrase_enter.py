#!/usr/bin/env python3
"""Contract: the native phrase lowering uses the shared two-second entrance.

The C++ header ImportantPhrasePack.hpp defines kPhraseEnterFrames. The Python
lowering in emit_native_phrase_pack.py must default to the same value when a
motion does not declare its own `enter`. Both are pinned here so the two
producers cannot drift apart again.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import emit_native_phrase_pack as emitter  # noqa: E402

HEADER = ROOT / "include/chronontemplate/important_phrases/ImportantPhrasePack.hpp"

failures = 0
checks = 0


def check(condition: bool, what: str) -> None:
    global failures, checks
    checks += 1
    if condition:
        print(f"  [OK] {what}")
    else:
        failures += 1
        print(f"  [FAIL] {what}")


def header_enter_frames() -> int:
    text = HEADER.read_text(encoding="utf-8")
    match = re.search(r"kPhraseEnterFrames\s*=\s*(\d+)\s*;", text)
    if not match:
        raise SystemExit(f"kPhraseEnterFrames not found in {HEADER}")
    return int(match.group(1))


def main() -> int:
    print("== native phrase entrance default")
    shared = header_enter_frames()
    check(shared == 60, f"the C++ shared entrance is 60 frames (found {shared})")

    recorded: list[int] = []
    original = emitter.extended_keyframes

    def recorder(track, duration, enter):  # type: ignore[no-untyped-def]
        recorded.append(enter)
        return original(track, duration, enter)

    emitter.extended_keyframes = recorder
    try:
        motion = {
            "tracks": [
                {
                    "property": "opacity",
                    "easing": "linear",
                    "keyframes": [{"frame": 0, "value": 0}, {"frame": 8, "value": 1}],
                }
            ]
        }
        emitter.lower_motion(motion, 300)
    finally:
        emitter.extended_keyframes = original

    check(bool(recorded), "lower_motion lowers at least one track")
    check(all(value == shared for value in recorded),
          f"a motion without `enter` lowers with the shared entrance {shared} "
          f"(recorded {recorded})")

    print(f"\n{checks} checks, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
