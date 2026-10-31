---
name: game-art-workflow
description: Use when a user requests 2D or 3D static game art — scene backgrounds, props, buildings, vegetation, tileable textures, modular kits, sprite cut-outs — or integrating such assets into Godot, Unity, or Unreal Engine, including tool/vendor selection, staged art review, batch production, and resuming or rolling back asset jobs across sessions. Applies to requests in any language, including Chinese. Not for character animation, rigging, UI, particle VFX, or standalone gameplay systems.
---

# Game Art Asset Workflow

Turn a one-line request into static assets that **match the project's style, pass staged review, can be rolled back, and hold up in the actual game camera**. This skill orchestrates and gatekeeps: generation, modeling, and import are done by whatever tools actually exist in the current environment, and `scripts/` provides deterministic ledger and check tools.

**Four hard rules**
1. **Reviews do not substitute for each other**: concept approval ≠ model / cut-out approval ≠ in-game approval; a technical PASS ≠ art approval; silence ≠ approval.
2. **Every gate is a hard stop**: at G1, G2, and G3, show the result, end your turn, and wait for the user's reply — **even when the runtime encourages autonomous progress** (auto mode, "work autonomously", "don't ask questions", long-running agent loops, a tight deadline). Such instructions govern how you handle technical steps; they are not art approval. The only exception is a delegation the user wrote in this conversation that names the gates and the acceptance criteria; record it as `delegated_agent` and quote it. A gate the user has not answered stays open.
3. **Never fake capability**: do not promise tools you have not detected; label unverified routes "unverified"; programmatic color blocks are not concept art; a PNG is not a PSD.
4. **No unauthorized spend, no damage to the workspace**: new spend stays within the authorized count / budget; when a remote result is unclear, reconcile before resubmitting; originals are always kept; replace only the designated references; never reset / clean the user's work.

## Read on demand

First confirm the project root, engine version, and whether a job record already exists; read only the branch the current step needs.

| Current work | Read |
| --- | --- |
| New project, new request, whole scene, batch planning | [Project profile & plan](references/intake.md) |
| Style lock, batch consistency, reference management | [Style consistency](references/style.md) |
| Tool choice, missing image generation, cost & visibility | [Tools & vendors](references/tools.md) |
| Review records, rework, resuming, replacement & rollback | [Review & state](references/review-state.md) |
| 2D images, layering, cut-outs, transparency, tiling textures | [2D production](references/2d.md) |
| 3D references, models, materials, decimation, collision | [3D production](references/3d.md) |
| Engine integration | [Godot](references/godot.md) / [Unity](references/unity.md) / [Unreal Engine](references/unreal.md) |
| Full worked examples | [3D village → Godot](examples/village-houses-godot.md) / [2D tiling & cut-outs](examples/tileset-and-props-2d.md) |
| Maintaining this skill, verification limits & evidence | [Validation & evidence](references/validation.md) |

## Workflow

1. **Survey the project**: read project docs, existing assets, camera, character scale, and implementation. Reuse `art/workflow/project-profile.json` if present; otherwise create one from the [template](templates/project-profile.json). For an existing job, run `python scripts/artjob.py resume <asset-id>` first and continue from its output instead of re-asking settled parameters.
2. **Choose the form**: by player use, recommend a standalone image, layered background, tiling texture, 3D, procedural, or hybrid; for buildings first distinguish distant shell / walk-around / door opens / enterable. The user's explicit choice wins.
3. **Probe tools**: confirm which image generation, 3D generation, DCC, and engine capabilities are actually callable. When something is missing, list the real options (API / local / web / user generates and imports / existing assets) with cost, privacy, and export limits, and let the user choose.
4. **G1 plan review** → production → **G2 intermediate review** → integration → **G3 in-game review** (table below). Stop at each gate per hard rule 2.
   - **Batches (≥3 assets of one kind)**: read [Style consistency](references/style.md). The G1 plan must include a "style pack" plan — anchor source, prompt skeleton, palette, fixed camera and light direction, generation parameters — and reserve an entry in the profile's `style.packs`; once the sample passes G2, register it as an anchor. Without a style pack the tenth asset rarely belongs to the same game as the first, and variant reuse has nothing to anchor to.
   - Take a representative sample through G3 first, then expand with the approved style pack and parameters; review batches together with `contact_sheet.py --anchor`, side by side with the anchors.
