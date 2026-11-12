# Scene Workflow: direction → blockout by modules → generated parts → assembly

For a whole 3D scene or set piece (a launch site, a temple, a hangar), not a single prop. Adapted from a community Tripo + Blender scene workflow (2026) and fitted to this skill's gates. A single model inside the scene still goes through [the model chain](model-pipeline.md).

| Step | Work | Who | Gate |
| --- | --- | --- | --- |
| S0 Direction | reference research, several style directions in one fixed framing, pick one | agent researches and writes prompts; user generates and picks | **G1** (direction) |
| S1 Blockout | split the scene into modules; block each in Blender at real size with flat materials | agent | **G2** (blockout at game camera) |
| S2 Parts | replace modules: hand-model or Tripo per module; props from a style-matched prop sheet | agent + user's image AI | **G2** per part / per batch |
| S3 Assembly | import parts at blockout transforms; the human does the set dressing | agent places structure, user places dressing | **G3** |
| S4 Life | VFX, lights, interactions | outside this skill (scope separately) | — |

## S0 Direction

1. **Research before prompting.** Look at how the subject is actually built and how strong illustrations stage it: real facilities and hardware for grounded subjects, art books and illustrators for stylised ones. Write a one-page note: the 8–15 structures and props the scene needs (these become S1 modules), scale cues, and the visual traits of the target look.
2. **Translate a named style into traits.** "In the style of <living director / artist / film>" is weak and borrows someone else's identity. Describe what you can see: palette, light, weather, lens and framing, scale of people to structures, materials, wear, mood. Keep the named source only in the internal note.
3. **Directions, not variations.** Write 3–6 directions that differ in one or two big choices (time of day, weather, setting, palette), with the **same framing, subject list and aspect ratio**, so the user compares looks, not compositions. Use the [concept prompt pack](../templates/concept-prompt-pack.md) shape; scene shots use the game aspect ratio and a real game-camera framing instead of the single-object view.
4. The user generates (e.g. Nano Banana, Midjourney) and picks; review with a contact sheet and rubric A1–A3 and A7. **Stop at G1.** Then 1–2 refinement passes on the chosen direction, changing one thing per pass. Register the approved image as the scene's style anchor in the profile `style.packs`.

## S1 Blockout by modules

- Split the approved concept into modules by function and by how they will be built: e.g. a building → stairs, columns, lights, walls, floor; a launch site → pad deck, tower, umbilical arms, flame trench, tanks, light masts, roads. Each module gets an ID, a real size, a pivot, a reuse count and a build route (hand-model / Tripo / kit / procedural).
- The agent builds the blockout in headless Blender from primitives at real metres, one object per module, flat colour materials roughly matching the concept palette. Render it from the actual game camera (and the concept's angle) next to the concept. This catches scale and composition errors before any spend.
- **Stop at G2** for the blockout. The blockout file becomes the layout source of truth: module transforms come from it.

## S2 Parts

- **Large and exact structures** (towers, stairs, walls, modular pieces): usually hand-modelled or kit-built in Blender from the blockout dimensions; Tripo only when the form is organic or ornamental. When using Tripo for a structural module, prefer a clean-topology / smart-mesh model family and say why on the card ([Tripo notes](tripo.md)).
- **Props**: make a **prop sheet** in the scene's style — one image AI generation of a grid of compact props (3×3 / 4×4), following the sheet rules in [generation.md](generation.md) (one class per sheet, margins, same view and scale). Slice with `grid_slice.py`, review the pack, then each approved prop becomes its own [model chain](model-pipeline.md) job with its real size. Props that are wide, tall or collision-bearing get their own image.
- Every part is reviewed against the scene anchor; batches are reviewed on a contact sheet with `--anchor`.

## S3 Assembly

- The agent imports approved parts and snaps structural modules to the blockout transforms (an engine bridge or editor Python). It may place repeated kit pieces along explicit rules.
- **Set dressing is the human's**: props, clutter, composition and sight lines are placed by the user in the editor. Agents placing dressing by coordinates produce stiff, evenly scattered scenes; the agent's job is to make every approved prop available, correctly sized and pivoted, and to report what is placed.
- **Stop at G3** with captures from the real game camera.

## S4 Life

Effects (smoke, steam, sparks), lighting passes and interactions make the scene; they are outside this art skill. List them as follow-ups with their dependencies.
