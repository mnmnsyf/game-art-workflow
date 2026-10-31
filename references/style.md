# Style Consistency

Making one good-looking asset is easy; making **the tenth still belong to the same game as the first** is hard. Lock style with a reusable "style pack", not by re-describing it every time.

## Define a system, not a mood

Before the first pack, settle each axis with observable properties:

| Axis | Settle |
| --- | --- |
| Shape | Rounded / angular / chunky / slender; which shapes signal friendly, dangerous, interactive |
| Silhouette | What must read at game scale; which parts may never merge into the main mass |
| Value | How many value bands; does the asset read in grayscale against the real backgrounds |
| Color | Palette **roles** (environment, accent, interactive, danger, reward), not just swatches |
| Edge | Pixel clusters, clean vector, ink line, painterly lost edges, soft bevels |
| Material | How wood, stone, metal, cloth, foliage, glass differ |
| Light | Direction, softness, contrast, ambient color, what is baked vs. dynamic |
| Detail | Where detail concentrates and what vanishes at native size |
| Camera | Projection, angle, horizon, facing convention |

The first approved target is a **contract**: a small board with the hero asset at real game size on common and worst-case backgrounds, the role-labeled palette, and do / don't examples. Later outputs are judged against it at the same size and light.

## Style pack

After the first G2 approval, register a style pack in the profile's `style.packs[]` and keep its files in a versioned directory (e.g. `art/workflow/style/<pack-id>/`):

| Content | Notes |
| --- | --- |
| 2–4 anchor images | Approved actual outputs (not web references), each noting what it stands for: silhouette, material, color, detail density |
| Prompt skeleton | Fixed parts (style, camera, light direction, background, material wording) and variable slots (`{subject}`, `{variant}`) |
| Negatives / avoid list | Elements that actually went wrong: photoreal noise, too many small ornaments, wrong perspective, text watermarks, etc. |
| Generation parameters | Channel, model version, size, reference strength, the seed actually submitted; note anything that cannot be controlled |
| Palette | 5–12 main hex colors and the allowed saturation / value range |
| Technical spec | Pixel density or triangle / texture tier, light direction, outline width, ground-shadow rule |

Style packs are versioned; any change is a new version, and each asset records the version it used.

## Generation discipline

- **Edit before regenerating**: variants of an approved asset (recolor, add a chimney) should use edit / inpainting with the approved image as input and explicit invariants.
- **Give references roles**: separate style references (borrow the look only), design references (borrow structure), and edit targets (the image to modify); tell the tool which is which.
- **Fix camera and light**: a batch shares one perspective and one light direction, or it falls apart once placed in the scene.
- **More candidates, fewer rounds**: within the authorized count, generate several candidates at once and choose on a contact sheet instead of trial and error one by one.
- For channels without seed or reference-strength control, state the consistency risk in G1.

## Consistency review

Put new outputs and anchors on the same contact sheet (`contact_sheet.py --anchor`) and check each dimension:

1. Silhouette language (round / angular, degree of exaggeration)
2. Color (within the palette, value hierarchy)
3. Detail density (brush or geometric detail at the same screen size)
4. Light direction and shadows
5. Material rendering (wood, stone, cloth painted the same way)
6. In-game sense of scale (side by side in a scene screenshot)

Judge at three distances: **native game size** (identity and state read at a glance), **working size** (edges, seams, material cues), and **in context** (a real game capture with lighting, neighbors, and effects). An asset that only works zoomed in is not game art.

Common drift signals: proportions or height change between variants; outline color or width changes; highlights imply a different light direction; the palette grows near-duplicate muddy colors; texture noise increases on later generations; the camera angle or projection shifts; ground contact and shadow footprint move.

When something drifts, name the dimension, then return to the approved seed and make a constrained edit, or regenerate. Never keep editing a drifted derivative until it becomes the accidental reference.

## 3D style consistency

Image-to-3D style is mostly set by the input reference: make sure references belong to one style pack before generating. Generated materials often skew photoreal or gray; unifying them with the project's master material / grading rules is a **material alteration** — send it for review and keep the original PBR.
