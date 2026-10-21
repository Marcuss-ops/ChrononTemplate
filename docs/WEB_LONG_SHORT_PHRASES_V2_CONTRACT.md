# Web + Long/Short Phrases Web 2.0 + Highlighting Edition

## Scene contract

- **Subject:** a contemporary editorial web page that supports both long article context and short, high-impact phrases.
- **Composition:** 16:9 page canvas, editorial masthead and article columns for the complete-page shots; centered phrase on a clean plate for short-phrase shots. The long-phrase focus shot holds the key phrase sharp while surrounding context recedes in blur.
- **Camera:** fixed frontal 2D composition through the canonical render-plan canvas; 1920×1080, 30 fps. No 3D model assets or camera move are required for these typography-led scenes.
- **Motion:** page/highlight variants use the native WebPageHighlightPack timing; short variants use the native ShortPhrasePack timing and stagger. Web clips are 240 frames (8 s); short clips are 210 frames (7 s).
- **Layers:** Web background/page, masthead/navigation, article headline and metadata, article/body text, highlight marker and context text are authored as separate render-plan layers. Short phrases use a color plate plus an independently animated text layer.
- **Must not appear:** browser chrome or screenshots, substitute photos/models, clipping, missing text, or unrelated transitions.
- **Approval preview:** representative 854×480 frames must show the long headline in sharp focus with surrounding context visibly softened and the short phrase fully readable, centered, and unclipped. Contact sheet: `out/web_long_short_v2/contact_sheet.png`.

## Included animation set

The renderer script emits the native plan families and renders a compact selection:

1. Complete editorial page, light theme.
2. 3D headline highlight, dark theme.
3. Long-phrase blur focus, light theme.
4. Short-phrase baseline rise.
5. Short-phrase contrast sweep.
6. Short-phrase kinetic center build.

The underlying packs expose six Web plans (three recipes × two themes) and 27 short-phrase recipes. The six clips above are the representative export set; the other plans remain available in `out/web_long_short_v2/plans/`.

## Assets and compatibility

- Web typography uses the bundled Inter faces in `assets/fonts/`.
- The short-phrase modern recipes requested `Bricolage-Grotesque.ttf`, which is absent from this checkout. Their emitted plans use the bundled `Inter-Bold.ttf` instead. The weight and sans-serif character are retained; the specific Bricolage letterforms are not.
- A subset of short recipes references `assets/images/short_phrase_dark.png` or `short_phrase_light.png`, which are also absent. The selected showcase recipes use native color layers and do not depend on those files. Recipes that reference the missing plates are emitted but are not part of this render set.
- No external imagery or model assets are used.

## Render and review

From the ChrononTemplate root, run:

```bash
tools/web_presets/render_web_long_short_v2.sh
```

The script renders through Chronon3D's software backend by default, writes NV12 raw frames, encodes once with ffmpeg/libx264, and verifies H.264, 1920×1080, 30 fps, and exact frame count with ffprobe. Set `CHRONON_BACKEND=vulkan` to select Vulkan when available.

Inspect opening, middle, and ending frames from each MP4 before treating the delivery as complete. The still preview PNGs from Chronon3D are not pixel-truth outputs; the contact sheet is extracted from raw-video renders.
