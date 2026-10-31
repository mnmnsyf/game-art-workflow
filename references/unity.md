# Unity Integration

Operating procedure for Unity projects. It has not yet been run end to end in a real Unity project by this skill's maintainers; treat every route as **unverified** until it passes in the user's project, then backfill the version, render pipeline, and commands into the profile's `engine.verified`.

## Probe first

Read `ProjectSettings/ProjectVersion.txt` (Unity version), `Packages/manifest.json` (render pipeline package, `com.unity.cloud.gltfast`, 2D packages, Test Framework), and the active render pipeline asset under Graphics settings. Note Built-in vs. URP vs. HDRP — material channels differ (below). Look for existing importers, AssetPostprocessors, Editor scripts, and folder conventions under `Assets/` before adding anything.

Unity imports everything under `Assets/`, so keep `.art-workflow/` at the project root, never inside `Assets/`. `Library/`, `Temp/`, and `Logs/` are generated and never committed.

## .meta files and references

- Every asset has a `.meta` file holding its GUID; scenes and prefabs reference assets by GUID. **Never delete or regenerate `.meta` files**, and commit them alongside the asset.
- Move, rename, or delete assets through the Editor or `AssetDatabase` (`MoveAsset`, `RenameAsset`), not the file system, so GUIDs and references survive.
- To replace an asset in place while keeping every reference, overwrite the file content and keep its `.meta`; to introduce a new version, import it side by side and repoint only the designated references.

## 2D

- Texture import: Texture Type *Sprite (2D and UI)*, correct **Pixels Per Unit** (match the profile's px/m), pivot at the ground point (Custom pivot), Filter Mode *Point* for pixel art, Compression *None* or high quality for pixel art and soft alpha, Generate Mip Maps off for 2D, *Alpha Is Transparency* on for straight-alpha sprites.
- Batch sprites with a Sprite Atlas; keep padding to avoid bleeding.
- Sorting: Sorting Layers and Order in Layer; for top-down depth sorting set *Transparency Sort Mode* to *Custom Axis* (0, 1, 0) and use a Sorting Group on multi-part objects. Sort by the foot pivot, not the image center.
- Tiles: Tilemap + Tile Palette; tiling textures still pass `tile_preview.py` before import.
- Collision: 2D colliders on the footprint (BoxCollider2D / PolygonCollider2D / CompositeCollider2D on tilemaps), never the full transparent rectangle.

## 3D

- **Format**: FBX is the native route. glTF/GLB needs the glTFast package; confirm it is installed before promising a GLB route.
- **Units and axes**: Unity uses meters, Y-up, left-handed. Check *Scale Factor* / *Convert Units*, and enable *Bake Axis Conversion* (or apply transforms on export) so meshes don't arrive with a stray −90° X rotation. Verify the asset's world bounds against the character height.
- **Model import**: Read/Write off unless scripts need it; *Generate Lightmap UVs* only for baked lighting (it does not touch the color UVs); mesh compression off for faithful-import comparisons; import materials then extract them (*Extract Materials*) so they are editable assets.
- **Material channels — the common trap**:
  - URP/Built-in Lit (metallic workflow): metallic in **R**, *smoothness* in **A** of the metallic map. glTF stores *roughness* in G and metallic in B, so convert: smoothness = 1 − roughness, repacked into A. Never plug a glTF metal-rough texture in directly.
  - HDRP Lit: Mask Map = R metallic, G ambient occlusion, B detail mask, A smoothness.
  - Normal maps: Texture Type *Normal map*; data textures (metallic, mask, AO) have *sRGB* off; base color has sRGB on.
  - Verify the channel conversion with `compare_images.py` on the repacked channels, and compare a neutral-light render against the source.
- **Prefabs**: wrap the model in a Prefab (visual mesh + separate collider children + LODGroup if needed); variants are Prefab Variants. Replace scene references at the prefab level and record the original prefab GUID and transform for rollback.
- **Collision**: BoxColliders / primitive compounds for walls; MeshCollider only for static geometry (convex is required for dynamic rigidbodies and caps at 255 triangles); keep doorways open; test step height and slope against the CharacterController's *Step Offset* and *Slope Limit*.
- **Occlusion fade**: duplicate the material and change only surface type / alpha, or use the project's existing fade shader / URP renderer feature; never swap in a generic shader that drops normal, mask, or emission channels. Fading never removes colliders.
- **Static & lighting**: set Static flags only per the project's lighting approach; don't bake lighting unless the project already does.

## Verification

Prefer the project's own commands. CLI shapes only — check flags against the installed version; angle brackets are placeholders:

```text
<Unity> -batchmode -nographics -projectPath <project> -executeMethod <Namespace.Class.ImportCheck> -logFile <log> -quit
<Unity> -batchmode -projectPath <project> -runTests -testPlatform PlayMode -testResults <results.xml> -logFile <log>
```

- Check the exit code and the log for import errors and missing-reference warnings.
- `-nographics` cannot render; in-game screenshots need a run with graphics (e.g. a PlayMode test calling `ScreenCapture.CaptureScreenshot` from the target camera).
- Walk the actual character controller through doors, steps, and around the asset; a teleport is not "walkable".
- Run the checks relevant to the asset and stop; build a player only when the user asks for one.

Each review gate still stops for the user's reply.
