# Three Plane Camera Focus Check V1

## Scene contract

- **Subject and assets:** a generated photographic background, one editable text layer reading `FOCUS TEST`, and one generated transparent foreground object (vintage camera lens). Keep each visual on its own layer and preserve the generated asset sources.
- **Layer order and depth:** layer 0 is the far background at 900 render units; layer 1 is the text at 650 units; layer 2 is the foreground object at 450 units. Camera looks along world -Z from the origin. Layer 2 is composited in front of layer 1, which is in front of layer 0.
- **Focus samples:** render three previews with all three layers present. Focus 900 on the background, focus 650 on the text, and focus 450 on the foreground object. In each sample the requested plane should be sharpest while the other planes remain visible and blur according to their depth, including foreground layers in front of the current focus plane.
- **Camera and format:** use the existing Chronon perspective camera/DOF path, FOV 48°, f-stop 0.7, near/far 10/1200, 854×480 composition preview followed by 1920×1080 focus states, and software backend. No engine changes.
- **Must not appear:** text baked into generated images, green-screen matte, logos, watermarks, extra captions, or a flattened scene.
- **Preview acceptance:** inspect the actual first preview at 854×480 before producing the three-state comparison. Confirm the background, text, and foreground object are all visible and correctly layered. Then inspect all three focus states to check that focus follows depth independently of layer order.

## Coordinate convention

X is horizontal, Y is vertical, and the camera looks along world -Z from the origin. The RenderPlan perspective view uses its backward axis, so the camera rotation is `[0, 180, 0]` to face world -Z. The positive focus distance is measured from the camera along that optical axis; the three plane depths are 900, 650 and 450 renderer units. The background image plane is scaled to cover the camera frame. The foreground lens partially overlaps the title so the compositing order is visible while focus changes.
