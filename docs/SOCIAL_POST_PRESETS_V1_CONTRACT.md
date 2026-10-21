# Social Post Presets V1

## Scope

Deliver two native, editable compositions: `web.x.post.v1` and
`web.youtube.community_post.v1`. Keep the existing generic `SocialPostCard`
API working while the new shared spec and platform resolvers are introduced.

## Scene contract

- **Subject and fields:** One X post and one YouTube Community post. Both use
  editable author/display name, handle or channel, timestamp, multiline body,
  avatar path, optional attached image, interaction counts, and an optional
  semantic highlighted phrase. X additionally has an optional verified mark.
  V1 shows comment/reply counts as platform metadata; full comment cards and
  nested quote/thread posts remain separate variants.
- **Composition:** Static 16:9 render at 1920×1080, with one recognizable
  platform card centered in an uncluttered neutral surround. X uses its dark
  timeline palette and the avatar/name/handle row, body, attached media, time,
  and interaction bar. YouTube Community uses its light surface, channel row,
  body, attached media, and like/comment controls. Layout dimensions derive
  from content and shaped line metrics rather than character-count estimates.
- **Camera and coordinates:** Front-facing 1920×1080 canvas, center origin for
  composition transforms, with top-left pixel coordinates in resolved text
  layout. No camera motion in the composition approval preview.
- **Layers and sources:** Native Chronon shape, text, and image layers only.
  Text stays independently editable. Avatars and attached images remain image
  layers. Text wrapping and highlight spans use `WebTextLayout` and the
  Chronon3D text shaper callback.
- **Must not appear:** Browser chrome, screenshot-only posts, unrelated
  platform controls, clipped text/media, invented reactions or counts, or
  motion/effects before the static composition is approved.
- **Preview approval:** Render one representative light YouTube and dark X
  composition at 854×480 (or closest supported size). Both must show plausible
  platform hierarchy, readable multiline text, an optional image, interaction
  metadata, and a correctly placed highlight. Inspect the actual render before
  adding motion, camera work, DOF, or further effects.

## Asset inspection

Before choosing sample assets, record dimensions, orientation, alpha, and
renderer compatibility. User-supplied media paths are preserved verbatim in
image layers. Sample mockup accounts and values are fictional and are labeled
as mock content in the showcase.

The showcase uses `assets/images/people_sample_portrait_b.png` (1254×1254,
square RGB, no alpha; center-cropped into a circular avatar) and
`assets/images/investigative_journalist_hero.jpg` (1376×768, landscape RGB,
no alpha; cover-fitted to the attached media frame). Both loaded successfully
through the Chronon3D software compositing path. They are existing repository
assets; no external assets were added.

## Delivery

Native preset specs and layout resolvers, unit coverage for wrapping and span
geometry, a showcase plan, and an inspected static preview contact sheet. After
composition approval, add reusable camera and motion recipes in a separate
stage.

The current review images are rendered at 854×480 from one-frame native
Chronon render plans. The preview accounts and engagement numbers are fictional
mock data. The scene contract targets 1920×1080 for production composition;
this review pass uses the requested smaller preview size.
