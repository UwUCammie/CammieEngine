# Nightmare Vision package-family Mods session

This bounded package exposes the source `funkin.Mods` list and selected-package behavior over roots admitted by `ImportPackageFamilyCatalog.forOwner(ownerRoot)`. The immutable owner root remains the runtime lease anchor. A family session maps source folder labels to catalog-authorized retained roots and shares selection, list ordering, enable flags, and persistence across Mods contexts that intentionally attach to that session.

`NightmareVisionModFamilySession` accepts a selected source directory, its lease root, typed family members, and optional `readList` / `writeList` callbacks. The host should back those callbacks with the imported owner's private `CodenameOwnerSaveData` field `nightmareVisionFamilyModsList`; list text is loaded once and each changed serialization is written through the callback. A failed write leaves the updated in-memory list available and propagates the failure. Context release detaches from the session, which releases its catalog and callbacks after the last attached context closes.

Family list operations retain the donor ordering rules: a nonempty current/top directory is first and forced enabled, previously ordered existing roots follow with their stored enabled flags, and newly discovered catalog directories append enabled. `parseList()` calls `updateModList()` before parsing. `updateModList(top)` intentionally ignores its formal argument and orders from the current selection. `loadTopMod()` clears selection, parses the ordered list, selects its first enabled row, then retains that package's config locally. Unknown persisted labels are pruned before parsing and cannot resolve to arbitrary folders. A selected package's global flag contributes only when its list row is enabled.

When no private family list has been stored, first-use ordering starts with the current package followed by other existing catalog members, all enabled. The donor's process-wide `modsList.txt` is not imported or migrated, so prior user ordering and disabled flags from that global file are outside this package. The first changed update stores the family list in the owner-private field.

Singleton contexts keep their owner-only selection and existing API behavior. `selectedRoot()` still returns the lease root when provenance has no source label, allowing legacy Paths lookups to continue. Family selection accepts only exact source labels from the catalog, plus null or empty to clear selection. The session rechecks labels and roots, rejects duplicate roots under different labels, and keeps path resolution inside authorized roots; the existing Paths providers perform physical symlink checks.

`getPack(null)` defaults to the currently selected family member. An explicit empty folder, or a null default when selection is empty, refers to shared content-root metadata that this package cannot access; it returns null with a boundary diagnostic and never falls back to the lease owner's `meta.json`. JSON5 parse failures follow the source `FunkinAssets.parseJson5` behavior: log and return null. A failed config read therefore leaves earlier list and selection mutations intact and does not replace the context's prior config.

`applyModConfig()` keeps a parsed config local to the Mods context. It does not apply process-wide options, window title or icon, transitions, Discord RPC identity, default font or UI prefixes, or state redirects. The complete menu/configuration transition remains outside this package.

Focused validation passed with:

```powershell
$env:PYTHONPATH='tools/tests'
python -m unittest test_nightmare_vision_source_api_contexts test_nv_package_family_paths
```

The tests cover owner-only compatibility, list ordering and enable flags, shared-context selection, owner-private persistence callbacks and session restart, invalid labels and roots, and actual family Paths/FunkinAssets routing. The application build and native runtime probe are owned by the root task.
