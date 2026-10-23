"""Scene 08 - tactical_radar_graphic (frames 0239-0246).

Reference beats: mirrored orange seated figures split by a white light bar,
then bright green vertical panels sweeping with figure silhouettes.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *


def build(sc):
    dark_world(sc, (0.002, 0.003, 0.002, 1))
    setup_bloom(sc, threshold=0.85, size=0.5, strength=0.9)
    cam = add_camera(sc, location=(0, -13, 0.8), rot=(math.pi / 2, 0, 0), lens=52)

    orange = (0.85, 0.32, 0.06)
    rim = (1.0, 0.55, 0.15)

    # mirrored seated figures
    left = blob_figure('seatL', -6.5, 1.5, -2.8, scale=1.35, color=orange, rim=rim, pose='sit')
    chairL = rounded_box('chairL', -6.5, 3.4, -1.7, 3.4, 3.6, 0.5, orange, bevel=0.25, emit=1.5)
    right = blob_figure('seatR', 6.5, 1.5, -2.8, scale=1.35, color=orange, rim=rim, pose='sit')
    right.rotation_euler = (0, 0, math.pi)
    chairR = rounded_box('chairR', 6.5, 3.4, -1.7, 3.4, 3.6, 0.5, orange, bevel=0.25, emit=1.5)

    # central white light bar
    bar = rounded_box('lightbar', 0, 0, 0.4, 0.22, 0.22, 12.5, (1.0, 0.98, 0.95), emit=9)

    # green panels (sweep in later)
    panels = []
    for i, px in enumerate((-4.2, 4.2)):
        p = rounded_box(f'green{i}', px, -0.5, 0, 5.2, 0.3, 12.0, (0.16, 0.95, 0.2), emit=3.2)
        panels.append(p)
    sils = []
    for i, (sx, flip) in enumerate(((-4.2, 1), (4.2, -1))):
        s = blob_figure(f'sil{i}', sx, -1.2, -2.2, scale=1.0, color=(0.08, 0.45, 0.12),
                        rim=(0.35, 1.0, 0.4), pose='sit')
        s.rotation_euler = (0, 0, 0 if flip == 1 else math.pi)
        sils.append(s)

    return cam, [left, chairL, right, chairR, bar], panels, sils


def animate(sc, cam, early, panels, sils):
    cam.location = (0, -13.5, 0.8)
    cam.keyframe_insert('location', frame=239)
    cam.location = (0, -12.6, 0.8)
    cam.keyframe_insert('location', frame=246)
    for ob in panels + sils:
        full = tuple(ob.scale)
        ob.scale = (0.001, 0.001, 0.001)
        ob.keyframe_insert('scale', frame=241)
        ob.scale = full
        ob.keyframe_insert('scale', frame=243)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s08')
    first, last = int(args.get('first', 239)), int(args.get('last', 246))
    sc = clean_scene()
    cam, early, panels, sils = build(sc)
    animate(sc, cam, early, panels, sils)
    render_range(sc, out, first, last)
