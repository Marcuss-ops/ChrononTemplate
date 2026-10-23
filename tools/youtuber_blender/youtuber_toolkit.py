"""Shared Blender toolkit for Youtuberstle native rebuilds.

Look target: smooth volumetric neon figures, dark starfield backdrops,
warm paper/dossier plates, soft bloom edges (Blender 5.2 EEVEE + Glare/Bloom).
"""
import bpy
import math
import os
import sys
from mathutils import Vector

# ---------------------------------------------------------------- scene setup

def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    try:
        sc.render.engine = 'BLENDER_EEVEE_NEXT'
    except Exception:
        sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False
    return sc


def dark_world(sc, color=(0.0015, 0.0012, 0.0025, 1.0)):
    world = bpy.data.worlds.new('dark')
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs[0].default_value = color
    bg.inputs[1].default_value = 1.0
    sc.world = world


def setup_bloom(sc, threshold=0.9, size=0.55, strength=1.0):
    ng = bpy.data.node_groups.new('comp', 'CompositorNodeTree')
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    sc.compositing_node_group = ng
    rl = ng.nodes.new('CompositorNodeRLayers')
    gl = ng.nodes.new('CompositorNodeGlare')
    gl.inputs['Type'].default_value = 'Bloom'
    gl.inputs['Threshold'].default_value = threshold
    gl.inputs['Size'].default_value = size
    gl.inputs['Strength'].default_value = strength
    go = ng.nodes.new('NodeGroupOutput')
    ng.links.new(rl.outputs['Image'], gl.inputs['Image'])
    ng.links.new(gl.outputs['Image'], go.inputs['Image'])


def add_camera(sc, location=(0, -10, 0), rot=(math.pi / 2, 0, 0), lens=50):
    cam = bpy.data.cameras.new('cam')
    cam.lens = lens
    ob = bpy.data.objects.new('cam', cam)
    sc.collection.objects.link(ob)
    ob.location = location
    ob.rotation_euler = rot
    sc.camera = ob
    return ob

# ---------------------------------------------------------------- materials

