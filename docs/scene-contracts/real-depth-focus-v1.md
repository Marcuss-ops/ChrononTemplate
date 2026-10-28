# Real Depth Focus V1

## Scene

- Native ChrononTemplate C++ emitter: `tools/showcases/emit_real_depth_focus_v1.cpp`.
- 1920×1080, 30 fps, 180 frames (6 seconds), H.264 MP4.
- Three editable Inter Display text layers (`CAMERA`, `FOCUS`, `DEPTH`) occupy distinct Z planes. The C++ scene uses Chronon's animated physical camera focus, a small orbit, lens shift and restrained cyan text glow.
- The DOF kernel applies a dense Gaussian using each output pixel's CoC and passes the in-focus plane through unchanged. The refreshed MP4 was rendered with the software backend; Vulkan SPIR-V compiles and validates, but this local release binary currently fails while creating its `layer_batch` pipeline.
- RenderPlan: `out/real_depth_focus_v1/real_depth_focus_v1.plan.json`.
- MP4: `out/real_depth_focus_v1/real_depth_focus_v1.mp4`.

## Speaking list (Italian voice-over)

| Time | Voice-over |
|---|---|
| 0:00–0:02 | «La profondità non è uno zoom: è spazio reale.» |
| 0:02–0:04 | «La camera attraversa tre piani e il fuoco li rivela, uno alla volta.» |
| 0:04–0:06 | «Prospettiva, parallasse e profondità di campo. Tutto nella stessa scena.» |

The MP4 is intentionally silent; this timed script is the voice-over cue sheet.
