# DOCUMENTARY TITLE → SNAPSHOT V1

## Objective

Author documentary title-to-image reveals as one ChrononTemplate scene. A normal
text layer and a normal image layer share scene space; the recipe describes the
narrative handoff while ChrononMotion3D evaluates the camera path.

## To-do actions

### Next actions

- [x] **P0 — center connected snapshot plate:** positioned rounded frame
  geometry no longer receives an extra local `-size/2` offset. The C ABI
  contract checks that a positioned media card and its image share the same
  transform; the focused test passes (23 assertions).
- [x] **P0 — fit-aware connected snapshot frame:** the documentary pack authors
  the card border as an ordinary rounded `Shape` layer behind the image. For
  `Fit`, its dimensions follow the measured source bounds; `Fill` and `Crop` use
  the declared viewport. The connected Chronon3D pixel check reports image
  bounds `(522,205)–(1397,874)`, frame bounds `(515,197)–(1404,882)`, and 7/8 px
  margins. Rendered aspect 1.3075 differs from the 1920×1472 source aspect by
  0.24%.
- [x] **P0 — inspect connected canary holds:** raw frames 0/45 show the title
  only; frames 53/120 show the photo and the centered rounded plate. Individual
  decoded frames have been reviewed over the intended dark background.
- [x] **P1 — keep archive caption on one line:** update the canary backend's
  measured width; the decoded final frame now shows `ROME, 1986` on one line.
- [x] **P1 — verify caption placement:** the connected final frame places
  `ROME, 1986` centered above the card on one line and inside the 1920×1080
  safe frame.

- [x] **P0 — RenderPlan ContentHost adapter:** add the callback-backed
  `RenderPlanContentHost`, which keeps media creation and measurement in the
  supplied backend and maps each wire-bound Text/Image/Video/Shape request to a
  native `LayerPlan`. Image plans carry fit, normalized crop, target viewport,
  rounded frame, saturation, contrast, deterministic grain, and vignette;
  shapes become native rectangles.
- [x] **P0 — typed media style emission:** extend ChrononMotion's RenderPlan
  JSON writer to preserve media background frames and the native saturation,
  contrast, seeded-noise, and vignette subset. Unsupported effect types and
  parameter tracks fail validation instead of being dropped. The emitted V3
  image plan passes Chronon3D CLI validation and renders the archival image
  through the software backend.
- [x] **P0 — connected asset canary:** render the non-square archival image in
  `Fit`, `Fill`, and explicit `Crop` through `RenderPlanContentHost`. Decoded
  final frames for Fill and Crop show the image filling the rounded viewport
  with the frame aligned; normalized crop lowering preserves the requested
  crop bounds and target aspect. Fit also passes the pixel bounds/aspect check
  above. The connected comparison artifacts are recorded below.
- [x] **P0 — native Fit/Fill/Crop canary:** render the 1920×1472 archival
  portrait in a 400×220 image viewport through RenderPlan and inspect the decoded
  1920×1080 frame. `contain` shows 287×220 content centered with 56.5 px side
  margins; `cover` shows a 1920×1056 source window (208 px top offset); explicit
  crop `[0.14,0.08]+[0.72,0.84]` followed by cover shows source bounds
  `[268.8,355.84]–[1651.2,1116.16]`. The frame visually confirms all three
  preserve the source aspect ratio and that explicit crop changes framing.
- [x] **P0 — motion review:** render snap-down at 30 fps (121 frames) and inspect
  title hold, peak travel (frame 48), handoff (frame 53), and final hold (120).
  The declared transition spans frames 45–53 (8 frames); all camera channels
  stop changing at frame 53 and remain exact through frame 120.
