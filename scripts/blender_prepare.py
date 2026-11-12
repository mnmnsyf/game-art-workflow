"""Run inside Blender (called by model_job.py process): faithful A1 prep of one static GLB.

blender --background --factory-startup --python blender_prepare.py -- --spec spec.json --input raw.glb --output DIR

Does only: real size from the spec (height or longest extent), ground-centred origin, baked
transforms, one named root. Keeps every part, UV layer, material slot and texture. No welding,
decimation, re-unwrap or repaint: those are A2 optimizations and art changes, reviewed separately.
Writes DIR/model.glb, DIR/source.blend and DIR/report.json. Rendering is done by render_asset.py.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not points or not all(math.isfinite(axis) for p in points for axis in p):
        raise ValueError('No finite mesh bounds')
    return (Vector(tuple(min(p[i] for p in points) for i in range(3))),
            Vector(tuple(max(p[i] for p in points) for i in range(3))))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    spec = json.loads(args.spec.read_text(encoding='utf-8-sig'))
    axis = spec.get('size_axis', 'height')
    target = float(spec['height_m'])
    args.output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()))
    if any(obj.type == 'ARMATURE' for obj in bpy.context.scene.objects):
        raise ValueError('This static-asset workflow does not alter rigged characters; use the character workflow')
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not meshes:
        raise ValueError('GLB contains no mesh')
    if any(obj.data.shape_keys for obj in meshes):
        raise ValueError('Morph-target models need a separate workflow; raw input preserved')
    for obj in meshes:
        if any(not math.isfinite(float(c)) for vertex in obj.data.vertices for c in vertex.co):
            raise ValueError('Non-finite vertex coordinates')
    bpy.context.view_layer.update()
    low, high = bounds(meshes)
    before = high - low
    measured = before.z if axis == 'height' else max(before)
    if measured <= 1e-6:
        raise ValueError('Asset has no measurable ' + axis)
    factor = target / measured
    centre = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
    normalization = Matrix.Scale(factor, 4) @ Matrix.Translation(-centre)
    originals = {obj.name: obj.matrix_world.copy() for obj in meshes}
    # Bake each static part independently. Keep names, UVs and material slots; never join all geometry.
    for obj in meshes:
        transform = normalization @ originals[obj.name]
        obj.parent = None
        obj.data = obj.data.copy()
        obj.data.transform(transform)
        if transform.to_3x3().determinant() < 0:
            obj.data.flip_normals()
        obj.matrix_world = Matrix.Identity(4)
        obj.data.update()
    for obj in list(bpy.context.scene.objects):
        if obj not in meshes:
            bpy.data.objects.remove(obj, do_unlink=True)
    root = bpy.data.objects.new(spec['asset_id'], None)
    bpy.context.collection.objects.link(root)
    for obj in meshes:
        obj.parent = root
        obj.matrix_parent_inverse = Matrix.Identity(4)
    bpy.context.view_layer.update()
    low, high = bounds(meshes)
    size = high - low
    achieved = size.z if axis == 'height' else max(size)
    checks = (abs(low.z) < 1e-5 and abs((low.x + high.x) / 2) < 1e-5 and abs((low.y + high.y) / 2) < 1e-5
              and abs(achieved - target) < 1e-4 * max(1.0, target))
    if not checks:
        raise ValueError('Normalization failed; refusing delivery')
    triangle_count, parts = 0, []
    for obj in meshes:
        obj.data.calc_loop_triangles()
        tris = len(obj.data.loop_triangles)
        triangle_count += tris
        parts.append({'name': obj.name, 'triangles': tris, 'material_slots': len(obj.material_slots),
                      'uv_layers': len(obj.data.uv_layers)})
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=str(args.output / 'model.glb'), export_format='GLB',
                              use_selection=True, export_animations=False)
    warnings = []
    if triangle_count > spec['triangle_budget']:
        warnings.append('Triangle count exceeds budget. Review the raw model first; reduction is an A2 branch, never automatic.')
    if len(meshes) == 1:
        warnings.append('One mesh part: semantic splitting (doors, lids, moving parts) is not guaranteed and may need manual work.')
    textures = [{'name': im.name, 'size': list(im.size)} for im in bpy.data.images if im.size[0]]
    report = {'asset_id': spec['asset_id'], 'blender_version': bpy.app.version_string, 'geometry_checks_passed': checks,
              'size_axis': axis, 'scale_factor_applied': factor,
              'dimensions_m': {'x': size.x, 'y': size.y, 'z_height': size.z}, 'ground_z': low.z, 'origin': 'bottom-centre',
              'triangles': triangle_count, 'triangle_budget': spec['triangle_budget'], 'parts': parts,
              'materials': len({slot.material.name for obj in meshes for slot in obj.material_slots if slot.material}),
              'textures': textures, 'warnings': warnings,
              'axes': 'Blender Z-up, front = -Y. glTF export converts to Y-up; engines convert on import (UE: check scale and forward axis once per project).',
              'collision': 'not generated; choose per asset and use',
              'visual_review': 'required', 'approved_for_game': False}
    (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str((args.output / 'source.blend').resolve()))
    print('LOCAL_ASSET_READY ' + str(args.output))


if __name__ == '__main__':
    main()
