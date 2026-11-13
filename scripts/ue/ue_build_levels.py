# Unreal editor Python (GUI, verified on 5.8 and 5.9): build two levels from the imported meshes and the package's
# placements, capture the game cameras, quit.
#   ART_UE_LEVEL   content only (the placed meshes); stream this into the game's main level (ue_attach_sublevel.py)
#   ART_UE_REVIEW  review lighting, ground placeholder, the game cameras, with the content level always loaded
#                  (default <content>/Review/<level name>_Review)
# Run (GUI; actors can't be spawned in a commandlet):
#   UnrealEditor.exe <project>.uproject /Engine/Maps/Entry -ExecCmds="py <this file>" -unattended -nosplash
#   (Git Bash: set MSYS_NO_PATHCONV=1 or /Engine/... gets rewritten)
# Env: ART_UE_PKG, ART_UE_LEVEL (required), ART_UE_REVIEW, ART_UE_CONTENT / ART_UE_MESHES as for the import.
# Blender (m, Z-up, right-handed) -> UE (cm, left-handed): (x, y, z) -> (x, -y, z) * 100, yaw -> -yaw.
import os, json, math
import unreal

PKG = os.environ["ART_UE_PKG"]
CONTENT = os.environ.get("ART_UE_CONTENT", "/Game/Art").rstrip("/")   # set it to the project's own art folder
MESH_DIR = os.environ.get("ART_UE_MESHES", CONTENT + "/Meshes")
TEX_DIR = os.environ.get("ART_UE_TEXTURES", CONTENT + "/Textures")
MAT_DIR = os.environ.get("ART_UE_MATERIALS", CONTENT + "/Materials")

OUT = os.path.join(PKG, "shots"); os.makedirs(OUT, exist_ok=True)
P = json.load(open(os.path.join(PKG, "package.json"), encoding="utf-8"))
LEVEL = os.environ["ART_UE_LEVEL"]
REVIEW = os.environ.get("ART_UE_REVIEW", CONTENT + "/Review/" + LEVEL.rsplit("/", 1)[-1] + "_Review")
eal = unreal.EditorAssetLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {"placed": 0, "missing": [], "screenshots": []}


def ue(v): return unreal.Vector(v[0] * 100.0, -v[1] * 100.0, v[2] * 100.0)


def open_empty(path):
    """Open the level (create it if missing) and remove every actor of its persistent level. Deleting and
    recreating a level that another level streams in can fail silently, and the spawns then land in the
    startup map, so existing levels are emptied in place instead."""
    ok = les.load_level(path) if eal.does_asset_exist(path) else les.new_level(path, False)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not ok or world.get_path_name().split(".")[0] != path:
        raise RuntimeError("could not open %s (editor world is %s)" % (path, world.get_path_name()))
    removed = []
    for a in actors.get_all_level_actors():
        if isinstance(a, unreal.WorldSettings) or a.get_class().get_name() == "Brush": continue
        if a.get_level().get_outermost().get_name() != path: continue   # keep actors of streamed sublevels
        removed.append(a.get_class().get_name()); actors.destroy_actor(a)
    report.setdefault("cleared", {})[path] = len(removed)
    return world


open_empty(LEVEL)

for pl in P["placements"]:
    kit = P["assets"][pl["asset"]]["kit"]
    mesh = eal.load_asset("%s/%s/%s" % (MESH_DIR, kit, pl["asset"]))
    if mesh is None:
        report["missing"].append(pl["asset"]); continue
    rx, ry, rz = pl["rotation_deg"]
    a = actors.spawn_actor_from_object(mesh, ue(pl["location"]), unreal.Rotator(roll=rx, pitch=-ry, yaw=-rz))
    a.set_actor_scale3d(unreal.Vector(*pl["scale"]))
    a.set_actor_label(pl["asset"].replace("SM_", "") + "_" + pl["object"].split(".")[-1] if "." in pl["object"] else pl["asset"].replace("SM_", ""))
    a.set_folder_path(kit)
    report["placed"] += 1


