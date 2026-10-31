# Tools, Channels & Cost

Choose vendors by capability, not brand habit. Mark every channel with one of four states: **executable** (actually called successfully in this session), **needs setup** (exists but lacks login / key / plugin), **known limited** (export, visibility, or quota limits), **unverified**. A tool existing does not mean it is logged in, callable, or able to export.

## Probe order

1. Image generation / editing built into this session and related skills (e.g. imagegen): prefer them when they fit, and follow their save requirements.
2. Wrappers already verified in the project (scripts or CLIs registered in the profile's `tools.wrappers`).
3. Existing API configuration: check only **whether** environment variables or config entries exist — never print keys, search the user's secrets, or read browser cookies.
4. Local services (explicit address), installed CLIs, DCC tools (e.g. Blender background Python), usable web pages.

Write the probe results to the profile's `tools.channels` and reuse them next time; ask again only when conditions change (errors, insufficient balance, the user changes their mind).

## When channels fall short

Show the user the options that **actually exist**: existing API, local service, web generation, user generates and imports, existing licensed assets, procedural / hand modeling. For each, list cost, privacy / visibility, export limits, manual steps, and verification status.

- Without a browser, deliver an "external generation pack": prompt, size, role of each reference image, alpha / tiling requirements, avoid list, export format, and the file name to send back; then record `waiting_external`.
- Never silently switch to a paid API; never pass programmatic color blocks off as generated concept art. When a procedural route fits better, recommend it openly in G1.

## Capabilities and limits

| Capability | Common routes | Limits |
| --- | --- | --- |
| Image generation / editing | Built-in tool; API, local model, or web page chosen by the user | Verify non-built-in channels one by one; no promise that every service is supported |
| Background removal / cut-outs | Generators that support editing, image software, deterministic processing | Cropping is not inpainting; verify real alpha with `alpha_check.py` |
| 3D generation | Image-to-3D cloud services (e.g. Tripo, Meshy, Rodin) or local models | Check balance, model version, price, topology options, and export rights separately |
| Modeling / cleanup | Blender background Python or the project's DCC tools | Regular structures can be modeled directly; don't claim cloud generation |
| Integration | Godot CLI / scripts; UE editor Python / project bridge | Per the actual verification level in each engine file |

## General notes on 3D generation services

- Choose the mode by goal: shape fidelity, clean topology, and low triangle count are different options. Don't infer that a budget took effect from writing "low-poly" in the prompt — go by the returned triangle count.
- Models, multi-view input, textures, part splitting, high-resolution textures, and export formats are often billed or membership-gated separately; check the current official docs and pages each time and never hardcode prices, free quotas, or model labels. High-resolution textures do not fix geometry.
- Web submission: before uploading, check the thumbnail, version, parameters, count, visibility, balance, and estimated cost; downloads must yield a real file — never scrape hidden URLs to bypass permissions. Web credits and API balance are separate.
- API: use official authentication, never log tokens; poll with a bound and do independent work while waiting.

Vendor parameters measured in a specific project (e.g. a version's triangle count or credit cost) go in that project's profile, not in this file.

## Authorization and visibility

Record the approved count, steps, attempts, budget, channel, and visibility for this job (`artjob.py spend` and the brief's `authorization`). Ask again when exceeding or materially changing them; a total budget is not unlimited retries, and free retries are still bound by count and review. When a vendor only gives estimates, do not claim a hard spend ceiling. Maintaining or testing this skill never consumes generation quota.

Private first. If the only route is public, show the specific image and the consequences of publishing and ask; approving an image is not permission to publish it. Record asset sources and the basis for commercial use; when unclear, say so — never invent license guarantees.

## Submission and recovery

Before submitting, persist `submitting` (`artjob.py stage <id> submitting`) and record the real job ID / URL immediately on success. On disconnect, timeout, or an unclear result, record `needs_reconcile`, recover and download the original job — never click generate again or switch channels and pay twice.
