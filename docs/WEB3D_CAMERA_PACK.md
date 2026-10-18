# Web3D camera pack

## Scene contract

- **Subject and source:** the supplied `C:\Users\pater\Downloads\table.glb`, a static product model. The file contains one mesh, one PBR material and two embedded PNG textures; the asset metadata attributes the model to yryabchenko on Sketchfab under CC BY 4.0.
- **Composition:** keep the whole table in frame, centered on its measured bounds. The GLB bounds are X `[-2.2673, 2.2673]`, Y `[-0.0848, 3.2124]`, Z `[-2.2673, 2.2673]`; aim at `(0, 1.5638, 0)`. glTF uses Y-up. Chronon camera looks down local `-Z`.
- **Motion and timing:** ten single-shot camera recipes, 90–150 frames at 30 fps; the table stays fixed and `CameraRig` carries the motion. The generic framing resolver uses the supplied subject center and extents.
- **Layers:** one imported table mesh, plus the existing scene background and lighting. No extra furniture or fabricated props.
- **Must not appear:** substitute imagery, UI overlays, additional objects, or camera moves applied to the mesh transform.
- **Preview acceptance:** 854×480 opening, middle and ending frames show the entire table with no clipping; each move produces a visible camera pose change and ends on the intended framing.

## Recipes

| ID | Move | Duration |
|---|---|---:|
| `camera_motion_web3d_product_push` | measured product push-in | 96 frames |
| `camera_motion_web3d_orbit` | centered 48° orbit | 120 frames |
| `camera_motion_web3d_arc_left` | left arc with gentle push | 105 frames |
| `camera_motion_web3d_arc_right` | right arc with gentle push | 105 frames |
| `camera_motion_web3d_rise_reveal` | rise and level reveal | 90 frames |
| `camera_motion_web3d_top_down` | elevated overhead reveal | 108 frames |
| `camera_motion_web3d_lateral_slide` | lateral slide with counter-yaw | 96 frames |
| `camera_motion_web3d_dolly_arc` | assertive dolly with a slight arc | 90 frames |
| `camera_motion_web3d_crane_down` | crane down and pitch settle | 100 frames |
| `camera_motion_web3d_slow_drift` | long, subtle showroom drift | 150 frames |

The recipes are ordinary `CameraMotionPreset` values in the existing
`CameraMotionPack`; `applyCameraMotionShot` lowers them onto ChrononMotion3D's
`CameraRig`. The asset itself remains a content-side GLB; these recipes need no
model-specific camera code.

```cpp
CameraMotionShot shot;
shot.subject.center = {0.f, 1.5638f, 0.f};
shot.subject.halfWidth = 2.2673f;
shot.subject.halfHeight = 1.6487f;
shot.fov = 50.f;
applyCameraMotionShot(scene, CameraMotionPreset::Web3DOrbit, shot);
```

Web/product scenes can select the full set with
`cameraMotionSuggestions(CameraContentKind::Web3DObject)`. The standard
`PremiumUI3D` selection also includes three safe starting moves.
