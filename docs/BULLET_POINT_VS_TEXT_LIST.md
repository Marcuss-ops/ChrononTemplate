# Bullet points and text lists

ChrononTemplate keeps two authoring surfaces separate:

## Bullet point

A single marked text item with one entrance transition. It is authored with
`chronontemplate_emit_bullet_point_transitions` from
`tools/bullet_points/emit_bullet_point_transitions.cpp`. The sample has one
sentence, wraps it at 30 characters, and uses a restrained camera push. It does
not lay out or sequence multiple items.

## Text list

Several sentences arranged as separate rows. Each row wraps at 30 characters,
enters on a stagger, and the camera travels vertically through the sequence. It
is authored with `chronontemplate_emit_text_list_transitions` from
`tools/text_lists/emit_text_list_transitions.cpp`.

The current list transition renders are in `out/text_list_transitions_v1/`.
Single-item point renders are in `out/bullet_points_v1/`. The latter directory
also preserves the first prototype set; `tilt_in` and `yaw_flip` there are
historical samples and are no longer offered by the current reveal picker.

Both tools currently use `BulletListPack` for the shared text-layer reveal
mechanics. List layout and camera travel are selected only by the text-list
emitter; the standalone bullet-point emitter authors exactly one item.

## Bullet point → camera → image

For a narrated sequence where each statement is typed first and then the camera
travels down to its related image, use
`tools/bullet_points/emit_bullet_camera_images.cpp`. It reuses the modern
typewriter's GPU glyph-window reveal, a perspective camera, and a cyan leader
with native glow. The `fast_intro` preset has two short beats; `normal_chapter`
has three longer reading beats. Supply one image per point with repeated
image paths as arguments (relative to the workspace root):

```sh
cmake --build ChrononTemplate/build/release-fast --target chronontemplate_emit_bullet_camera_images
ChrononTemplate/build/release-fast/chronontemplate_emit_bullet_camera_images fast_intro \
  ChrononTemplate/out/bullet_camera_images_v1/bullet_camera_fast_intro.plan.json \
  ChrononTemplate/assets/first.png ChrononTemplate/assets/second.png
ChrononTemplate/build/release-fast/chronontemplate_emit_bullet_camera_images normal_chapter \
  ChrononTemplate/out/bullet_camera_images_v1/bullet_camera_normal_chapter.plan.json \
  ChrononTemplate/assets/first.png ChrononTemplate/assets/second.png ChrononTemplate/assets/third.png
```

The command writes an editable RenderPlan under
`ChrononTemplate/out/bullet_camera_images_v1/`. The no-argument fast-intro
example uses the three `web_archive_v1` sample images already in the repository.
