# Concept prompt pack: <asset-id> v<n>

For the user to run in their own image AI. Save results to `art/inbox/<asset-id>/` as `<asset-id>_<tool>_<nn>.png` and note the tool and version used.

## What this image is for

- Asset: <what it is, gameplay role>
- In-game: <real size in m>, seen at <camera / screen size>
- Must read clearly: <silhouette, key parts, focal details>
- Style anchors: <paths or attached images; say which to show the image AI as reference>

## Prompt (shared core)

Keep this core identical across a family; change only SUBJECT.

```text
SUBJECT: <one specific object, its state, materials, key parts>
VIEW: single object, three-quarter front view from slightly above, moderate perspective, whole object in frame with margin
ART DIRECTION: <shape language>, <palette roles>, <material finish>, <edge treatment>
LIGHT: soft even studio light, no strong cast shadows, no rim light, no dramatic contrast
BACKGROUND: plain solid <#hex> background, no gradient, no floor, no shadow on the background
EXCLUDE: text, labels, logos, UI, scenery, extra objects, people, cropped edges, watermark, depth of field, motion blur
```

## Per-tool notes

Check the tool's current docs for exact parameter names; these are the intents to carry over.

- **Tools with a style-reference feature** (e.g. Midjourney): pass the anchor image as a *style* reference, not a character/object reference; square aspect; put EXCLUDE items in the tool's negative / "no" parameter.
- **Chat-based image tools** (e.g. GPT, Gemini): attach the anchor image and say "match the style of the attached image, but draw <SUBJECT>"; ask for a square image.
- **Others** (e.g. Flux): paste the core prompt; put EXCLUDE items in the negative-prompt field if there is one.

## Tripo-ready checklist (the user can check before sending)

- [ ] One complete object, nothing cut off at the edges
- [ ] Three-quarter view; front, one side and the top are visible
- [ ] Parts are distinct; gaps between parts are visible where they exist
- [ ] Plain solid background, no floor, no cast shadow on it
- [ ] Light is soft; no black shadow areas hiding shape
- [ ] No text, no extra objects
- [ ] At least 1024 px on the short side

## Optional extra views (only if they will agree)

Side and back views help only when made from the approved front image by editing (same object, same proportions, same part count). Do not generate them independently.
