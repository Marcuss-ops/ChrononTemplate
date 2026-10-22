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
