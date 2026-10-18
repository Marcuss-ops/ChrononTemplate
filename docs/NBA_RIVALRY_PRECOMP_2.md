# NBA Rivalry Precomp 2.0

## Scene contract

- **Subject and assets:** The existing Paul Pierce and LeBron James archival photos, each with a cream photo mat and its own small, softened red pushpin; corkboard background.
- **Composition:** 1920×1080 corkboard. The two photo-and-pin groups begin separated and readable, then meet as one centered layered precomp with a visible paper edge.
- **Motion and timing:** 8 seconds at 30 fps. Present the two photo and pin layers separately, animate each pin onto its photo, move both cards into a single stack, then swing the camera to a steep three-quarter side view and return to a readable front view.
- **Layers and source:** Existing local photos, corkboard, and pushpin assets plus a flat cream matte image. Chronon's render plan animates the image, matte, and pushpin layers in a single composition and encodes the MP4 directly; no Python or external video compositor.
- **Must not appear:** Browser UI, unrelated text, extra photographs, or unexplained graphics.
- **Preview acceptance:** Opening shows both separate cards; middle shows the cards joining; ending shows the photo stack's offset paper edges during the camera turn and a stable readable final frame. Inspect opening, middle, and ending decoded video frames for framing and visible change.