- [x] **P1 — focus and blur canary:** expose existing camera DOF channels as
  RenderPlan camera animation properties, then render `doc_title_focus_drop`
  through Chronon3D at 30 fps (121 frames). The C++ dumper now samples focus
  distance and aperture from the native `DocumentaryShot`; the canary no longer
  substitutes a hand-authored focus curve. Visual review confirms the snapshot
  is blurred at the opening and sharp at the ending, with no visible temporal
  smear after the camera settles. The recipe tracks exact camera-to-title and
  camera-to-photo distances and stays inside the RenderPlan aperture range.
  DOF animation requires `camera.dof.enabled=true`; the C ABI decoder contract
  passes all 7 DOF-channel assertions, and the normalized crop decoder contract
  passes all 9 assertions.
- [x] **P1 — animated DOF authoring:** add a `CameraRig` maximum-blur channel
  and lower animated focus distance, aperture, and max blur to Chronon3D's
  typed camera tracks. `chronontemplate_plan_lowering_test` verifies the three
  emitted tracks, endpoint values, and the case where aperture opens after
  frame zero.
- [x] **P1 — red portal authoring:** expose a native rectangle through
  `TemplateScene::shape`, animate its opacity through the push-through, and add
  peak-opacity and viewport-coverage contracts.
- [x] **P1 — push-through render canary:** render 121 frames in Chronon3D and
  inspect title hold (45), full red coverage (53), red/photo blend during settle
  (80), and final photo hold (120). The plan verifies at 1920×1080.
- [x] **P1 — red portal render hookup:** render `PushThroughSnapshot` through
  `RenderPlanContentHost`; its native `ShapeRequest` reaches Chronon3D as a
  shape layer and decoded frame 53 measures 100.0% red viewport coverage.
- [x] **P1 — synchronized light leak:** lower the existing `LightLeakResolver`
  gradient to a native screen-space shape and key its opacity from sampled
  camera speed. Connected canary reports leak peak frame 49, camera-speed peak
  frame 50, and final opacity 0; decoded review confirms the reveal is clean
  after settle. The profile uses a restrained warm edge sweep.
- [x] **P1 — style render review:** render the seven styles on one archival asset
  through Chronon3D's decoded video path. The review exposed excessive grain in
  Archive and Filmstrip; the pack presets and gallery now use subtler levels.
- [x] **P1 — connected style hookup:** the adapter maps each `ImageRequest`
  frame, grade, vignette, grain amount, and seed to a native LayerPlan. All seven
  presets were rendered through the adapter and Chronon3D; the decoded contact
  sheet confirms distinct borders and grading, including monochrome Newspaper
  and B&W Documentary.
- [x] **P1 — native camera motion blur hookup:** carry V3 temporal shutter
  settings through `TemplateScene`, RenderPlan lowering/emission, and the
  Chronon3D CLI render settings. Documentary handoffs use an existing global
  temporal shutter (90 degrees, 8 samples). Connected Reveal90 frame 49 differs
  from the no-blur render over the moving title/photo projection; settled frame
  120 differs by at most 1 RGB level and remains visually sharp. Plan emission
  and decode validate through the connected CLI.
- [ ] **P1 — recipe handoff visual review:** inspect transition-specific frames
  for all 12 recipes through `RenderPlanContentHost`, then record any
  composition fixes. Frame-53 renders exist for all 12 recipes. Fresh final
  holds were rendered with explicit `Fit` for all 12 and reviewed as a contact
  sheet under `out/documentary_snapshot_v1/recipe_final_v3/`. Single-card pixel
  checks pass at aspect 1.3036 (source 1.3043) with even 7 px margins; PhotoStack,
  Filmstrip, and ArchiveCrane were reviewed individually. Reveal90's mirrored
  snapshot/caption defect is fixed; its final endpoint has been re-rendered and
  reviewed. Reveal90 now has an 8-frame turn with temporal blur. The aligned
  wall-anchor canary and revised title/caption timing remove the oblique title
  and reverse-facing caption from the frame-49 turn sample; the photo is inside
  the viewport and the frame-53 settle is sharp. PhotoStack now crossfades one
  caption per camera waypoint and its final camera target includes the caption
  envelope; the no-shutter connected frame-120 diagnostic now shows the final
  `ROME, 1986` caption fully legible above the last card, with the card and text
  inside the viewport (`out/documentary_snapshot_v1/photo_stack_caption_fit_v5.png`).
  The full temporal-shutter Vulkan render is still pending: Chronon3D currently
  rejects a native SourceOver composite during this recipe, and the error path
  is being instrumented to expose the backend's specific failure. Continue
  sampling all other recipe transitions.
  Earlier frame-53 sheet is under
  `out/documentary_snapshot_v1/recipe_handoff_v1/`. Split-depth focus endpoints
  and the Motion→RenderPlan DOF mapping have been corrected. Focus-drop opening
  and final composition are reviewed.
