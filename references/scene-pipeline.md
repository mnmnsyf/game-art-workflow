# Scene Workflow: direction → blockout by modules → generated parts → assembly

For a whole 3D scene or set piece (a launch site, a temple, a hangar), not a single prop. Adapted from a community Tripo + Blender scene workflow (2026) and fitted to this skill's gates. A single model inside the scene still goes through [the model chain](model-pipeline.md).

| Step | Work | Who | Gate |
| --- | --- | --- | --- |
| S0 Direction | study how illustrators draw such scenes, imagine our own scene, render it in several styles with an image AI, pick a direction, derive the game views | user researches, imagines and picks; agent analyses references, lists views and objects, writes short edit lines, reviews | **G1** (style anchor + views) |
| S1 Blockout | split the scene into modules; block each in Blender at real size with flat materials | agent | **G2** (blockout at game camera) |
| S2 Parts | replace modules: hand-model or Tripo per module; props from a style-matched prop sheet | agent + user's image AI | **G2** per part / per batch |
| S3 Assembly | import parts at blockout transforms; the human does the set dressing | agent places structure, user places dressing | **G3** |
| S4 Life | VFX, lights, interactions | outside this skill (scope separately) | — |

## S0 Direction

Order matters: **illustration research → imagine our own scene → AI renders it in different styles → a human picks the direction → derive the game views**. Field result (a launch-site scene, 2026-11): nine rounds of long, carefully specified text prompts never landed; what worked was a reference found in the research, converted by an image AI, then short edits.

1. **Research illustrations and art books.** Collect works that depict this kind of scene (for a launch site: classic space-art paintings, launch photography, film stills) and study *how they are drawn*: camera height and lens, composition and framing, what is in the foreground / middle / background, where the light comes from, the palette, how scale is shown, what mood it carries. Keep the collection in the project (e.g. `art/ref/`). The agent can help: gather candidates, put them on a contact sheet, and write a short breakdown of each one's camera, composition, light and palette.
2. **Imagine our own scene.** Decide what this scene is in *our* game: the moment it shows, the **game cameras** it must serve (from the design doc: e.g. countdown side view, player-control front view, liftoff low angle, establishing shot), and the **structures and props** it needs (these become S1 modules). Note which reference each decision borrows from — camera from one, palette from another — and what is not taken (brushwork, text, insignia, a specific real product).
3. **AI renders it in different styles.** Give the image AI the chosen reference and one short instruction per style, e.g. "turn this into a high-quality Unreal Engine 5 next-gen render", or a stylized / low-poly / cel-shaded game render. Engine and render words ("UE5 next-gen", "in-game screenshot") land between photo and cartoon better than "stylized" or "realistic". Long described prompts fail in specific ways: palette words are painted literally (a written night palette became a purple fantasy glow), "stylized" drifts to cartoon and "realistic" to a stock photo, multi-image requests come back as collages, "a rocket" becomes the most famous real one.
4. **A human picks the direction.** The agent puts the candidates side by side and reviews them, but the choice is the user's. The chosen image is the **style anchor**.
5. **Derive the game views by short edits** of the anchor, one change per instruction, loose wording so the model can fill in: `Same scene, seen straight from the front.` / `Same scene from the side, just before launch.` / `Same launch site from far away.` / `Same launch site seen from above.` Over-specified edit prompts constrain it into worse images. Fix with one-liners: `Remove the text and insignia.` `Replace the red lights with warm white work lights.` `Remove the truck.` `Pull back a little.`
6. **Agent review per image**: does it serve its game camera (e.g. in a front control view the player must read the rocket's tilt; leave room for HUD), is it the same site as the anchor, can the structures be split into modules, leftover text / real-product look-alikes / unwanted elements. Archive and rename by view (`<scene>_view<N>_<name>_<nn>`). **Stop at G1** with the anchor and the view set.
7. **Rights note.** An anchor converted from someone else's artwork stays close to that artwork. Fine for internal direction; the 3D scene rebuilt in S1–S3 is original work, but the concept images themselves should not be published as the game's art (store page, jam submission, marketing).

When the research turns up no reference close enough, fall back to text prompts ([concept prompt pack](../templates/concept-prompt-pack.md)): short, only wanted things, one change per round.

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
