# Premium FX 5 second canaries

Render plans and MP4s are in `ChrononTemplate/out/premium_fx_canaries_5s/`.
Lossless sequential golden checkpoints and random-access reports are grouped here:

```text
rgb/ bloom/ background/ light_leak/ premium_torture/
```

Each scene uses 1920x1080, 30 fps, 150 frames. Checkpoints are 0, 30, 60,
90, 120 and 149. The tool renders each scene sequentially to raw RGBA and
renders those six frames directly; `random_access_report.json` compares the
raw bytes before H.264 encoding.

Rebuild videos, checkpoints and CPU/Vulkan Bloom evidence with:

```sh
python3 ChrononTemplate/tools/backgrounds/render_premium_fx_canaries_5s.py \
  --render --frames --cpu-vulkan
```

The current CLI schema rejects the existing RenderPlan Field2D fields
`field_ramp`, `field_drift` and `field_render_scale`. The background canary
therefore exercises radial gradients and `turbulent_displace` instead of the
Field2D generator/operator chain. HDR values above 1 and transparent-surface
alpha certification are also outside this SDR H.264 canary path; their results
must not be inferred from these videos.
