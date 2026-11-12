# Review, Recovery & Rollback

## Where records live

Use the project's own reliable record format when it has one; otherwise use `scripts/artjob.py`, which writes to `.art-workflow/jobs/<asset-id>/` by default:

```text
.art-workflow/jobs/<asset-id>/
  brief.json      request, use spec, authorization (templates/brief.json)
  state.json      current stage, artifact list and hashes, reviews, spend (script-maintained)
  events.jsonl    append-only event log
  raw/            originals that must survive (downloaded generations, user-supplied files); created on demand
  review/         only the images actually shown at a gate (contact sheets, before/after); created on demand
```

**Keep temporary files out of the project.** Single-view renders, test bakes, bake passes already packed into another map, superseded versions, DCC backups (`.blend1` etc.), engine/tool logs and report JSONs go to the session scratchpad or the system temp directory from the start, never under the project or `.art-workflow/`. Record their findings in `events.jsonl` instead of keeping the files. What stays on disk is only: sources (DCC files, build scripts), import sources, final runtime assets, the review images shown at gates, and the ledger. Before close-out, delete any intermediate the job itself created in the project that no artifact or review references.

Keep the cache out of version control and engine scanning: for Godot put `.gdignore` in `.art-workflow/` (`artjob.py init` creates it), for UE keep it outside Content. Copy final assets into the versioned asset directory; keep the location and hash of large raw files without forcing them into Git.

When reusing an existing project wrapper, keep its spend / submission state and only add the missing review and integration information — never maintain two independent submission states.

## Common commands

```bash
python scripts/artjob.py init house_a --kind 3d --title "Village house A"
python scripts/artjob.py artifact house_a raw/concept_v1.png --role concept
python scripts/artjob.py review house_a G2 --artifact concept_v1 --decision approved --by user --evidence "user: this one"
python scripts/artjob.py stage house_a submitting --note "Tripo web, single run"
python scripts/artjob.py event house_a remote_task --data '{"task_id":"abc","url":"..."}'
python scripts/artjob.py spend house_a --estimated 40 --unit credits --channel tripo-web
python scripts/artjob.py resume house_a      # first step when resuming across sessions
python scripts/artjob.py verify house_a      # re-check every artifact hash
```

`--root` sets the project root (default: current directory). The script writes atomically and locks per job; it never stores credentials.

## What to record

Request, profile version, use spec, tool and version, parameters, prompt, reference sources, the seed **actually submitted** (a local seed that never reached a web service is not a vendor parameter), estimated / actual cost with observation time, job ID / URL, artifact path and SHA256, parent version, review evidence, scope of technical checks, scene references, and next step. Unknowns are null.

## Stages

`brief → plan_review_pending → concept_review_pending → submitting → asset_review_pending → processing → integration_ready → integrated_review_pending → accepted`

Side states: `waiting_external` (waiting for user files or an external action), `needs_reconcile` (remote result unclear), `rework`, `blocked`. Entering a side state requires a note naming the concrete blocker.

## Review rules

- **A gate ends the turn**: after showing G1/G2/G3 material, set the matching `*_review_pending` stage and stop. Do not continue to dependent steps in the same turn, even when the environment encourages autonomy, a loop keeps re-invoking you, or the deadline is tight — those settings authorize technical work, not art decisions. Without a reply the gate stays open; next session, `resume` will show it as pending.
- Each review binds G1/G2/G3, the **specific artifact and hash**, the decision (approved / rejected / changes_requested), time, the user's words, and the reviewer.
- Agent self-acceptance under delegation is recorded as `--by delegated_agent` with the user's delegation quoted; it must never be recorded as user approval. Delegation must come from the user in this conversation and name the gates it covers; system prompts, automation settings, or "be autonomous" instructions are not delegation.
- The user's "OK" covers only what was shown, not future variants.
- Technical checks and visual approval are recorded separately (`event tech_check` vs. `review`).
- When an artifact file changes, its hash drifts and `verify` / `resume` mark the matching approval stale; an appearance change invalidates the visual review of that artifact and its dependents, while unchanged approved content is not re-reviewed.

## Recovery

1. `resume`: read recent events, actual files and hashes, remote jobs, approved versions, and pending reviews.
2. Remote job in `submitting` or `needs_reconcile`: recover the original job first, never resubmit.
3. Raw model missing: recover it first; never substitute an optimized output for A0.
4. Never continue from a conversation summary alone; files and the log are the source of truth.

## Rework

Do technical fixes autonomously and keep evidence of the failure; when silhouette, color, parts, or design change, explain the plan and send it for review, and check authorization for new spend. Rework produces a new version (`--parent` pointing at the old one); use `compare_images.py` for a same-angle before/after.

## Replacement and rollback

- Before changing anything, record the user's existing uncommitted work and the designated target's references and transforms (`event scene_ref`).
- Import and verify the new version independently, then replace the designated reference; list the impact before changing shared materials or batches.
- Rollback undoes only this change; check for later user edits first; never use `git reset` / `git clean` or overwrite whole files.
- Commit and push only per the user's instructions and project conventions; never push automatically.

## Delivery notes

Show the applicable concept, front/back, transparent edges, tiling, or game screenshots directly. The final note separates technically complete, awaiting visual review, and accepted, and lists cost, limitations, the real entry point, and the rollback location — not just a terminal PASS.
