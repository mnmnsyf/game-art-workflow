# Tripo Notes: inputs, model choice, API and Studio

Field notes for image-to-3D with Tripo. Researched 2026-10-31 from community case reports and Tripo's product and API docs, then used in a real project. These are risk reducers, not guarantees: no input style was shown to reliably produce a model that needs no cleanup. Prices, model labels, free quotas and export rights change — read them from the live page or the CLI dry run every time and keep measured values in the project profile.

## What the community cases show

- **Readable structure beats "simple".** Clear silhouette, distinct parts, sensible perspective and visible hidden structure matter more than stripping detail. Keep the design; remove ambiguity.
- **Multi-view costs consistency.** Extra views help only when they agree on parts, proportions and facing. Mismatched views produce fused or duplicated parts.
- **Clean background ≠ enough information.** Thin parts disappear, near parts fuse, backs are invented. Gaps between legs, ropes, dense leaves and building backs are known risks.
- **Hard cases often go HD-then-retopology.** For buildings and complex shapes, a high-fidelity generation followed by reduction can beat a low-poly mode. Compare shape fidelity and usable topology separately.
- **"Game-ready" showcases include real manual work** (cleanup, retopology, normal bakes, hand fixes). Do not budget as if the raw output is final; record actual cleanup minutes.
- **Remove-lighting / delight options depend on the plan.** Keep painted shading for hand-painted looks without dynamic light; remove it when the engine will light the asset. Check support for the exact model version.

## Choosing assets and settings

| Asset kind | Cleanup risk | Notes |
| --- | --- | --- |
| Thick, closed, matte props (rocks, crates, jars, chunky machine parts) | lower | good first candidates; still verify |
| Rounded stylised single props with flat colour regions | low–medium | prompt words like "low poly" or "clay" are not switches |
| Thin legs, openwork, ropes, antennae, struts | medium–high | check gaps, thickness and use positions |
| Dense foliage, hair, cables | high | plan cards or procedural instead |
| Whole interactive buildings, exact openings, removable roofs | high | modular or hand-built structure is usually better |

- **H-series** leans to geometric detail and fidelity; **P-series** to controllable face count and editable topology. Neither replaces a local shape, UV and material check. Write the reason for the choice on the M0 card.
- The returned triangle count is the truth; a requested `face_limit` or a Studio setting may not hold.
- High-resolution textures do not fix wrong geometry. Do not keep buying texture, segmentation or conversion steps for a raw model whose structure failed.
- Change one variable per comparison (image, model, texture option, post-processing). Different seeds vary on their own.

## Before spending (zero-cost checks)

1. Real size, camera size, functional openings, separate parts and which back details must be right are written down.
2. The image is uncropped, parts are readable, perspective is moderate, hidden structure has a basis; nothing was deleted just to be "AI-friendly".
3. Multi-view sets are aligned (part counts, positions, facing, proportions, materials). If not, fix the images first.
4. Model version, delight / texture support, export entitlement, visibility, the actual button cost and the balance are confirmed for this job.
5. Only the one authorized job is run; no automatic retries.

## API (tripo-cli)

`model_job.py` wraps the official CLI pinned to a verified version (see [Setup](setup.md)). It calls node directly (no shell interpretation of prompts), disables update checks and analytics, redacts an environment key from anything it saves, uses a dry run to read the estimate, and submits exactly one candidate. `doctor` checks login without spending.

## Field notes: Smart Mesh batch (2026-11)

- **Smart Mesh P2.0** (Studio, "clean topology") returns a quad mesh near the requested polycount (10k quads ≈ 20k tris) with **no UVs and no texture**. Either add Tripo **Texture** (20 credits; auto-UV + texture baked from the concept image) or unwrap in Blender and bake a generic weathered material ([hand-built parts](scene-pipeline.md#hand-built-structures)). Smart Mesh costs 100 credits per generation after the free trials; Studio resets "Number of Generation" (to 4) and Privacy (to Sharing Only) when the workspace reloads — set 1 and Private every session.
- **Browser choice.** The desktop app's built-in browser cannot upload files (no file tool; the native picker is outside the page). Use Claude in Chrome (`file_upload` on the hidden image input) or computer use. Chrome needs: Tripo logged in, the site allowed for automatic downloads, and "Ask where to save each file" off — otherwise each export waits behind a Save-As dialog (the data still lands as a complete `.tmp` in Downloads).
- **One-page loop that held for 16 models:** remove the input image (trash icon) → upload the next image → Generate → wait ~60 s → Texture → wait ~70 s → Export (format GLB is remembered) → move the newest `.glb` out of Downloads under the asset name. The export file name defaults to Tripo's own caption, so rename by order, not by name.
- Tripo Texture follows the concept image well for painted/rusty props; open containers can come back without a roof — check the clay row. A roof plate added in Blender (ray-cast the inner walls, recess under the top rail, colour from the median wall texel, own baked material) closed it without a regeneration.
- Island checks: the textured GLB is split along UV seams, so weld by position before counting parts (thousands of "islands" otherwise). Across 16 Smart Mesh models almost every small island was a bolt or bracket sitting on the body; only one model had real floating faces (22). Don't budget a big cleanup step for Smart Mesh output.
- Recolouring by texture (e.g. a red signal lens): a hue mask on the base colour PNG, dilated 2 px, is enough; save the new image to a file before exporting so the GLB embeds the edit.

## Studio (web credits)

Studio credits and API balance are different wallets. A browser agent operates the real page; Python only records state and attaches the browser's own download. No private endpoints, cookies, tokens or hidden URLs.

1. `init --provider studio …`, then open the logged-in Studio tab. Read visible content through the browser tool; avoid screenshot loops.
2. Set the authorized options (model, texture, one candidate, **private** visibility — Studio may default to public). Read the button cost, balance and export entitlement *after* settings are final.
3. `studio-preflight --page-url <workspace URL> --model-label <visible label> --credits <button cost> --balance <balance> --export-status available|blocked|unknown --visibility private|public`. Add `--allow-public` only with the user's explicit consent. `blocked`/`unknown` stops the job unless the user explicitly authorized a single export test (`--allow-export-probe`, which never bypasses a seen paywall).
4. `studio-begin --max-credits <cap>` (valid for 5 minutes), then click Generate **once**. If the outcome is unclear, look in the asset list — never click again.
5. `studio-record --asset-url <model page URL>`; for an existing model use `--existing` and generate nothing.
6. Export GLB through the page, capture the browser's real download path, then `studio-attach --file <path>` and `process`. ZIP or external-file glTF is not a self-contained GLB; pick a supported export. A paywall or verification prompt is a real stop, not a reason to switch to the API.
