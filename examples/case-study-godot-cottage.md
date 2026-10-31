# Case Study: A 3D Cottage in Godot 4.7.2

This is the field evidence for the 3D → Godot branch of this skill, from the maintainer's own indie project. The numbers belong to that project only and are not defaults for any other project.

## Results

- Asset: one cottage from a single image-to-3D generation.
- Raw output: 41,939 triangles; 4K base color, metallic-roughness, and normal maps.
- After faithful normalization: max vertex-position and UV error 0; the three textures' byte hashes match the source files.
- Integration: native-PBR eave occlusion fade, wall collision, and door step / ramp traversal checks passed; in-engine screenshots and a standalone Windows export were completed.

## Evidence kept in that project

- Provenance and fidelity records next to the model (source job, hashes, per-channel comparison)
- A targeted engine test for collision, door step, and occlusion fade
- In-engine screenshots from the actual camera

## Earlier failures (where this skill's design came from)

- Swapping the roof during integration and calling it "optimization".
- Re-unwrapping UVs, which misaligned the textures.
- A generic shader truncating material channels and losing metallic-roughness, so the result no longer matched the source model.

Matching rules: "fidelity vs. alteration", the A0–A3 phases, and "duplicate the full native material and change only the necessary visibility".

## Not covered

Other Godot versions and renderers, a complete three-gate 2D task. (Unreal Engine was verified separately by the maintainer; see `references/unreal.md`.)
