"""Package an assembled Blender scene for a game engine (headless Blender).

blender -b <scene>/S3_assembly/<scene>.blend -P <skill>/scripts/blender_export_engine.py -- <scene>/S4_<engine>
      [--max-tex 2048] [--kit LaunchPad] [--map kits.json]

Writes OUT_DIR/fbx/SM_*.fbx (one per unique asset, transform reset to identity), OUT_DIR/textures/T_*_D.png and
T_*_ORM.png (R = AO 1, G = roughness, B = metallic), and OUT_DIR/package.json with assets, material slots,
instance placements and the game cameras (Blender coordinates, metres; UE conversion happens in the UE script).
Hidden objects, child objects and anything the map sets to null are not exported.
"""
import json, math, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector


import argparse
_P = argparse.ArgumentParser()
_P.add_argument("out"); _P.add_argument("--max-tex", type=int, default=2048)
_P.add_argument("--kit", default="Scene", help="kit name for assets the map does not name (e.g. LaunchPad)")
_P.add_argument("--map", help='JSON {"<collection id or object base name>": ["Kit", "Name"] | null}; null skips it')
_ARGS = _P.parse_args(sys.argv[sys.argv.index('--') + 1:])
OUT = Path(_ARGS.out).resolve(); MAX_TEX = _ARGS.max_tex
MAP = json.loads(Path(_ARGS.map).read_text()) if _ARGS.map else {}
(OUT / 'fbx').mkdir(parents=True, exist_ok=True); (OUT / 'textures').mkdir(exist_ok=True)


def pascal(s): return ''.join(w.capitalize() for w in s.split('_'))


def asset_key(o):
    """(kit, name) for a top-level mesh, or None to skip it. Lookup order: object base name, collection id
    (the part before the first '_', e.g. 'C04'), full collection name; default: (--kit, PascalCase of the
    collection name without its id)."""
    col = o.users_collection[0].name if o.users_collection else ''
    for k in (o.name.split('.')[0], o.name.split('.')[0].split('_')[0], col.split('_')[0], col):
        if k in MAP:
            return tuple(MAP[k]) if MAP[k] else None
    return (_ARGS.kit, pascal(col.split('_', 1)[1] if '_' in col else col))


def pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32); img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def save_png(arr, path, colorspace):
    h, w = arr.shape[:2]
    if max(w, h) > MAX_TEX:   # box-filter down by an integer factor (4096 -> 2048)
        f = -(-max(w, h) // MAX_TEX)
        arr = arr[:h - h % f, :w - w % f].reshape(h // f, f, w // f, f, -1).mean(axis=(1, 3)); h, w = arr.shape[:2]
    img = bpy.data.images.new(path.stem, w, h, alpha=False)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.filepath_raw = str(path); img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)


def source(sock):
    """(image, channel) feeding a BSDF input, or (None, constant)."""
    if not sock.links: return None, sock.default_value
    n = sock.links[0].from_node; out = sock.links[0].from_socket.name
    if n.type == 'SEPARATE_COLOR':
        ch = {'Red': 0, 'Green': 1, 'Blue': 2}[out]; n = n.inputs[0].links[0].from_node
        return n.image, ch
    if n.type == 'TEX_IMAGE': return n.image, 0
    raise RuntimeError(f'unsupported node {n.type} on {sock.name}')


def export_textures(mat, tex_name):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bc, _ = source(bsdf.inputs['Base Color'])
    if bc is None: raise RuntimeError(f'{mat.name}: no base colour texture')
    d = pixels(bc)
    save_png(d, OUT / 'textures' / f'{tex_name}_D.png', 'sRGB')
    chans = []
    for k in ('Roughness', 'Metallic'):
        img, ch = source(bsdf.inputs[k])
        chans.append((pixels(img)[..., ch], img.size[0]) if img else (float(ch), 0))
    res = max([c[1] for c in chans] + [64])
    orm = np.ones((res, res, 4), np.float32)
    for i, (v, n) in enumerate(chans, start=1):
        if isinstance(v, float): orm[..., i] = v
        else:
            if n != res:  # nearest resample to the larger map
                idx = (np.arange(res) * n // res)
                v = v[idx][:, idx]
            orm[..., i] = v
    save_png(orm, OUT / 'textures' / f'{tex_name}_ORM.png', 'Non-Color')
    return {'D': f'{tex_name}_D', 'ORM': f'{tex_name}_ORM', 'size': [bc.size[0], res],
            'const': {k: (c[0] if isinstance(c[0], float) else None) for k, c in zip(('roughness', 'metallic'), chans)}}


assets, placements = {}, []
for o in bpy.data.objects:
    if o.type != 'MESH' or o.hide_render or o.parent is not None: continue
    key = asset_key(o)
    if not key: continue
    kit, name = key; sm = f'SM_{kit}_{name}'
    placements.append({'asset': sm, 'object': o.name, 'location': list(o.location),
                       'rotation_deg': [math.degrees(a) for a in o.rotation_euler], 'scale': list(o.scale)})
    if sm in assets: continue
    slots = []
    for i, s in enumerate(o.material_slots):
        suffix = '' if len(o.material_slots) == 1 else f'_{i + 1:02d}'
        mi = f'MI_{kit}_{name}{suffix}'
        info = export_textures(s.material, f'T_{kit}_{name}{suffix}')
        s.material.name = mi           # FBX slot name == material instance name
        slots.append({'slot': i, 'mi': mi, **info})
    saved = o.matrix_world.copy(); o.matrix_world = Matrix.Identity(4)
    for x in bpy.context.scene.objects: x.select_set(x == o)
    bpy.context.view_layer.objects.active = o
    bpy.ops.export_scene.fbx(filepath=str(OUT / 'fbx' / f'{sm}.fbx'), use_selection=True, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Y', axis_up='Z',
                             mesh_smooth_type='FACE', use_tspace=True, add_leaf_bones=False,
                             bake_space_transform=False, path_mode='STRIP', embed_textures=False)
    o.matrix_world = saved
    me = o.data
    vs = [v.co for v in me.vertices]
    assets[sm] = {'kit': kit, 'fbx': f'fbx/{sm}.fbx', 'slots': slots,
                  'triangles': sum(len(p.vertices) - 2 for p in me.polygons),
                  'local_bounds': [[min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]]}
    print('ASSET', sm, assets[sm]['triangles'], len(slots), flush=True)

cams = []
for c in [o for o in bpy.data.objects if o.type == 'CAMERA']:
    m = c.matrix_world
    cams.append({'name': c.name, 'location': list(m.translation),
                 'forward': list((m.to_3x3() @ Vector((0, 0, -1))).normalized()),
                 'up': list((m.to_3x3() @ Vector((0, 1, 0))).normalized()),
                 'hfov_deg': math.degrees(2 * math.atan(c.data.sensor_width / 2 / c.data.lens))})
(OUT / 'package.json').write_text(json.dumps({'assets': assets, 'placements': placements, 'cameras': cams}, indent=1))
print('PACKAGE', len(assets), 'assets', len(placements), 'placements', len(cams), 'cameras', flush=True)