def emission_mat(name, color, strength=8.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value = (*color, 1.0)
    em.inputs[1].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def neon_body_mat(name, core, rim, rough=0.32, emit=0.55):
    """Volumetric neon: principled base + fresnel rim emission (figure look)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    mix = nt.nodes.new('ShaderNodeMixShader')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    dark = tuple(c * 0.10 for c in core)
    bsdf.inputs['Base Color'].default_value = (*dark, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    if 'Emission Color' in bsdf.inputs:
        bsdf.inputs['Emission Color'].default_value = (*core, 1.0)
        bsdf.inputs['Emission Strength'].default_value = emit * 0.25
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value = (*rim, 1.0)
    em.inputs[1].default_value = 2.4
    fres = nt.nodes.new('ShaderNodeLayerWeight')
    fres.inputs['Blend'].default_value = 0.35
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.58
    ramp.color_ramp.elements[1].position = 0.97
    nt.links.new(fres.outputs['Facing'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], mix.inputs['Fac'])
    nt.links.new(bsdf.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m


def paper_mat(name, image_path, rough=0.62, glow=1.0):
    """Self-lit image plane (screens/graphics look, no scene lights needed)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = rough
    tex = nt.nodes.new('ShaderNodeTexImage')
    img = bpy.data.images.load(image_path)
    tex.image = img
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    if 'Emission Color' in bsdf.inputs:
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = glow
    return m

# ---------------------------------------------------------------- geometry

def _meta_el(mb, co, radius, stiff=2.0):
    el = mb.elements.new()
    el.co = co
    el.radius = radius
    el.stiffness = stiff
    return el


def blob_figure(name, x, y, z, scale=1.0, color=(0.9, 0.08, 0.55),
                rim=None, pose='stand', rot_z=0.0):
    """Smooth tube humanoid built from beveled curves + sphere head
    (matches the inflated neon-tube figure style of the references)."""
    rim = rim or tuple(min(1.0, c * 1.6 + 0.25) for c in color)
    s = scale
    cu = bpy.data.curves.new(name + '_cu', 'CURVE')
    cu.dimensions = '3D'
    cu.fill_mode = 'FULL'
    try:
        cu.use_fill_caps = True
    except Exception:
        pass
    cu.bevel_depth = 0.36 * s
    cu.bevel_resolution = 8
    cu.resolution_u = 24
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)

    def spline(pts, radii=None):
        sp = cu.splines.new('BEZIER')
        sp.bezier_points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            bp = sp.bezier_points[i]
            bp.co = (p[0] * s, p[1] * s, p[2] * s)
            bp.handle_left_type = bp.handle_right_type = 'AUTO'
            bp.radius = radii[i] if radii else 1.0

    # torso spine: hip -> neck (gentle S curve)
    spline([(0, 0, 1.05), (0.14, 0, 1.95), (0, 0, 2.85)], [1.3, 1.5, 1.15])
    # legs
    spline([(-0.12, 0, 1.2), (-0.32, 0, 0.4), (-0.36, 0, -0.5)], [1.15, 0.95, 0.78])
    spline([(0.12, 0, 1.2), (0.32, 0, 0.4), (0.36, 0, -0.5)], [1.15, 0.95, 0.78])
    if pose == 'stand':
        spline([(-0.18, 0, 2.5), (-0.8, 0, 1.85), (-0.95, 0, 1.1)], [1.0, 0.82, 0.62])
        spline([(0.18, 0, 2.5), (0.8, 0, 1.85), (0.95, 0, 1.1)], [1.0, 0.82, 0.62])
    elif pose == 'raise':  # right arm raised overhead holding orb
        spline([(0.18, 0, 2.55), (0.95, 0, 3.15), (0.72, 0, 4.15)], [1.0, 0.85, 0.62])
        spline([(-0.18, 0, 2.5), (-0.8, 0, 1.85), (-0.95, 0, 1.1)], [1.0, 0.82, 0.62])
    elif pose == 'reach':  # forward lean, arm extended
        spline([(0.2, 0, 2.5), (1.15, 0, 2.35), (1.95, 0, 2.3)], [1.0, 0.85, 0.6])
        spline([(-0.18, 0, 2.45), (-0.75, 0, 1.8), (-0.9, 0, 1.05)], [1.0, 0.82, 0.62])
    elif pose == 'sit':
        spline([(0, 0, 1.1), (0, 0.55, 0.8), (0, 1.15, 0.55)], [1.35, 1.2, 0.9])
        spline([(-0.18, 0, 2.5), (-0.85, 0, 1.95), (-1.05, 0, 1.35)], [1.0, 0.82, 0.62])
        spline([(0.18, 0, 2.5), (0.85, 0, 1.95), (1.05, 0, 1.35)], [1.0, 0.82, 0.62])

    mat = neon_body_mat(name + '_mat', color, rim)
    ob.data.materials.append(mat)

    # head sphere (local coords, parented so it follows the figure)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.58 * s, segments=32, ring_count=16)
    head = bpy.context.object
    head.name = name + '_head'
    for p in head.data.polygons:
        p.use_smooth = True
    head.data.materials.append(mat)
    head.parent = ob
    head.location = (0.03 * s, 0, 3.38 * s)

    ob.location = (x, y, z)
    ob.rotation_euler = (0, 0, rot_z)
    return ob


def glow_sphere(name, x, y, z, radius, color, strength=14.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(x, y, z), segments=32, ring_count=16)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(emission_mat(name + '_mat', color, strength))
    return ob


