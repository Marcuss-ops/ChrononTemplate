"""Scene 12 - dramatic_cutout_pushin (frames 0401-0415).

Reference: cyan neon figure holding star cards, push-in; orange map with
route line appears right.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def build(sc):
    dark_world(sc, (0.002, 0.004, 0.004, 1))
    setup_bloom(sc, threshold=0.8, size=0.55, strength=1.0)
    starfield(count=120, seed=61)
    cam = add_camera(sc, location=(0.5, -14, 0.6), rot=(math.pi / 2, 0, 0), lens=52)

    cyan = (0.08, 0.55, 0.55)
    rim = (0.35, 1.0, 0.95)
    fig = blob_figure('agent', -2.2, 0, -2.9, scale=1.35, color=cyan, rim=rim, pose='raise')

    # star cards in raised hand
    cards = []
    for i in range(2):
        c = rounded_box(f'card{i}', -0.55 + i * 0.35, -0.6, 3.55 + i * 0.3, 1.15, 0.12, 1.6,
                        (0.55, 0.95, 0.92), bevel=0.06, emit=3.2,
                        rot=(0, 0.18 - i * 0.3, 0))
        cards.append(c)
    star = glow_sphere('card_star', -0.4, -0.8, 3.75, 0.22, (0.2, 0.9, 0.85), strength=5)

    map_m = paper_mat('map12_mat', os.path.join(ASSETS, 's12_map.png'), rough=0.5, glow=1.0)
    mapob = plate('map12', 5.6, -1.2, 0.6, 5.6, 4.5, map_m)

    return cam, fig, cards + [star], mapob


def animate(sc, cam, fig, cards, mapob):
    # push-in
    for fr, cy in ((401, -14.5), (408, -13.4), (415, -12.2)):
        cam.location = (0.5, cy, 0.6)
        cam.keyframe_insert('location', frame=fr)
    mapob.scale = (0.001, 0.001, 0.001)
    mapob.keyframe_insert('scale', frame=408)
    mapob.scale = (2.8, 2.25, 1)
    mapob.keyframe_insert('scale', frame=411)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s12')
    first, last = int(args.get('first', 401)), int(args.get('last', 415))
    sc = clean_scene()
    cam, fig, cards, mapob = build(sc)
    animate(sc, cam, fig, cards, mapob)
    render_range(sc, out, first, last)
