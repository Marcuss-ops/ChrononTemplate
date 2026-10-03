# Chronon Signature Visuals v1

These two RenderPlan V3 canaries are built by `tools/build_signature_visuals_v1.py`.
They use Chronon's current 3D text and perspective camera path support.

- **Anamorphic Typography** solves each glyph position along its own camera ray.
  At frame 110 the camera reaches the authored alignment pose and the word reads
  `CHRONON`; the later camera push breaks the alignment again.
- **Powers of Ten** hands off through ten camera-relative coordinate bands. Each
  band reuses local scene coordinates, while its physical scale label stays in
  scene metadata. The values describe representative scales, not a simulation
  of one world spanning atomic to astronomical coordinates.

Regenerate the plans with:

```sh
python3 ChrononTemplate/tools/build_signature_visuals_v1.py
```

Render the two scenes serially on Chronon's Vulkan backend with:

```sh
python3 ChrononTemplate/tools/build_signature_visuals_v1.py --render
```
