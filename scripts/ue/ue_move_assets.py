# Unreal editor Python (verified on 5.9) (commandlet): move assets between content folders with reference fix-up.
# Env ART_MOVES: JSON {"<src dir or asset>": "<dst dir or asset>", ...}; subfolders keep their relative paths.
# After renaming, saves the referencers it touched and deletes redirectors nobody references any more.
# Config soft references (*.ini) are NOT updated; grep and fix them separately.
# Run: UnrealEditor-Cmd.exe AD.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -AllowCommandletRendering
# Env ART_UE_PKG: folder for ue_move_report.json.
import os, json
import unreal

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
reg = unreal.AssetRegistryHelpers.get_asset_registry()
MOVES = json.loads(os.environ["ART_MOVES"])
report = {"moved": [], "failed": [], "conflicts": [], "redirectors_deleted": [], "redirectors_kept": {}}


def is_redirector(p):
    return str(eal.find_asset_data(p).asset_class_path.asset_name) == "ObjectRedirector"


moves = []
for src, dst in MOVES.items():
    if eal.does_asset_exist(src):
        pairs = [(src, dst)]
    else:
        pairs = [(p.split(".")[0], dst + p.split(".")[0][len(src):])
                 for p in eal.list_assets(src, recursive=True, include_folder=False) if not is_redirector(p)]
    for s, d in pairs:
        (report["conflicts"] if eal.does_asset_exist(d) else moves).append([s, d] if eal.does_asset_exist(d) else (s, d))
if not report["conflicts"] and moves:
    data = [unreal.AssetRenameData(eal.load_asset(s), d.rsplit("/", 1)[0], d.rsplit("/", 1)[1]) for s, d in moves]
    report["rename_ok"] = tools.rename_assets(data)
    for s, d in moves:
        (report["moved"] if eal.does_asset_exist(d) else report["failed"]).append([s, d])
    report["saved_dirty"] = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
for src in MOVES:
    paths = [src] if not eal.does_directory_exist(src) else eal.list_assets(src, recursive=True, include_folder=False)
    for p in paths:
        p = p.split(".")[0]
        if not eal.does_asset_exist(p) or not is_redirector(p): continue
        refs = [str(r) for r in (reg.get_referencers(p, opts) or []) if str(r) != p]
        if refs: report["redirectors_kept"][p] = refs
        elif eal.delete_asset(p): report["redirectors_deleted"].append(p)
pkg = os.environ.get("ART_UE_PKG")
if pkg:
    with open(os.path.join(pkg, "ue_move_report.json"), "w", encoding="utf-8") as fh:
        json.dump({k: (len(v) if k in ("moved", "redirectors_deleted") else v) for k, v in report.items()}, fh, indent=1)
