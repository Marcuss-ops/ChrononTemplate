# F's PluginsProjects reuse audit

Reviewed `bryful/F-s-PluginsProjects` and the focused implementations for LineExtraction, AlphaFill, Grain, Gradient, and InnerFlare on 2026-10-18. The latest visible release at review time was `v1.1.0` (2026-05-04), described as bug fixes and category changes. No third-party code has been copied into Chronon.

## Findings

| Effect | Chronon overlap | Recommendation |
|---|---|---|
| **LineExtraction** | No direct image-to-lines extraction. `RoughenEdges`, `Stroke`, `Sharpen`, and blur are adjacent but do not implement this edge-color extraction pipeline. | **Best experiment.** It smooths with a bilateral filter, builds luminance, compares inner/outer min/max neighborhoods, then colors and levels the extracted edges. Port only the image algorithm into a standalone pixel routine; keep the AE adapter out. Good for archival photos, maps, and illustrated transitions. |
| **AlphaFill** | Chronon has luma/chroma keying with threshold, softness, and spill controls, but no dedicated transparent-edge RGB fill. | **Small useful utility.** Could reduce color fringes around cutouts. Audit premultiplication and alpha-zero behavior before porting; the current source appears to read the spill amount from the softness parameter, so do not transplant it blindly. |
| **Grain** | Chronon already has Noise, NoiseSampler, and Banded Grain; Banded Grain has native CPU and Vulkan routes. | **Do not port now.** Compare visual character only if a sample proves the existing grain cannot match it. |
| **Gradient** | Chronon supports shape gradients and a four-color gradient effect. | **Do not port now.** No demonstrated capability gap. |
| **InnerFlare** | Chronon has Glow, Bloom, Light Rays, Blur, and Threshold, but not this exact alpha-driven inner/outer flare recipe. | **Niche follow-up.** The source describes min/max → blur → hyperbolic shaping of alpha. Prototype only for a real cutout or logo shot where the existing stack cannot produce the desired rim. |
| **CameraShake** | ChrononMotion3D already contains camera-motion presets and animated camera tracks. | **No renderer port.** Keep camera motion in ChrononMotion3D. |
| **BurstLines** | No named effect match, though shape/line primitives can make the artwork. | Treat it as a reusable documentary/transition template first, not a new pixel effect. |

## Portability and license

The repo's root license is MIT. Any copied or adapted source must retain its copyright and permission notice. The plug-in entry points are not portable: these files call Adobe `PF_*` pixel formats, `AEGP_SuiteHandler`, and host iteration suites. Separate the algorithm from that host code and validate its alpha, pixel-depth, and color-space behavior before registering it.

The clearest first port is a small LineExtraction prototype with an original image, line mask, and composite preview so its difference from existing `RoughenEdges` and `Stroke` is visible. AlphaFill is a smaller, lower-priority utility. No plugin binaries or full repository checkout belong in Chronon.

## Sources

- [Repository README and effect categories](https://github.com/bryful/F-s-PluginsProjects/blob/master/README.md)
- [LineExtraction README](https://github.com/bryful/F-s-PluginsProjects/blob/master/LineExtraction/README.MD), [main implementation](https://github.com/bryful/F-s-PluginsProjects/blob/master/LineExtraction/LineExtraction.cpp), and [filter implementation](https://github.com/bryful/F-s-PluginsProjects/blob/master/LineExtraction/LineExtractionFilter.cpp)
- [AlphaFill README](https://github.com/bryful/F-s-PluginsProjects/blob/master/AlphaFill/README.MD), [filter implementation](https://github.com/bryful/F-s-PluginsProjects/blob/master/AlphaFill/AlphaFillFilter.cpp), and [chroma-key implementation](https://github.com/bryful/F-s-PluginsProjects/blob/master/AlphaFill/ChromaKey.cpp)
- [InnerFlare README](https://github.com/bryful/F-s-PluginsProjects/blob/master/InnerFlare/README.MD) and [implementation](https://github.com/bryful/F-s-PluginsProjects/blob/master/InnerFlare/InnerFlare.cpp)
- [Grain implementation](https://github.com/bryful/F-s-PluginsProjects/blob/master/Grain/Grain.cpp), [Gradient implementation](https://github.com/bryful/F-s-PluginsProjects/blob/master/Gradient/Gradient.cpp), and [MIT license](https://github.com/bryful/F-s-PluginsProjects/blob/master/LICENSE)
- [Project releases](https://github.com/bryful/F-s-PluginsProjects/releases)
- Chronon3D's local [effect path matrix](/home/pater/projects/Chronon3d/docs/reference/effect-path-matrix.md) lists 50 effects with native Vulkan routes, including Banded Grain, Vignette, gradients, and compositing effects.
