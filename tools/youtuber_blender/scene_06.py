"""Scene 06 - documentary_still_evidence (frame 0149).

Reference: close-up of the CIA seal (blue field, red compass star, AGENCY ring).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def build(sc):
    dark_world(sc, (0.01, 0.015, 0.05, 1))
    setup_bloom(sc, threshold=0.95, size=0.4, strength=0.7)
    cam = add_camera(sc, location=(0, -6.2, 0), rot=(math.pi / 2, 0, 0), lens=50)
    m = paper_mat('seal_mat', os.path.join(ASSETS, 's06_seal.png'), rough=0.5, glow=0.75)
    seal = plate('seal', 0, 0, 0, 9.5, 9.5, m)
    return cam, seal


def animate(sc, cam, seal):
    cam.location = (0, -6.2, 0)
    cam.keyframe_insert('location', frame=149)
    cam.location = (0, -5.7, 0.15)
    cam.keyframe_insert('location', frame=149)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s06')
    sc = clean_scene()
    cam, seal = build(sc)
    animate(sc, cam, seal)
    render_range(sc, out, 149, 149)
