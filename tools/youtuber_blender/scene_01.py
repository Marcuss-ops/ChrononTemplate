"""Scene 01 - subject_floating_push (frames 0007-0030).

Reference beats:
  07-13  hero magenta solo, arm raised holding glowing scribble orb
  14-23  second figure + thought bubble + purple beam, orange lab bench right
  24-30  camera pans right, red figures in foreground with shout rays
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *
from mathutils import Vector


def beam_between(name, p1, p2, radius, color, strength=8.0):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    mid = (p1 + p2) / 2
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=d.length, location=mid)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = d.to_track_quat('Z', 'Y')
    ob.data.materials.append(emission_mat(name + '_mat', color, strength))
    return ob


def scale_in(ob, frame, full=None, hidden_first=True):
    full = full if full is not None else tuple(ob.scale)
    if hidden_first:
        ob.scale = (0.001, 0.001, 0.001)
        ob.keyframe_insert('scale', frame=frame - 3)
    ob.scale = full
    ob.keyframe_insert('scale', frame=frame)


def build(sc):
    dark_world(sc)
    setup_bloom(sc, threshold=0.8, size=0.55, strength=1.0)
    starfield(count=170, seed=11)
    cam = add_camera(sc, location=(-1.5, -26.0, 2.2), rot=(math.pi / 2 - 0.02, 0, -0.04), lens=55)

    # hero magenta figure, right of center, arm raised
    fig = blob_figure('hero', 5.4, 0, -2.6, scale=1.15, color=(0.62, 0.03, 0.38),
                      rim=(1.0, 0.12, 0.7), pose='raise')
    orb = glow_sphere('orb', 6.3, 0, 2.8, 0.42, (0.95, 0.5, 0.9), strength=3)
    for i, rr in enumerate((0.8, 0.65, 0.5)):
        glow_torus(f'orb_ring{i}', 6.3, 0, 2.8, rr, 0.035, (0.75, 0.95, 1.0), strength=3.5,
                   rot=(math.pi / 2 + 0.5 + i * 0.5, 0.3 * i, 0.2 * i))

    # second magenta figure + thought bubble + beam (appears mid-sequence)
    fig2 = blob_figure('thinker', 13.5, 2.0, -3.1, scale=0.85, color=(0.55, 0.03, 0.35),
                       rim=(1.0, 0.12, 0.7), pose='stand')
    bubble = glow_sphere('bubble', 12.3, 2.0, 3.6, 0.55, (0.95, 0.75, 0.98), strength=3.5)
    for i, (dx, dz, r) in enumerate(((-1.15, -0.75, 0.16), (-1.55, -1.15, 0.11))):
        glow_sphere(f'bubble_dot{i}', 13.3 + dx, 2.0, 3.6 + dz, r, (0.95, 0.75, 0.98), strength=6)
    beam = beam_between('beam', (6.6, 0, 3.1), (11.2, 1.6, 3.5), 0.06, (0.65, 0.3, 1.0), 4)

    # orange lab bench right (appears mid-sequence)
    lab = []
    lab.append(rounded_box('bench_top', 21.5, 4.0, -1.1, 7.0, 0.35, 1.6, (0.95, 0.42, 0.1), emit=2.2))
    for lx in (18.6, 24.4):
        lab.append(rounded_box('bench_leg' + str(lx), lx, 4.0, -2.6, 0.35, 0.35, 3.0, (0.95, 0.42, 0.1), emit=2.2))
    lab.append(blob_figure('chemist', 21.8, 4.6, -3.4, scale=0.95, color=(0.85, 0.32, 0.06),
                           rim=(1.0, 0.55, 0.15), pose='stand'))
    for i, fx in enumerate((18.9, 19.8, 23.3)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.32, depth=1.1, location=(fx, 3.6, -0.3))
        f = bpy.context.object
        f.name = f'flask{i}'
        f.data.materials.append(emission_mat(f'flask{i}_mat', (1.0, 0.55, 0.12), 4.5))
        lab.append(f)

    # red foreground figures (appear late)
    red1 = blob_figure('red_left', 7.5, -4.0, -5.0, scale=1.15, color=(0.72, 0.12, 0.16),
                       rim=(1.0, 0.35, 0.35), pose='stand')
    red2 = blob_figure('red_right', 17.5, -3.6, -5.0, scale=1.15, color=(0.72, 0.12, 0.16),
                       rim=(1.0, 0.35, 0.35), pose='reach')
    rays = []
    for base_x, base_z, flip in ((7.5, 3.2, 1), (17.5, 3.2, -1)):
        for i, ang in enumerate((-0.55, -0.2, 0.15)):
            p1 = (base_x + flip * (1.0 + i * 0.15), -3.8, base_z + 0.2)
            p2 = (base_x + flip * (2.4 + i * 0.35), -3.8, base_z + 1.5 + i * 0.45)
            rays.append(beam_between(f'ray_{base_x}_{i}', p1, p2, 0.09, (1.0, 0.42, 0.38), 8))

    staged = [(14, [fig2, bubble, beam] + [o for o in sc.objects if o.name.startswith('bubble_dot')]),
              (16, lab),
              (24, [red1, red2] + rays)]
    return cam, fig, orb, staged


def animate(sc, cam, fig, orb, staged):
    # camera pans right over the sequence (reveals later vignettes)
    for fr, cx, cy in ((7, -1.5, -26.0), (19, 3.5, -25.4), (30, 8.0, -23.5)):
        cam.location = (cx, cy, 2.2)
        cam.keyframe_insert('location', frame=fr)
    # hero float
    for fr, z in ((7, -2.6), (19, -2.45), (30, -2.25)):
        fig.location.z = z
        fig.keyframe_insert('location', index=2, frame=fr)
    # orb pulse
    for fr, s in ((7, 1.0), (14, 1.12), (22, 0.96), (30, 1.08)):
        orb.scale = (s, s, s)
        orb.keyframe_insert('scale', frame=fr)
    # staged appearances
    for frame, objects in staged:
        for ob in objects:
            scale_in(ob, frame)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s01')
    first, last = int(args.get('first', 7)), int(args.get('last', 30))
    sc = clean_scene()
    cam, fig, orb, staged = build(sc)
    animate(sc, cam, fig, orb, staged)
    render_range(sc, out, first, last)
