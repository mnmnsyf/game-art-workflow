# Godot Integration

There is real project evidence for Godot 4.x (see the [case study](../examples/case-study-godot-cottage.md)), but it does not guarantee compatibility with every version or renderer (Forward+ / Mobile / Compatibility). First read the project's `project.godot` version, import rules (`.import`, custom import plugins), scene structure, run entry, and existing verification commands.

## 2D

- Use whatever the project already uses — Sprite2D, TileMapLayer / TileSet, ParallaxBackground / Parallax2D, or existing scenes — instead of introducing a new system.
- Lock anchors (offset / centered), pixel size, `z_index` / `y_sort_enabled`, and the character's foot sort point; an occluder's sort origin sits on its ground line, not the image center.
- Decide texture filtering (Nearest for pixel art), mipmaps, compression (VRAM compression can break pixel art and alpha edges), and atlas edges by art style.
- When 2D textures go into a 3D scene, also check Sprite3D billboard mode, alpha scissor / blend, shadow casting, and depth sorting.

## 3D

- For static assets prefer the project's verified GLB / glTF import route; check meters, Y-up orientation, origin, normals, sRGB base color, and the metallic-roughness channels (glTF: G = roughness, B = metallic).
- Don't apply a generic shader that truncates material features. For buildings that fade when occluding, duplicate the complete native material (StandardMaterial3D or the project shader) and change only the necessary transparency / distance-fade parameters, keeping normals, metallic-roughness, AO, UVs, and channels. Technical acceptance compares the **actual active material** against the source material.
- Configure collision separately by use (StaticBody3D + simple shapes / convex decomposition / trimesh) and verify collision layer / mask, character capsule size, wall thickness, doorways, step height, and slope limit. Fading the display never removes collision.
- Replace only the designated resource references. When saving a PackedScene, don't recursively reset the owner of nodes inside nested imported scenes; keep sub-scene ownership, or explicitly create your own display node reusing the Mesh resource and free the temporary import tree, to avoid duplicate nodes and RID leaks.

## Verification

Prefer the project's existing commands. The following are CLI shapes only — check arguments against the actual version; angle brackets are placeholders and must not be run verbatim:

```text
<godot> --headless --path <project> --editor --import --quit
<godot> --headless --path <project> --script res://<targeted_check.gd>
<godot> --path <project> --script res://<in_engine_screenshot.gd>
```

- Check the real exit code and error log (including import warnings). Passing headless physics does not mean the visuals pass; in-engine screenshots need real rendered output.
- Run the target scene and use **the actual character controller's physical movement** to check front/back occlusion, walking around, door steps, grounding, and stuck recovery; a successful teleport is not "walkable".
- Run the checks relevant to the asset's use and stop; repeat only for new changes, failures, or unresolved issues. Export only when the user wants a playable build or the project's delivery requires it, into a new output directory so you don't lock the user's running exe, and never kill the user's processes casually.
- If a project forbids a mode of operation (e.g. computer use), keep that restriction and use the CLI, in-engine screenshots, and automated input instead; it is a project-profile preference, not a rule for other projects.

Backfill the first successful version, renderer, commands, and results into the profile's `engine.verified`.