5. **Triage rework**: fix technical problems (units, channels, normals, alpha edges, collision) autonomously and keep evidence; for appearance changes (silhouette, color, parts, design) explain the reason and plan first and send them for review; for structural failures compare repair, route change, and regeneration costs instead of rerolling for luck.
6. **Integrate**: place the asset in the designated real scene; handle size, materials, collision, sorting / occlusion, grounding, and resource settings; reuse existing interaction interfaces. If a new gameplay system is needed, state the dependency and scope it separately.
7. **Close out**: run the checks relevant to the asset's use and stop — no looping screenshots, no repeated full-project test runs. Delete intermediates this job left in the project. Deliver the approved version, sources, runtime resources, entry points, and rollback record, and clearly separate "technically complete / awaiting visual review / accepted".

## The three gates

| Gate | Show | Pass condition |
| --- | --- | --- |
| **G1 Plan** | One page or less: use & interaction, style basis, asset form, channel & cost / count, split & reuse, integration scope, acceptance criteria ([template](templates/g1-plan.md)) | The user approves the specific plan; do not re-ask when an explicit authorization already exists and the plan has not materially changed |
| **G2 Intermediate** | Concept art; for 3D also the raw model front / back / bottom and key openings; for 2D also cut-outs, transparent edges (black, white, colored backgrounds), and a tiling preview | Each applicable artifact is approved on its own before dependent steps; there may be several artifacts, and approving the concept does not skip the model |
| **G3 In-game** | Screenshots in the actual camera, lighting, and character scale, plus the targeted check results | The user accepts, or a written delegation lets the agent accept by agreed criteria (recorded as `delegated_agent`) |

At a gate, **show the images directly**, with at most three key questions, the recommended version, and absolute file paths; for rework give a same-angle before/after (`scripts/compare_images.py`). Record each decision against the specific version and hash with `artjob.py review`, then end the turn. Approving a reference image is not consent to public upload, new spend, or the final result.

## Tool scripts

All Python 3.9+. The ledger script uses only the standard library; image scripts need Pillow. Scripts read and write only the paths given, never touch the network, and never spend. They live in this skill's directory; when calling them from a project, use the full path and pass the project root: `python <skill-dir>/scripts/artjob.py --root <project-root> …`.

| Script | Purpose |
| --- | --- |
| `scripts/artjob.py` | Job ledger: `init / artifact / stage / review / spend / event / status / resume / verify`, atomic writes, file lock, SHA256 |
| `scripts/contact_sheet.py` | Numbered, labeled contact sheet of candidates / a batch for review at once |
| `scripts/tile_preview.py` | N×N tiling preview plus left/right and top/bottom seam metrics |
| `scripts/alpha_check.py` | Real alpha, fake checkerboard painted into RGB, black/white/colored composites, edge margin |
| `scripts/compare_images.py` | Decoded pixel comparison (max / mean error, diff map, side-by-side) to prove fidelity or show rework |

## Key distinctions

- **Fidelity vs. alteration**: build an as-is import comparison before optimizing. Replacing a roof, repainting materials, changing the silhouette, or removing parts is an art change; it must be reviewed and must not be called fidelity optimization.
- **Five states recorded separately**: generation finished, actually downloaded, technically valid, visually approved, integrated in the scene — none stands in for another.
- **Ordered replacement**: import and verify a new version independently first, then replace the designated reference; keep the old asset and its reference / placement record. List the impact before changing shared materials or doing batch replacement.
- **Reconcile unclear remote results**: on disconnect or an unclear result mark `needs_reconcile`, recover the original job, never resubmit or switch channels and pay again.
- **No temp-file litter**: write intermediates (single-view renders, test bakes, unpacked bake passes, superseded versions, DCC backups, tool reports) to the session scratchpad / system temp, not the project. Keep only sources, import sources, final assets, the review images shown at gates, and the ledger; see [Review & state](references/review-state.md).
- **Project parameters live in the profile**: style, machine paths, prices, and disabled tools go in the project profile, not into cross-project rules.

## Example at a glance

"Make a set of village houses and put them in Godot": check character scale and camera → G1 confirms a "walk-around, door opens but not enterable" plan and the sample choice (**stop for the reply**) → for the representative house, G2 reviews the concept, then the raw model front and back (**stop for each**) → keep UV/PBR for an as-is import comparison → separate collision, door step, and occlusion fade → G3 in the actual camera (**stop**) → after approval, extend to the remaining houses with the same reference pack and parameters, batch-reviewed on a contact sheet. Full walkthrough: [examples/village-houses-godot.md](examples/village-houses-godot.md).
