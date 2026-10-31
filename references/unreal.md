# Unreal Engine Integration

The maintainer has verified this workflow in a real UE5 project. That does not make it a general auto-importer or guarantee every engine version, plugin set, or project layout: still probe each project, and backfill the actual version, tools, and results into its profile on first use. Never auto-install the engine / plugins or modify an arbitrary existing UE project just to install this skill.

## Probe first

Confirm the .uproject, UE version, target platform, project directory conventions, existing importers / Editor Utilities / MCP bridges, and the actual enabled state of the Python Editor Script Plugin, Editor Scripting Utilities, etc. Check plugin names and APIs against the version. If the project does not use Paper2D, don't assume it is enabled; when configuration changes are needed, state the scope.

With enough capability, prefer official editor Python or the project's existing tools; before running editor scripts from the command line, confirm the entry point and arguments against the current version's docs. Without a bridge or scripting, provide an import package and exact settings for the user to apply, and record that you are waiting on an external action; never mark the asset integrated just because instructions were written.

## Asset import and level placement

1. For 3D choose FBX or a verified glTF / Interchange route by version and project; don't assume every version supports the same GLB flow. Check UE centimeters, Z-up, orientation, transforms, pivot, and DCC export to avoid 100× scaling and double conversion.
2. Base color is sRGB; normal and roughness / metallic / AO are data — check normal compression, normal direction, and channel packing. Don't use a glTF metallic-roughness texture as the project's ORM without rewiring. Use material instances of the verified master material; don't overwrite shared master materials.
3. For Static Meshes check LOD, material slots, shadows, lighting approach, and collision complexity. Choose Simple / Complex by use; complex collision on static buildings still needs real traversal tests, and dynamic physics has its own constraints. Keep functional openings when splitting doors, blockers, and interaction components.
4. Decide Nanite, virtual textures, and lightmap UVs by target platform and lighting approach; never enable them globally by default. Lightmap UVs and color-texture UVs serve different purposes; don't re-unwrap the original material UVs unconditionally for static lighting.
5. For 2D choose Paper2D, a background plane, or material cards per the project; configure pixel scale, pivot, filtering, mipmaps, translucent / masked, two-sided, shadows, sorting, and collision. Creating a Sprite or Texture asset does not mean it appears correctly in the level.
6. Import into a versioned Content directory; compose meshes, separate collision, and existing interactions with Actors / Blueprints; place into the designated level and record Actor transforms, asset paths, and pre-replacement references. Save only the necessary Packages / Map, never unrelated dirty packages. Rename / delete assets through editor asset operations so references follow; never move .uasset files directly.

## Acceptance and capability promotion

Verify import, materials, units, collision, and real level display on a representative asset first, then test traversal, door steps, sorting, and occlusion with the actual character in PIE / Standalone. Capture screenshots from the target camera; editor thumbnails or DCC turntables are not game acceptance. Choose performance checks by platform and asset impact; don't package the whole project without reason. Each review gate still stops for the user's reply.

Record each item as executable / needs setup / limited / unverified. Only a route that actually ran successfully is promoted to "verified for this version and project"; keep logs, sources, import settings, and game screenshots. Fold corrections from real UE projects into this adapter, keep project-specific parameters in the profile, and don't pollute the Godot branch.
