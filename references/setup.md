# Setup for the 3D model chain

What a new machine needs before [the model chain](model-pipeline.md) runs. The agent checks; it never installs engines or tools on its own, never reads saved keys, and never asks for a key in chat.

```text
python <skill>/scripts/model_job.py --root <project> doctor
```

`doctor` prints each capability as `executable` or `needs setup` with the fix. It spends nothing.

| Need | For | Install |
| --- | --- | --- |
| Python 3.9+ and Pillow | all scripts, review sheets | `python -m pip install Pillow` |
| Blender (verified on 5.3; older versions untested) | M3 prepare and render | blender.org or Steam. If it is not on PATH, set `BLENDER_EXE`, pass `--blender`, or put the path in the profile `tools.blender` |
| Node.js 20+ and `tripo-cli@0.8.1` | M2 API route | `npm install -g tripo-cli@0.8.1` |
| Tripo login | M2 API route | `tripo login --region <region> --no-open --no-wait --json` prints a link and code; the user authorizes in their browser, then the same command finishes and `tripo doctor --json` confirms. Choose the region of the user's account (international vs. China); never infer it from the language |
| Logged-in Studio tab | M2 Studio route | the user signs in to studio.tripo3d.ai in the agent's browser |
| Engine bridge | M5 | the project's own (e.g. UE MCP / editor Python); see the engine reference |

Project once: add `.asset-workflow/` to `.gitignore`, and record in `art/workflow/project-profile.json` → `tools`: the Blender path, the Tripo route(s) the user chose, and the region. Do not store keys there.

**CLI version pin.** `model_job.py` refuses any tripo-cli other than the pinned version because it reads the dry-run JSON (`valid`, `steps`, `candidates`, `generation_credits_estimate`) to enforce the credit cap. To move to a newer CLI: install it in a scratch prefix, run a dry run, confirm those fields, run `test_model_job.py`, then change `PINNED_CLI` in one commit.

**Image generation** is outside this toolchain. The user uses whatever image AI they prefer (Midjourney, GPT, Gemini, Flux, …) with the agent's prompt pack; see [the model chain M1](model-pipeline.md#m1-concept-g2a).
