# Date Timeline v1 scene contract

## Purpose

An independent documentary video scene that lays out every year in the
existing technology date-group sample on a classic horizontal timeline.

## Composition and camera

- 1920×1080 at 30 fps, screen-space 2D, no camera move or external assets.
- Warm ivory background, restrained charcoal typography, a short hairline rail
  (about 1,200 px on a 1920 px canvas), short stems and small neutral markers.
  No neon, gradients or decorative tech motifs.
- Ten milestone points span 1948–2026. Each point contains both dates from its
  source group, preserving all twenty years. Labels alternate above and below
  the rail to fit the full sequence.

## Motion and timing

- Ship ten selectable motion treatments: quiet fade, marker pop, alternating
  rise, short side slide, center-out reveal, traveling cursor, segment draw,
  paired wave, dates-first reveal, and soft cascade. Each preserves the same
  date data and minimal composition.
- Each milestone remains visible through the end.
- Total duration: 188 frames (6.27 seconds).

## Layers and source

- Background, rail, ticks, stems, labels and dates are native ChrononTemplate
  color and text layers.
- Milestone names and years reuse the sample in
  `tools/date_groups/emit_date_groups.cpp`.

## Must not appear

- No Fast Intro, portraits, logos, footage or invented calendar days.
- Do not omit any of the twenty sample year values.

## Preview acceptance

- A comparison sheet shows all ten variants; opening, middle and ending frames
  show an intentional, advancing timeline.
- All ten milestones and their paired dates remain inside the frame and
  legible; no black frame or missing subject.
