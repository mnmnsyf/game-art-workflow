"""Blender helpers for hand-built scene parts (import as a module from your build script, inside Blender):
procedural weathered materials (concrete / steel / paint over steel), per-channel bake into one atlas,
UV unwrap, edge refinement (bevel + weighted normals), GLB export.

    import sys; sys.path.insert(0, "<skill>/scripts"); import blender_bake as bb
    bb.OUT = Path(out_dir)
    m = bb.mat_slot("W_concrete", "concrete", (0.42, 0.40, 0.37))
    obj.data.materials.append(m); bb.refine_edges(obj, 0.03); bb.uv_unwrap(obj); bb.bake(obj, "pad_base", 2048)
    bb.export_glb(obj, Path(out_dir) / "pad_base.glb")

See references/scene-pipeline.md "Hand-built structures"."""
import math
from pathlib import Path
import bpy

TEX = 1024
OUT = Path('.')   # bake output dir; callers set blender_bake.OUT

# ---------------------------------------------------------------- materials
def _ramp(nt, inp, stops):
    r = nt.nodes.new('ShaderNodeValToRGB'); e = r.color_ramp.elements
    e[0].position, e[0].color = stops[0]; e[1].position, e[1].color = stops[1]
    nt.links.new(inp, r.inputs['Fac']); return r

def _mix(nt, fac, a, b, mode='MIX'):
    m = nt.nodes.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = mode
    L = nt.links.new
    if isinstance(fac, float): m.inputs['Factor'].default_value = fac
    else: L(fac, m.inputs['Factor'])
    for sock, v in ((m.inputs[6], a), (m.inputs[7], b)):
        if isinstance(v, tuple): sock.default_value = v
        else: L(v, sock)
    return m.outputs[2]

def weathered(name, kind, color=(0.5, 0.5, 0.5), rust=0.5, scale=1.0):
    """Procedural weathered surface. kind: concrete | steel | paint. Output channels are routed to an
    Emission shader for baking; returns (material, {channel: socket})."""
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    nt = mat.node_tree; N = nt.nodes; L = nt.links.new; N.clear()
    out = N.new('ShaderNodeOutputMaterial'); emit = N.new('ShaderNodeEmission'); L(emit.outputs[0], out.inputs['Surface'])
    tc = N.new('ShaderNodeTexCoord')
    def noise(s, d=6.0, r=0.6):
        n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = s * scale
        n.inputs['Detail'].default_value = d; n.inputs['Roughness'].default_value = r
        L(tc.outputs['Object'], n.inputs['Vector']); return n.outputs['Fac']
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.samples = 12; ao.inputs['Distance'].default_value = 0.3
    geo = N.new('ShaderNodeNewGeometry')
    cav = _ramp(nt, ao.outputs['AO'], [(0.0, (0.35, 0.35, 0.35, 1)), (1.0, (1, 1, 1, 1))]).outputs['Color']
    # edge wear: where a 2.5 cm shader bevel bends the normal away from the true normal. Unlike Pointiness this
    # does not depend on vertex density, so low-poly boxes don't turn into one big chipped edge.
    bev = N.new('ShaderNodeBevel'); bev.samples = 8; bev.inputs['Radius'].default_value = 0.025
    dot = N.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
    L(bev.outputs['Normal'], dot.inputs[0]); L(geo.outputs['Normal'], dot.inputs[1])
    edge = _ramp(nt, dot.outputs['Value'], [(0.93, (1, 1, 1, 1)), (0.985, (0, 0, 0, 1))]).outputs['Color']
    grime = _ramp(nt, noise(0.8), [(0.35, (0.82, 0.82, 0.82, 1)), (0.65, (1, 1, 1, 1))]).outputs['Color']
    crevice = _ramp(nt, ao.outputs['AO'], [(0.45, (1, 1, 1, 1)), (0.8, (0, 0, 0, 1))]).outputs['Color']
    rust_n = noise(3.0, 8, 0.7)
    rust_patch = _ramp(nt, rust_n, [(0.72 - 0.25 * rust, (0, 0, 0, 1)), (0.82 - 0.25 * rust, (1, 1, 1, 1))]).outputs['Color']
    rust_mask = _mix(nt, 1.0, rust_patch, _mix(nt, 1.0, crevice, (rust,) * 3 + (1,), 'MULTIPLY'), 'LIGHTEN')
    rust_col = _ramp(nt, noise(9.0), [(0.3, (0.12, 0.05, 0.02, 1)), (0.7, (0.30, 0.13, 0.05, 1))]).outputs['Color']
    c = tuple(color) + (1,)
    if kind == 'concrete':
        base = _ramp(nt, noise(2.5, 8, 0.65), [(0.3, tuple(x * 0.75 for x in color) + (1,)), (0.7, c)]).outputs['Color']
        stain = _ramp(nt, noise(0.6), [(0.55, (1, 1, 1, 1)), (0.75, (0.7, 0.68, 0.66, 1))]).outputs['Color']
        base = _mix(nt, 1.0, base, stain, 'MULTIPLY')
        rough = (0.9, 0.9, 0.9, 1); metal = (0, 0, 0, 1)
    elif kind == 'steel':
        base = _ramp(nt, noise(1.2), [(0.3, tuple(x * 0.6 for x in color) + (1,)), (0.7, c)]).outputs['Color']
        base = _mix(nt, rust_mask, base, rust_col)
        base = _mix(nt, edge, base, (0.5, 0.49, 0.47, 1))
        rough = _mix(nt, rust_mask, _ramp(nt, noise(6.0), [(0.3, (0.4,) * 3 + (1,)), (0.7, (0.62,) * 3 + (1,))]).outputs['Color'], (0.85,) * 3 + (1,))
        metal = _mix(nt, rust_mask, (0.9,) * 3 + (1,), (0.1,) * 3 + (1,))
    else:  # paint over steel: chips at edges show bare metal, rust in crevices
        base = _mix(nt, rust_mask, c, rust_col)
        base = _mix(nt, edge, base, (0.42, 0.41, 0.40, 1))
        rough = _mix(nt, edge, (0.55,) * 3 + (1,), (0.35,) * 3 + (1,))
        rough = _mix(nt, rust_mask, rough, (0.85,) * 3 + (1,))
        metal = _mix(nt, edge, (0.0,) * 3 + (1,), (0.85,) * 3 + (1,))
    base = _mix(nt, 1.0, _mix(nt, 1.0, base, grime, 'MULTIPLY'), cav, 'MULTIPLY')
    chans = {'basecolor': base}
    for k, v in (('roughness', rough), ('metallic', metal)):
        if isinstance(v, tuple):
            rgb = N.new('ShaderNodeRGB'); rgb.outputs[0].default_value = v; v = rgb.outputs[0]
        chans[k] = v
    mat['_emit'] = emit.name
    return mat, chans

