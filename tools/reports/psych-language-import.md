# Psych translation input import coverage

The source `Language.reloadPhrases()` reads authored `<language>.lang` inputs from the selected owner's published shared, current-level, and root data scopes. Before this change, Psych compatibility import retained only direct `data/` sidecars and selected script families; it did not publish `.lang` files from nested data or library scopes. Chart-free global-pack import retained media trees and `data/settings.json`, but likewise omitted language files.

`ModuleFunctions.mergeCompatScriptTrees()` now publishes `.lang` files from authenticated Psych `data/` trees while preserving their owner-relative paths. This covers the package root, `shared/`, direct library roots, `base_game/<library>/`, and named `library/<library>/` scopes. `PsychGlobalPackImporter` applies the same `.lang`-only rule to chart-free global packs. Both paths preserve authored file names and bytes, retain existing owner copies on refresh, reject paths outside their selected source or owner, and leave unrelated data files and `mods/` roots out of language publication. Full retained-source snapshots are unchanged and remain complete.

The focused filesystem tests exercise root and shared companions, current-level and base-game libraries, nested language paths, case-insensitive `.lang` extensions, same-name translations in distinct scopes, non-overwriting refresh, excluded `mods/` content, unrelated file exclusion, and unchanged donor bytes.

Validation: `python -m unittest test_compat_script_import test_psych_global_pack_import` passed 8 tests. No full suite, game build, or native game launch was run for this importer change.

Known source-profile gap: pinned donor `Project.xml` lines 88-89 maps `assets/translations` with `rename='assets'`, and the donor has `assets/translations/shared/data/pt-BR.lang`. The new import path preserves known owner data/library layouts and does not interpret that `Project.xml` asset rename. This translations-prefixed layout is not published into the owner paths consumed by `Language` yet. It needs an explicit, source-profile-backed mapping before this report can claim complete donor translation coverage; no path flattening is inferred from the folder name.

The integrated `Psych Engine` importer revision is now 3, so retained imports using revision 2 regenerate these language files. Final build, full-suite and native evidence is recorded in `psych-standard-services-integration.md`.
