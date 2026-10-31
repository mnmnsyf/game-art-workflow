"""Render review views of a 3D model with Blender in background mode.

    blender -b -P blender_views.py -- model.glb --out review/house_a --size 768

You cannot judge a GLB/FBX by reading it; render it. Writes front, back,
left, right, top, bottom, and three-quarter PNGs (transparent background,
Workbench renderer with base-color textures) plus stats.json: world-space
size in meters, triangle count, object/material counts. Use the views for
the G2 raw-model review and the size to catch generators that export every
model 1 unit tall.

Requires Blender 3.6+ on PATH (bpy is only available inside Blender).
Not exercised by selftest.py — verify it in your own Blender before relying on it.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        sys.exit("usage: blender -b -P blender_views.py -- MODEL [--out DIR] [--size PX]")
    model, out, size = Path(argv[0]), None, 768
    i = 1
    while i < len(argv):
        if argv[i] == "--out":
            out, i = Path(argv[i + 1]), i + 2
        elif argv[i] == "--size":
            size, i = int(argv[i + 1]), i + 2
        else:
            sys.exit(f"unknown argument {argv[i]}")
    return model, out or model.with_suffix("").parent / (model.stem + "_views"), size


def import_model(path):
    ext = path.suffix.lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    else:
        sys.exit(f"unsupported format {ext}")


def main():
    model, out, size = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_model(model)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        sys.exit("no mesh objects imported")

    deps = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e18,) * 3), Vector((-1e18,) * 3)
    tris, mats = 0, set()
    for o in meshes:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
        ev = o.evaluated_get(deps)
        m = ev.to_mesh()
        m.calc_loop_triangles()
        tris += len(m.loop_triangles)
        ev.to_mesh_clear()
        mats.update(s.material.name for s in o.material_slots if s.material)
    dims = hi - lo
    center = (lo + hi) / 2
    radius = max(dims) or 1.0

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "TEXTURE"
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = size

    target = bpy.data.objects.new("target", None)
    scene.collection.objects.link(target)
    target.location = center
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = radius * 1.25
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    track = cam.constraints.new("TRACK_TO")
    track.target, track.track_axis, track.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"

    d = radius * 3
    # Blender is Z-up; glTF importers map the model's front (+Z in glTF) to -Y.
    views = {
        "front": (0, -d, 0), "back": (0, d, 0), "left": (-d, 0, 0), "right": (d, 0, 0),
        "top": (0, -d * 0.02, d), "bottom": (0, -d * 0.02, -d),
        "three_quarter": (d * 0.7, -d * 0.7, d * 0.5),
    }
    out.mkdir(parents=True, exist_ok=True)
    for name, off in views.items():
        cam.location = center + Vector(off)
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    stats = {
        "model": str(model.resolve()),
        "size_m": {"x": round(dims.x, 4), "y_depth": round(dims.y, 4), "z_height": round(dims.z, 4)},
        "triangles": tris, "mesh_objects": len(meshes), "materials": sorted(mats),
        "views": sorted(f"{n}.png" for n in views),
    }
    (out / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


main()
