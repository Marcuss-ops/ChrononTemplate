"""Scene 09 - newspaper_dossier_zoom (frames 0259-0262).

Reference: zoom into document text 'remote viewing' with yellow highlight.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def build(sc):
    dark_world(sc, (0.06, 0.06, 0.062, 1))
    setup_bloom(sc, threshold=1.05, size=0.35, strength=0.5)
    cam = add_camera(sc, location=(0, -8, 0), rot=(math.pi / 2, 0, 0), lens=50)
    m = paper_mat('doc_mat', os.path.join(ASSETS, 's09_doc.png'), rough=0.55, glow=0.9)
    doc = plate('doc', 0, 0, 0, 16, 10.6, m)
    # yellow highlight behind 'remote viewing'
    hl = rounded_box('hl', -1.55, -1.35, 1.6, 4.35, 1.35, 0.02, (1.0, 0.88, 0.12), emit=0.0)
    hm = bpy.data.materials.new('hl_mat')
    hm.use_nodes = True
    b = hm.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (1.0, 0.86, 0.1, 1)
    if 'Emission Color' in b.inputs:
        b.inputs['Emission Color'].default_value = (1.0, 0.86, 0.1, 1)
        b.inputs['Emission Strength'].default_value = 0.7
    hl.data.materials.clear()
    hl.data.materials.append(hm)
    return cam, doc, hl


def animate(sc, cam, doc, hl):
    for fr, cy, s in ((259, -8.6, 1.0), (262, -7.6, 1.12)):
        cam.location = (0, cy, 0)
        cam.keyframe_insert('location', frame=fr)
        doc.scale = (8 * s, 5.3 * s, 1)
        doc.keyframe_insert('scale', frame=fr)
    # highlight grows in
    hl.scale = (0.001, 1, 1)
    hl.keyframe_insert('scale', frame=260)
    hl.scale = (1, 1, 1)
    hl.keyframe_insert('scale', frame=261)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s09')
    first, last = int(args.get('first', 259)), int(args.get('last', 262))
    sc = clean_scene()
    cam, doc, hl = build(sc)
    animate(sc, cam, doc, hl)
    render_range(sc, out, first, last)
