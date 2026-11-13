# Prompting & Raw Generation

How to ask a generator for game art so the output survives deterministic processing. The generator makes source material; size, alpha, grid, anchors, and scale are fixed afterwards by scripts, never trusted from the image.

## Prompt card

Write prompts by hand from these blocks. Keep the invariant blocks (VIEW, ART DIRECTION, LOCKS, EXCLUDE) identical across a family and change only SUBJECT; store the card in the style pack.

```text
ROLE/PURPOSE: production asset for [gameplay role]
SUBJECT: [specific object and state]
VIEW: [orthographic / top-down / side / three-quarter], [camera angle and facing]
ART DIRECTION: [shape language], [palette roles], [materials], [edge / outline treatment]
GAME-SCALE READ: [silhouette and focal details that must survive at W×H on screen]
TECHNICAL OUTPUT: [size / aspect], [solid background colour or scene], [grid / slot count]
LOCKS: preserve [identity, proportions, palette, lighting, line weight] from the reference
EXCLUDE: text, labels, UI, mockup frames, scenery, duplicate objects, cropped edges, signatures, watermarks
```

- Describe observable properties; vague words ("beautiful", "high quality", "cinematic") add nothing, and never use a living artist's name as the style — translate references into palette, geometry, material, lighting, and mark-making.
- For edits, state both what changes and what stays fixed. Change one variable per edit pass.
- Show a local reference image to the tool as an image (view / attach it) before referring to it; a file path in the prompt is not a visual input.
- Save the exact prompt next to the output (`<asset>.prompt.txt`) and in the ledger event; reproduction depends on it.

## Backgrounds and transparency

- **Never prompt for "transparent background"** — generators paint a checkerboard into RGB. Use a tool's native alpha option when it has one and verify it with `alpha_check.py`; otherwise prompt a **solid flat background** and key it with `chroma_key.py`.
- Choose the key colour to be (1) far from every colour in the subject and (2) for soft or painted edges, close to the in-game surroundings so any residual fringe blends (forest → dark green, dungeon → dark gray, sky → steel blue). Magenta `#FF00FF` is a good default for hard-edged and pixel art that contains no pink or purple.
- Say "no gradient, no texture, no shadow, no floor plane" for the background; a cast shadow on the backdrop cannot be keyed cleanly.
- 3D references for image-to-3D keep their solid background unless the vendor asks otherwise.

## Sheets, kits, and grids

Batching several objects in one image is cheaper and keeps style consistent, but only for the right objects.

- Classify each object first: **compact** (rocks, crates, lamps, shrubs) may share a square `2x2` / `3x3` / `4x4` pack; **wide or long** (bridges, fences, platforms, roads, aspect beyond ~1.6:1), **tall or large** (buildings, gates, big trees), **collision-bearing** (doors, ledges, walkable edges, hazards), and **tile / strip pieces** get their own generation, a custom wide cell, or a tile workflow. Never mix classes in one sheet.
- Containment, stated in the prompt: every object fully inside its cell, a margin of background on all four sides, the same scale and view in every cell, no borders or lines between cells.
- Treat the returned grid as a candidate, not exact data: slice with `grid_slice.py`, which trims, applies one shared scale, aligns a common anchor (feet by default), and flags cells that touch an edge. A flagged object is regenerated on its own — do not relax the check or keep retrying the same pack.
- A layout guide image (empty grid with safe areas) helps strict packs; say it is layout-only so its boxes are not drawn.

## Size and direction

- Downscaling a 1024 px generation to a 64 px sprite turns it to mud. Design for display sizes of about 128 px and up, prompt bold, flat forms with few small details, or generate a kit and slice it. For true pixel art the generation is a draft — enforce the grid and palette afterwards (see [2d.md](2d.md)).
- Keep the original generated resolution as the source; make separate engine-scale exports.
- Generators often get left/right and facing wrong. Generate one facing and mirror at runtime or in processing, unless the design is asymmetric and both sides were designed.
- Every asset gets an **in-game size** in the manifest (meters for 3D, tile size for textures, display pixels for sprites). Many image-to-3D tools export every model about one unit tall; the manifest, not the generator, decides the real size.

## Families and drift

- Derive variants from one approved hero asset by editing it, prompting only what changes.
- When outputs drift, go back to the approved seed and make a constrained edit; never keep editing a drifted derivative until it becomes the accidental reference.
- Local generators (open image / mesh models on the user's GPU) are free but slow and one job at a time; run them sequentially. Paid APIs need confirmation before the first call (see [tools.md](tools.md)).

## Driving an image AI through a browser

When the user's image tool is a web app the agent operates in their browser (signed in by the user):

- One image per request, short instructions; the reference image is attached once per chat.
- Long chats get slow and may stop saving; start a new chat every ~5 images and re-attach the reference.
- The page often shows a reduced preview and thought images next to the result; download only the final full-resolution image and check its pixel size before using it.
- Name each download by asset and version (`<scene>_obj_<name>_01`), then move it out of the inbox once reviewed.
