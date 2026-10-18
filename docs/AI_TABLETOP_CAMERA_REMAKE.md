# AI tabletop camera remake

## Scene contract

- **Subject and assets:** four newly generated, original 16:9 illustrations of Japanese historical imagery: (1) sepia ink-and-watercolor Kyoto temple on a torn parchment, (2) richly colored woodblock print of a lone samurai crossing a rainy bridge, (3) close-up of lacquered samurai armor and a katana on dark wood, (4) monochrome sumi-e battle scene with a restrained vermilion accent. No source-video frames or source video texture are used.
- **Composition and camera:** four separate image cards sit on a dark wooden tabletop in world space. A perspective `CameraRig` starts over the parchment card and moves between cards with a slow push-in, lateral drift, a short diagonal/roll move, then a final close push. Keep the image plane edges, tabletop and spatial separation visible where the reference move reveals them. Render 1920x1080, 30 fps, about 8.7 s.
- **Motion and timing:** approximate the reference's slow push over the parchment for the opening, drift/zoom toward the next printed image, then a more pronounced diagonal transition and close framing on the final monochrome artwork. Animate camera position, target, roll and FOV through ChrononMotion3D `CameraRig`; the four cards remain separate 3D planes so parallax is real.
- **Layers and source:** four independent generated PNG image layers plus a procedural dark tabletop/background. The supplied MP4 is reference-only for shot rhythm and is not sampled, mapped or included as an output layer. No added text or audio.
- **Must not appear:** captured browser/player chrome, cursor, source video frames, copied reference pictures, titles or captions.
- **Preview acceptance:** an inspected 854x480 frame must show original generated artwork on the tabletop, without player UI; opening, transition and final frames must show a visible camera move and different artwork. The approved final is a 1920x1080 H.264 MP4.

## Camera convention

Follow the repository render-plan convention: pixel-like XY positions use top-left origin, render-plan camera looks toward +Z after converting from Motion's local -Z forward. Units are scene units (pixel-equivalent on image-card dimensions); camera FOV/near/far and card transforms are stored in the generated plan.
