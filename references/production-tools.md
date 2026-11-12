# Production helpers: GPT-first, no local models

2026-11-01. Adopts useful production patterns from [Godogen asset-gen](https://github.com/htdt/godogen/tree/master/asset-gen) and [godogen_assets](https://github.com/htdt/godogen_assets): examine exported geometry both textured and clay, review alpha composites, and verify actual runtime behavior. Helpers here are independently implemented; no upstream script or model weights are copied. GPT remains the image-generation default. These helpers are local processing/rendering, not generative backends.

## Alpha processing

Use the built-in GPT image tool's real alpha when supported. Preserve existing native alpha; do not strip it or turn it back into a colored background. Creative corrections go through the available image-edit tool according to its instructions. Deterministic processing can use the following helper when appropriate:

```text
python <skill>/scripts/matte_image.py <input.png> --out <scratch>/new-version.png
python <skill>/scripts/matte_image.py <input.png> --mask <reviewed-mask.png> --out <scratch>/masked.png
python <skill>/scripts/matte_image.py <opaque-composite.png> --mask <alpha.png> --bg "#ffffff" --unmix --out <scratch>/decontaminated.png
```

Replace placeholders with actual absolute paths. Pillow is the only dependency; no rembg, ONNX or weights are installed. Always writes a new PNG and black/white/colored QA sheet, with paths and source hash as JSON on stdout. Existing output/source paths are rejected. Processing preserves canvas dimensions and does not crop or move anchors.

- Native alpha: copied unchanged unless an explicit mask is supplied.
- Mask: grayscale values are alpha; the mask must match dimensions and be visually reviewed. Existing source alpha is multiplied, not discarded.
- Opaque solid background: only similar pixels connected to an image border are removed. Automatic corner checks reject obvious ambiguity. This does not detect objects and intentionally preserves enclosed same-color regions; use a mask for actual interior background holes. Corner agreement alone is not proof the result is correct.
- `--inner` / `--outer`: max-channel color-distance thresholds in 0..255; tune on a representative asset, not a whole batch blindly. Low-contrast objects may be damaged; review rather than automatically widening thresholds.
- `--unmix`: approximate inverse compositing for a known solid background and matching soft mask. It changes partial-edge RGB, can amplify errors, and refuses already-transparent source inputs. It is not a universal halo repair button.

Run `alpha_check.py` for alpha/edge checks as needed and show the output/composites at G2. Failure does not authorize a new generation or a new provider. Generate again only under the existing review and spend rules.

## Three-dimensional diagnostics

Run only in a fresh background Blender process, never an unsaved interactive session:

```text
<blender> --background --python-exit-code 1 --python <skill>/scripts/render_asset.py -- <model.glb> --out <scratch>/model-review --resolution 384 --samples 8
python <skill>/scripts/contact_sheet.py <scratch>/model-review/*.png --out <review>/model-sheet.png --cols 6
```

The renderer imports a self-contained GLB, never exports a modified mesh, and verifies the source hash after rendering. External image/buffer dependencies are rejected. It renders front/right/back/left/top/bottom as textured and clay (12 images). A neutral orthographic studio keeps counterpart cameras equal. Imported cameras/lights cannot contaminate it. A blank result, unsupported extension, missing texture, or shader issue still needs investigation; successful file output is not an art PASS.

`stats.json` records source hash, source-unit bounds, actual triangle counts, UV layers, material slots and image dimensions. Boundary/non-manifold counts use a disposable statistically welded BMesh copy, without welding the imported source. They are findings, not watertightness guarantees or automatic rejection rules. No scale normalization, retopology, unwrap or rebake occurs.

Write all raw diagnostic frames/logs/statistics to scratch, retain findings in the ledger, and keep only the review contact sheet actually shown at a gate. Rendering uses CPU by default for repeatability and avoids installing GPU packages. Do not repeat rendering after success unless inputs/settings changed or a specific unresolved issue needs it.

## Runtime evidence

Keep DCC diagnostics separate from engine proof. At G3 capture the actual game camera, light, character scale and relevant movement. Use a short clip only when it resolves moving occlusion, collision, sorting or flicker better than screenshots; a still image cannot prove traversal. Detect existing capture/encoding tools and use project-allowed engine capture or scripted input. Do not install a recorder automatically or always demand a 15–20 second video for static assets.

For a walkthrough, record the route and relevant interactions/checks, capture once, inspect the resulting images or clip and report observed limits. A compile success or an unviewed video is not validation. Respect project bans on computer use and stop after relevant checks pass. Existing G1/G2/G3 hard stops remain in force.

## Execution contract

Use explicit input/output paths and argument arrays. Image helpers return JSON paths, counts and warnings, with errors on stderr/nonzero exit. Blender has its own log output: redirect it to a scratch log, check the process exit code and read the known report path rather than assuming its entire stdout is JSON. Keep model/session environments separate; no helper changes global Python/CUDA settings. No helper here submits cloud tasks, downloads weights or spends credits.
