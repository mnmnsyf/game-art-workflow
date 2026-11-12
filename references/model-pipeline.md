# Generated 3D Model Chain: concept image → Tripo → Blender → review

The default route for a generated static 3D model (props, rocks, vehicle and machine parts, simple buildings). The agent cannot rely on its own image generation: **the user makes concept images in any image AI, the agent writes the prompt pack and reviews**; the agent then drives Tripo and Blender itself. Characters and anything rigged go to [Character production](characters.md); exact, modular, or enterable structures are usually better modeled in Blender directly (decide at G1, see [3D production](3d.md)).

One asset moves through six stages. G-gates are hard stops (SKILL.md hard rule 2).

| Stage | Who | Output | Gate |
| --- | --- | --- | --- |
| M0 Spec | agent | size, budget, camera, Tripo route, credit cap | **G1** |
| M1 Concept | user generates, agent reviews | one approved Tripo-ready image | **G2a** |
| M2 Generate | agent (Tripo API) or browser agent (Studio) | one raw GLB, untouched | — |
| M3 Prepare + render | agent (Blender, headless) | true-size GLB, `.blend`, 14-view review sheet | **G2b** |
| M4 Optimize (optional) | agent | A2 branch: LOD / decimation / texture budget | review if appearance changes |
| M5 Engine | agent (engine bridge) | imported asset in the real scene | **G3** |

Before the first job on a machine run `python <skill>/scripts/model_job.py --root <project> doctor` and fix what it reports ([Setup](setup.md)). Record the Blender path and Tripo route in the project profile's `tools`.

## M0 Spec (G1)

Fill these before any image is made; the G1 card is short.

- **In-game size** in metres and which axis it means: `height` for things that stand (props, buildings), `longest` for things without a natural up (rocks, debris, ship parts). Generators export everything about one unit tall; this number, not the generator, decides real size.
- **Camera and screen size**: how big it appears in the actual game camera (e.g. "fills 1/6 of the screen at closest approach"). This sets detail level and triangle budget.
- **Triangle budget** and texture budget, as acceptance targets. Tripo API passes the budget as `face_limit`; Studio may ignore it — judge by the returned count.
- **Parts that must be separate** (lids, hatches, turrets, doors). A single generated mesh rarely splits cleanly; if movement matters, plan Blender work or a modular build.
- **Route**: Tripo API (`tripo-cli`, API balance) or Studio (web credits, browser agent). Never switch wallets mid-job. Model family: H-series favours shape fidelity, P-series favours controllable topology; write the reason on the card ([Tripo notes](tripo.md)).
- **Credit cap** for this one job, and visibility (private by default).

## M1 Concept (G2a)

1. Write a **prompt pack** from [the template](../templates/concept-prompt-pack.md): one prompt per image AI the user may use, the Tripo-ready requirements, and the file name to save back. Show style anchors as images when the user has them.
2. The user generates and drops candidates into `art/inbox/<asset-id>/` (or attaches them). Record the tool and version they used; it goes into provenance.
3. Review every candidate with [the model-review rubric](../templates/model-review-rubric.md), section A. Look at the image itself, not the filename. Present a contact sheet (`contact_sheet.py --anchor <style anchors>`), the scores, a recommended pick, and for each rejected image the concrete fix and a revised prompt line.
4. **Stop at G2a.** Only an approved image goes forward. Edits are made by the user in their image tool; change one thing per pass.

What makes an image Tripo-ready (details in [Tripo notes](tripo.md)): one complete object, uncropped, three-quarter view at moderate perspective, readable parts and silhouette, plain solid background, soft even light without baked cast shadows, no text, no ground plane or scenery. Keep design detail that matters — do not simplify the design into a box to please the generator. Multi-view input only when the views genuinely agree (same part count, proportions, facing); independently generated "front" and "back" images are not a multi-view set.

## M2 Generate