- [ ] **P2 — torture canary render:** the assembled 20-second plan (601 frames,
  68 layers) validates in Chronon3D, but a full software encode and a Vulkan
  encode both proved impractically slow in this environment. Keep the plan and
  validation result; retry the complete render when a performant multi-layer
  render path is available, then inspect the opening, all handoffs, and final
  archive layout.

### Ordered implementation actions

1. [x] Run focused C ABI decoder contracts for animated focus/aperture/max-blur
   ranges and normalized image crops. Both pass (7 and 9 assertions).
2. [x] Add camera rig authoring and typed RenderPlan lowering for animated
   focus distance, aperture, and maximum blur; verify endpoint values.
3. [x] Add callback-backed `RenderPlanContentHost` and map Text, Image, Video,
   and Shape requests to native plans by unique wire id.
4. [x] Add adapter contracts for fit, crop, frame, grade, stable grain,
   vignette, and native shape fill.
5. [x] Extend typed RenderPlan emission for the media frame and effect subset;
   validate the V3 output with Chronon3D CLI and render the archival image.
   Connected Fit/Fill/Crop placement and source crop contracts are now covered
   by the adapter canaries and plan-lowering checks.
6. [x] Define the `Fit` frame contract around fitted source bounds and assert
   projected card/image bounds and title-hold visibility. Connected canary
   pixel checks pass at the title hold and final snapshot.
7. [x] Render the non-square asset in `Fit`, `Fill`, and explicit `Crop` through
   the connected host; review decoded frames and confirm the crop contract.
8. [x] Connect the seven snapshot styles through the adapter and compare their
   decoded output. The first review caught a dumper default overriding the
   selected preset; after correcting it, the seven connected outputs differ as
   expected.
9. [x] Verify the archive caption's one-line layout, projected position, and
   safe-frame bounds in the connected canary.
10. [x] Add a native light-leak handoff to the connected snap render, keyed to
    peak camera speed. Decoded frames 48–50 review the flash; final frame 120
    confirms the leak returns to zero. Whip coverage remains part of follow-up
    recipe verification.
11. [x] Build `documentary_title_snapshot_torture_v1` from the V1 recipes and
    styles; the 601-frame, 68-layer plan validates with Chronon3D. Full encoding
    remains open because both available render backends were impractically slow.
12. [x] Review the updated focus-drop opening and final frames through the
    connected adapter. The opening keeps title and snapshot in frame with the
    snapshot/caption out of focus; the final photo and caption are sharp, the
    card is front-facing, and the decoded Fit aspect is 1.3075 vs source 1.3043.
    Caption spacing and final camera target were adjusted. Artifacts:
    `out/documentary_snapshot_v1/focusdrop_anchor_review_v5/`.
13. [x] Render all 12 final holds through the connected adapter with explicit
    `Fit`, run the source-aspect/frame pixel check for each single-card recipe,
    review PhotoStack/Filmstrip/ArchiveCrane separately, and refresh the final
    contact sheet. Single-card output is 1.3036:1 vs 1.3043:1 source; multi-card
    images remain inside their frames. Reveal90's previous mirrored image and
    caption are fixed and the refreshed connected endpoint is reviewed.