def bake(obj, tag, res=TEX):
    """Bake every material slot's channels into one atlas per channel, swap in a PBR material."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 12; sc.render.bake.margin = 6
    for o in bpy.context.scene.objects: o.select_set(False)
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    mats = [s.material for s in obj.material_slots]
    imgs = {}
    for ch in ('basecolor', 'roughness', 'metallic'):
        img = bpy.data.images.new(f'{tag}_{ch}', res, res, alpha=False)
        img.colorspace_settings.name = 'sRGB' if ch == 'basecolor' else 'Non-Color'
        for m in mats:
            nt = m.node_tree; emit = nt.nodes[m['_emit']]
            sock = CHANS[m.name][ch]; nt.links.new(sock, emit.inputs['Color'])
            node = nt.nodes.get('_bake') or nt.nodes.new('ShaderNodeTexImage'); node.name = '_bake'
            node.image = img; nt.nodes.active = node
        bpy.ops.object.bake(type='EMIT')
        path = OUT / f'{tag}_{ch}.png'
        img.filepath_raw = str(path); img.file_format = 'PNG'; img.save()   # raw bake values, no view transform
        imgs[ch] = img
    fin = bpy.data.materials.new(f'{tag}_pbr'); fin.use_nodes = True
    fn = fin.node_tree.nodes; fl = fin.node_tree.links; bsdf = fn['Principled BSDF']
    for ch, sock in (('basecolor', 'Base Color'), ('roughness', 'Roughness'), ('metallic', 'Metallic')):
        t = fn.new('ShaderNodeTexImage'); t.image = imgs[ch]; fl.new(t.outputs['Color'], bsdf.inputs[sock])
    obj.data.materials.clear(); obj.data.materials.append(fin)
    return fin

CHANS = {}
def mat_slot(name, kind, color, rust=0.5, scale=1.0):
    if name in bpy.data.materials: return bpy.data.materials[name]
    m, ch = weathered(name, kind, color, rust, scale); CHANS[name] = ch; return m

def uv_unwrap(obj):
    for o in bpy.context.scene.objects: o.select_set(False)
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')

def export_glb(obj, path):
    for o in bpy.context.scene.objects: o.select_set(False)
    obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True)

def tris(obj): return sum(len(p.vertices) - 2 for p in obj.data.polygons)

def refine_edges(obj, width, segments=2, angle=30.0):
    """Small bevel on hard edges + smooth-by-angle + face-area weighted normals, applied.
    Gives game-style edge highlights instead of razor-sharp CG edges."""
    for o in bpy.context.scene.objects: o.select_set(False)
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    b = obj.modifiers.new('art_bevel', 'BEVEL')
    b.width = width; b.segments = segments; b.limit_method = 'ANGLE'; b.angle_limit = math.radians(angle)
    b.use_clamp_overlap = True; b.profile = 0.6
    bpy.ops.object.modifier_apply(modifier=b.name)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle), keep_sharp_edges=True)
    w = obj.modifiers.new('art_wn', 'WEIGHTED_NORMAL'); w.mode = 'FACE_AREA'; w.keep_sharp = True; w.weight = 50
    bpy.ops.object.modifier_apply(modifier=w.name)
    return obj

