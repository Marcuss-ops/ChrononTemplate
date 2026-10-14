#!/usr/bin/env python3
"""Place models, heuristic extraction and Nominatim geocoding for map tools.

This module deliberately depends only on the Python standard library so the
text-to-place pipeline can be tested without loading OpenCV or tile renderers.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Place:
    query: str                      # what the user wrote
    display_name: str = ""          # Nominatim's answer
    lat: float = 0.0
    lon: float = 0.0
    preset: str = "dive"            # dive | tilt | orbit | metric
    ok: bool = False

    @property
    def short_name(self) -> str:
        if not self.display_name:
            return self.query.upper()
        return self.display_name.split(",")[0].strip().upper()

    @property
    def subtitle(self) -> str:
        """A compact first locality component that fits the reveal card."""
        return (self.display_name or self.query).split(",")[0].strip().upper()[:36]


@dataclass
class Tour:
    text: str
    stops: list[Place] = field(default_factory=list)
    mp4: Path | None = None
    stats: list[dict] = field(default_factory=list)


_STOPWORDS = {
    "poi", "e", "ed", "infine", "quindi", "dopo", "con", "a", "al", "alla",
    "in", "nel", "nella", "da", "dal", "per", "tra", "fra", "su", "il", "lo",
    "la", "i", "gli", "le", "un", "uno", "una", "di", "del", "della", "dei",
    "delle", "che", "mostra", "voglio", "fare", "video", "tour", "poi-", "poi.",
}

# Lowercase name particles may connect adjacent capitalised place-name words.
# Tour connectors deliberately remain hard boundaries.
_INTERNAL_NAME_PARTICLES = {
    "di", "del", "dello", "della", "dei", "degli", "delle", "da", "dal",
    "dallo", "dalla", "dai", "dagli", "dalle", "in", "nel", "nello",
    "nella", "nei", "negli", "nelle", "sul", "sullo", "sulla", "sui",
    "sugli", "sulle", "of", "the",
}
_TOUR_WORDS = {"tour", "itinerario", "viaggio", "giro"}


def extract_places(text: str) -> list[Place]:
    """Extract place candidates from free Italian/English text, without an NLP model.

    Capitalised runs (or quoted names) are candidates; stop-words split runs,
    while lowercase particles can stay inside a name. Preset keywords attach to
    the preceding place, or to the next place if no place has been named yet.
    """
    text = text.replace("\u201c", "\"").replace("\u201d", "\"")
    quoted = re.findall(r'"([^\"]{2,60})"', text)
    for name in quoted:
        text = text.replace(f'"{name}"', " " + name.replace(" ", "_") + " ")

    tokens = re.findall(r"[A-Za-z_][A-Za-z_'\-]*|,", text)
    places: list[Place] = []
    run: list[str] = []
    pending_preset = "dive"

    def flush_run() -> None:
        nonlocal pending_preset
        if run:
            places.append(Place(query=" ".join(run), preset=pending_preset))
            run.clear()
            pending_preset = "dive"

    for index, token in enumerate(tokens):
        if token == ",":
            flush_run()
            continue
        low = token.lower().replace("_", " ")
        if low in ("tilt", "orbita", "orbit", "metric", "metrica"):
            flush_run()
            preset = ("tilt" if low == "tilt" else
                      "orbit" if low in ("orbita", "orbit") else "metric")
            if places:
                places[-1].preset = preset
            else:
                pending_preset = preset
            continue
        if low in _STOPWORDS or low in _TOUR_WORDS:
            next_is_name = (index + 1 < len(tokens)
                            and tokens[index + 1] != ","
                            and (tokens[index + 1][0].isupper() or "_" in tokens[index + 1]))
            if run and low in _INTERNAL_NAME_PARTICLES and next_is_name:
                run.append(low)
            else:
                flush_run()
            continue
        if token[0].isupper() or "_" in token:
            run.append(token.replace("_", " "))
        else:
            flush_run()
    flush_run()
    if pending_preset != "dive" and places:
        places[-1].preset = pending_preset
    return places


def geocode(place: Place, language: str = "it") -> Place:
    """Resolve one place with Nominatim, keeping failures as unresolved places."""
    query = urllib.parse.urlencode({"q": place.query, "format": "json", "limit": 1,
                                   "accept-language": language})
    request = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{query}",
        headers={"User-Agent": "ChrononGeoCameraRuntime/1.0"})
    try:
        rows = json.load(urllib.request.urlopen(request, timeout=12))
    except Exception as exc:  # offline: keep the place unresolvable
        print(f"  [geocode] {place.query}: UNREACHABLE ({exc})", flush=True)
        return place
    if not rows:
        print(f"  [geocode] {place.query}: NOT FOUND", flush=True)
        return place
    row = rows[0]
    place.display_name = row["display_name"]
    place.lat, place.lon = float(row["lat"]), float(row["lon"])
    place.ok = True
    print(f"  [geocode] {place.query} -> {place.display_name.split(',')[0]} "
          f"({place.lat:.5f}, {place.lon:.5f})", flush=True)
    return place


__all__ = ["Place", "Tour", "extract_places", "geocode"]
