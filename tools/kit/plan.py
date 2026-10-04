"""RenderPlan V3 authoring: one Plan builder instead of per-script scaffolding.

The dict shapes mirror the canonical `chronon.render-plan.v3` contract used by
the handwritten suite scripts (field names and key order included, so plans
written through the kit stay diff-stable against the originals). `track()`
compresses the repetitive keyframe blocks that dominated every script.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

SCHEMA = "chronon.render-plan.v3"
SCHEMA_VERSION = 3


@dataclass(frozen=True)
class Canvas:
    width: int = 1920
    height: int = 1080
    fps: int = 30
    duration_frames: int = 150

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "fps_num": self.fps,
            "fps_den": 1,
            "duration_frames": self.duration_frames,
        }


def track(property: str, easing: str, *keys: tuple[int, float]) -> dict:
    """One animation track from (frame, value) pairs.

    Example:
        track("scale", "in_out_cubic", (0, 0.92), (24, 1.0), (149, 1.0))
    """
    return {
        "property": property,
        "easing": easing,
        "keyframes": [{"frame": frame, "value": value} for frame, value in keys],
    }


def fade(easing: str, *keys: tuple[int, float]) -> dict:
    """Alias for opacity tracks (reads better in preset tables)."""
    return track("opacity", easing, *keys)


@dataclass
class Plan:
    """One render plan: canvas + output + the layers being authored."""

    job_id: str
    canvas: Canvas
    output_path: Path
    layers: list[dict] = field(default_factory=list)

    # -- layer builders -----------------------------------------------------

    def color_layer(
        self,
        layer_id: str,
        rgba: Sequence[float],
        start_frame: int = 0,
        duration_frames: int | None = None,
    ) -> dict:
        layer = {
            "id": layer_id,
            "type": "color",
            "color": list(rgba),
            "start_frame": start_frame,
            "duration_frames": duration_frames or self.canvas.duration_frames,
        }
        self.layers.append(layer)
        return layer

    def image_card(
        self,
        layer_id: str,
        asset: str,
        size: Sequence[int],
        position: Sequence[float],
        tracks: Iterable[dict] = (),
        *,
        radius: float = 0.0,
        fit: str = "cover",
        enable_3d: bool = True,
        start_frame: int = 0,
        duration_frames: int | None = None,
    ) -> dict:
        layer = {
            "id": layer_id,
            "type": "image",
            "asset": asset,
            "size": list(size),
            "position": list(position),
            "radius": float(radius),
            "fit": fit,
            "enable_3d": enable_3d,
            "start_frame": start_frame,
            "duration_frames": duration_frames or self.canvas.duration_frames,
            "animation": {"tracks": list(tracks)},
        }
        self.layers.append(layer)
        return layer

    def text_card(self, layer_id: str, text: str, *, size: Sequence[int],
                  position: Sequence[float], font: str, font_size: float,
                  fill: str = "#FFFFFF", fit_mode: str | None = None,
                  glow: dict | None = None, tracks: Iterable[dict] = (),
                  start_frame: int = 0,
                  duration_frames: int | None = None) -> dict:
        """Text layer per the multi_phrase/entity_presentation contract:
        styling lives in `style` (fill is hex, never an rgba list)."""
        style: dict = {"font": font, "font_size": float(font_size), "fill": fill}
        if fit_mode:
            style["fit_mode"] = fit_mode
        if glow:
            style["glow"] = dict(glow)
        layer = {
            "id": layer_id,
            "type": "text",
            "text": text,
            "position": list(position),
            "size": list(size),
            "style": style,
            "start_frame": start_frame,
            "duration_frames": duration_frames or self.canvas.duration_frames,
            "animation": {"tracks": list(tracks)},
        }
        self.layers.append(layer)
        return layer

    def layer(self, raw: dict) -> dict:
        """Escape hatch: append a fully hand-authored layer dict."""
        self.layers.append(raw)
        return raw

    # -- output -------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "version": SCHEMA_VERSION,
            "job_id": self.job_id,
            "canvas": self.canvas.to_dict(),
            "output": {
                "path": str(self.output_path),
                "format": "mp4",
                "codec": "h264",
            },
            "layers": self.layers,
        }
