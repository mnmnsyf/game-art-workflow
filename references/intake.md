# Project Art Profile & Production Plan

Read the code, assets, project rules, and history before asking the user; the user's latest explicit instruction wins. The profile can grow over time — it does not require a finished art bible up front.

## Project profile

Follow the project's own conventions first; otherwise start from [templates/project-profile.json](../templates/project-profile.json) and save it, versioned, to `art/workflow/project-profile.json`. Unknowns are null and go into `open_questions`; **never record a recommendation as approved**. Bump `version` and set `updated` on every change.

The profile covers:

- **Engine**: version, renderer, platforms, actual camera and resolution, 2D / 3D display mode, verified import and check commands.
- **Style**: approved references and their purpose, palette, detail density, outline, material and lighting tendencies, banned elements (see [style.md](style.md)).
- **Scale**: character height reference, 2D anchors and pixel density (px/m), 3D units, origin, module grid.
- **Budgets**: triangle count, texture resolution, material count, memory, and LOD targets per camera distance and platform.
- **Channels**: tool preferences and status, cost / count authorization, visibility, asset sources and commercial licenses.
- **Conventions**: asset directories, naming, rollback method, disabled verification tools.

Record the basis and date; never store secrets.

## First questions

Ask once, together, about the gaps that change **appearance, use, cost, or scope** — at most five questions, each with a recommended default. Ordinary naming, folders, and technical parameters: just recommend, don't ask one by one.

## Single-asset spec

Write into the brief's `spec`: player use, visible sides, walk-around / openings / traversal, whether doors or roof come off, reuse and variants, expected screen size.

- Buildings: distinguish a **shell** (exterior only) from a **functional building** (door opens / enterable).
- Vegetation: distinguish single plants, clusters, and cards.
- A back side or interior inferred from a single image must not be presented as "designed".

## G1 plan

Use [templates/g1-plan.md](../templates/g1-plan.md), one page or less: what to make, how it displays and interacts, style basis, recommended form and why, split and reuse, tools and cost, delivery location, acceptance criteria. Offer two or three meaningful options with a recommendation rather than listing every possibility. Then stop and wait for the reply (SKILL.md hard rule 2).

When the user only wants to discuss or see concepts, do not expand into paid models or game changes.

## Batches and samples

A batch G1 must include a style pack plan ([style.md](style.md)): consistency comes from anchors, prompt skeletons, and parameters agreed in advance, not from picking afterwards. Pick samples that expose shared difficulties first: door steps and roofs, module corners, vegetation alpha edges, etc. Sample categories with clearly different structural risk separately — one clay pot does not represent all buildings. Expand only after the sample passes G3; when standards change, re-review only the affected parts. Review expansion batches together on a `contact_sheet.py` sheet and record a decision per asset.
