# NBA Web long and short phrase redo

## Scene contract

- **Subjects and source assets:** Two already-rendered NBA article web compositions. Kuminga uses the 1920×1080 RGB page plate `out/web_article_fold/static_page.png` and bundled Inter fonts. Mark Cuban uses `out/reference_article_styles/nba_article_preview.png`, the existing web article image with its embedded hero photograph, plus bundled fonts. Preserve the article copy, masthead, photo, and established color treatment in each source.
- **Composition:** Kuminga is a straight-on white article page centered over a softly defocused charcoal surround. Mark Cuban is a slightly tilted dark article card with a wide photo header, headline, byline, and blurred body copy. Both remain full-frame 16:9 web scenes.
- **Camera and coordinate convention:** 1920×1080 screen composition, top-left image origin for the raster plates. No new 3D camera or model transforms; keep each existing article plate's framing and transforms.
- **Motion and timing:** Four clips, each 8 seconds at 30 fps. Hold the article page for about 3.3 seconds, fade the page to black, then fade in the centered phrase and its quiet underline. Hold the completed title through the end. This follows the approved NBA article-to-title clips. Long phrases use two centered lines; short phrases use one.
- **Layers and sources:** Preserve the two original article plates. Add the Kuminga headline to the reserved headline area in its plate. Composite a separate black title card in the approved bold italic NBA style, then encode H.264 with FFmpeg.
- **Must not appear:** The prior on-page fold/marker treatments, generic text-only opening, replacement NBA photos, browser controls, clipping, or new paper/grain treatments.
- **Preview acceptance:** The first section must clearly show the corresponding NBA article; the ending must show the long or short phrase centered and fully readable on black. Inspect the opening, transition, title hold, and ending for every clip.

## Existing approved references

- Kuminga article fold: `out/web_article_fold/review/contact.png` and `out/web_article_fold/Web_Article_Fold_Title_1080p.mp4`.
- Mark Cuban article web page: `out/reference_article_styles/review/nba_contact.png` and `out/reference_article_styles/rendered/NBA_Article_and_Title_Chronon.mp4`.

## Delivery

Four H.264 MP4s at 1920×1080, 30 fps, 240 frames each, plus `review_v2/contact_sheet.png` showing the opening, hold, transition, title, and ending. Verify frame counts with ffprobe and confirm temporal change from decoded frames. The Mark Cuban hero photo is the already embedded screenshot crop in `nba_header_photo.png`; do not replace it.
