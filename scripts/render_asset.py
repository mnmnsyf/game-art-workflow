"""Blender-only non-destructive GLB review: six textured and six clay views.

blender --background --python-exit-code 1 --python render_asset.py -- model.glb --out TEMP_DIR
Only imports and renders. Never exports, saves over a model, or modifies its UV/materials.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--resolution', type=int, default=384)
    parser.add_argument('--samples', type=int, default=8)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if not 32 <= args.resolution <= 4096 or not 1 <= args.samples <= 256:
        raise ValueError('resolution must be 32..4096 and samples 1..256')
    if args.input.suffix.lower() != '.glb' or not args.input.is_file():
        raise ValueError('provide an existing self-contained GLB')
    # Reject external buffers/images before Blender could access them.
    import struct
    data = args.input.read_bytes()
    if len(data) < 28 or data[:4] != b'glTF' or struct.unpack_from('<I', data, 8)[0] != len(data):
        raise ValueError('invalid GLB header')
    length = struct.unpack_from('<I', data, 12)[0]
    document = json.loads(data[20:20+length])
    if any(item.get('uri') and not item['uri'].startswith('data:')
           for key in ('buffers', 'images') for item in document.get(key, [])):
        raise ValueError('external GLB dependencies are not supported')
    source_hash = hashlib.sha256(data).hexdigest()
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError('output directory is not empty; choose a new review version')
    args.out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not meshes:
        raise ValueError('model contains no mesh')
    # Imported lights/cameras must not contaminate the neutral review studio.
    for obj in list(bpy.context.scene.objects):
        if obj.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()
    points = [obj.matrix_world@Vector(c) for obj in meshes for c in obj.bound_box]
    if not all(math.isfinite(component) for p in points for component in p):
        raise ValueError('non-finite bounds')
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    size = high-low
    extent = max(size)
    if extent <= 1e-8:
        raise ValueError('model has degenerate bounds')
    center = (low+high)*.5
    report = {'source':str(args.input.resolve()),'source_sha256':source_hash,'blender_version':bpy.app.version_string,
              'dimensions_source_units':list(size),'triangles':0,'parts':[],
              'boundary_edges_after_statistical_weld':0,'nonmanifold_edges_after_statistical_weld':0,
              'views':[],'note':'Topology is diagnostic, not a universal pass/fail. Open plant cards may be intentional. Model front is not inferred; front labels mean Blender -Y.'}
    for obj in meshes:
        obj.data.calc_loop_triangles()
        report['triangles'] += len(obj.data.loop_triangles)
        bm = bmesh.new();bm.from_mesh(obj.data)
        # Weld only this disposable statistics copy; imported mesh and UVs stay intact.
        local_extent = max((max(v.co[i] for v in bm.verts)-min(v.co[i] for v in bm.verts)) for i in range(3)) if bm.verts else 0
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=max(local_extent*1e-7, 1e-9))
        boundary = sum(edge.is_boundary for edge in bm.edges)
        nonmanifold = sum(not edge.is_manifold and not edge.is_boundary for edge in bm.edges)
        report['boundary_edges_after_statistical_weld'] += boundary
        report['nonmanifold_edges_after_statistical_weld'] += nonmanifold
        report['parts'].append({'name':obj.name,'triangles':len(obj.data.loop_triangles),
                                'uv_layers':len(obj.data.uv_layers),'material_slots':len(obj.material_slots),
                                'boundary_edges':boundary,'nonmanifold_edges':nonmanifold})
        bm.free()
    report['textures'] = [{'name':im.name,'size':list(im.size)} for im in bpy.data.images if im.size[0]]
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES';scene.cycles.device = 'CPU'
    scene.cycles.samples = args.samples;scene.cycles.use_denoising = False
    scene.render.resolution_x = args.resolution;scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100;scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('NeutralReview');world.use_nodes = True;scene.world = world
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.55,.55,.55,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
    for i, offset in enumerate([(3,-4,5),(-4,2,3)]):
        light_data = bpy.data.lights.new('ReviewSoftbox'+str(i),'AREA')
        light_data.energy = 60*extent*extent;light_data.size = extent*3
        light = bpy.data.objects.new(light_data.name,light_data);scene.collection.objects.link(light)
        light.location = center+Vector(offset)*extent
        light.rotation_euler = (center-light.location).to_track_quat('-Z','Y').to_euler()
    camera_data = bpy.data.cameras.new('ReviewCamera');camera_data.type = 'ORTHO'
    camera_data.ortho_scale = size.length*1.15
    camera = bpy.data.objects.new(camera_data.name,camera_data);scene.collection.objects.link(camera);scene.camera = camera
    clay = bpy.data.materials.new('ReviewClay');clay.use_nodes = True
    clay.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.40,.40,.40,1)
    clay.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .85
    angles = [('front',(0,-1,.35)),('right',(1,0,.35)),('back',(0,1,.35)),('left',(-1,0,.35)),
              ('top',(0,-.001,1)),('bottom',(0,-.001,-1))]
    for mode in ('textured','clay'):
        scene.view_layers[0].material_override = clay if mode == 'clay' else None
        for name, direction in angles:
            camera.location = center+Vector(direction).normalized()*extent*3
            camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
            filename = mode+'_'+name+'.png';scene.render.filepath = str((args.out/filename).resolve())
            bpy.ops.render.render(write_still=True);report['views'].append(filename)
    if hashlib.sha256(args.input.read_bytes()).hexdigest() != source_hash:
        raise ValueError('source hash changed while rendering')
    (args.out/'stats.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('ART_REVIEW_RESULT '+json.dumps({'report':str((args.out/'stats.json').resolve()),'views':len(report['views'])}))


if __name__ == '__main__':
    main()
