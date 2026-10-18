# Web article title fold

## Scene contract

- **Subject:** A full-screen sports-news webpage, based on the supplied screenshot.
- **Composition:** A crisp white, straight-edged article page centered over a dark, softly defocused surround. The page has a small sports masthead, headline, byline and date, share/like row, blurred article copy, and a soft-focus recommendation card. The headline is the only large readable text.
- **Camera and coordinates:** Front-facing 1920×1080 page with a restrained 3.5% push-in over the shot; canvas origin is top-left for the prepared plate.
- **Motion and timing:** Eight seconds at 30 fps. The first headline line folds into view letter by letter; the second line follows after a short pause. Hold the complete headline for the remainder.
- **Layers and sources:** `generate_web_article_fold_background.py` authors the clean static page. `render_web_article_fold.py` composites the per-character vertical fold reveal and encodes H.264. The Chronon plan is an editable native scene alternative; its 3D text animation is not used for the delivered MP4 because the 1080p title path was too slow and did not match the compositor output.
- **Must not appear:** Aged or torn paper, archival film grain, browser window chrome, cursors or playback controls, readable filler paragraphs.
- **Preview acceptance:** Inspect 854×480 and full-resolution frames at the beginning, during both line reveals, and at the end. The page must read as a modern article site; the headline remains within the page and resolves cleanly; all supporting text stays defocused.

## Delivery

- MP4: `Web_Article_Fold_Title_1080p.mp4`, H.264, 1920×1080, 30 fps, 8 seconds.
- Editable scene and plate-grade plans plus assets: delivery `JSON` folder.
- Sampled-frame contact sheet and preview: delivery `Preview` folder.
- The delivered MP4 uses Pillow for the page artwork and per-glyph vertical-fold reveal, then FFmpeg for H.264 encoding. The Python animation is a 2D fold-style reveal, not a 3D page fold. No Chronon grade is claimed for this video.
