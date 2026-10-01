# Location map data

## Checked-in map base alternatives

All three assets in `catalog/maps/` are raster crops of the same geographic extent (longitude -100°…50°, latitude 8°…72°), prepared at 1480 × 630 for the current 16:9 location scenes. They are retained as interchangeable bases; the comparison canary uses the same boundaries, Paris pin, labels, framing, and timing for each.

- `natural_earth_hypso_relief_water.jpg` — Natural Earth 1:10m Cross-Blended Hypsometric Tints with shaded relief and water. Source package: `HYP_LR_SR_W`; public domain.
  Source: https://www.naturalearthdata.com/downloads/10m-raster-data/10m-cross-blend-hypso/
- `natural_earth_landcover_relief_water.jpg` — Natural Earth 1:10m Natural Earth I land cover with shaded relief and water. Source package: `NE1_LR_LC_SR_W`; public domain.
  Source: https://www.naturalearthdata.com/downloads/10m-raster-data/10m-natural-earth-1/
- `nasa_blue_marble_august.jpg` — NASA Blue Marble: Next Generation, August 2004 (Terra/MODIS), cropped from its 21,600 × 10,800 cloud-free global composite. NASA describes source imagery at 500 m resolution and makes it freely available.
  Source: https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/

## Geographic overlays

Country boundaries come from Natural Earth Admin 0 Countries, 1:50m GeoJSON, public domain.
Source: https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-0-countries-2/

The map renderer uses an equirectangular crop spanning longitude -100°…50° and latitude 8°…72°. Pins, routes, fills, and boundaries share that projection. The perspective canary applies one homography to both the map and its geographic overlays.