14. [x] Correct Reveal90's mirrored snapshot/caption while retaining its
    quarter-turn camera move. Add `flip_x` to the normalized crop contract,
    RenderPlan decoder, schema, fingerprint, compiler, and software image
    mapping; this flips image content without reflecting its 3D transform.
    The caption is oriented for readability and the title fades during the
    turn to avoid an edge-on trace. `chronontemplate_documentary_snapshot_pack_test`
    passes all 1,585 checks. Connected frame 120 matches the source photo
    orientation, keeps `ROME, 1986` readable, and passes Fit pixel bounds with
    uniform 7 px margins. Artifacts:
    `out/documentary_snapshot_v1/reveal90_orientation_review_v4/` (orientation)
    and `out/documentary_snapshot_v1/reveal90_orientation_review_v5/` (final
    title fade). The quarter-turn now occupies the declared 8-frame handoff;
    connected frames 53/80/120 show the photo settled and correctly oriented.
    Temporal blur is authored at 90 degrees with 8 samples and reaches the
    Chronon3D CLI runtime. Contract tests pass (1,585 documentary checks, 145
    ChrononMotion authoring checks, plus Template plan lowering). The frame-49
    blur changes the moving output while the settled frame-120 RGB differs by
    at most one level from the no-blur image. Artifacts:
    `out/documentary_snapshot_v1/reveal90_temporal_blur_review_v4/`.
15. [ ] Render and inspect transition samples (title hold, handoff, mid-move,
    settle) across all 12 recipes; record and fix framing, focus, overlap, and
    motion-settle defects. Frame 80 is rendered for all recipes at
    `out/documentary_snapshot_v1/recipe_transition_mid_v1/`; contact sheet:
    `out/documentary_snapshot_v1/recipe_transition_mid_v1/documentary_transition_mid_contact_sheet.png`.
    CornerTurn connected frames 40/48/120 confirm a clean title hold and a
    fully framed settled photo; the mid-turn crop at frame 80 is transient. For
    ArchiveCrane, the review found the old final target cropped/decentered the
    photo group. The settle now targets an envelope around title, cards, and
    captions and derives a fit distance. The ArchiveCrane caption also follows
    the card opacity handoff, so its title hold is clear. Connected frame 120
    shows all cards and title inside the viewport. Artifacts:
    `out/documentary_snapshot_v1/corner_turn_transition_review_v1/` and
    `out/documentary_snapshot_v1/archive_crane_transition_review_v3/`.
    ForegroundPhotoPass moves image, frame, and caption together; connected
    frames 80/120 and the Fit pixel bounds pass:
    `out/documentary_snapshot_v1/foreground_pass_card_review_v2/`. Continue
    transition review for the remaining recipes; Reveal90's endpoint and settle
    pass. Its 8-frame turn sample at frame 49 now shows the photo fully in-frame
    without title/caption intrusion, and frame 53 is sharp. The title exits just
    after the hold, and its caption fades in one frame after the turn ends.
    Temporal blur and light leak peak with camera speed. Samples:
    `out/documentary_snapshot_v1/reveal90_transition_review_v1/` and
    `out/documentary_snapshot_v1/reveal90_transition_review_v2/`; revised pixel
    truth: `out/documentary_snapshot_v1/reveal90_caption_timing_v2/`. PhotoStack
    caption handoff is checked at its second waypoint (1,594 documentary
    checks pass); connected frame 80 shows one active label. Its frame-120
    caption is still absent in the earlier v3 diagnostic; the updated v5
    no-shutter connected frame now confirms it is legible and within frame.
    Full-shutter Vulkan visual review remains open while the native composite
    failure is diagnosed.
    Artifacts: `out/documentary_snapshot_v1/photo_stack_caption_handoff_v1/`,
    `out/documentary_snapshot_v1/photo_stack_caption_fit_v2/`, and the
    no-shutter diagnostics `out/documentary_snapshot_v1/photo_stack_caption_fit_v3.png`
    and `out/documentary_snapshot_v1/photo_stack_caption_fit_v5.png`.
16. [ ] Run the V1 verification suite across all recipes: static title
    transforms, anchor framing, exact transition boundaries, deterministic
    direct/sequential frame sampling, safe frame, image aspect ratio/crop,
    motion settle, and final snapshot visibility. Record results and mark
    acceptance only after these connected-render checks pass. All 12 current
    recipe plans validate through the connected adapter at
    `out/documentary_snapshot_v1/connected_plan_validation_v2/`; visual
    static contracts and plan validation pass; connected transition review
    remains incomplete.
