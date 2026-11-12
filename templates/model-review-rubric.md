# Model review rubric

Score each line 0–2 (0 = fails, 1 = acceptable with a noted fix, 2 = good) and cite the evidence (image name / view / report field). A single 0 in a **blocking** line means "do not proceed" regardless of the total. Scores are advice for the gate; the user decides.

## A. Concept image (G2a, before any spend)

| # | Check | Blocking |
| --- | --- | --- |
| A1 | Matches the brief: right object, role and key parts | yes |
| A2 | Style matches the anchors (shape language, palette, finish) | yes |
| A3 | Reads at game scale: silhouette and focal details survive at the real screen size (judge from a downscaled copy) | |
| A4 | Tripo-ready: one whole uncropped object, plain background, soft light, no text or scenery | yes |
| A5 | Structure is unambiguous: parts separated, hidden sides inferable, no impossible perspective | yes |
| A6 | Risky features flagged: thin parts, openwork, ropes, dense detail (accept only with a plan) | |
| A7 | Design detail kept: not simplified into a generic shape | |

For each rejected candidate give: the failing lines, where in the image, and one revised prompt line that targets that failure.

## B. Generated model (G2b, from `review-sheet.png` + `report.json`)

| # | Check | Evidence | Blocking |
| --- | --- | --- | --- |
| B1 | Silhouette and proportions match the approved concept | `front34` vs anchor | yes |
| B2 | Part count and key details present; nothing fused or duplicated | textured + clay rows | yes |
| B3 | Back, sides and bottom are plausible (not smeared or invented badly) | back / left / right / bottom | |
| B4 | Geometry clean: no holes, lumps, floating fragments, collapsed thin parts | clay row; `boundary_edges` as a hint only | yes |
| B5 | Materials: no baked harsh lighting, smears, seams or wrong colours | textured row | |
| B6 | Real size correct on the chosen axis; origin at the base | `dimensions_m`, `ground_z`, `size_axis` | yes |
| B7 | Triangles and textures within budget, or a reduction plan is stated | `triangles`, `textures` | |
| B8 | Separate parts needed for gameplay exist, or Blender work is planned | `parts` | |

Recommendation, one of: **accept** → M5 (or M4 if over budget) · **fix in Blender** (state what; technical fixes need no new spend) · **new concept** (structural failure caused by the image) · **new generation** (only with the same approved image and a stated reason; needs new authorization).

Geometry problems (clay) and material problems (textured) are reported separately; a technical PASS in `report.json` is not an art PASS.
