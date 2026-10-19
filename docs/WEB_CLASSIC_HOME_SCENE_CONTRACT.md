# Classic editorial home page — scene contract

## Scene

- **Subject:** A conventional editorial/news home page in two palette variants: light paper with dark ink, and dark paper with light ink.
- **Composition:** 1920×1080, 16:9, screen-space 2D. A compact masthead/navigation row sits above a two-column lead story. The left column holds section label, two-line headline, short summary and one call-to-action. The right column holds one large feature photograph. A “Latest” section below has three compact story rows/cards and a restrained footer. Keep generous margins, square corners and clear type hierarchy.
- **Camera:** None; fixed front-facing screen-space composition. No perspective tilt or camera move.
- **Motion plan (after composition approval):** 8 seconds at 30 fps. Reveal masthead/navigation first, then bring in the lead headline and summary, then the feature image; stagger the three lower stories in reading order. Settle into a static hold. Both themes use identical timing and geometry.
- **Layers and assets:** Separate native layers for page background, navigation, section label, headline, summary, button, image, latest-story cards, dividers and footer. Reuse the existing landscape JPEG `assets/images/investigative_journalist_hero.jpg` for the lead image after composition fit is checked; it is 1376×768, RGB, without alpha. No external assets or browser screenshot.
- **Must not appear:** Browser frame, address bar, cursor, controls, irrelevant imagery, extra display effects, cropped headline, or overlapping text.
- **Composition preview:** Render separate light and dark base frames at 854×480 before animation. Approval requires the lead image and all page regions to fit, the headline to remain readable, and the light/dark variants to share the same layout.

## Asset note

The hero JPEG is already present in the project. Its file contains no source/attribution record; preserve the original and carry that provenance limitation in the delivery notes unless a source record is found.
