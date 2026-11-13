# Unreal Engine Integration: First Project Route Verified (see field notes)

This file is an operating procedure to verify before execution, not a general UE auto-importer that has already run end to end. No UE project, import script, or runtime test is claimed as passing. On first use in UE, backfill the actual version, tools, and results into the project profile; never auto-install the engine / plugins or modify an arbitrary existing UE project just to install this skill.

## Probe first

Confirm the .uproject, UE version, target platform, project directory conventions, existing importers / Editor Utilities / MCP bridges, and the actual enabled state of the Python Editor Script Plugin, Editor Scripting Utilities, etc. Check plugin names and APIs against the version. If the project does not use Paper2D, don't assume it is enabled; when configuration changes are needed, state the scope.

With enough capability, prefer official editor Python or the project's existing tools; before running editor scripts from the command line, confirm the entry point and arguments against the current version's docs. Without a bridge or scripting, provide an import package and exact settings for the user to apply, and record that you are waiting on an external action; never mark the asset integrated just because instructions were written.

## Asset import and level placement

1. For 3D choose FBX or a verified glTF / Interchange route by version and project; don't assume every version supports the same GLB flow. Check UE centimeters, Z-up, orientation, transforms, pivot, and DCC export to avoid 100× scaling and double conversion.
2. Base color is sRGB; normal and roughness / metallic / AO are data — check normal compression, normal direction, and channel packing. Don't use a glTF metallic-roughness texture as the project's ORM without rewiring. Use material instances of the verified master material; don't overwrite shared master materials.
3. For Static Meshes check LOD, material slots, shadows, lighting approach, and collision complexity. Choose Simple / Complex by use; complex collision on static buildings still needs real traversal tests, and dynamic physics has its own constraints. Keep functional openings when splitting doors, blockers, and interaction components.
4. Decide Nanite, virtual textures, and lightmap UVs by target platform and lighting approach; never enable them globally by default. Lightmap UVs and color-texture UVs serve different purposes; don't re-unwrap the original material UVs unconditionally for static lighting.
5. For 2D choose Paper2D, a background plane, or material cards per the project; configure pixel scale, pivot, filtering, mipmaps, translucent / masked, two-sided, shadows, sorting, and collision. Creating a Sprite or Texture asset does not mean it appears correctly in the level.
6. Import into a versioned Content directory; compose meshes, separate collision, and existing interactions with Actors / Blueprints; place into the designated level and record Actor transforms, asset paths, and pre-replacement references. Save only the necessary Packages / Map, never unrelated dirty packages. Rename / delete assets through editor asset operations so references follow; never move .uasset files directly.

## Field notes: a verified route (UE 5.8 / 5.9, 2026-11)

One project took a 35-mesh scene through this end to end. Treat as a starting point and re-check per version. The scripts:

```text
blender -b <scene>.blend -P <skill>/scripts/blender_export_engine.py -- <pkg> --kit <Kit> [--map kits.json]
set ART_UE_PKG=<pkg>  ART_UE_CONTENT=<project art folder, e.g. what existing meshes use>  ART_UE_LEVEL=/Game/<levels>/L_<Scene>
UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script=<skill>/scripts/ue/ue_import_package.py -unattended -nosplash -AllowCommandletRendering
UnrealEditor.exe <project>.uproject /Engine/Maps/Entry -ExecCmds="py <skill>/scripts/ue/ue_build_levels.py" -unattended -nosplash
set ART_PARENT=<main level>  ART_SUBLEVEL=<content level>
UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script=<skill>/scripts/ue/ue_attach_sublevel.py -unattended -nosplash -AllowCommandletRendering
```

Each writes a JSON report into `ART_UE_PKG` (commandlets don't show `unreal.log`).

- **Package from Blender, not the engine**: one FBX per unique asset with its transform reset, textures as `_D` (sRGB) plus a packed `_ORM` (R = AO, G = roughness, B = metallic, linear), and a JSON placement list (asset, location, rotation, scale) plus the game cameras. Coordinates: Blender (x, y, z) m → UE (x, −y, z) × 100 cm, yaw → −yaw; verify once on an asymmetric mesh.
- **Import in a commandlet** (`-run=pythonscript`), place in the GUI editor (`-ExecCmds="py <file>"`): actors cannot be spawned from a commandlet. UE 5.9 commandlets also need `-AllowCommandletRendering` to compile materials, and `unreal.log` output does not reach commandlet stdout — write a JSON report.
- **Interchange** imports FBX/PNG, auto-creates materials next to meshes (assign your material instances by slot name, then delete the extras) and enables Nanite (turn it off unless the platform wants it). Triangle counts read in a commandlet can be stale; check in the GUI.
- **Master material**: every `TextureSampleParameter2D` needs a default texture, or the master fails to compile and every instance renders grey.
- **Levels**: a content-only level streamed into the game's main level (LevelStreamingDynamic, not initially loaded) plus a separate review level with lighting and cameras. Deleting and recreating a level that another level streams can fail silently and the spawns land in the startup map — open and empty it instead, and check the editor world's path. `delete_asset` on a `.umap` or a redirector may leave the file on disk; delete it once nothing references it.
- **Moving assets**: `AssetTools.rename_assets`, then re-save the levels that reference them (maps keep pointing at redirectors otherwise), then delete unreferenced redirectors; `*.ini` soft references are not updated — grep and fix them. `fixup_referencers` and `ObjectRedirector` are not exposed to Python in 5.9; test the asset class name instead.
- **C++ projects**: a new engine version needs the project modules rebuilt (`Build.bat <Project>Editor Win64 Development -Project=...`) before the editor opens unattended. Run the project's automation tests before pushing.
- **Old World Partition maps**: their external actors do not load in a commandlet; read values from the actor packages or rebuild the actors.

## Acceptance and capability promotion

Verify import, materials, units, collision, and real level display on a representative asset first, then test traversal, door steps, sorting, and occlusion with the actual character in PIE / Standalone. Capture screenshots from the target camera; editor thumbnails or DCC turntables are not game acceptance. Choose performance checks by platform and asset impact; don't package the whole project without reason. Each review gate still stops for the user's reply.

Record each item as executable / needs setup / limited / unverified. Only a route that actually ran successfully is promoted to "verified for this version and project"; keep logs, sources, import settings, and game screenshots. Fold first-UE-project corrections into this adapter, keep project-specific parameters in the profile, and don't pollute the Godot branch.
