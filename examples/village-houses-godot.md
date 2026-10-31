# Example: A Set of Village Houses into Godot (3D)

> User: "Make me a set of village houses and put them in the Godot village scene."

## 0. Survey (no questions yet)

- Read `project.godot`: Godot 4.x, Forward+; third-person top-down camera at about 45°, character capsule 1.7 m tall.
- `scenes/village.tscn` already has terrain and two gray-box placeholders; the character controller is a CharacterBody3D with a 0.3 m step limit.
- No project profile → create one from the template, with style, budget, and channel in `open_questions`.
- Probe tools: this session has image generation; Blender 4.x is installed; the project has no 3D generation wrapper; a browser is available.

## 1. One batch of first questions (three)

1. Style: follow the warm hand-painted cartoon look of the existing terrain next to the gray boxes? (Recommended: yes)
2. Function: doors open but houses are not enterable, players can walk around? (Recommended: yes; interiors later)
3. 3D channel: an image-to-3D web service, about X per generation for the sample; or a Blender procedural body plus generated textures (free, more regular). (Recommended: web service for the sample, then choose the batch route after comparing)

## 2. G1 plan (one page)

| Item | Content |
| --- | --- |
| What | 5 houses: 2 sizes × roof variants, plus swappable door and chimney parts |
| Interaction | Walk-around; doors open, not enterable; eaves fade when the player is near |
| Style pack | `village-v1`: 3/4 top-down, light from upper left, plain background; palette and anchors locked after the sample passes G2 |
| Sample | House A: door step and overhanging roof, covering the hardest step and eave-occlusion cases |
| Budget | Mid range about 8–15k triangles, 2K base color + normal + ORM |
| Acceptance | In the actual camera the character walks around, opens the door, climbs the step without floating; the eave fade shows no holes |

**Stop and wait.** The user replies "go with this" → `artjob.py review village_house_a G1 --artifact plan_v1 --decision approved --by user --evidence "go with this"`.

## 3. G2 concept

- Generate 3 candidates and build a contact sheet with `contact_sheet.py`; recommend #2 (clear door step, readable roof silhouette). **Stop and wait.**
- User picks #2 → register the artifact and hash, record G2 approval, and register it as the first anchor of style pack `village-v1` ([style.md](../references/style.md)).

## 4. Submit 3D generation

- `stage submitting` → upload the approved image on the web page, check thumbnail, private visibility, and estimated cost → record the job ID.
- The browser disconnects midway → `stage needs_reconcile`; reopen the job list, find the original job, and download it — **without clicking generate again**.

## 5. G2 raw model

- A0: download the raw GLB and textures, register hashes. Show four screenshots: front, back, bottom, doorway. **Stop and wait.**
- The back windows have melted into one patch → this is an appearance issue: offer "local fix in Blender (about 30 minutes, free)" vs. "regenerate (another credit, no guarantee of improvement)", recommend the fix. The user agrees.
- The fix outputs `house_a_v2.glb` (`--parent` pointing at the raw); after a same-angle comparison the user approves v2.

## 6. Faithful import and integration

- A1: normalize to meters and a ground origin, no decimation (the triangle count is within budget, so A2 is skipped). `compare_images.py` compares the source textures with the imported ones: max diff 0.
- Collision: walls as box compounds, the doorway left open, the door step as two box steps plus a gentle slope; no whole-building convex hull.
- Eave fade: duplicate the full native material, change only the distance-fade parameters, keep collision.
- Replace only gray box A's Mesh reference, recording the original transform for rollback.

## 7. Targeted checks and G3

- Automated walking with the actual character controller: once around the house, up the door step, close to the eaves → no sticking, no floating, fade correct.
- Three screenshots in the actual camera (far, mid, near the eaves) go to G3; checks passed, so stop — no repeated screenshots. **Stop and wait.**
- The user accepts → `stage accepted`.

## 8. Expansion batch

- Generate the other 4 houses with style pack `village-v1` and the verified parameters; review them together on a contact sheet with the anchors and record a decision per house.
- Delivery note: each house's approved version and hash, total cost, scene references, rollback method; state clearly "5 houses technically complete, 3 accepted, 2 awaiting G3".
