# NBA Rivalry Pushpin Recreation

## Scene contract

- **Subject and assets:** Two distinct web-sourced photographs of Paul Pierce and LeBron James on a textured corkboard, each presented as an aged print with a red pushpin.
- **Composition:** 1920×1080 full-frame corkboard. Pierce enters first near center, then moves left. LeBron's print enters from the right. The pushpins drop onto each print and settle with a small bounce. No titles, browser chrome, or unrelated UI.
- **Motion and timing:** 8 seconds at 30 fps (240 frames). Opening setup, first pin impact, second print and pin reveal, then hold on the two-photo layout.
- **Layers and source:** Chronon plan uses separate image layers for the board, photos, and pushpins, plus shape layers for paper mats and shadows. Sources and attribution are recorded below.
- **Preview acceptance:** Actual raw video frames at opening, middle, and ending must show the photos fully in frame, paper behind each photo, and pins attached to the prints. Confirm visible motion between these times.

## Assets and attribution

- Corkboard: generated texture at `assets/nba_rivalry/web/corkboard_bg.png`.
- Paul Pierce photo: Keith Allison, [Paul Pierce 2008-01-13](https://commons.wikimedia.org/wiki/File:Paul_Pierce_2008-01-13.jpg), CC BY-SA 2.0.
- LeBron James photo: Keith Allison, [Lbjheat cropped](https://commons.wikimedia.org/wiki/File:Lbjheat_cropped.jpg), CC BY-SA 2.0.
- Red pushpin: authored SVG, rasterized to PNG for Chronon image-layer use.

## Render

- Editable plan: `out/nba_rivalry/nba_rivalry_chronon.plan.json`.
- Chronon backend: software video render to raw YUV420P; this installed build does not expose an H.264 sink.
- MP4 encoding: FFmpeg/libx264, 1920×1080, 30 fps, 8 seconds.

## Final compositing note

The Chronon video compositor did not preserve the full-canvas board and matte/pin layering consistently across the animated frames, so it was not used for the delivered MP4. The final animation uses the same authored/project assets, with FFmpeg's overlay/rotate filters driven by the editable graph at `out/nba_rivalry/final.ffgraph`. The Chronon render plan is retained as the editable scene reference; the delivered pixels come from the FFmpeg graph.
