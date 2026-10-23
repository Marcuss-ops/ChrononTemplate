"""Scene 13 - newspaper_headline_wipe (frames 0440-0457).

Reference: red figure under spotlight beam, 'JACK ANDERSON' name appears,
newspaper page wipes in at the end.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtuber_toolkit import *
from mathutils import Vector

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def beam_plane(name, p1, p2, width, color, strength):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    mid = (p1 + p2) / 2
    bpy.ops.mesh.primitive_plane_add(size=1, location=mid)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = d.to_track_quat('Y', 'Z')
    ob.scale = (width, d.length / 2, 1)
    m = bpy.data.materials.new(name + '_mat')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    mix = nt.nodes.new('ShaderNodeMixShader')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value = (*color, 1)
    em.inputs[1].default_value = strength
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.55
    nt.links.new(lw.outputs['Facing'], inv.inputs[1])
    nt.links.new(inv.outputs[0], mul.inputs[0])
    nt.links.new(mul.outputs[0], mix.inputs['Fac'])
    nt.links.new(em.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    ob.data.materials.append(m)
    return ob


def build(sc):
    dark_world(sc, (0.004, 0.002, 0.003, 1))
    setup_bloom(sc, threshold=0.8, size=0.55, strength=1.0)
    starfield(count=80, seed=71)
    cam = add_camera(sc, location=(0, -13, 0.5), rot=(math.pi / 2, 0, 0), lens=52)

    # spotlight beam diagonal
    beam = beam_plane('spot', (-2, 1.5, 8.5), (2.2, -1.2, -6.5), 6.5, (0.95, 0.62, 0.55), 1.4)

    fig = blob_figure('redman', 0.4, -0.5, -2.9, scale=1.5, color=(0.62, 0.09, 0.12),
                      rim=(1.0, 0.32, 0.32), pose='stand')

    # name text
    import os as _os
    from PIL import Image, ImageDraw  # noqa: F401  (texture pre-generated below)
    name_png = _os.path.join(ASSETS, 's13_name.png')
    m = paper_mat('name13_mat', name_png, rough=0.5, glow=1.1)
    name = plate('name13', 5.8, -1.6, 1.2, 7.2, 1.5, m)

    news_m = paper_mat('news13_mat', _os.path.join(ASSETS, 's13_news.png'), rough=0.55, glow=1.0)
    news = plate('news13', -8.2, -1.2, 5.6, 4.6, 5.8, news_m)
    news.rotation_euler = (math.pi / 2, 0, -0.45)

    return cam, beam, fig, name, news


def animate(sc, cam, beam, fig, name, news):
    for fr, cy in ((440, -13.6), (449, -12.9), (457, -12.2)):
        cam.location = (0, cy, 0.5)
        cam.keyframe_insert('location', frame=fr)
    name.scale = (0.001, 1, 1)
    name.keyframe_insert('scale', frame=448)
    name.scale = (3.6, 0.75, 1)
    name.keyframe_insert('scale', frame=452)
    news.scale = (0.001, 0.001, 0.001)
    news.keyframe_insert('scale', frame=455)
    news.scale = (2.3, 2.9, 1)
    news.keyframe_insert('scale', frame=457)


if __name__ == '__main__':
    args = parse_args()
    out = args.get('out', '/tmp/s13')
    first, last = int(args.get('first', 440)), int(args.get('last', 457))
    sc = clean_scene()
    cam, beam, fig, name, news = build(sc)
    animate(sc, cam, beam, fig, name, news)
    render_range(sc, out, first, last)
