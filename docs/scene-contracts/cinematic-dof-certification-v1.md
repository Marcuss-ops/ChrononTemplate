# Cinematic Depth of Field Certification V1

## Scope and acceptance criteria

- Reuse the ten preserved focus-plane PNG assets and their authored camera-space depths from 450 to 2250 units. Use the existing Chronon camera, focus sampler and DoF kernels; do not add another blur system.
- Render a 150-frame, 30 fps, 1920×1080 MP4 with linearly interpolated camera focus across all ten distances. Keep all layers present for every frame.
- Verify deterministic random-access output by rendering selected frames in chronological and shuffled order and comparing raw pixels byte-for-byte.
- Compare the exact same RenderPlan on the software and Vulkan backends. Use strict backend selection and record the Vulkan device; a missing Vulkan build or hardware device is a reported limitation, not a software fallback.
- Render a second scene with three partially overlapping transparent objects at distinct depths to examine occlusion and alpha edges while focus moves among them.
- Compare f-stop 0.7, 2.8 and 8 using the same scene, focus distance and blur cap. Do not tune max blur between aperture renders.
- Save representative PNG frames, MP4, plan files, a contact sheet, performance evidence and this validation report. Record CPU wall/render time and peak RAM; GPU time, VRAM and allocation counts are only reported if the available backend/tooling exposes them.

## Camera convention

Use the existing render-plan camera at the origin looking along world -Z; its Y rotation is 180° because RenderPlan follows the backward-axis convention. X is horizontal, Y is vertical. Focus distances are positive camera-space optical-axis distances in renderer units. FOV is 48°, focal length 22.723370 mm, sensor width 36 mm, and the output is 1920×1080 at 30 fps.
