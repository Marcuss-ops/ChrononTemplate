"""Scene 11 - subject_tilt_reframe (frames 0329-0336).

Reference: light-line reveal + '1979 / PROJECT STARGATE CHALLENGE' gold title,
brain image plate appearing above the line.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def build(sc):
    dark_world(sc, (0.002, 0.002, 0.004, 1))
    setup_bloom(sc, threshold=0.75, size=0.55, strength=1.05)
    starfield(count=110, seed=51)
    cam = add_camera(sc, location=(0, -13, 0.8), rot=(math.pi / 2, 0, 0), lens=52)

    # glowing horizontal light line
    line = rounded_box('lightline', 0, -1.0, -0.6, 15, 0.14, 0.14, (1.0, 0.98, 0.94), emit=8)

    # brain image plate above the line
    brain_m = emission_mat('brain_mat', (0.12, 0.25, 0.75), 1.6)
    brain = plate('brain', 0, -0.6, 3.4, 6.2, 3.4, brain_m)
    ring = glow_torus('brain_ring', 0, -0.6, 3.4, 2.1, 0.12, (0.35, 0.6, 1.0), strength=6)

    m = paper_mat('t11_mat', os.path.join(ASSETS, 's11_title.png'), rough=0.45, glow=1.1)
    title = plate('t11', 0, -1.3, -2.1, 11.5, 6.4, m)

    return cam, line, brain, ring, title


def animate(sc, cam, line, brain, ring, title):
    for fr, cy in ((329, -13.6), (333, -12.8), (336, -12.3)):
        cam.location = (0, cy, 0.8)
        cam.keyframe_insert('location', frame=fr)
    # line sweeps open
    line.scale = (0.02, 1, 1)
    line.keyframe_insert('scale', frame=329)
    line.scale = (1, 1, 1)
    line.keyframe_insert('scale', frame=331)
    # brain + ring grow in
    for ob in (brain, ring):
        full = tuple(ob.scale)
        ob.scale = (0.001, 0.001, 0.001)
        ob.keyframe_insert('scale', frame=330)
        ob.scale = full
        ob.keyframe_insert('scale', frame=333)
    title.scale = (0.001, 0.001, 0.001)
    title.keyframe_insert('scale', frame=330)
    title.scale = (5.75, 3.2, 1)
    title.keyframe_insert('scale', frame=332)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s11')
    first, last = int(args.get('first', 329)), int(args.get('last', 336))
    sc = clean_scene()
    cam, line, brain, ring, title = build(sc)
    animate(sc, cam, line, brain, ring, title)
    render_range(sc, out, first, last)
