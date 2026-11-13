# Unreal editor Python (commandlet, verified on 5.8 and 5.9): import a package written by blender_export_engine.py.
# Run (set ART_UE_PKG first): UnrealEditor-Cmd.exe AD.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -AllowCommandletRendering
# (UE 5.9 commandlets have no renderer by default; without that flag the master material cannot compile)
# Env: ART_UE_PKG (package folder, required); ART_UE_CONTENT (default /Game/Art) or ART_UE_MESHES / _TEXTURES / _MATERIALS.
# Meshes -> <meshes>/<Kit>, textures -> <textures>/<Kit>, MIs -> <materials>/<Kit>, one shared master
# <materials>/M_BakedPBR (created only if missing). Nanite off. Writes ue_import_report.json into the package.
import os, json
import unreal

PKG = os.environ["ART_UE_PKG"]
CONTENT = os.environ.get("ART_UE_CONTENT", "/Game/Art").rstrip("/")   # set it to the project's own art folder
MESH_DIR = os.environ.get("ART_UE_MESHES", CONTENT + "/Meshes")
TEX_DIR = os.environ.get("ART_UE_TEXTURES", CONTENT + "/Textures")
MAT_DIR = os.environ.get("ART_UE_MATERIALS", CONTENT + "/Materials")

P = json.load(open(os.path.join(PKG, "package.json"), encoding="utf-8"))
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
report = {"meshes": {}, "removed_autogen": [], "textures": 0}


def import_file(path, dest, name):
    t = unreal.AssetImportTask()
    t.filename = path; t.destination_path = dest; t.destination_name = name
    t.automated = True; t.replace_existing = True; t.save = False
    tools.import_asset_tasks([t])
    return list(t.imported_object_paths)


# ---- master material (created on first use, with the first imported textures as parameter defaults;
# a TextureSampleParameter2D without a default texture fails to compile and every MI falls back to grey) ----
MASTER = MAT_DIR + "/M_BakedPBR"
master = None


def ensure_master(d, orm_tex):
    global master
    if master: return master
    if eal.does_asset_exist(MASTER):
        master = eal.load_asset(MASTER); report["master"] = "existing, untouched"; return master
    master = tools.create_asset("M_BakedPBR", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    def param(cls, name, x, y):
        n = mel.create_material_expression(master, cls, x, y); n.set_editor_property("parameter_name", name); return n
    bc = param(unreal.MaterialExpressionTextureSampleParameter2D, "BaseColor", -700, -200)
    bc.set_editor_property("texture", d)
    orm = param(unreal.MaterialExpressionTextureSampleParameter2D, "ORM", -700, 250)
    orm.set_editor_property("texture", orm_tex)
    orm.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    tint = param(unreal.MaterialExpressionVectorParameter, "Tint", -700, -450)
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    rs = param(unreal.MaterialExpressionScalarParameter, "RoughnessScale", -700, 550)
    rs.set_editor_property("default_value", 1.0)
    mul = mel.create_material_expression(master, unreal.MaterialExpressionMultiply, -350, -300)
    mel.connect_material_expressions(bc, "RGB", mul, "A"); mel.connect_material_expressions(tint, "", mul, "B")
    rmul = mel.create_material_expression(master, unreal.MaterialExpressionMultiply, -350, 400)
    mel.connect_material_expressions(orm, "G", rmul, "A"); mel.connect_material_expressions(rs, "", rmul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    mel.connect_material_property(rmul, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(orm, "B", unreal.MaterialProperty.MP_METALLIC)
    mel.recompile_material(master); eal.save_loaded_asset(master); report["master"] = "created"
    return master


for sm, a in P["assets"].items():
    kit = a["kit"]
    mdir, tdir, idir = MESH_DIR + "/" + kit, TEX_DIR + "/" + kit, MAT_DIR + "/" + kit
    before = set(eal.list_assets(mdir, recursive=True)) if eal.does_directory_exist(mdir) else set()
    import_file(os.path.join(PKG, a["fbx"]), mdir, sm)
    mesh = eal.load_asset("%s/%s" % (mdir, sm))
    if mesh is None:
        report["meshes"][sm] = "IMPORT FAILED"; continue
    slots = {}
    for s in a["slots"]:
        tex = {}
        for k in ("D", "ORM"):
            import_file(os.path.join(PKG, "textures", s[k] + ".png"), tdir, s[k])
            t = eal.load_asset("%s/%s" % (tdir, s[k]))
            if k == "ORM":
                t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
                t.set_editor_property("srgb", False)
            eal.save_loaded_asset(t); tex[k] = t; report["textures"] += 1
        mpath = "%s/%s" % (idir, s["mi"])
        mi = eal.load_asset(mpath) if eal.does_asset_exist(mpath) else \
            tools.create_asset(s["mi"], idir, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi, ensure_master(tex["D"], tex["ORM"]))
        mel.set_material_instance_texture_parameter_value(mi, "BaseColor", tex["D"])
        mel.set_material_instance_texture_parameter_value(mi, "ORM", tex["ORM"])
        mel.update_material_instance(mi); eal.save_loaded_asset(mi)
        slots[s["mi"]] = mi
    # assign by slot name (FBX material name == MI name), fall back to slot order
    mats = list(mesh.get_editor_property("static_materials"))
    for i, m in enumerate(mats):
        name = str(m.material_slot_name)
        mi = slots.get(name) or slots.get(a["slots"][min(i, len(a["slots"]) - 1)]["mi"])
        mesh.set_material(i, mi)
    ns = mesh.get_editor_property("nanite_settings"); ns.enabled = False
    mesh.set_editor_property("nanite_settings", ns)
    eal.save_loaded_asset(mesh)
    # drop the materials/textures the importer generated next to the mesh
    for p in set(eal.list_assets(mdir, recursive=True)) - before:
        n = p.split("/")[-1].split(".")[0]
        if n != sm:
            eal.delete_asset(p); report["removed_autogen"].append(p)
    b = mesh.get_bounds()
    report["meshes"][sm] = {
        "slots": [str(m.material_slot_name) for m in mats],
        "materials": [mesh.get_material(i).get_name() for i in range(len(mats))],
        "tris": mesh.get_num_triangles(0),
        "origin_uu": [round(b.origin.x, 1), round(b.origin.y, 1), round(b.origin.z, 1)],
        "extent_uu": [round(b.box_extent.x, 1), round(b.box_extent.y, 1), round(b.box_extent.z, 1)],
        "nanite": mesh.get_editor_property("nanite_settings").enabled,
    }
    unreal.log("ART_MESH %s %s" % (sm, json.dumps(report["meshes"][sm])))

with open(os.path.join(PKG, "ue_import_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=1)
unreal.log("ART_IMPORT_DONE %d meshes %d textures" % (len(report["meshes"]), report["textures"]))
