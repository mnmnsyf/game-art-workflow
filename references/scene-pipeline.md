# Scene Workflow: direction → blockout by modules → generated parts → assembly → engine

For a whole 3D scene or set piece (a launch site, a temple, a hangar), not a single prop. Adapted from a community Tripo + Blender scene workflow (2026) and fitted to this skill's gates. A single model inside the scene still goes through [the model chain](model-pipeline.md).

| Step | Work | Who | Gate |
| --- | --- | --- | --- |
| S0 Direction | study how illustrators draw such scenes, imagine our own scene, render it in several styles with an image AI, pick a direction, derive the game views | user researches, imagines and picks; agent analyses references, lists views and objects, writes short edit lines, reviews | **G1** (style anchor + views) |
| S1 Blockout | split the scene into modules; block each in Blender at real size with flat materials | agent | **G2** (blockout at game camera) |
| S2 Parts | replace modules: hand-model or Tripo per module; props from a style-matched prop sheet | agent + user's image AI | **G2** per part / per batch |
| S3 Assembly | put the parts together in Blender at the blockout transforms; render the game cameras | agent | **G2** (assembled scene) |
| S4 Engine | export, import into the engine, place at the blockout transforms; the human does the set dressing | agent places structure, user places dressing | **G3** |
| S5 Life | VFX, lights, interactions | outside this skill (scope separately) | — |

## S0 Direction

Order matters: **illustration research → imagine our own scene → AI renders it in different styles → a human picks the direction → derive the game views**. Field result (a launch-site scene, 2026-11): nine rounds of long, carefully specified text prompts never landed; what worked was a reference found in the research, converted by an image AI, then short edits.

