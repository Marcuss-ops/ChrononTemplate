"""Scene 05 - archival_evidence_box (frames 0091-0137).

Reference beats: continuous zoom-out chain of nested vignettes:
red crystal ball scene -> framed inside a red dossier panel ->
orange figure at Soviet-flag computer -> blue thought-bubble figure.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def build(sc):
    dark_world(sc, (0.003, 0.002, 0.004, 1))
    setup_bloom(sc, threshold=0.8, size=0.55, strength=1.0)
    starfield(count=140, seed=31)

    # ---- beat A (91-107): red crystal ball with figure
    camA = add_camera(sc, location=(0, -10, 1.2), rot=(math.pi / 2, 0, 0), lens=52)
    figA = blob_figure('seer', -2.6, 1.5, -2.2, scale=1.05, color=(0.68, 0.1, 0.14),
                       rim=(1.0, 0.32, 0.32), pose='stand')
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.35, location=(1.4, 0, -0.4), segments=48, ring_count=24)
    ball = bpy.context.object
    ball.name = 'crystal'
    bm = bpy.data.materials.new('crystal_mat')
    bm.use_nodes = True
    nt = bm.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    mix = nt.nodes.new('ShaderNodeMixShader')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value = (1.0, 0.32, 0.36, 1)
    em.inputs[1].default_value = 1.8
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs['Facing'], inv.inputs[1])
    nt.links.new(inv.outputs[0], mix.inputs['Fac'])
    nt.links.new(em.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    ball.data.materials.append(bm)
    ped = rounded_box('pedestal', 1.4, 0, -2.3, 1.8, 1.2, 1.4, (0.62, 0.1, 0.13), bevel=0.2, emit=1.2)

    # ---- beat B (108-115): red dossier panel containing mini scene
    dossier = rounded_box('dossier', 40, 2, 0, 9.5, 11.5, 0.9, (0.68, 0.1, 0.13), bevel=0.35, emit=1.5)
    inner = rounded_box('dossier_inner', 40, 1.45, 0.2, 6.6, 8.2, 0.3, (0.1, 0.02, 0.03), bevel=0.2)

    # ---- beat C (116-127): orange figure at Soviet computer
    figC = blob_figure('operator', 80, 2.5, -2.6, scale=1.1, color=(0.85, 0.32, 0.06),
                       rim=(1.0, 0.55, 0.15), pose='sit')
    desk = rounded_box('desk', 80, -1.5, -1.9, 9, 2.2, 1.2, (0.85, 0.32, 0.06), bevel=0.18, emit=1.6)
    mon = rounded_box('monitor', 80, -1.2, 0.7, 5.6, 3.6, 0.5, (0.85, 0.32, 0.06), bevel=0.14, emit=1.8)
    flag_m = paper_mat('flag_mat', os.path.join(ASSETS, 's05_flag.png'), rough=0.5)
    flag = plate('flag', 80, -1.55, 0.75, 4.9, 3.0, flag_m)
    tower = rounded_box('tower', 85.2, -1.3, -0.2, 1.6, 3.2, 2.6, (0.85, 0.32, 0.06), bevel=0.14, emit=1.6)

    # ---- beat D (128-137): blue thought-bubble figure
    figD = blob_figure('dreamer', 120, 0, -2.8, scale=1.15, color=(0.1, 0.28, 0.85),
                       rim=(0.35, 0.65, 1.0), pose='sit')
    cloud = []
    for i, (dx, dz, r) in enumerate(((0, 3.4, 1.15), (-1.35, 3.0, 0.85), (1.3, 3.05, 0.8),
                                     (-2.3, 2.6, 0.5), (2.25, 2.65, 0.48))):
        cloud.append(glow_sphere(f'cloud{i}', 120 + dx, -1.2, dz, r, (0.35, 0.62, 1.0), strength=1.4))
    for i, (dx, dz, r) in enumerate(((-1.1, 1.9, 0.28), (-1.65, 1.35, 0.2))):
        cloud.append(glow_sphere(f'cdrop{i}', 120 + dx, -1.2, dz, r, (0.35, 0.62, 1.0), strength=3))

    beats = [(camA, [figA, ball, ped], 91, 107),
             (camA, [dossier, inner], 108, 115),
             (camA, [figC, desk, mon, flag, tower], 116, 127),
             (camA, [figD] + cloud, 128, 137)]
    return beats


def animate(sc, beats):
    cam = beats[0][0]
    # each beat: camera at that vignette, gentle push-in; items scale in at beat start
    for bi, (_, objs, f0, f1) in enumerate(beats):
        cx = (0, 40, 80, 120)[bi]
        cam_y, cam_z = ((-11.5, 1.2), (-11.5, 1.2), (-16.5, 2.6), (-13.5, 1.0))[bi]
        for ob in objs:
            if ob.name.startswith(('cloud', 'cdrop', 'fig', 'seer', 'dreamer', 'operator',
                                   'crystal', 'pedestal', 'dossier', 'desk', 'monitor', 'flag', 'tower')):
                full = tuple(ob.scale)
                ob.scale = (0.001, 0.001, 0.001)
                ob.keyframe_insert('scale', frame=f0 - 2)
                ob.scale = full
                ob.keyframe_insert('scale', frame=f0)
        cam.location = (cx, cam_y, cam_z)
        cam.keyframe_insert('location', frame=f0)
        cam.location = (cx, cam_y + 1.3, cam_z - 0.2)
        cam.keyframe_insert('location', frame=f1)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s05')
    first, last = int(args.get('first', 91)), int(args.get('last', 137))
    sc = clean_scene()
    beats = build(sc)
    animate(sc, beats)
    render_range(sc, out, first, last, skip=(108,))
