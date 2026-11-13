# Unreal editor Python (verified on 5.9) (commandlet): open and re-save levels so their references follow moved assets
# (the levels then point at the new paths directly and the redirectors can be deleted).
# Env ART_LEVELS: comma-separated level paths.
import os
import unreal
for lv in os.environ["ART_LEVELS"].split(","):
    unreal.EditorLoadingAndSavingUtils.load_map(lv)
    w = unreal.EditorLevelLibrary.get_editor_world()
    unreal.EditorLoadingAndSavingUtils.save_map(w, lv)
