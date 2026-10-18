# Reference article styles

## Scene contract

- **Subjects:** Two recreated web article looks based on user-provided screenshots: a dark, tilted sports article with a blurred basketball image, and a bright serif article page with blurred surrounding copy and a yellow highlighted passage.
- **Title cards:** Each article transitions to a black frame with its related YouTube title centered in white. The NBA title uses bold italic sans serif; the synthetic-weed title uses a restrained serif treatment.
- **Composition:** 1920×1080, full frame. No browser chrome, playback controls, cursor, red pin, or unrelated imagery. The supplied screenshot is the source for the blurred NBA header crop; article filler is recreated as editable SVG text.
- **Motion and timing:** Two 8-second, 30 fps clips. The article holds for about 3.5 seconds, then crossfades to the centered title over 0.4 seconds and holds to the end.
- **Layers and source:** The article and title are separate SVG-authored raster assets, used as separate Chronon image layers. `build_reference_article_previews.mjs` regenerates the assets and native render plans.
- **Preview acceptance:** The NBA page must read as a dark sports article with slanted panel and header photo. The chemistry page must read as a light article excerpt with legible serif text and yellow highlighting. Each title must be centered on pure black and fit without clipping.
- **Delivery:** `NBA_Article_and_Title_Chronon.mp4` and `Chemistry_Article_and_Title_Chronon.mp4` in the user's `Altri_video` folder. Chronon Vulkan renderer, 1920×1080, H.264, 30 fps, 8 seconds each.

## Source notes

The visual content in the screenshots was supplied by the user. The NBA header crop comes from the supplied screenshot. The body copy and design elements are recreated for visual matching and are not claimed as a complete transcription of either source article.
