#!/usr/bin/env python3
"""Place models, heuristic extraction and Nominatim geocoding for map tools.

This module deliberately depends only on the Python standard library so the
text-to-place pipeline can be tested without loading OpenCV or tile renderers.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from geo_catalog import GeographicCatalog


NOMINATIM_MIN_INTERVAL_SECONDS = 1.0
_GEOCODE_TIMEOUT_SECONDS = 12
_GEOCODE_CACHE_VERSION = 1
_GEOCODE_LOCK = Lock()
_LAST_GEOCODE_REQUEST = 0.0


def _geocode_cache_path() -> Path:
    configured = os.environ.get("CHRONON_GEOCODE_CACHE")
    if configured:
        return Path(configured).expanduser()
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_home / "chronontemplate" / "nominatim_geocodes.v1.json"


def _load_geocode_cache(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if (not isinstance(payload, dict)
            or payload.get("version") != _GEOCODE_CACHE_VERSION
            or not isinstance(payload.get("entries"), dict)):
        return {}
    return payload["entries"]


def _save_geocode_cache(path: Path, entries: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"version": _GEOCODE_CACHE_VERSION, "entries": entries},
                         ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(payload)
            output.write("\n")
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


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


def _catalog_region_center(geometry: dict) -> tuple[float, float] | None:
    """Return the ADM1 boundary bounding-box center in lon/lat."""
    coordinates = geometry.get("coordinates", [])
    if geometry.get("type") == "Polygon":
        polygons = [coordinates]
    elif geometry.get("type") == "MultiPolygon":
        polygons = coordinates
    else:
        return None
    points = [point for polygon in polygons for ring in polygon for point in ring
              if isinstance(point, list) and len(point) >= 2]
    if not points:
        return None
    longitudes = [float(point[0]) for point in points]
    latitudes = [float(point[1]) for point in points]
    return ((min(latitudes) + max(latitudes)) / 2.0,
            (min(longitudes) + max(longitudes)) / 2.0)


def geocode(place: Place, language: str = "it", *, offline_only: bool = False,
            catalog_path: str | Path | None = None, catalog=None) -> Place:
    """Resolve from the checked-in gazetteer first, then optionally Nominatim.

    Global/localized exact city names, unique ADM1 region names and country
    names/capitals are resolved offline. Set ``offline_only`` to prohibit
    network fallback entirely (also available as ``CHRONON_GEOCODE_OFFLINE``).
    """
    owns_catalog = catalog is None
    if catalog is None:
        try:
            catalog = GeographicCatalog(catalog_path) if catalog_path else GeographicCatalog()
        except FileNotFoundError:
            catalog = None

    unresolved_ambiguous_query = False
    if catalog is not None:
        try:
            city = catalog.exact_city(place.query)
            if city:
                place.display_name = ", ".join(
                    value for value in (city["name"], city.get("region_name"), city["country_iso2"])
                    if value)
                place.lat = float(city["latitude"])
                place.lon = float(city["longitude"])
                place.ok = True
                print(f"  [geocode] {place.query} -> {city['name']} "
                      f"({place.lat:.5f}, {place.lon:.5f}) [offline catalog]", flush=True)
                return place

            regions = catalog.find_regions(place.query, include_geometry=True)
            country_candidates = catalog.countries_by_name(place.query)
            country = country_candidates[0] if len(country_candidates) == 1 else None
            # Names shared by an ADM1 region and a country (e.g. Georgia) are
            # ambiguous without explicit context; do not guess a fly-to target
            # or send the unresolved query to an online geocoder.
            region_country_collision = bool(regions and country_candidates)
            if regions and (len(regions) != 1 or region_country_collision):
                unresolved_ambiguous_query = True
            if unresolved_ambiguous_query:
                place.ok = False
                print(f"  [geocode] {place.query}: NOT FOUND [offline catalog; ambiguous]", flush=True)
                return place

            if len(regions) == 1 and regions[0].get("geometry"):
                center = _catalog_region_center(regions[0]["geometry"])
                if center:
                    place.lat, place.lon = center
                    place.display_name = f"{regions[0]['name']}, {regions[0]['country_iso2']}"
                    place.ok = True
                    print(f"  [geocode] {place.query} -> {place.display_name} "
                          f"({place.lat:.5f}, {place.lon:.5f}) [offline ADM1]", flush=True)
                    return place

            if country and country.get("capital"):
                capital = catalog.exact_city(country["capital"], country_iso2=country["iso2"])
                if capital:
                    place.lat = float(capital["latitude"])
                    place.lon = float(capital["longitude"])
                    place.display_name = f"{country['name']} ({capital['name']})"
                    place.ok = True
                    print(f"  [geocode] {place.query} -> {place.display_name} "
                          f"({place.lat:.5f}, {place.lon:.5f}) [offline country]", flush=True)
                    return place
        finally:
            if owns_catalog:
                catalog.close()

    offline_only = offline_only or os.environ.get("CHRONON_GEOCODE_OFFLINE", "").casefold() in {
        "1", "true", "yes", "on"
    }
    if offline_only:
        print(f"  [geocode] {place.query}: NOT FOUND [offline catalog]", flush=True)
        return place

    """Resolve remote-only places with Nominatim, persistent cache and 1 req/s."""
    global _LAST_GEOCODE_REQUEST
    normalized_query = " ".join(place.query.casefold().split())
    cache_key = json.dumps([normalized_query, language.casefold()], ensure_ascii=False,
                           separators=(",", ":"))
    cache_path = _geocode_cache_path()
    with _GEOCODE_LOCK:
        entries = _load_geocode_cache(cache_path)
        if cache_key in entries:
            row = entries[cache_key]
            if row is not None:
                place.display_name = str(row["display_name"])
                place.lat, place.lon = float(row["lat"]), float(row["lon"])
                place.ok = True
                print(f"  [geocode] {place.query} -> {place.display_name.split(',')[0]} "
                      f"({place.lat:.5f}, {place.lon:.5f}) [cache]", flush=True)
            else:
                print(f"  [geocode] {place.query}: NOT FOUND [cache]", flush=True)
            return place

        remaining = NOMINATIM_MIN_INTERVAL_SECONDS - (time.monotonic() - _LAST_GEOCODE_REQUEST)
        if _LAST_GEOCODE_REQUEST and remaining > 0:
            time.sleep(remaining)
        query = urllib.parse.urlencode({"q": place.query, "format": "json", "limit": 1,
                                        "accept-language": language})
        request = urllib.request.Request(
            f"https://nominatim.openstreetmap.org/search?{query}",
            headers={"User-Agent": "ChrononGeoCameraRuntime/1.0"})
        _LAST_GEOCODE_REQUEST = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=_GEOCODE_TIMEOUT_SECONDS) as response:
                rows = json.load(response)
        except Exception as exc:  # transient errors must not poison persistent cache
            print(f"  [geocode] {place.query}: UNREACHABLE ({exc})", flush=True)
            return place

        if not rows:
            entries[cache_key] = None
            _save_geocode_cache(cache_path, entries)
            print(f"  [geocode] {place.query}: NOT FOUND", flush=True)
            return place
        row = rows[0]
        place.display_name = str(row["display_name"])
        place.lat, place.lon = float(row["lat"]), float(row["lon"])
        place.ok = True
        entries[cache_key] = {"display_name": place.display_name,
                              "lat": place.lat, "lon": place.lon}
        _save_geocode_cache(cache_path, entries)
        print(f"  [geocode] {place.query} -> {place.display_name.split(',')[0]} "
              f"({place.lat:.5f}, {place.lon:.5f})", flush=True)
        return place


__all__ = ["Place", "Tour", "extract_places", "geocode"]
