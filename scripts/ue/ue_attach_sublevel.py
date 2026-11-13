# Unreal editor Python (verified on 5.9): hang a content level on a persistent level as a Blueprint-streamed sublevel
# (LevelStreamingDynamic: not loaded or visible until game code loads it, so the persistent level looks unchanged).
# Run: UnrealEditor-Cmd.exe AD.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -AllowCommandletRendering
# Env: ART_PARENT (the main level, required), ART_SUBLEVEL (required),
#      ART_UE_PKG: folder for ue_attach_report.json (unreal.log output is not shown by commandlets).
import os, json
import unreal

PARENT = os.environ["ART_PARENT"]
SUB = os.environ["ART_SUBLEVEL"]
SHORT = SUB.rsplit("/", 1)[-1]
report = {"parent": PARENT, "sublevel": SUB}

unreal.EditorLoadingAndSavingUtils.load_map(PARENT)
world = unreal.EditorLevelLibrary.get_editor_world()
report["world"] = world.get_name() if world else None
report["levels_before"] = [l.get_outermost().get_name() for l in unreal.EditorLevelUtils.get_levels(world)]
existing = unreal.GameplayStatics.get_streaming_level(world, SHORT)
if existing:
    report["result"] = "already attached (%s)" % existing.get_class().get_name()
else:
    lvl = unreal.EditorLevelUtils.add_level_to_world(world, SUB, unreal.LevelStreamingDynamic)
    s = unreal.GameplayStatics.get_streaming_level(world, SHORT)
    if lvl is None or s is None:
        report["result"] = "FAILED (a World Partition map cannot take streaming sublevels; use a Level Instance)"
    else:
        s.set_editor_property("initially_loaded", False)
        s.set_editor_property("initially_visible", False)
        ok = unreal.EditorLoadingAndSavingUtils.save_map(world, PARENT)
        report["result"] = "attached" if ok else "attached but SAVE FAILED"
        report["streaming_class"] = s.get_class().get_name()
report["levels_after"] = [l.get_outermost().get_name() for l in unreal.EditorLevelUtils.get_levels(world)]
pkg = os.environ.get("ART_UE_PKG")
if pkg:
    with open(os.path.join(pkg, "ue_attach_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