```text
python <skill>/scripts/model_job.py --root <project> init --asset <id> --height <m> [--size-axis longest] --triangles <n> --image <approved.png> --image-source "<tool + version>" [--provider studio]
python <skill>/scripts/model_job.py --root <project> plan    --job <job>          # API: zero-cost dry run; shows estimate
python <skill>/scripts/model_job.py --root <project> submit  --job <job> --max-estimated-credits <cap>
python <skill>/scripts/model_job.py --root <project> resume  --job <job>          # poll + download; repeat until downloaded
```

- `init` copies the image into the job and pins its SHA256; a changed image is refused. One job = one attempt; a new image or new settings = a new job.
- `submit` refuses a multi-step or multi-candidate plan, a missing estimate, or an estimate over the cap. It persists `submitting` before calling out; an unclear result becomes `needs_reconcile` — look up the task in Tripo's history and `resume --task-id <id>`. **Never submit again to recover.**
- Studio route: follow [Tripo notes → Studio](tripo.md#studio-web-credits) (`studio-preflight` → `studio-begin` → one click → `studio-record` → export → `studio-attach`).
- An existing GLB (bought, made by hand, or downloaded earlier): `import-local --file <glb>`, no spend.

## M3 Prepare and render (G2b)

```text
python <skill>/scripts/model_job.py --root <project> process --job <job> [--blender <path>]
```

Runs Blender headless twice: `blender_prepare.py` (A1 faithful prep: real size, ground-centred origin, baked transforms; keeps parts, UVs, materials, textures; refuses armatures and shape keys) and `render_asset.py` (7 textured + 7 clay views incl. a front three-quarter, plus stats). Output in `<job>/final/`: `model.glb`, `source.blend`, `report.json`, `review/`, `review-sheet.png` (concept image tagged as anchor, then textured row and clay row). The raw download is never changed; existing `final/` is never overwritten.

Review with rubric section B:

1. **Independent reviewer.** When subagents are available, give a fresh reviewer only the brief, the approved concept, `review-sheet.png` and `report.json`, and ask for rubric B scores with evidence per view. The agent that ran the job does not grade its own output. The reviewer's verdict is advice; the user decides at the gate.
2. Separate **geometry** problems (clay row: lumps, holes, fused parts, wrong back, floating fragments) from **material** problems (textured row: baked lighting, smears, seams, wrong colours).
3. Compare against the concept at `front34`: silhouette, proportions, part count, key details.
4. **Stop at G2b.** Show the sheet, scores, triangle count vs budget, and the recommendation: accept / fix in Blender / new concept / new generation. Fix choice follows SKILL.md step 5: repair locally when the problem is technical or small; a structural failure goes back to M1 rather than a paid reroll for luck.

## M4 Optimize (only when needed)

If the accepted model exceeds the triangle or texture budget at the real camera, make an A2 branch from `final/source.blend` (decimate with UV and normal preservation, LODs, texture downsize), re-render with `render_asset.py`, and compare against the A1 sheet. Any visible change to silhouette or materials is an art change and is reviewed. Do not decimate for process' sake.

## M5 Engine (G3)

Import the approved GLB through the project's engine bridge (for Unreal see [unreal.md](unreal.md); UE 5.x imports GLB via Interchange — confirm scale and forward axis once per project and record them in the profile). Place it in the real level at the real camera, capture, and **stop at G3**. A DCC render is not game acceptance.

## Ledger and files

- Job files live in `<project>/.asset-workflow/<asset>/<job>/` (add it to `.gitignore`). Large raw models stay out of version control.
- Record gate decisions with `artjob.py review` against the approved file's hash, and credits with `artjob.py spend`. `model_job.py status --job <job>` shows the machine state; `approved_for_game` stays false until G3.
- Only the approved, prepared model (and its `.blend` if the project keeps sources) is copied into the project's art folder. Inside a scene workflow, list it in the scene's `S2_parts/tripo.json` (job folder + file to use) instead of copying it ([folder layout](scene-pipeline.md#folder-layout)).