if not unreal.EditorLoadingAndSavingUtils.save_map(unreal.EditorLevelLibrary.get_editor_world(), LEVEL):
    raise RuntimeError("saving %s failed" % LEVEL)
report["content_actors_saved"] = len([a for a in actors.get_all_level_actors() if isinstance(a, unreal.StaticMeshActor)])

# ---- review level: lighting and cameras first (they go into its persistent level), then stream the content in
open_empty(REVIEW)


def spawn(cls, loc=(0, 0, 0), rot=unreal.Rotator(0, 0, 0)):
    x = actors.spawn_actor_from_class(cls, unreal.Vector(*loc), rot); x.set_folder_path("Lighting"); return x


ground = actors.spawn_actor_from_object(eal.load_asset("/Engine/BasicShapes/Plane"), unreal.Vector(0, 0, -2), unreal.Rotator(0, 0, 0))
ground.set_actor_scale3d(unreal.Vector(1200, 1200, 1)); ground.set_actor_label("Ground_Placeholder"); ground.set_folder_path("Lighting")
ground.static_mesh_component.set_material(0, eal.load_asset("/Engine/EngineMaterials/WorldGridMaterial"))
sun = spawn(unreal.DirectionalLight, rot=unreal.Rotator(roll=0, pitch=-38, yaw=-130))
sun.light_component.set_intensity(8.0)
sun.light_component.set_editor_property("atmosphere_sun_light", True)
spawn(unreal.SkyAtmosphere)
sky = spawn(unreal.SkyLight)
sky.light_component.set_editor_property("real_time_capture", True)
spawn(unreal.ExponentialHeightFog)

cams = {}
for c in P["cameras"]:
    cam = spawn(unreal.CameraActor)
    loc = ue(c["location"]); f = c["forward"]
    cam.set_actor_location(loc, False, False)
    cam.set_actor_rotation(unreal.MathLibrary.make_rot_from_x(unreal.Vector(f[0], -f[1], f[2])), False)
    cam.camera_component.set_editor_property("field_of_view", c["hfov_deg"])
    cam.camera_component.set_editor_property("aspect_ratio", 16.0 / 9.0)
    cam.set_actor_label("Cam_" + c["name"]); cam.set_folder_path("Cameras")
    cams[c["name"]] = cam

world = unreal.EditorLevelLibrary.get_editor_world()
if not unreal.GameplayStatics.get_streaming_level(world, LEVEL.rsplit("/", 1)[-1]):
    unreal.EditorLevelUtils.add_level_to_world(world, LEVEL, unreal.LevelStreamingAlwaysLoaded)
if not unreal.EditorLoadingAndSavingUtils.save_map(world, REVIEW):   # the persistent level, whichever level is current
    raise RuntimeError("saving %s failed" % REVIEW)
report["level"] = LEVEL; report["review_level"] = REVIEW
report["review_meshes_visible"] = len([a for a in actors.get_all_level_actors() if isinstance(a, unreal.StaticMeshActor)])
report["tris"] = {}
for sm, a in P["assets"].items():
    m = eal.load_asset("%s/%s/%s" % (MESH_DIR, a["kit"], sm))
    if m: report["tris"][sm] = [a["triangles"], m.get_num_triangles(0)]

shots = list(cams.items())
state = {"i": 0, "wait": 60.0, "pending": None}   # seconds: let new shaders compile and textures stream in


def tick(dt):
    if state["wait"] > 0:
        state["wait"] -= dt; return
    if state["pending"]:
        if not os.path.exists(state["pending"]): return
        state["pending"] = None
    if state["i"] >= len(shots):
        with open(os.path.join(PKG, "ue_level_report.json"), "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
        unreal.log("ART_LEVEL_DONE " + json.dumps(report))
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.SystemLibrary.quit_editor(); return
    name, cam = shots[state["i"]]
    path = os.path.join(OUT, "ue_%s.png" % name)
    if os.path.exists(path): os.remove(path)
    # advance state before the call: the screenshot request can re-enter this tick callback
    state["pending"] = path; state["i"] += 1; state["wait"] = 3.0
    report["screenshots"].append(path)
    unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, path, cam)


handle = unreal.register_slate_post_tick_callback(tick)