17. [ ] Retry the full 20-second torture render on a performant multi-layer
    render path, then inspect the opening, all handoffs, and final archive
    layout. The current 601-frame, 68-layer plan validates in Chronon3D.
18. [ ] Make the connected documentary render produce visible pixels through
    the strict Vulkan path, then inspect and publish a GPU-rendered frame/video.
    The current 1920x1080 PhotoStack plan can lose the Vulkan device when its
    radial light-leak shape or image EffectStack falls back through CPU readback.
    With those optional effects removed, a raw Vulkan job exits successfully but
    its output is fully transparent (all RGBA bytes are zero); do not treat that
    output as visual evidence. The debug trace identifies the unsupported radial
    Rect as `ShapeType::Rect` (type 1), while `synchronize_native_output` sees
    no retained surface handle on the frame output. Investigate native output
    residency/readback and unsupported-effect policy before the Drive upload.

### Completed actions

- [x] Add the semantic `DocumentaryShot` description with title and snapshot anchors.
- [x] Add all twelve native camera recipes in V1, including stack, filmstrip,
  foreground pass, depth split, corner turn, and archive crane reveal.
- [x] Add reusable `snapshot_clean`, `snapshot_archive`, and `snapshot_evidence`
  frame styles through the existing image content path.
- [x] Add the remaining planned looks (`snapshot_polaroid`, `snapshot_filmstrip`,
  `snapshot_newspaper`, `snapshot_bw_documentary`) using existing image-frame
  and effect inputs.
- [x] Keep title/photo transforms static for camera recipes and author motion on
  the existing camera rig. The foreground pass moves its card by design.
- [x] Emit stable recipe and style rows in the generated ChrononTemplate catalog.
- [x] Add deterministic P0 contracts for static transforms, final photo framing,
  transition timing, settle, style handoff, and direct-versus-sequential evaluation.
- [x] Add the scene-quality P0 contracts: focus handoff, push-through viewport
  coverage, the 90-degree reveal angle, bounded corner-turn continuity,
  foreground-pass occlusion, stack depth ordering, and filmstrip gap consistency.
- [x] Add the title safe-frame and stable style-grain seed contracts; camera,
  focus, layer-transform, and direct-versus-sequential sampling are deterministic.
- [x] Add stack, filmstrip, and archive multi-image compositions using ordinary
  image layers with caller-declared anchors.
- [x] Keep snapshot cards hidden through the title hold for reveal recipes;
  focus-drop keeps its blurred snapshot visible so the rack-focus handoff is
  readable from frame one.
- [x] Add fit/fill/crop requests through the existing image/content contract,
  including explicit normalized crop rectangles and target card size.
- [x] Carry normalized image crop rectangles through the v2-compatible
  RenderPlan schema, decoder, fingerprint, image compiler, and adjustment-layer
  validation; the C ABI decoder case passes its 9 crop assertions.
- [x] Render the native Fit/Fill/Crop comparison with the current Chronon3D CLI
  and inspect its decoded pixel-truth frame.
- [x] Verify each fit mode against rendered assets from the connected
  RenderPlanContentHost, including source aspect ratio and crop framing. The
  plan-lowering contract checks that Cover emits an in-bounds normalized crop
  whose source window matches the target viewport aspect.
- [x] Render and metadata-validate a documentary snapshot canary in Chronon3D.
- [x] Review the connected canary's final card framing against the declared
  `Fit` behavior; the plate follows the fitted source bounds, centered with
  uniform 7/8 px margins. Fill and explicit Crop use viewport-sized plates.
- [x] Review snap motion and settle quality on the full-rate canary, including
  transition start, peak travel, and the final camera hold.
- [x] Exercise rack focus, grain, and light leak through connected render
  canaries. Temporal camera blur is connected and visually compared on Reveal90;
  transition-specific blur tuning remains in the open recipe review.
