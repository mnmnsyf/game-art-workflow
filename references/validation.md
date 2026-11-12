# Validation Scenarios & Evidence

This skill is workflow orchestration and integration guidance with deterministic ledger / check scripts; it is not a fully automatic cross-engine executor. Tools that don't exist must be probed, chosen, or explicitly waited on.

## Maturity

| Branch | Status | Basis |
| --- | --- | --- |
| 3D static → Godot 4.x | Tested in a real project | [Case study](../examples/case-study-godot-cottage.md) |
| 2D sprites / backgrounds → Godot | Project practice exists; the full three-gate flow awaits a complete task | — |
| Tiling textures, modular kits | Workflow defined, awaiting a real test | — |
| Unreal Engine 5 | Verified by the maintainer in a real UE5 project | [unreal.md](unreal.md) |
| Unity | Operating reference, awaiting the first Unity project | [unity.md](unity.md) |
| Character concepts / consistent sheets / static character generation and Blender preparation | Project sample exists; does not verify a rig | [Character production](characters.md) |
| Character auto-rigging / generic animation retargeting / animated Godot integration | Workflow documented; real sample still pending | [Character production](characters.md) |
| Animated Unreal character integration | Workflow documented; real UE sample still pending | [Character production](characters.md) |
| `scripts/` (except the Blender scripts) | Local self-test passes (below) | `python scripts/selftest.py` |
| `scripts/blender_views.py` | Written against the Blender 3.6+ API, not yet run in CI or by the maintainer | — |
| `scripts/model_job.py` state machine, credit cap, Studio branch, tool discovery | Unit tests pass with the Tripo CLI mocked (no network, no spend) | `python scripts/test_model_job.py` |
| `model_job.py process` → `blender_prepare.py` + `render_asset.py` | Real run on Blender 5.3.0 (Windows): synthetic GLB sized by longest axis, 14 views, review sheet | `ART_TEST_BLENDER=<blender> python scripts/test_model_job.py` |
| Tripo API submit / resume through `tripo-cli@0.8.1` | Ran in a real project before it moved into this skill; not yet re-run from `model_job.py` | [Tripo notes](tripo.md) |
| External concept handoff + rubric review | Documented; first real asset pending | [Model chain](model-pipeline.md) |

Only a route that actually ran successfully may be promoted in a project profile to "verified for this version and project".

## Design basis

This skill grew out of an older workflow for a single project's 3D pipeline. Its real failures included swapping a roof during integration, re-unwrapping UVs, and losing material channels so the result no longer matched the source model; it also lacked 2D / UE branches, a project art profile, and unified review records. These failures are the direct source of "fidelity vs. alteration", the three gates, and the ledger protocol.

## Scenario walkthrough

| Scenario | Expected behavior | Must not happen |
| --- | --- | --- |
| No built-in image generation, user wants a 2D house | List actual API / local / web / manual import options, pick a channel or deliver an external generation pack | Claiming images were generated, silently using a paid API |
| Model generation after concept approval | Record the concept version hash, download the raw model, submit it for model G2 | Treating concept approval as model / game approval |
| Disconnect after web submission | Record `needs_reconcile`, recover and download the original job | Clicking generate again or switching to an API and paying twice |
| Roof needs rebuilding, project is in a hurry | State it is an alteration, give a comparison, send for review per authorization | Calling it fidelity optimization and overwriting the source model |
| Ten houses, limited budget | Take a representative sample to G3, then expand with the approved standard and style pack | Spending the whole quota on a batch up front |
| Same asset continued across sessions | `artjob.py resume` checks files / hashes, approvals, and jobs before continuing | Re-asking all parameters, redoing approved outputs |
| No UE runtime | Mark unverified, provide probe and integration steps | Claiming both engines were tested |
| Project has uncommitted level changes | Import independently, replace the designated reference, record rollback | reset / clean or overwriting unrelated files |
| All relevant checks pass, user worries about quota | Give game screenshots and the review conclusion, stop testing | Endless screenshots, repeated full-project regression |
| User only wants to discuss style | Give references and options, stop before G1 production | Generating paid models or changing the game unasked |
| A tiling texture "looks fine" | Produce a 3×3 with `tile_preview.py` and report seam error | Declaring it tileable from a single image |
| Background removed, about to ship | `alpha_check.py` black / white / colored tests | Treating a checkerboard painted in RGB as transparency |
| User asks for a pack of rocks, crates, and a wide town gate | Pack the compact props; generate the gate on its own; key, slice, and flag | One square sheet with the gate squeezed in, or prompting "transparent background" |
| Runtime says "work autonomously, don't ask" | Do technical steps, then stop at the gate and wait for the reply | Treating the instruction as G1/G2/G3 approval and continuing |

`evals/evals.json` holds runnable eval prompts and grading points for these scenarios.

## Script self-test

`python scripts/selftest.py` builds synthetic images and jobs in a temp directory and covers: job init, artifact hashing, reviews bound to versions, hash-drift detection, the resume summary, the tiling seam metric (seamless ≈ 1, seamed much higher), fake checkerboard detection, size and palette budgets, chroma keying with despill, sheet slicing with shared scale / feet alignment / edge flags, pixel comparison, and contact sheet output. It proves the scripts behave correctly, not art quality.

## Maintenance checks

- `python scripts/check_skill.py`: checks frontmatter, description length, that every relative link resolves, and that scripts compile.
- Revision principle: revise only for decision gaps found in real tasks; don't pile on generic restrictions without evidence; project-specific parameters go in the project profile.
- Maintaining this skill never calls paid image generation, model generation, or full game tests.

## 2026-11-01 production-helper extension

GPT image generation/editing is now the default; no local generation or segmentation backend was added. Independently implemented `matte_image.py` and Blender `render_asset.py` adopt the processing/diagnostic patterns described in [Production helpers](production-tools.md).

`python scripts/test_production.py` tests native-alpha and source preservation, border-connected background removal with protected interior regions, known-mask soft-edge decontamination, refusal of ambiguous inputs and source overwrite. Set `ART_TEST_BLENDER` to an installed executable to also run the actual 12-view renderer on a synthetic GLB and check geometry count, source hash, report and view output. Without that variable the renderer test is skipped, not claimed passed.

On 2026-11-01 all six cases passed with Blender 5.2.3 LTS on Windows. The existing H3.0 cottage (41939 triangles) was also rendered in six textured and six clay views and inspected as a contact sheet, without changing the source GLB. No supplier generation or game regression run was performed. This is helper validation, not a new G2/G3 approval of the cottage, general semantic-segmentation capability, or a UE integration test.

## 2026-11-04 character branch

The production route is written before its rigging and animation trial, as requested. Existing evidence is one character task from the maintainer's own project: GPT reference and model sheets, a private Studio H3.1 static source, raw GLB download, 48270 triangles, a 1.6m prepared copy and three 4096² PBR images with unchanged decoded pixels. These are a particular sample, not fixed vendor prices, universal budgets or an animated-character success claim. The quoted humanoid/Mixamo binding was not submitted.

A real design failure also informs the branch: trying to improve riggability by replacing a large-headed mascot with a human changed the user's intended identity; the user rejected it. Improve hair/clothing readability within approved proportions first.

Character scenarios added to `evals/evals.json` cover identity, view consistency, skinned-file preservation, paid steps, locomotion and evidence boundaries. They are **defined, not agent-executed** by this documentation update. Structure/link/JSON checks are separate from future behavior and end-to-end character validation. No supplier submission, binding, animation purchase or game test is needed to install this update.
