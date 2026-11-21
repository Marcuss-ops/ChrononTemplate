# ChrononPlugin map previews in ChrononTemplate

This bridge makes the existing ChrononPlugin map showcase clips selectable from
ChrononTemplate's render-plan workflow. The clip is decoded as a video layer by
Chronon3D. The map effect itself is still authored by ChrononPlugin; this does
not claim a native ChrononTemplate implementation of the effect.

## Browse and render

From the workspace root:

```bash
python3 ChrononTemplate/tools/map/preview_chrononplugin_maps_v1.py --list
python3 ChrononTemplate/tools/map/preview_chrononplugin_maps_v1.py --preset editorial_connection_arc --render
```

The first command prints each selectable ID, Plugin animation ID, and title.
Replace the preset ID in the second command to preview another effect in the
Chronon3D runtime. Plans are written to
`ChrononTemplate/out/chrononplugin_map_previews_v1/`; rendered MP4s land there
too. Use `--all-plans` to emit plans for every available sample, or
`--all-plans --render` to render the whole gallery.

## Coverage and limits

The catalog covers every animation ID in
`ChrononPlugin/plugins/maps/maps-renderer-catalog.v1.json`: 26 IDs, including
route line and multi-leg (using the existing Tuscany ticket renders), plus
geographic examples, GPU variants, six editorial styles, and three basemap
looks. Samples are verified at 1920x1080 and at most 10 seconds when plans are
generated. The weak Firenze–Pisa route-line clip is retained as a labelled
baseline so it is not mistaken for the quality target.

The showcase MP4s are generated artifacts under `ChrononPlugin/out`. If one is
missing after cleaning build outputs, regenerate the relevant Plugin showcase
first. To make an effect editable/generated natively in ChrononTemplate, its
map shader/geometry/motion still needs a separate renderer implementation.