1. **Research illustrations and art books.** Collect works that depict this kind of scene (for a launch site: classic space-art paintings, launch photography, film stills) and study *how they are drawn*: camera height and lens, composition and framing, what is in the foreground / middle / background, where the light comes from, the palette, how scale is shown, what mood it carries. Keep the collection in the project (e.g. `art/ref/`). The agent can help: gather candidates, put them on a contact sheet, and write a short breakdown of each one's camera, composition, light and palette.
2. **Imagine our own scene.** Decide what this scene is in *our* game: the moment it shows, the **game cameras** it must serve (from the design doc: e.g. countdown side view, player-control front view, liftoff low angle, establishing shot), and the **structures and props** it needs (these become S1 modules). Note which reference each decision borrows from — camera from one, palette from another — and what is not taken (brushwork, text, insignia, a specific real product).
3. **AI renders it in different styles.** Give the image AI the chosen reference and one short instruction per style, e.g. "turn this into a high-quality Unreal Engine 5 next-gen render", or a stylized / low-poly / cel-shaded game render. Engine and render words ("UE5 next-gen", "in-game screenshot") land between photo and cartoon better than "stylized" or "realistic". Long described prompts fail in specific ways: palette words are painted literally (a written night palette became a purple fantasy glow), "stylized" drifts to cartoon and "realistic" to a stock photo, multi-image requests come back as collages, "a rocket" becomes the most famous real one.
4. **A human picks the direction.** The agent puts the candidates side by side and reviews them, but the choice is the user's. The chosen image is the **style anchor**.
5. **Derive the game views by short edits** of the anchor, one change per instruction, loose wording so the model can fill in: `Same scene, seen straight from the front.` / `Same scene from the side, just before launch.` / `Same launch site from far away.` / `Same launch site seen from above.` Over-specified edit prompts constrain it into worse images. Fix with one-liners: `Remove the text and insignia.` `Replace the red lights with warm white work lights.` `Remove the truck.` `Pull back a little.`
6. **Agent review per image**: does it serve its game camera (e.g. in a front control view the player must read the rocket's tilt; leave room for HUD), is it the same site as the anchor, can the structures be split into modules, leftover text / real-product look-alikes / unwanted elements. Archive and rename by view (`<scene>_view<N>_<name>_<nn>`). **Stop at G1** with the anchor and the view set.
7. **Rights note.** An anchor converted from someone else's artwork stays close to that artwork. Fine for internal direction; the 3D scene rebuilt in S1–S3 is original work, but the concept images themselves should not be published as the game's art (store page, jam submission, marketing).

**Outputs** (in `S0_direction/`): the style anchor, one image per game camera (`views/`), a short direction note (what the scene is, which camera serves what, which reference each choice came from), the edit lines that worked, and the draft list of structures and props that becomes the S1 module list.

When the research turns up no reference close enough, fall back to text prompts ([concept prompt pack](../templates/concept-prompt-pack.md)): short, only wanted things, one change per round.

## S1 Blockout by modules

- Split the approved concept into modules by function and by how they will be built: e.g. a building → stairs, columns, lights, walls, floor; a launch site → pad deck, tower, umbilical arms, flame trench, tanks, light masts, roads. Each module gets an ID, a real size, a pivot, a reuse count and a build route (hand-model / Tripo / kit / procedural).
- The agent builds the blockout in headless Blender from primitives at real metres, one object per module, flat colour materials roughly matching the concept palette. Render it from the actual game camera (and the concept's angle) next to the concept. This catches scale and composition errors before any spend.
- **Stop at G2** for the blockout. The blockout file becomes the layout source of truth: module transforms come from it.

## S2 Parts

- **Large and exact structures** (towers, stairs, walls, modular pieces): usually hand-modelled or kit-built in Blender from the blockout dimensions; Tripo only when the form is organic or ornamental. When using Tripo for a structural module, prefer a clean-topology / smart-mesh model family and say why on the card ([Tripo notes](tripo.md)).
- **Props**: make a **prop sheet** in the scene's style — one image AI generation of a grid of compact props (3×3 / 4×4), following the sheet rules in [generation.md](generation.md) (one class per sheet, margins, same view and scale). Slice with `grid_slice.py`, review the pack, then each approved prop becomes its own [model chain](model-pipeline.md) job with its real size. Props that are wide, tall or collision-bearing get their own image.
- Every part is reviewed against the scene anchor; batches are reviewed on a contact sheet with `--anchor`.
- A prop that is large, tall or seen up close gets its **own** image rather than a sheet cell; a sheet cell is too small for the model generator to read the back and the openings.

### Hand-built structures

Build them as **scripts** (helpers: `scripts/blender_bake.py`), not by hand in the UI, so a proportion change found in S3 (a tower shorter than the rocket beside it) is one parameter and a re-run.

1. Start from the blockout geometry of the module (it already has the right size and place); join its primitives into one mesh per module.
2. **Small bevel + weighted normals** on hard edges (e.g. 1–3 cm, 2 segments, edges above ~30°, then smooth-by-angle and face-area weighted normals). Edges catch light instead of reading as razor-sharp CG.
3. **Unwrap** (smart project is enough for baked atlases) and **bake a procedural weathered material** per channel (base colour, roughness, metallic) into one atlas: concrete, bare steel, paint over steel. Typical layers: object-space noise for colour variation, AO for cavity and crevice rust, an edge mask for chipped paint, a soot gradient near engines and trenches.
4. Swap in a plain PBR material that reads the baked maps and export the module (GLB), keeping its world placement or a recorded transform.

Two traps that make every surface bake as bare silver metal:
- **Edge masks from `Pointiness`** depend on vertex density; on low-poly boxes every vertex is a corner, so whole faces count as edge. Use a shader bevel (Bevel node normal · true normal) instead.
- **Saving bakes with the render pipeline** (`save_render`) applies the view transform and washes colours out. Save the image buffer itself (raw values); keep colour textures sRGB and data textures non-colour.

### Model-generator props

Run each prop through the [model chain](model-pipeline.md): process to its real size and review the 14-view sheet, then a refine pass in Blender for what the review found (missing roof, a forbidden red light baked into the texture, floating fragments) — see [Tripo notes](tripo.md). Record which job and which file the scene uses (`S2_parts/tripo.json`) instead of copying files around.

## S3 Assembly

- In Blender, swap every blockout placeholder for its approved part (structural modules keep the blockout transforms; a placeholder made of several primitives is one prop instance). Render the game cameras and compare with S1. This is the cheap place to catch proportion problems between parts (e.g. a rocket taller than its service tower) before anything enters the engine.

## S4 Engine

- Export one file per unique asset with its transform reset, plus a placement list (asset, location, rotation, scale) and the game cameras (`scripts/blender_export_engine.py`); then import and snap structural modules to those transforms (an engine bridge or editor Python). Follow the project's existing content folders and naming before any generic convention. It may place repeated kit pieces along explicit rules.
- **Set dressing is the human's**: props, clutter, composition and sight lines are placed by the user in the editor. Agents placing dressing by coordinates produce stiff, evenly scattered scenes; the agent's job is to make every approved prop available, correctly sized and pivoted, and to report what is placed.
- **Stop at G3** with captures from the real game camera.
- Engine-specific route, settings and traps: [Unreal](unreal.md), [Godot](godot.md), [Unity](unity.md). Cap texture size at export (e.g. 2K for generator textures that arrive at 4K) rather than in the engine, so the source assets stay small.
- When the scene enters a project other people are working in: follow the repository's own content-folder and naming rules, check for teammates' unpublished work on the same levels or folders before moving assets, simulate merges before making them, and build and run the project's tests before publishing.

## S5 Life

Effects (smoke, steam, sparks), lighting passes and interactions make the scene; they are outside this art skill. List them as follow-ups with their dependencies.

## Folder layout

One folder per scene or reusable kit, one sub-folder per step; shared tools in one place. Job ledgers stay where the tools keep them.

```
art/
├─ inbox/                      new, unreviewed images; move them out once reviewed (keep it empty)
├─ ref/                        outside references (never published)
├─ workflow/                   project-profile.json, style packs
├─ tools/                      scripts shared by all scenes (blender/, engine/)
└─ work/
   ├─ <scene>/                 e.g. launchpad
   │  ├─ S0_direction/         style anchor, view images, direction notes
   │  ├─ S1_blockout/          blockout .blend, module list, review/
   │  ├─ S2_parts/
   │  │  ├─ concepts/          prop and part concept images
   │  │  ├─ modules/           hand-built / kit parts (GLB + textures)
   │  │  ├─ tripo.json         which model-chain jobs this scene uses: {"job": <.asset-workflow job dir>, "use": "refined/model.glb"}
   │  │  └─ review/
   │  ├─ S3_assembly/          assembled .blend, review/ game-camera renders
   │  ├─ S4_<engine>/          e.g. S4_ue: export package (meshes, textures, placements + cameras), engine shots/, logs/
   │  ├─ scripts/              scene-only scripts and run_*.sh, logs/
   │  ├─ _archive/             superseded versions (move, don't delete)
   │  └─ README.md             what each step produced and how to rerun it
   └─ <kit>/                   a reusable set used by several scenes (e.g. a modular rocket): same steps, often without S1
<project>/.asset-workflow/     model-chain job ledger (raw/final/refined per job); referenced from tripo.json, never copied
```

- Current outputs sit at the top of their step folder; gate images go in `review/`; replaced versions go to `_archive/`.
- A scene that uses a kit references the kit's files (e.g. the kit's assembled `.blend`) instead of copying them.
- Scripts take every path as an argument or environment variable and resolve shared helpers relative to `art/tools/`, so moving a scene folder doesn't break them. Images inside saved `.blend` files are absolute paths — remap them after moving files.
- Engine content follows the project's existing folders (check where its current meshes, textures and levels live) even when a naming document says otherwise; ask only if the two disagree and nothing exists yet.

## Pitfalls seen in production

| Symptom | Cause and fix |
| --- | --- |
| Baked textures look washed-out silver | Pointiness edge mask on low-poly geometry, or bakes saved through the view transform — see [hand-built structures](#hand-built-structures) |
| Every engine material renders grey | The master material failed to compile (e.g. a texture parameter with no default) — check the master first, not the instances |
| A long image-AI chat slows down and stops saving | Start a new chat every few images; download only the full-resolution result, not the preview |
| A browser can't upload to the generator | Use a browser tool that can set file inputs; the native file picker is outside the page |
| Downloads stall behind save dialogs | Allow automatic downloads for the site and turn off "ask where to save" before a batch |
| Renders or files appear in an unexpected root folder | A script used relative paths; resolve every path to absolute |
| Textures go missing in a `.blend` after reorganising folders | Saved images keep absolute paths; remap them after moving files |
| A rebuilt level is empty and its actors landed in another map | Recreating a level another level references can fail silently; open and empty it instead, and check which world is current |
