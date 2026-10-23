"""Scene 02 - portrait_parallax_drift (frames 0034-0047).

Reference beats: B/W polaroids drifting in parallax -> red angled title
'SOME CONSPIRACY THEORIES THAT TURNED OUT TRUE. PART 2' -> vintage TV 'THIS IS REAL'.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def build(sc):
    dark_world(sc, (0.002, 0.002, 0.003, 1))
    setup_bloom(sc, threshold=0.85, size=0.5, strength=0.9)
    cam = add_camera(sc, location=(0, -14, 0), rot=(math.pi / 2, 0, 0), lens=50)

    pol = []
    for i in range(4):
        p = os.path.join(ASSETS, f's02_pola{i}.png')
        m = paper_mat(f'pola{i}_mat', p, rough=0.5)
        ob = plate(f'pola{i}', -4.2 + i * 2.9, -1.5 + i * 1.1, 1.2 - i * 0.7, 3.4, 4.0, m)
        ob.rotation_euler = (math.pi / 2, 0.12 - i * 0.07, 0)
        pol.append(ob)

    title_m = paper_mat('title_mat', os.path.join(ASSETS, 's02_title.png'), rough=0.5)
    title = plate('title', 0, -2.2, 0.2, 15.5, 7.3, title_m)
    title.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 1.0

    # vintage TV on the right
    tv_body = rounded_box('tv_body', 8.2, -0.5, 0.2, 6.6, 5.0, 2.2, (0.045, 0.045, 0.05), bevel=0.35)
    scr_m = paper_mat('tv_scr_mat', os.path.join(ASSETS, 's02_tv.png'), rough=0.32)
    scr = plate('tv_scr', 8.2, -1.75, 0.35, 5.2, 3.6, scr_m)
    for i, sx in enumerate((7.4, 9.0)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.32, depth=0.25,
                                            location=(sx, -1.85, -2.05), rotation=(math.pi / 2, 0, 0))
        k = bpy.context.object
        k.name = f'tv_knob{i}'
        k.data.materials.append(emission_mat(f'knob{i}_mat', (0.25, 0.22, 0.2), 1.2))
    starfield(count=60, seed=5)

    staged = []
    return cam, pol, title, tv_body, staged


def animate(sc, cam, pol, title, tv_body, staged):
    # slow parallax drift of polaroids + camera dolly
    for i, ob in enumerate(pol):
        for fr, dx, dz in ((34, 0, 0), (40, 0.55 + i * 0.1, 0.22), (47, 1.1 + i * 0.2, 0.42)):
            ob.location.x = -4.2 + i * 2.9 + dx
            ob.location.z = 1.2 - i * 0.7 + dz
            ob.keyframe_insert('location', frame=fr)
    for fr, cy, cx in ((34, -14, 0), (41, -13.0, 5.0), (47, -11.5, 8.0)):
        cam.location = (cx, cy, 0.2)
        cam.keyframe_insert('location', frame=fr)
    # title fades in via scale
    title.scale = (0.001, 0.001, 0.001)
    title.keyframe_insert('scale', frame=38)
    title.scale = (7.75, 3.65, 1)
    title.keyframe_insert('scale', frame=42)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s02')
    first, last = int(args.get('first', 34)), int(args.get('last', 47))
    sc = clean_scene()
    cam, pol, title, tv_body, staged = build(sc)
    animate(sc, cam, pol, title, tv_body, staged)
    render_range(sc, out, first, last)
