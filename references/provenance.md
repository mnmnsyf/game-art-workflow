# Asset Rights & Provenance

Recordkeeping so every shipped file can answer "where did this come from and may we ship it?". This is production practice, not legal advice; when terms are unclear or the release matters commercially, flag it for a human rights review instead of guessing.

## Record per shipped asset

Keep these in the set manifest ([templates/asset-manifest.json](../templates/asset-manifest.json)) and the job ledger:

- stable asset ID and repository path
- source: tool / model / version and date for generated work; creator, URL, or order for acquired work
- prompt and reference IDs (generated), or the original file (acquired)
- license name and version, with a saved copy or link to the terms
- attribution text and where it must appear
- restrictions: commercial use, modification, redistribution of source files, AI training
- edits and derivatives, and who / which tool made them
- review status and reviewer (from the G1/G2/G3 records)

Keep receipts and license snapshots containing account or personal data out of public repositories.

## Rules

1. "Free", "royalty-free", visible in a search engine, or model-generated is not a license.
2. Verify terms at the original source, not a repost or aggregator.
3. Attribution survives atlas packing, renaming, conversion, and derivative edits.
4. Shipping a game and publishing editable source assets can have different permissions — check before putting raw sources in a public repo.
5. Do not request direct imitation of a living artist; describe properties or use references the project may edit.
6. Preserve embedded provenance metadata (e.g. C2PA content credentials) where the pipeline allows; if optimization strips it, the manifest record remains the source of truth.
7. Platform disclosure: storefronts change their AI rules faster than this file. Steam's Content Survey, for example, asks about generative AI and distinguishes content generated during development from content generated at runtime. Mark each asset `generated: true/false` in the manifest so the survey is answered from records, not memory.

## References

- [SPDX license list](https://spdx.org/licenses/)
- [Creative Commons license chooser](https://creativecommons.org/chooser/)
- [C2PA specifications](https://spec.c2pa.org/specifications/)
- [Steamworks Content Survey](https://partner.steamgames.com/doc/gettingstarted/contentsurvey)