def glow_torus(name, x, y, z, major, minor, color, strength=10.0, rot=(math.pi / 2, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(location=(x, y, z), major_radius=major,
                                     minor_radius=minor, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(emission_mat(name + '_mat', color, strength))
    return ob


def plate(name, x, y, z, w, h, mat, rot=(math.pi / 2, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x, y, z), rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (w / 2, h / 2, 1)
    ob.data.materials.append(mat)
    return ob


def rounded_box(name, x, y, z, w, h, d, color, bevel=0.08, emit=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=(x, y, z), rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (w / 2, h / 2, d / 2)
    bpy.ops.object.transform_apply(scale=True)
    bev = ob.modifiers.new('bev', 'BEVEL')
    bev.width = bevel
    bev.segments = 4
    if emit:
        ob.data.materials.append(emission_mat(name + '_mat', color, emit))
    else:
        m = bpy.data.materials.new(name + '_mat')
        m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (*color, 1.0)
        b.inputs['Roughness'].default_value = 0.4
        ob.data.materials.append(m)
    return ob

# ---------------------------------------------------------------- backdrop

def starfield(count=220, seed=7, radius=60.0, z=25.0):
    import random
    rnd = random.Random(seed)
    for i in range(count):
        x = rnd.uniform(-radius, radius)
        y = rnd.uniform(-6, 20)
        zz = rnd.uniform(-6, z)
        r = rnd.uniform(0.015, 0.06)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, zz), segments=8, ring_count=6)
        ob = bpy.context.object
        ob.name = f'star_{i}'
        a = rnd.uniform(0.15, 0.75)
        m = emission_mat(f'star_{i}_mat', (a, a * 0.92, a), rnd.uniform(0.6, 2.4))
        ob.data.materials.append(m)


def vignette_glow(name, x, y, z, radius, color, strength=0.14):
    """Big soft radial glow blob behind the action."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(x, y, z), segments=32, ring_count=16)
    ob = bpy.context.object
    ob.name = name
    m = bpy.data.materials.new(name + '_mat')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    mix = nt.nodes.new('ShaderNodeMixShader')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value = (*color, 1.0)
    em.inputs[1].default_value = 3.0
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    inv = nt.nodes.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = strength
    nt.links.new(lw.outputs['Facing'], inv.inputs[1])
    nt.links.new(inv.outputs[0], mul.inputs[0])
    nt.links.new(mul.outputs[0], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    ob.data.materials.append(m)
    return ob

# ---------------------------------------------------------------- text texture

FONT_DIR = '/mnt/c/Users/pater/Pyt/Chronon3d/assets/fonts'


def text_texture(path, lines, size=90, color=(245, 240, 230), bg=(8, 8, 12),
                 font='Inter-Bold.ttf', align='left', width=1600, pad=60,
                 highlight=None, highlight_color=(255, 226, 40), line_gap=1.35):
    """Render text into a PNG texture with PIL (used on Blender planes)."""
    from PIL import Image, ImageDraw, ImageFont
    font_path = os.path.join(FONT_DIR, font)
    fnt = ImageFont.truetype(font_path, size)
    heights = []
    for ln in lines:
        heights.append(int(size * line_gap))
    W = width
    H = pad * 2 + sum(heights)
    img = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(img)
    y = pad
    for ln, h in zip(lines, heights):
        if highlight and highlight in ln:
            x0 = 0 if align == 'left' else None
            bbox = d.textbbox((0, 0), ln, font=fnt)
            tw = bbox[2] - bbox[0]
            hx = pad if align == 'left' else (W - tw) // 2
            d.rectangle([hx - 12, y + int(size * 0.12), hx + tw + 12, y + int(size * 1.05)],
                        fill=highlight_color)
        if align == 'left':
            d.text((pad, y), ln, font=fnt, fill=color)
        else:
            d.text((W / 2, y), ln, font=fnt, fill=color, anchor='ma')
        y += h
    img.save(path)
    return path

# ---------------------------------------------------------------- render loop

def render_range(sc, out_dir, first, last, skip=()):
    os.makedirs(out_dir, exist_ok=True)
    sc.render.filepath = os.path.join(out_dir, 'frame_')
    sc.render.image_settings.file_format = 'PNG'
    sc.frame_start = first
    sc.frame_end = last
    for fr in range(first, last + 1):
        if fr in skip:
            continue
        sc.frame_set(fr)
        sc.render.filepath = os.path.join(out_dir, f'frame_{fr:04d}')
        bpy.ops.render.render(write_still=True)
    print(f'ReNDERED {out_dir} frames {first}-{last}')


def parse_args():
    if '--' in sys.argv:
        return dict(zip(sys.argv[sys.argv.index('--') + 1::2],
                        sys.argv[sys.argv.index('--') + 2::2]))
    return {}
