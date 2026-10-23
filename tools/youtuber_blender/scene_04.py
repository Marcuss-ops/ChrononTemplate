"""Scene 04 - cinematic_title_beat (frames 0068-0080).

Reference beats: red glow backdrop with particles, big soft 'CHAPTER 1'
title with under-glow bar -> pixel-block dissolve toward next vignette.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def build(sc):
    dark_world(sc, (0.012, 0.003, 0.004, 1))
    setup_bloom(sc, threshold=0.7, size=0.65, strength=1.15)
    cam = add_camera(sc, location=(0, -13, 0.4), rot=(math.pi / 2, 0, 0), lens=52)
    vignette_glow('red_halo', 0, 9, 0, 12.0, (0.85, 0.06, 0.07), strength=0.07)
    starfield(count=90, seed=21)

    m = paper_mat('ch_mat', os.path.join(ASSETS, 's04_title.png'), rough=0.42)
    title = plate('chapter', 0, -2.5, 0.6, 12.5, 4.35, m)

    bar = rounded_box('red_bar', 0, -2.2, -3.55, 30, 0.35, 0.12, (0.95, 0.08, 0.1), emit=6)

    # pixel blocks that sweep in later (dissolve motif)
    blocks = []
    import random
    rnd = random.Random(4)
    for i in range(26):
        x = -1.5 + rnd.uniform(0, 7.5)
        z = 1.2 - rnd.uniform(0, 4.2)
        s = rnd.uniform(0.28, 0.5)
        col = (0.95, rnd.uniform(0.35, 0.55), rnd.uniform(0.06, 0.14))
        b = rounded_box(f'px{i}', x, -2.6, z, s, s, s * 0.5, col, bevel=0.05, emit=4.5)
        b.scale = (0.001, 0.001, 0.001)
        blocks.append(b)
    return cam, title, bar, blocks


def animate(sc, cam, title, bar, blocks):
    # slow push-in
    for fr, cy in ((68, -13.5), (74, -12.6), (80, -11.6)):
        cam.location = (0, cy, 0.4)
        cam.keyframe_insert('location', frame=fr)
    # title slight rise
    for fr, z in ((68, 0.2), (80, 0.55)):
        title.location.z = z
        title.keyframe_insert('location', index=2, frame=fr)
    # pixel blocks appear one by one after frame 72
    for i, b in enumerate(blocks):
        f = 72 + int(i * 0.32)
        b.keyframe_insert('scale', frame=f)
        b.scale = (1, 1, 1)
        b.keyframe_insert('scale', frame=f + 2)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s04')
    first, last = int(args.get('first', 68)), int(args.get('last', 80))
    sc = clean_scene()
    cam, title, bar, blocks = build(sc)
    animate(sc, cam, title, bar, blocks)
    render_range(sc, out, first, last)
