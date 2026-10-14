#!/usr/bin/env python3
"""Read-only API for the offline global geography catalog."""
from __future__ import annotations

import gzip
import json
import pathlib
import sqlite3
from typing import Any

DEFAULT_CATALOG = pathlib.Path(__file__).resolve().parents[2] / "catalog" / "geographic_catalog.v1.sqlite"


class GeographicCatalog:
    """Indexed continent -> country -> ADM1 region -> city lookups."""

    def __init__(self, path: str | pathlib.Path = DEFAULT_CATALOG):
        self.path = pathlib.Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(
                f"Geographic catalog not found: {self.path}. "
                "Build it with tools/map/build_geographic_catalog.py."
            )
        self._db = sqlite3.connect(f"file:{self.path.resolve()}?mode=ro", uri=True)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys=ON")

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> "GeographicCatalog":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    @property
    def metadata(self) -> dict[str, Any]:
        return {row["key"]: json.loads(row["value"])
                if row["value"].startswith(("{", "[")) or row["value"] in ("true", "false", "null")
                else row["value"]
                for row in self._db.execute("SELECT key,value FROM metadata ORDER BY key")}

    def continents(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._db.execute(
            "SELECT code,name,geoname_id FROM continents ORDER BY name")]

    def countries_by_name(self, query: str) -> list[dict[str, Any]]:
        value = " ".join(query.casefold().split())
        return [dict(row) for row in self._db.execute(
            "SELECT iso2,iso3,iso_numeric,name,capital,continent_code,geoname_id "
            "FROM countries WHERE lower(name)=? ORDER BY iso2", (value,)
        )]

    def country_by_name(self, query: str) -> dict[str, Any] | None:
        rows = self.countries_by_name(query)
        return rows[0] if len(rows) == 1 else None

    def countries(self, continent: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
        sql = ("SELECT iso2,iso3,iso_numeric,name,capital,continent_code,geoname_id "
               "FROM countries WHERE 1=1")
        params: list[Any] = []
        if continent:
            sql += " AND continent_code=?"; params.append(continent.upper())
        if query:
            sql += " AND name LIKE ?"; params.append(f"%{query}%")
        sql += " ORDER BY name COLLATE NOCASE"
        return [dict(row) for row in self._db.execute(sql, params)]

    def regions(self, country_iso2: str, query: str | None = None,
                include_geometry: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT geoname_id,country_iso2,admin1_code,code,name,ascii_name,boundary_geojson_gzip FROM regions WHERE country_iso2=?"
        params: list[Any] = [country_iso2.upper()]
        if query:
            sql += " AND (name LIKE ? OR ascii_name LIKE ?)"; params.extend((f"%{query}%", f"%{query}%"))
        sql += " ORDER BY name COLLATE NOCASE"
        result = []
        for row in self._db.execute(sql, params):
            item = dict(row)
            geometry = item.pop("boundary_geojson_gzip")
            if include_geometry and geometry:
                item["geometry"] = json.loads(gzip.decompress(geometry))
            result.append(item)
        return result

    def find_regions(self, query: str, include_geometry: bool = False) -> list[dict[str, Any]]:
        """Find ADM1 regions by exact official/ASCII name across countries."""
        value = " ".join(query.casefold().split())
        rows = self._db.execute(
            "SELECT geoname_id,country_iso2,admin1_code,code,name,ascii_name,"
            "boundary_geojson_gzip FROM regions "
            "WHERE lower(name)=? OR lower(ascii_name)=? ORDER BY country_iso2,code",
            (value, value),
        )
        result = []
        for row in rows:
            item = dict(row)
            geometry = item.pop("boundary_geojson_gzip")
            if include_geometry and geometry:
                item["geometry"] = json.loads(gzip.decompress(geometry))
            result.append(item)
        return result

    def exact_city(self, query: str, country_iso2: str | None = None) -> dict[str, Any] | None:
        """Resolve an exact official/ASCII/alternate city name conservatively."""
        value = " ".join(query.casefold().split())
        sql = (
            "SELECT c.geoname_id,c.name,c.ascii_name,c.alternate_names,c.country_iso2,"
            "c.admin1_code,r.name AS region_name,c.latitude,c.longitude,c.population,c.feature_code "
            "FROM cities c LEFT JOIN regions r ON r.geoname_id=c.region_geoname_id "
            "WHERE (c.name_key=? OR c.ascii_name_key=? OR c.alternate_names_key LIKE ?)"
        )
        params: list[Any] = [value, value, f"%|{value}|%"]
        if country_iso2:
            sql += " AND c.country_iso2=?"
            params.append(country_iso2.upper())
        rows = [dict(row) for row in self._db.execute(sql, params)]
        if not rows:
            return None
        capitals = [row for row in rows if row["feature_code"] == "PPLC"]
        if len(capitals) == 1:
            return capitals[0]
        if len(capitals) > 1:
            return None
        if len(rows) == 1:
            return rows[0]
        return None

    def cities(self, query: str | None = None, country_iso2: str | None = None,
               region_code: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 10000:
            raise ValueError("limit must be between 1 and 10000")
        sql = ("SELECT c.geoname_id,c.name,c.ascii_name,c.alternate_names,c.country_iso2,c.admin1_code,"
               "r.name AS region_name,c.latitude,c.longitude,c.population,c.feature_code "
               "FROM cities c LEFT JOIN regions r ON r.geoname_id=c.region_geoname_id WHERE 1=1")
        params: list[Any] = []
        if country_iso2:
            sql += " AND c.country_iso2=?"; params.append(country_iso2.upper())
        if region_code:
            sql += " AND r.code=?"; params.append(region_code.upper())
        if query:
            # Rank exact/localized aliases above substring matches, then prefer
            # official city seats and population for useful video label results.
            value = " ".join(query.casefold().split())
            escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            sql += " AND (c.name_key LIKE ? ESCAPE '\\' OR c.ascii_name_key LIKE ? ESCAPE '\\' OR c.alternate_names_key LIKE ?)"
            params.extend((f"%{escaped}%", f"%{escaped}%", f"%|{value}|%"))
        sql += (" ORDER BY CASE WHEN c.name_key=? OR c.ascii_name_key=? "
                "OR c.alternate_names_key LIKE ? OR c.alternate_names LIKE ? THEN 0 ELSE 1 END, "
                "CASE WHEN c.feature_code IN ('PPLC','PPLA','PPLA2','PPLA3','PPLA4') THEN 0 ELSE 1 END, "
                "c.population DESC,c.name COLLATE NOCASE LIMIT ?")
        if query:
            value = " ".join(query.casefold().split())
            params.extend((value, value, f"%|{value}|%", f"%{query.strip()}%"))
        else:
            params.extend(("", "", "", ""))
        params.append(limit)
        return [dict(row) for row in self._db.execute(sql, params)]

    def city_by_geoname_id(self, geoname_id: int) -> dict[str, Any] | None:
        rows = self._db.execute(
            "SELECT c.geoname_id,c.name,c.ascii_name,c.alternate_names,c.country_iso2,c.admin1_code,"
            "r.name AS region_name,c.latitude,c.longitude,c.population,c.feature_code "
            "FROM cities c LEFT JOIN regions r ON r.geoname_id=c.region_geoname_id "
            "WHERE c.geoname_id=?", (int(geoname_id),)).fetchone()
        return dict(rows) if rows else None


__all__ = ["DEFAULT_CATALOG", "GeographicCatalog"]
