# Archival cards: one-command workflow

The archival card pack is authored in ChrononTemplate and rendered by the
Chronon3D Release CLI. Use the Release build with Vulkan support.

From the repository root, render all three examples with:

```sh
python3 ChrononTemplate/tools/single_images/render_archival_cards_chronon.py
```

The command incrementally builds the ChrononTemplate emitter and writes the
RenderPlans. Chronon composes the frames on Vulkan; FFmpeg then encodes the
NV12 frame stream with NVIDIA NVENC. The synchronized handoff avoids the
intermittent black frames seen with direct native-surface encoding. The
command fails if NVENC is unavailable; it does not fall back to CPU encoding.
Each scene also gets a quiet 18-frame entrance dissolve, with the photographs
kept registered in place. The output is decoded and checked for black-frame
dropouts before replacing the prior MP4.

Outputs are written to
`ChrononTemplate/out/archival_cards_refs_v2/`. Render one recipe with
`--only archival_torn_paper_portrait`, choose another CLI with `--cli PATH`,
or change the build folder with `--build-dir PATH`.

The scenes use still-photo assets and separate Chronon layers for paper,
frames, text, and restrained film dust. They do not add camera zooms or pan
motion. A scene that needs moving historical footage must supply a video asset;
the film-projection example here demonstrates the archival presentation
around its supplied still image.
