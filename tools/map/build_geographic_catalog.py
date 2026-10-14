#!/usr/bin/env python3
"""Build the checked-in YouTube map hierarchy SQLite catalog.

Sources are downloaded only when this explicit builder is run. Runtime tools use
geo_catalog.py and never need network access. Requires Python standard library.
"""
from __future__ import annotations

import datetime as dt
import gzip
import io
import json
import os
import pathlib
import sqlite3
import tempfile
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "catalog" / "geographic_catalog.v1.sqlite"
GEONAMES = "https://download.geonames.org/export/dump/"
NATURAL_EARTH_ADMIN1 = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_10m_admin_1_states_provinces.geojson"
)
USER_AGENT = "ChrononTemplateGeographicCatalog/1.0 (offline catalog builder)"
CONTINENTS = {
    "AF": "Africa", "AN": "Antarctica", "AS": "Asia", "EU": "Europe",
    "NA": "North America", "OC": "Oceania", "SA": "South America",
}
MIN_COUNTRIES = 245
MIN_REGIONS = 3500
MIN_CITIES = 200000
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE continents (
  code TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, geoname_id INTEGER NOT NULL UNIQUE
);
CREATE TABLE countries (
  iso2 TEXT PRIMARY KEY, iso3 TEXT NOT NULL UNIQUE, iso_numeric TEXT NOT NULL,
  name TEXT NOT NULL, capital TEXT NOT NULL DEFAULT '', continent_code TEXT NOT NULL,
  geoname_id INTEGER NOT NULL UNIQUE,
  FOREIGN KEY(continent_code) REFERENCES continents(code)
);
CREATE INDEX countries_name_idx ON countries(name COLLATE NOCASE);
CREATE TABLE regions (
  geoname_id INTEGER PRIMARY KEY, country_iso2 TEXT NOT NULL,
  admin1_code TEXT NOT NULL, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
  ascii_name TEXT NOT NULL, boundary_geojson_gzip BLOB,
  FOREIGN KEY(country_iso2) REFERENCES countries(iso2),
  UNIQUE(country_iso2, admin1_code)
);
CREATE INDEX regions_name_idx ON regions(name COLLATE NOCASE);
CREATE TABLE cities (
  geoname_id INTEGER PRIMARY KEY, name TEXT NOT NULL, ascii_name TEXT NOT NULL,
  name_key TEXT NOT NULL, ascii_name_key TEXT NOT NULL,
  alternate_names TEXT NOT NULL DEFAULT '',
  alternate_names_key TEXT NOT NULL DEFAULT '|',
  country_iso2 TEXT NOT NULL, admin1_code TEXT NOT NULL DEFAULT '',
  region_geoname_id INTEGER, latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90),
  longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
  population INTEGER NOT NULL DEFAULT 0, feature_code TEXT NOT NULL,
  FOREIGN KEY(country_iso2) REFERENCES countries(iso2),
  FOREIGN KEY(region_geoname_id) REFERENCES regions(geoname_id)
);
CREATE INDEX cities_name_key_idx ON cities(name_key);
CREATE INDEX cities_ascii_name_key_idx ON cities(ascii_name_key);
CREATE INDEX cities_country_region_idx ON cities(country_iso2, region_geoname_id);
"""


def fetch(url: str, timeout: int = 180) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def normalized_name(value: str) -> str:
    import unicodedata
    value = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(ch for ch in value if not unicodedata.combining(ch)).split())


def rows_from_text(data: bytes):
    for line in data.decode("utf-8").splitlines():
        if line and not line.startswith("#"):
            yield line.split("\t")


def load_admin1_boundaries():
    document = json.loads(fetch(NATURAL_EARTH_ADMIN1, timeout=240))
    boundaries = {}
    for feature in document.get("features", []):
        props = feature.get("properties", {})
        geoname_id = props.get("gn_id")
        if geoname_id in (None, -99, "-99"):
            continue
        boundaries.setdefault(str(geoname_id), []).append(feature.get("geometry"))
    # Only attach geometry if the GeoNames id identifies exactly one feature.
    return {key: value[0] for key, value in boundaries.items()
            if len(value) == 1 and value[0]}


def build(output: pathlib.Path = DEFAULT_OUTPUT) -> dict:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    country_rows = list(rows_from_text(fetch(GEONAMES + "countryInfo.txt")))
    admin1_rows = list(rows_from_text(fetch(GEONAMES + "admin1CodesASCII.txt")))
    cities_zip = zipfile.ZipFile(io.BytesIO(fetch(GEONAMES + "cities500.zip", timeout=240)))
    city_member = next(name for name in cities_zip.namelist() if name.endswith(".txt"))
    with cities_zip.open(city_member) as source:
        city_rows = [line.decode("utf-8").rstrip("\r\n").split("\t") for line in source]
    boundaries = load_admin1_boundaries()

    fd, temp_name = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    os.close(fd)
    temporary = pathlib.Path(temp_name)
    counts = {"continents": 0, "countries": 0, "regions": 0,
              "cities": 0, "regions_with_boundaries": 0, "cities_without_region": 0}
    try:
        db = sqlite3.connect(temporary)
        try:
            db.executescript(SCHEMA)
            for code, name, geoname_id in (
                ("AF", "Africa", 6255146), ("AN", "Antarctica", 6255152),
                ("AS", "Asia", 6255147), ("EU", "Europe", 6255148),
                ("NA", "North America", 6255149), ("OC", "Oceania", 6255151),
                ("SA", "South America", 6255150),
            ):
                db.execute("INSERT INTO continents VALUES (?,?,?)", (code, name, geoname_id))
            counts["continents"] = len(CONTINENTS)

            country_codes = set()
            for row in country_rows:
                if len(row) < 19:
                    continue
                iso2, iso3, numeric, _fips, name, capital = row[:6]
                continent, geoname_id = row[8], row[16]
                if continent not in CONTINENTS or not iso2 or not iso3:
                    continue
                country_codes.add(iso2)
                db.execute("INSERT INTO countries VALUES (?,?,?,?,?,?,?)",
                           (iso2, iso3, numeric, name, capital, continent, int(geoname_id)))
            counts["countries"] = len(country_codes)

            region_by_code = {}
            for row in admin1_rows:
                if len(row) < 4 or "." not in row[0]:
                    continue
                country, admin1 = row[0].split(".", 1)
                if country not in country_codes or not admin1:
                    continue
                geoname_id = int(row[3])
                geometry = boundaries.get(str(geoname_id))
                geometry_blob = (gzip.compress(json.dumps(
                    geometry, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), mtime=0)
                    if geometry else None)
                db.execute("INSERT INTO regions VALUES (?,?,?,?,?,?,?)",
                           (geoname_id, country, admin1, row[0], row[1], row[2], geometry_blob))
                region_by_code[row[0]] = geoname_id
                counts["regions"] += 1
                counts["regions_with_boundaries"] += geometry is not None

            city_batch = []
            for row in city_rows:
                if (len(row) < 19 or row[6] != "P" or row[7] == "PPLX"
                        or row[8] not in country_codes):
                    continue
                geoname_id, name, ascii_name = int(row[0]), row[1], row[2]
                country, admin1, feature_code = row[8], row[10], row[7]
                admin_key = f"{country}.{admin1}" if admin1 else ""
                region_id = region_by_code.get(admin_key)
                population = int(row[14] or 0)
                latitude, longitude = float(row[4]), float(row[5])
                if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    raise ValueError(f"Invalid WGS84 coordinates for GeoNames id {geoname_id}")
                alias_names = sorted({alias.strip() for alias in row[3].split(",")
                                      if alias.strip()})
                aliases = sorted({normalized_name(alias) for alias in alias_names})
                aliases_display = "|" + "|".join(alias_names) + "|"
                aliases_key = "|" + "|".join(aliases) + "|"
                city_batch.append((geoname_id, name, ascii_name, normalized_name(name),
                                   normalized_name(ascii_name), aliases_display, aliases_key, country, admin1,
                                   region_id, latitude, longitude, population, feature_code))
                if region_id is None:
                    counts["cities_without_region"] += 1
                if len(city_batch) >= 5000:
                    db.executemany("INSERT INTO cities VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", city_batch)
                    counts["cities"] += len(city_batch)
                    city_batch.clear()
            if city_batch:
                db.executemany("INSERT INTO cities VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", city_batch)
                counts["cities"] += len(city_batch)
            if (counts["countries"] < MIN_COUNTRIES or counts["regions"] < MIN_REGIONS
                    or counts["cities"] < MIN_CITIES):
                raise RuntimeError(f"Unexpectedly incomplete source data: {counts}")

            info = {
                "schema": "chronontemplate.geographic-hierarchy.v1",
                "built_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
                "city_source": "GeoNames cities500 (population > 500 or administrative seats down to PPLA4)",
                "city_source_retrieved": "daily dump",
                "country_region_source": "GeoNames countryInfo.txt and admin1CodesASCII.txt",
                "boundary_source": "Natural Earth 10m Admin 1 States/Provinces v5.1.1; matched by GeoNames gn_id",
                "crs": "OGC:CRS84 / WGS84 longitude-latitude; city coordinates stored as latitude, longitude",
                "license": "GeoNames CC BY 4.0; Natural Earth public domain",
                "attribution": "GeoNames (www.geonames.org); Natural Earth (www.naturalearthdata.com)",
                **counts,
            }
            db.executemany("INSERT INTO metadata VALUES (?,?)",
                           [(key, json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)
                            for key, value in info.items()])
            db.commit()
            db.execute("PRAGMA optimize")
        finally:
            db.close()
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return info


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2, ensure_ascii=False))
