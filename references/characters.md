# Character production: design → model → animation → engine

This branch includes static character production and a proposed skinned-character workflow. **Writing the branch does not validate it.** Character concepts, Studio generation/download and material-preserving Blender preparation have project evidence. Auto-rigging, animation retargeting, deformation quality and animated Godot/UE integration remain unverified until performed on a real sample. Read the shared review, tools and engine references only as needed.

## 1. Lock identity and use before solving topology

Record the existing reference/version, silhouette, face, head/body ratio, limb lengths, palette, hair construction, clothing layers and attachments. Distinguish approved invariants from elements the user explicitly allows changing. A request for clearer design or easier rigging does **not** authorize replacing a mascot with a human, adding human facial features, lengthening limbs or changing the art style. Preserve stylized proportions unless the user chooses otherwise; there is no universal preferred head count.

Recommend the smallest useful design change: readable paper/hair masses, clear sleeve roots/cuffs, visible wrists, a coherent torso, a short split hem and a gap between trouser legs. Preserve the approved costume identity. Explain when a long skirt, cape, paper flap, hair or scarf needs accessory bones, separate geometry, corrective weights or simulation. Auto-rigger difficulty alone is not a reason to silently redesign.

Determine actual needs: static display / NPC / playable, required idle/walk/run and interactions, view distance, facial animation if any, target skeleton/animation library, platform and collision convention. Infer settled choices from the project; ask only when a missing choice changes production. Record triangle/texture targets as project budgets, not promises that a generator will honor them.

## 2. Concepts and consistent three-view sheets

Prefer the available GPT image tool; the shared fallback choice applies if it is unavailable. Keep sources and prompt/provenance. Make model-sheet views when requested or needed to disambiguate shape; do not require another sheet for an already sufficient approved 3D source.

For a front/profile/back sheet, use the same scale, baseline, crown/head height, eye line, shoulder/waist/crotch levels and boot soles. Keep an orthographic or near-orthographic camera and a consistent neutral pose. Check actual shapes, not just view labels: profile must read as a profile; back must not show front-only features; asymmetric clasps, scarf tails and hair folds must stay on the same anatomical side. A generated back view is a proposed design until reviewed. Correct mismatches before using multi-view generation.

A/T-pose is selected for the intended rigger: arms clear of the torso, distinct hands, straight readable limbs, separated feet, no accessory hiding key joints. Do not stretch a small character into adult anatomy to force a standard pose. For asymmetric identity, compare the original and new reference directly at G2.

A turnaround **sheet** is for human review. For **single-image** 3D generation, upload one isolated character view, with a clean background and no text, other views or pedestal. Use the service's dedicated **multi-view** slots only if actually supported; supply front/side/back separately with verified directions and cross-view consistency. Never put a collage into a single-object slot. Do not substitute a different reference after approval.

## 3. Generate and review the static source

Probe the actual image/model channel, privacy, export entitlement, model version, candidate count and current UI price. Preserve existing valid budget authorizations; price, topology mode and face/texture counts are not fixed cross-project rules. Keep independent spend and remote IDs for generation, retopology, binding and animation. A generation budget is not an automatic paid post-processing budget. Reconcile an uncertain submission before any retry or wallet switch.

Download the raw mesh before cleanup. Preserve its source hash, UVs, all PBR connections and original material images. Inspect the **downloaded file**, not only the vendor viewer: front/profile/back, silhouette, hands/feet, hair roots, sleeve/armpit gaps, crotch, coat underside, thin paper folds and accessories. Neutral textured/clay views distinguish geometry from shading. Boundary/nonmanifold counts are diagnostics; a closed one-piece mesh is not evidence that limbs or clothing deform well.

For an **unskinned, unmorphed** file, ordinary static preparation can handle units/origin and material wiring. Preserve the raw source and review the normalized copy. Do not reduce faces, unwrap, repaint or weld sheets to disguise a conversion issue. Review the model separately from its concept. If the source fails structurally, compare repair, pose preparation and regeneration before spending on a binding chain.

## 4. Rigging route — documented, awaiting project execution

