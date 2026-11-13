# Guided Mode: leading someone through the workflow

Use this when the person is new to the skill, says "how do I start", "what do I do now", or is unfamiliar with the tools (image AI, Tripo, Blender, the engine). The person should never need to read this skill: the agent explains each step in conversation, says exactly what the person does next, and waits at the gates. Reply in the person's language; explain a term the first time it appears, in one short sentence.

## 1. Opening (first message of a new piece of work)

Survey the project first (engine, version, existing art folders, naming documents, an existing profile or job ledger), then send **one** message with three parts:

1. **What will happen**, in plain words, scaled to the request. For a whole scene:
   > We'll go in five steps. ① Pick the look: you choose a reference picture, an image AI turns it into our style, and we make one picture per game camera. ② Block it out: I build the scene from simple boxes at real size so we can check proportions before spending anything. ③ Make the parts: I build the big structures myself; for props you or I generate pictures and I turn them into 3D models. ④ Put it together in Blender and check it from the game cameras. ⑤ Bring it into the engine and check it in the real camera. I stop after ①, ②, ③, ④ and ⑤ for your OK.
   For a single prop, use the [model chain](model-pipeline.md) in one or two sentences instead.
2. **What only the person can do**: sign in to accounts (image AI, model generator), approve spending, pick between options at the gates, place set dressing by hand at the end. Say that keys and passwords are never typed into the chat.
3. **At most five questions**, each with a recommended default ([intake](intake.md)): what to make and where it appears, which engine project, which image AI they use, whether a model-generator account with credits exists, the budget. If the answer is already in the project, don't ask.

## 2. Setup check (before the first paid or tool-heavy step)

Run the zero-cost checks and translate the result into a short to-do list for the person, each item with where to click or what to run:

| Check | How | Typical fix the person does |
| --- | --- | --- |
| Python, Pillow, Blender | `model_job.py doctor` ([setup](setup.md)) | install, or tell the agent the Blender path |
| Model generator | API login or a signed-in Studio tab | sign in; for the browser route allow automatic downloads for the site and turn off "ask where to save each file" |
| Browser that can upload | the agent's browser tool list | use a browser tool that can set file inputs (the desktop app's built-in browser cannot) |
| Image AI | ask which one and whether the agent can drive it in their browser | sign in; or generate themselves with the agent's prompt pack and drop the files in `art/inbox/` |
| Engine | engine version vs the project's, C++ modules built for that version | install the matching version through the official launcher; rebuild the project modules |

Do the checks; don't make the person run commands they don't need to understand. Record the results in the project profile (`tools`).

## 3. Each stage: do, show, ask, say what's next

Every stage ends with the same shape of message:

- **What I did** (two or three lines, plain words).
- **What to look at**: the review images shown directly, with file paths.
- **One to three questions** that decide the next step, each with a recommendation.
- **What happens after your answer** (one line).

Stage by stage, what the agent does and what it asks the person:

| Stage | Agent does | Person does / decides | Gate question to ask |
| --- | --- | --- | --- |
| S0 Direction ([scene](scene-pipeline.md#s0-direction)) | lists game cameras and needed objects; writes the short edit lines; reviews the generated pictures | picks the reference picture; generates or lets the agent drive the image AI; picks the style | "Is this the look? Which view needs another try?" |
| S1 Blockout | builds the scene from primitives at real size; renders the game cameras next to the concept | checks proportions and composition | "Do the sizes look right from the game camera? (e.g. tower vs rocket)" |
| S2 Parts | hand-builds and bakes structures; prepares prop picture prompts; runs the model generator; processes to real size; refine pass | generates prop pictures if not delegated; approves spend per batch; approves each batch | "These N parts — keep, redo, or adjust? Spend for the next batch: X credits, OK?" |
| S3 Assembly | swaps placeholders for parts; renders the game cameras | checks the whole scene | "Ready to bring into the engine?" |
| S4 Engine ([engine notes](unreal.md)) | exports (`blender_export_engine.py`), imports (`ue/ue_import_package.py`), builds a content level and a review level (`ue/ue_build_levels.py`), captures the game cameras | opens the review level; later places set dressing by hand | "Does it hold up in the game camera? Anything to fix before we hook it into the game?" |

If the person delegates ("run it without me"), record the delegation with its scope and keep going, but still show the results at the end of each stage.

## 4. When the person is lost

If they ask "where are we", "what's left", or seem confused, answer with a status card, not a history:

```
Scene: <name>      Stage: S2 Parts (7 of 10 props done)
Done:   S0 style ✓  S1 blockout ✓
Now:    making the last 3 props (water tank, crane, signal post)
Next:   you approve the batch → S3 assembly
Files:  art/work/<scene>/README.md  (every output and how to rerun)
Spent:  1,820 credits, 1,270 left
```

Read it from the ledger and the scene README; don't guess. When they ask how to see something, give the exact steps in the tool they have open (e.g. which folder in the engine's content browser, which level to double-click).

## 5. Picking up later

At the start of a new session in a project that already has work: read the profile, the job ledgers and each scene's README, run `artjob.py resume` for open jobs, and open with the status card plus the single next action. Don't re-ask settled choices.

## 6. Working inside someone else's or a team's project

Before writing into a shared repository or engine project:

- Read the project's own rules first (naming and folder documents, contribution notes, branch and commit conventions) and follow them over this skill's defaults. If two documents disagree, show both and ask.
- Ask who else works on the same levels or folders and whether they have unpublished work; moving assets or editing a shared level under someone else's work causes conflicts that cannot be merged for binary files.
- Keep new art in its own content level (streamed into the main level) rather than editing the main level directly where possible.
- Never publish (push, merge, share) without the person's explicit OK, and before publishing build the project and run its tests.

## 7. Tone

Short sentences. One decision per question. Show pictures, not paragraphs. When something failed, say what failed, what it means for them, and the fix — then do the fix or ask for the one thing you need.
