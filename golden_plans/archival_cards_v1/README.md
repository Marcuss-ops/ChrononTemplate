# Archival documentary cards v1

Four reusable 1920x1080, five-second scene recipes authored in
`single_images/ArchivalCardPack`. They are compositions of ChrononTemplate
image, shape, text and effect layers; no renderer or camera subsystem was added.

## Looks

| Look id | Composition | Main recipe |
| --- | --- | --- |
| `archival_torn_paper_portrait` | Torn Paper Portrait | Aged grid paper, stains, shadowed irregular white mat, graded portrait, caption and subtle grain/RGB split |
| `archival_archive_print` | Black & White Archive Print | Worn grey ground, dust, double black rule, paper mount, monochrome portrait, scratches and grain |
| `archival_vintage_film_projection` | Vintage Film Projection | Black ground, diffuse halo, rounded projection window, monochrome source, vignette, dust and scratches |
| `archival_double_portrait` | Double Portrait Archive | Parchment, paired irregular mounts, two sepia portraits, centered names and archive line |

## Build and emit plans

From the ChrononTemplate checkout:

```sh
cmake --build build --target chronontemplate_emit_archival_cards -j16
./build/chronontemplate_emit_archival_cards /tmp/archival-card-plans
```

This emits a `.plan.json` and a matching five-second `.mp4` destination for
each look. The plan assets use the bundled NASA portrait examples and the
Chronon3D Inter font. Replace the paths and labels through `ArchivalCardSpec`
for production work. They are illustrative stand-ins, not the source images
from the four visual references.

The delivered MP4 previews are 1920x1080 at 30 fps. Chronon rendered each
composed frame with the Vulkan backend; the short preview holds that frame and
adds a restrained editorial push in post. It demonstrates the compositing
recipes, rather than certifying the full authored layer animation. The
Chronon CLI's required native GPU video path and FFmpeg NVENC were unavailable
on the render host, so H.264 encoding used the software encoder. The source
still assets and the final frame should be replaced/reviewed for a production
cut.

Render a plan through Chronon3D with the repository root as the asset mount:

```sh
Chronon3d/build/chronon/linux-video-test/apps/chronon3d_cli/chronon3d_cli render \
  --plan /tmp/archival-card-plans/archival_torn_paper_portrait.plan.json \
  --assets-root /absolute/path/to/VeloxEditing \
  --backend software --profile preview \
  -o /tmp/archival_torn_paper_portrait.mp4
```

The current renderer's still-PNG lane does not compose text layers. Use an
encoded video frame for visual review until the still lane has pixel-truth text
composition. The JSON plans are useful for integration review, but do not claim
reference-matched golden PNG certification. In particular, authentic paper
textures and the exact source photographs still need to be supplied and
reviewed against the references.

## API

Include `chronontemplate/single_images/ArchivalCardPack.hpp`, select an
`ArchivalCardLook`, fill an `ArchivalCardSpec`, then call
`addArchivalCard(scene, look, spec)`. It returns the principal layer IDs so
callers can adjust timing. The geometry defaults target a 1920x1080 canvas;
labels, asset paths, dimensions, timing and centre can be customized per card.