Choose only a detected capability: a vendor rigger, an available DCC rig/weight workflow, an existing compatible skeleton, or a user-supplied rig. Clarify unsupported stages. Do not invent CLI `rig`/`retarget` commands or describe a web menu as a working integration. Before a paid operation, verify the actual skeleton preset, supported pose/body type, export formats, price and remaining authorized budget.

Save binding as a child artifact/version with its own state and remote ID; do not overwrite generation IDs or raw mesh. Keep each bone's parent/rest pose, joints/skins, inverse bind matrices, weights and vertex associations. Check weighting near head/neck, shoulders, elbows, wrists, hips, knees and ankles, then costume overlaps. Large mascot heads, paper hair, short limbs and loose cloth often need targeted weight corrections; do not claim automatic success from a preview standing still.

**Skinned files are not static files.** A static cleaner that rejects armatures/morphs must route away, not be patched to ignore the guard. Do not detach every mesh, bake its transforms independently, discard the armature, or export with animations disabled. Scale/orient the complete rig consistently, or preserve it and apply a documented engine root transform; re-check rest pose and animation after conversion. Preserve shape keys and facial data when required. Retain original material channels and compare any re-encoded image by decoded pixels where fidelity matters.

## 5. Generic animations and deformation — documented, awaiting execution

Select the target skeleton based on available clips and the engine, not a preset name alone. Confirm bone hierarchy, rest A/T-pose, axes, scale, root/hips and mappings; generic humanoid motion is a candidate, not guaranteed plug-and-play on stylized anatomy. Check animation license/use rights for the chosen source. Keep source motions and retargeted outputs distinct.

Validate a minimal useful set: idle, walk, run, plus an actual project interaction if needed. Decide **in-place versus root motion** with the existing controller. Check loops, root displacement, foot contact/stride, knee/elbow directions, neck stability, hand positions and hair/scarf/coat penetration at representative extreme frames. Movement-driven animation speed should follow real speed/stride; retargeting is not an excuse to change approved gameplay speed.

Correct rest pose/mapping/weights or use suitable corrective motion when needed. A grossly failing rig should not trigger a blind paid retopology/animation chain. Record exactly which clip and deformation failed, costs and chosen repair. Show a short deformation sequence when motion matters; a still image or a list of named clips does not prove it. Follow G2 for new appearance/deformation results; technical fixes within already approved geometry do not require re-asking unchanged design questions.

## 6. Integrate into the real engine — awaiting animated sample

Probe the installed engine/version/import route and perform a representative animated sample before expanding. Preserve the existing controller, collision capsule, input and camera where applicable; attach the new visual/animation layer and define facing, feet anchor, overall scale and occlusion. Keep an explicit old-character rollback. Do not use the deforming render mesh as the default character collision.

- **Godot:** preserve Skeleton3D and imported animation resources. If the actual version supports it, use humanoid bone mapping/retarget import features with the available AnimationPlayer/AnimationTree setup. Verify tracks target the intended skeleton and blend idle/walk/run from actual controller state. Check forward axis and foot origin in the playable scene; do not rely on importer thumbnails.
- **Unreal:** distinguish skeletal from static import. Match the intended Skeleton and, where available, use IK Rig/IK Retargeter or the project's proven route. Inspect root-motion/extraction settings and the existing Animation Blueprint/locomotion state. Prove the result in PIE/Standalone before claiming UE integration. If UE is unavailable, deliver inputs and a validation plan, mark the route unverified.

At G3 show the actual gameplay camera and relevant movement: standing, walk/run transition, turn, slope/step, dialogue focus and lighting response. Check feet, clipping and readability without replacing the gameplay framing with a flattering render camera. Use project-approved engine captures/scripted inputs; respect disabled computer-use testing. Run only relevant checks, not repeated full-project regressions.

## 7. Evidence and handoff

Track independently: concept/sheet approved; model generated; raw actually downloaded; static checks passed; rig produced; motion/deformation verified; integrated; user accepted. Extend artifact roles using existing model/source/runtime/other records rather than claiming every state from one green result.

Deliver the raw model, editable source where it exists, rig/skin and clips that actually exist, textures, skeleton/mapping/export settings, sources/licenses, review images or motion, actual game entry point and rollback. Keep pending steps explicit. Record the tested engine, version and sample in the project profile; never mark this entire character branch or both engines verified based on a static mesh, written plan or document check.
