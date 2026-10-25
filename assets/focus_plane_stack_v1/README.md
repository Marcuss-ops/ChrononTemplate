# Focus Plane Stack V1 Assets

All source plates in `source_green/` were generated with ChatGPT Image for this camera-focus test. No external image sources were used. The plates are 1672×941 RGB with a uniform green background; the corresponding 854×480 RGBA files in `layers_rgba/` were chroma-keyed and despilled from these originals.

| Layer | Green-screen source | Keyed RGBA layer | Subject |
|---:|---|---|---|
| 01 | `source_green/01_kettle_mug.png` | `layers_rgba/01_kettle_mug.png` | Enamel kettle and mug |
| 02 | `source_green/02_compass_watch.png` | `layers_rgba/02_compass_watch.png` | Compass and pocket watch |
| 03 | `source_green/03_vase_stem.png` | `layers_rgba/03_vase_stem.png` | Blue ceramic vase and dried stem |
| 04 | `source_green/04_books_glasses.png` | `layers_rgba/04_books_glasses.png` | Burgundy books and reading glasses |
| 05 | `source_green/05_toy_robot_gears.png` | `layers_rgba/05_toy_robot_gears.png` | Toy robot and gears |
| 06 | `source_green/06_plant_stones.png` | `layers_rgba/06_plant_stones.png` | Terracotta pot, burgundy succulent and stones |
| 07 | `source_green/07_film_camera.png` | `layers_rgba/07_film_camera.png` | Film camera and canister |
| 08 | `source_green/08_citrus_bowl.png` | `layers_rgba/08_citrus_bowl.png` | Citrus bowl and spoon |
| 09 | `source_green/09_globe_telescope.png` | `layers_rgba/09_globe_telescope.png` | Globe and wooden telescope |
| 10 | `source_green/10_hourglass_key.png` | `layers_rgba/10_hourglass_key.png` | Hourglass, key and medallion |

The ten source subjects were generated as separate plates on green for this controlled test. The keying command used was:

```sh
ffmpeg -i source.png -vf \
  'despill=type=green:mix=0.8:expand=0.2,chromakey=0x00FF00:0.12:0.10,scale=854:480:flags=lanczos,format=rgba' \
  keyed.png
```
