#!/usr/bin/env python3
"""Offline tests for the global hierarchy builder and reader."""
import gzip
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import build_geographic_catalog as builder
from geo_catalog import GeographicCatalog


class GeographicCatalogTests(unittest.TestCase):
    def _fixture_database(self, path: Path) -> None:
        db = sqlite3.connect(path)
        db.executescript(builder.SCHEMA)
        for code, name, geoname_id in (
            ("AF", "Africa", 6255146), ("AN", "Antarctica", 6255152),
            ("AS", "Asia", 6255147), ("EU", "Europe", 6255148),
            ("NA", "North America", 6255149), ("OC", "Oceania", 6255151),
            ("SA", "South America", 6255150),
        ):
            db.execute("INSERT INTO continents VALUES (?,?,?)", (code, name, geoname_id))
        db.execute("INSERT INTO countries VALUES (?,?,?,?,?,?,?)",
                   ("IT", "ITA", "380", "Italy", "Rome", "EU", 3175395))
        geometry = gzip.compress(json.dumps({"type": "Polygon", "coordinates": []}).encode(), mtime=0)
        db.execute("INSERT INTO regions VALUES (?,?,?,?,?,?,?)",
                   (3170831, "IT", "07", "IT.07", "Lazio", "Lazio", geometry))
        db.execute("INSERT INTO regions VALUES (?,?,?,?,?,?,?)",
                   (3170832, "IT", "09", "IT.09", "Lombardy", "Lombardy", None))
        db.execute("INSERT INTO cities VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (3169070, "Rome", "Rome", "rome", "rome", "|Roma|", "|roma|rome|",
                    "IT", "07", 3170831, 41.9028, 12.4964, 2873000, "PPLC"))
        db.execute("INSERT INTO cities VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (3169071, "Romano Banco", "Romano Banco", "romano banco", "romano banco",
                    "|Romano Banco|", "|romano banco|", "IT", "09", 3170832, 45.42309, 9.10707,
                    26163, "PPLA3"))
        db.executemany("INSERT INTO metadata VALUES (?,?)", [
            ("schema", "chronontemplate.geographic-hierarchy.v1"),
            ("crs", "OGC:CRS84 / WGS84"),
            ("cities", "1"),
        ])
        db.commit(); db.close()

    def test_hierarchy_and_city_query_are_offline(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog.sqlite"
            self._fixture_database(path)
            with GeographicCatalog(path) as catalog:
                self.assertEqual(len(catalog.continents()), 7)
                self.assertEqual(catalog.countries("EU")[0]["iso2"], "IT")
                self.assertEqual(catalog.regions("IT")[0]["code"], "IT.07")
                self.assertEqual(catalog.regions("IT", include_geometry=True)[0]["geometry"]["type"], "Polygon")
                city = catalog.cities("Roma", country_iso2="IT")[0]
                self.assertEqual(city["name"], "Rome")
                self.assertIn("Roma", city["alternate_names"])
                self.assertEqual(catalog.cities("rome", country_iso2="IT")[0]["name"], "Rome")
                self.assertEqual(catalog.cities("Roma", country_iso2="IT")[0]["geoname_id"], 3169070)
                self.assertAlmostEqual(city["latitude"], 41.9028)
                self.assertAlmostEqual(city["longitude"], 12.4964)
                self.assertEqual(catalog.city_by_geoname_id(3169070)["region_name"], "Lazio")
                self.assertEqual(catalog.metadata["cities"], "1")

    def test_builder_creates_parent_relationships_and_only_unique_boundaries(self):
        countries = "\t".join([
            "IT", "ITA", "380", "", "Italy", "Rome", "60", "3012300", "EU",
            ".it", "EUR", "Euro", "39", "IT###", "", "it", "3175395", "VA,SM", "",
        ]) + "\n"
        admin1 = "IT.07\tLazio\tLazio\t3170831\n"
        cities = (
            "\t".join([
                "3169070", "Rome", "Rome", "Roma,ROMA", "41.9028", "12.4964",
                "P", "PPLC", "IT", "", "07", "", "", "", "2873000", "",
                "21", "Europe/Rome", "2026-01-01",
            ]) + "\n"
            + "\t".join([
                "3164603", "Milano", "Milan", "Milano", "45.4642", "9.19",
                "P", "PPLA", "IT", "", "07", "", "", "", "1370000", "",
                "122", "Europe/Rome", "2026-01-01",
            ]) + "\n"
            + "\t".join([
                "9999999", "Quarter of Rome", "Quarter of Rome", "Quarter of Rome",
                "41.9", "12.5", "P", "PPLX", "IT", "", "07", "", "", "", "10000", "",
                "20", "Europe/Rome", "2026-01-01",
            ]) + "\n"
        ).encode()
        zipped = __import__("io").BytesIO()
        import zipfile
        with zipfile.ZipFile(zipped, "w") as archive:
            archive.writestr("cities500.txt", cities)
        responses = {
            builder.GEONAMES + "countryInfo.txt": countries.encode(),
            builder.GEONAMES + "admin1CodesASCII.txt": admin1.encode(),
            builder.GEONAMES + "cities500.zip": zipped.getvalue(),
        }
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "catalog.sqlite"
            with mock.patch.object(builder, "fetch", side_effect=lambda url, **_: responses[url]), \
                 mock.patch.object(builder, "MIN_COUNTRIES", 1), \
                 mock.patch.object(builder, "MIN_REGIONS", 1), \
                 mock.patch.object(builder, "MIN_CITIES", 1), \
                 mock.patch.object(builder, "load_admin1_boundaries", return_value={
                     "3170831": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 1], [0, 0]]]},
                     "should-not-match": {"type": "Polygon", "coordinates": []},
                 }):
                counts = builder.build(output)
            self.assertEqual(counts["countries"], 1)
            self.assertEqual(counts["regions"], 1)
            self.assertEqual(counts["regions_with_boundaries"], 1)
            self.assertEqual(counts["cities"], 2)
            with GeographicCatalog(output) as catalog:
                self.assertEqual(catalog.cities("Roma", country_iso2="IT")[0]["geoname_id"], 3169070)
                cities_found = catalog.cities(country_iso2="IT", region_code="IT.07", limit=10)

                self.assertEqual({row["name"] for row in cities_found}, {"Rome", "Milano"})
                region = catalog.regions("IT", include_geometry=True)[0]
                self.assertEqual(region["geometry"]["type"], "Polygon")

    def test_coordinate_bounds_and_limit_are_enforced(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog.sqlite"
            self._fixture_database(path)
            with GeographicCatalog(path) as catalog:
                with self.assertRaises(ValueError):
                    catalog.cities(limit=10001)
            db = sqlite3.connect(path)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO cities VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (2, "bad", "bad", "bad", "bad", "bad", "|bad|", "IT", "07", 3170831,
                            95, 200, 0, "PPL"))
            db.close()


if __name__ == "__main__":
    unittest.main()
