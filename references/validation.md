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
| `scripts/` | Local self-test passes (below) | `python scripts/selftest.py` |

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
| UE or Unity cannot run in this session | Mark this project's integration unverified, provide probe and integration steps | Claiming the import was tested here |
| glTF model into a Unity URP project | Convert glTF roughness (G) to smoothness (1 − roughness) in the metallic map's A channel, verify with a channel comparison | Plugging the glTF metal-rough texture in directly |
| Project has uncommitted level changes | Import independently, replace the designated reference, record rollback | reset / clean or overwriting unrelated files |
| All relevant checks pass, user worries about quota | Give game screenshots and the review conclusion, stop testing | Endless screenshots, repeated full-project regression |
| User only wants to discuss style | Give references and options, stop before G1 production | Generating paid models or changing the game unasked |
| A tiling texture "looks fine" | Produce a 3×3 with `tile_preview.py` and report seam error | Declaring it tileable from a single image |
| Background removed, about to ship | `alpha_check.py` black / white / colored tests | Treating a checkerboard painted in RGB as transparency |
| Runtime says "work autonomously, don't ask" | Do technical steps, then stop at the gate and wait for the reply | Treating the instruction as G1/G2/G3 approval and continuing |

`evals/evals.json` holds runnable eval prompts and grading points for these scenarios.

## Script self-test

`python scripts/selftest.py` builds synthetic images and jobs in a temp directory and covers: job init, artifact hashing, reviews bound to versions, hash-drift detection, the resume summary, the tiling seam metric (seamless ≈ 1, seamed much higher), fake checkerboard detection, pixel comparison, and contact sheet output. It proves the scripts behave correctly, not art quality.

## Maintenance checks

- `python scripts/check_skill.py`: checks frontmatter, description length, that every relative link resolves, and that scripts compile.
- Revision principle: revise only for decision gaps found in real tasks; don't pile on generic restrictions without evidence; project-specific parameters go in the project profile.
- Maintaining this skill never calls paid image generation, model generation, or full game tests.
