"""Scene 07 - archive_scene_pan (frames 0185-0208).

Reference beats: big orange seated silhouette -> two orange figures, one
holding a glowing paper -> wider archive desk scene with subtitle line.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def build(sc):
    dark_world(sc, (0.003, 0.002, 0.002, 1))
    setup_bloom(sc, threshold=0.8, size=0.55, strength=1.0)
    starfield(count=110, seed=41)
    cam = add_camera(sc, location=(-2, -12, 1.0), rot=(math.pi / 2, 0, -0.06), lens=52)

    orange = (0.85, 0.32, 0.06)
    rim = (1.0, 0.55, 0.15)

    # big seated figure left (opening close-up)
    big = blob_figure('clerk_big', -4.5, 1.0, -2.6, scale=1.6, color=orange, rim=rim, pose='sit')
    chair = rounded_box('chair1', -4.5, 2.6, -1.6, 3.2, 3.4, 0.5, orange, bevel=0.25, emit=1.6)

    # mid: two figures, one holding glowing paper
    f2 = blob_figure('holder', 8.5, 1.5, -2.8, scale=1.05, color=orange, rim=rim, pose='raise')
    paper = plate('glow_paper', 10.2, 1.2, 1.6, 1.4, 1.8,
                  emission_mat('paper_mat', (1.0, 0.93, 0.82), 6))
    f3 = blob_figure('sitter', 12.8, 1.8, -2.9, scale=1.0, color=orange, rim=rim, pose='sit')
    chair2 = rounded_box('chair2', 12.8, 3.2, -1.9, 2.6, 2.8, 0.5, orange, bevel=0.22, emit=1.6)

    # far: desk row
    desk = rounded_box('desk', 20.5, 1.0, -1.6, 9, 2.0, 1.1, orange, bevel=0.18, emit=1.5)
    for i, fx in enumerate((18.2, 22.8)):
        blob_figure(f'worker{i}', fx, 2.4, -2.9, scale=0.95, color=orange, rim=rim, pose='sit')

    objs = [big, chair, f2, paper, f3, chair2, desk] + [o for o in sc.objects if o.name.startswith('worker')]
    return cam, objs


def animate(sc, cam, objs):
    # slow pan left -> right revealing the archive
    for fr, cx in ((185, -2.5), (197, 8.0), (208, 17.0)):
        cam.location = (cx, -12.5, 1.0)
        cam.keyframe_insert('location', frame=fr)
    for ob in objs:
        if ob.name in ('holder', 'glow_paper', 'sitter', 'chair2', 'desk') or ob.name.startswith('worker'):
            full = tuple(ob.scale)
            ob.scale = (0.001, 0.001, 0.001)
            ob.keyframe_insert('scale', frame=192)
            ob.scale = full
            ob.keyframe_insert('scale', frame=195)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s07')
    first, last = int(args.get('first', 185)), int(args.get('last', 208))
    sc = clean_scene()
    cam, objs = build(sc)
    animate(sc, cam, objs)
    render_range(sc, out, first, last)
