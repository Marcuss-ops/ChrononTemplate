"""Scene 03 - historical_archive_framing (frames 0053-0059).

Reference beats: blurred zoom over a grid of YouTube thumbnails ->
channel page 'Visual Venture' (@VisualVenture, mission line, Subscribe).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def build(sc):
    dark_world(sc, (0.004, 0.004, 0.006, 1))
    setup_bloom(sc, threshold=0.9, size=0.45, strength=0.8)
    cam = add_camera(sc, location=(0, -12, 0), rot=(math.pi / 2, 0, 0), lens=50)

    grid_m = paper_mat('grid_mat', os.path.join(ASSETS, 's03_grid.png'), rough=0.5)
    grid = plate('grid', 0, 2.5, 0, 26, 14.6, grid_m)

    ch_m = paper_mat('ch_mat', os.path.join(ASSETS, 's03_channel.png'), rough=0.5)
    ch = plate('channel', 0, -3.0, 0, 16, 9, ch_m)
    ch.scale = (0.001, 0.001, 0.001)
    return cam, grid, ch


def animate(sc, cam, grid, ch):
    # fast push-in on the grid (motion blur feel via big movement), then channel page
    for fr, cy, s in ((53, -12.0, 1.0), (55, -8.5, 1.25), (56, -6.5, 1.0)):
        if fr < 56:
            cam.location = (0, cy, 0)
            cam.keyframe_insert('location', frame=fr)
    grid.scale = (13, 7.3, 1)
    grid.keyframe_insert('scale', frame=53)
    grid.scale = (16.5, 9.3, 1)
    grid.keyframe_insert('scale', frame=55)
    # channel page scales in
    grid.scale = (16.5, 9.3, 1)
    grid.keyframe_insert('scale', frame=55)
    ch.scale = (0.001, 0.001, 0.001)
    ch.keyframe_insert('scale', frame=55)
    ch.scale = (8, 4.5, 1)
    ch.keyframe_insert('scale', frame=57)
    cam.location = (0, -9, 0)
    cam.keyframe_insert('location', frame=56)
    cam.keyframe_insert('location', frame=59)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s03')
    first, last = int(args.get('first', 53)), int(args.get('last', 59))
    sc = clean_scene()
    cam, grid, ch = build(sc)
    animate(sc, cam, grid, ch)
    render_range(sc, out, first, last)
