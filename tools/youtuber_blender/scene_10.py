"""Scene 10 - highlighter_evidence_sweep (frames 0313-0317).

Reference: white document 'Over the years more than 20 psychics were employed.'
with yellow highlighter sweeping across the sentence.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def build(sc):
    dark_world(sc, (0.08, 0.08, 0.082, 1))
    setup_bloom(sc, threshold=1.1, size=0.3, strength=0.45)
    cam = add_camera(sc, location=(0, -8.2, 0), rot=(math.pi / 2, 0, 0), lens=50)
    m = paper_mat('doc10_mat', os.path.join(ASSETS, 's10_doc.png'), rough=0.55, glow=1.0)
    doc = plate('doc10', 0, 0, 0, 15, 8.3, m)

    hm = bpy.data.materials.new('sweep_mat')
    hm.use_nodes = True
    b = hm.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (1.0, 0.86, 0.1, 1)
    if 'Emission Color' in b.inputs:
        b.inputs['Emission Color'].default_value = (1.0, 0.86, 0.1, 1)
        b.inputs['Emission Strength'].default_value = 0.7
    sweep = rounded_box('sweep', -5.6, -1.35, 1.6, 0.4, 1.5, 0.02, (1.0, 0.86, 0.1))
    sweep.data.materials.clear()
    sweep.data.materials.append(hm)
    return cam, doc, sweep


def animate(sc, cam, doc, sweep):
    cam.location = (0, -8.2, 0)
    cam.keyframe_insert('location', frame=313)
    cam.location = (0, -7.9, 0)
    cam.keyframe_insert('location', frame=317)
    # sweep grows left -> right across the headline
    for fr, x, w in ((313, -5.6, 0.4), (315, -3.0, 5.2), (317, 1.4, 9.6)):
        sweep.location.x = x
        sweep.scale = (w / 0.4 if w > 0.4 else 1, 1, 1)
        sweep.keyframe_insert('location', frame=fr)
        sweep.keyframe_insert('scale', frame=fr)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s10')
    first, last = int(args.get('first', 313)), int(args.get('last', 317))
    sc = clean_scene()
    cam, doc, sweep = build(sc)
    animate(sc, cam, doc, sweep)
    render_range(sc, out, first, last)
