# Web Evidence Highlight V1

## Scene contract

- **Subject:** a contemporary editorial article page introducing the 1972 Munich Olympic attack, with one key phrase called out in a yellow marker.
- **Composition:** light paper background, understated masthead, bold two-line headline, byline, article text and a single readable highlighted excerpt. Frame the article as a designed web page, not a browser screenshot.
- **Camera:** frontal 16:9 render-plan canvas, 1920×1080 at 30 fps; preserve the existing canonical camera and coordinate convention in `WebPageHighlightPack`.
- **Motion:** one controlled push-in and a single left-to-right marker reveal. Keep surrounding article copy stable and legible. First approval preview is a representative frame after the marker has completed.
- **Layers:** paper, navigation, headline, article text, highlight shape and highlighted text remain separate render-plan layers.
- **Must not appear:** browser chrome, unrelated sports content, substitute photos, clipped text, extra highlights, gratuitous transitions or unreviewed cinematic effects.
- **Approval preview:** 854×480 representative frame showing the complete headline and highlighted excerpt clearly, with the yellow marker behind the intended words. Do not build the full animation or add extra effects until this composition is approved.

## Assets and source

- Use bundled ChrononTemplate fonts and native text/shape layers; no external image or model assets.
- Render through Chronon3D's existing CLI/backend. The plan should remain editable JSON with separate layers.

## Delivery evidence

- Preview image and, after approval, a contact sheet with opening, middle and ending frames.
- Record backend, resolution, frame rate, duration, asset sources and any renderer limitation.