- [x] Add the native red push-through surface and verify its peak opacity.
- [x] Synchronize a light leak with peak camera speed in the connected
  RenderPlan path; plan checks confirm matching peak frames and zero final
  opacity.
- [x] Render all seven style looks visually in Chronon3D; the pack sends frame,
  grade, grain, and vignette settings through the normal image request.

## Review artifacts

- Native Fit/Fill/Crop gallery: `out/documentary_snapshot_v1/documentary_snapshot_fit_gallery_v1.png`
- Full-rate snap-down render: `out/documentary_snapshot_v1/doc_title_snap_down_canary_v1.mp4`
- Snap-down contact sheet around the handoff: `out/documentary_snapshot_v1/doc_title_snap_down_review_v1.png`
- Focus-drop render: `out/documentary_snapshot_v1/doc_title_focus_drop_canary_v1.mp4`
- Native focus-drop review (frames 0, 45, 53, 120): `out/documentary_snapshot_v1/doc_title_focus_drop_review_native_focus_v1.png`
- GPU diagnostic artifacts (not visual deliverables): `out/documentary_snapshot_v1/photo_stack_gpu_*`, `out/documentary_snapshot_v1/snap_down_gpu_native_minimal_*`. Vulkan build succeeds; full-quality GPU frames remain unverified because device-loss/transparent-output cases are reproduced.
- Connected adapter canary RenderPlan: `out/documentary_snapshot_v1/adapter_canary/documentary_snapshot_adapter_canary_v1.plan.json`
- Connected adapter pixel-truth frames 0, 45, 53, and 120: `out/documentary_snapshot_v1/adapter_canary/documentary_snapshot_adapter_frame_*.png`
- Connected Fill frames: `out/documentary_snapshot_v1/adapter_fill/documentary_snapshot_adapter_frame_*.png`
- Connected explicit Crop frames: `out/documentary_snapshot_v1/adapter_crop/documentary_snapshot_adapter_frame_*.png`
- Seven connected snapshot styles: `out/documentary_snapshot_v1/connected_snapshot_styles_v1.png`
- Connected light-leak peak and settle frames: `out/documentary_snapshot_v1/adapter_leak_review/documentary_snapshot_adapter_frame_*.png`
- Connected push-through portal frames: `out/documentary_snapshot_v1/adapter_push_through/documentary_snapshot_adapter_push-through-snapshot_frame_*.png`
- Recipe handoff frames at frame 53 and contact sheet: `out/documentary_snapshot_v1/recipe_handoff_v1/`
- Uniform-Fit final-hold frames and contact sheet: `out/documentary_snapshot_v1/recipe_final_v3/`
- Focus-drop opening/final connected review: `out/documentary_snapshot_v1/focusdrop_anchor_review_v5/`
- Earlier focus-drop contact sheets: `out/documentary_snapshot_v1/doc_title_focus_drop_review_detail_v1.png`, `out/documentary_snapshot_v1/doc_title_focus_drop_review_focus_v1.png`

## Implementation boundary

The pack adds no photo renderer, camera math, registry, or asset resolver. Photo
content comes from `TemplateScene::image`; camera keys go to the existing
`CameraRig`. DOF, motion blur, grain, and light leak remain dependent on existing
Chronon3D render support and are not simulated in the template layer.

`RenderPlanContentHost` is a callback-backed adapter in this workspace. It
lowers measured Text/Image/Video/Shape handles into native LayerPlans; its
connected snapshot canaries run through Chronon3D CLI. Integration with an
application's production ContentHost remains an adoption task. Static image
grade, grain, vignette, animated screen-space gradients, and light-leak opacity
tracks are emitted by the typed JSON writer. The red portal is authored as an
ordinary shape request and lowered to a native shape plan; its connected
push-through canary reaches full viewport coverage.

## Acceptance

- The title and snapshot layer transforms do not change during a camera-only shot.
- The camera target settles exactly on the snapshot anchor at shot end.
- All transition key times are derived from the declared frame window.
- Unsupported recipe/style values fail explicitly.
