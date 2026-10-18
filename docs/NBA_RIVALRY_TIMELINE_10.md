# NBA Rivalry Timeline: ten players

## Scene contract

- **Subject and assets:** Ten different players from the Boston Celtics–Miami Heat playoff rivalry: Paul Pierce, LeBron James, Kevin Garnett, Dwyane Wade, Ray Allen, Chris Bosh, Rajon Rondo, Udonis Haslem, Kendrick Perkins, and Shane Battier. Reuse the existing Pierce and James photos; source the other eight from Wikimedia Commons and retain attribution/license records.
- **Composition and camera:** Existing corkboard fills frame as a blurred, softened background. One archival photo card takes the foreground at a time. Each has a cream mat, dark paper edge, and player-name caption; no red pins or markers. Camera drifts continuously right and changes yaw/pitch at regular intervals while keeping the active card legible.
- **Motion and timing:** 20 seconds at 30 fps. Ten cards appear in order, each holds in the foreground, then settles into an offset pile as the next enters. The ending turns the full pile to show its layered edges.
- **Layers and source:** One Chronon3D render plan animates the background, ten independent 3D card layers, and the camera. Still card images are authored from each photo before rendering. Chronon renders the complete animation and writes the H.264 MP4 directly; there is no external video compositor.
- **Must not appear:** Red pushpin, browser UI, extra players, simultaneous featured photos, unrelated copy, or an unblurred background.
- **Preview acceptance:** Opening clearly shows player 1; samples at each card change show the next player in the foreground; ending shows all ten accumulated as a layered stack in a three-quarter view. Inspect representative decoded video frames for player visibility, order, camera motion, and blur.

## Photo sources and licenses

- Paul Pierce — Keith Allison, CC BY-SA 2.0: https://commons.wikimedia.org/wiki/File:Paul_Pierce_2008-01-13.jpg
- LeBron James — Keith Allison, CC BY-SA 2.0: https://commons.wikimedia.org/wiki/File:Lbjheat_cropped.jpg
- Kevin Garnett — Keith Allison, CC BY-SA 2.0: https://commons.wikimedia.org/wiki/File:Kevin_Garnett_2008.jpg
- Dwyane Wade — Keith Allison, CC BY-SA 2.0: https://commons.wikimedia.org/wiki/File:D_Wade_jump_shot_Dec_21_2011.jpg
- Ray Allen — Keith Allison, CC BY-SA 2.0: https://commons.wikimedia.org/wiki/File:Ray_Allen_2008-01-13.jpg
- Chris Bosh — scott mecum, CC BY 2.0: https://commons.wikimedia.org/wiki/File:Chris_Bosh_%288293734477%29.jpg
- Rajon Rondo — Aaron Frutman, CC BY 2.0: https://commons.wikimedia.org/wiki/File:Rajon_Rondo_Media_Day.jpg
- Udonis Haslem — Keith Allison, CC BY-SA 2.0: https://commons.wikimedia.org/wiki/File:Udonis_Haslem.jpg
- Kendrick Perkins — Terren in Virginia, CC BY 2.0: https://commons.wikimedia.org/wiki/File:Kendrick_Perkins_dunk.jpg
- Shane Battier — scott mecum, CC BY 2.0: https://commons.wikimedia.org/wiki/File:Shane_Battier_Heat_2012.jpg

The existing Pierce and LeBron source photos are reused. The other eight images are bundled in `assets/nba_rivalry/players/`; finished individual card PNGs are in `assets/nba_rivalry/cards/`. The blurred background and card artwork are static PNG assets. All ten card layers, their stacking motion, the camera moves, and H.264 encoding run in the Chronon3D render plan.
