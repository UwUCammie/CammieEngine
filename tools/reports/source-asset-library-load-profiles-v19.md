# Owner-scoped Lime library load profiles, v0.0.19

Psych and Nightmare Vision owner indexes now use sidecar schema v2. The
identity entries remain keyed by exact `(library, id)` and carry a
`preloadState` of `enabled`, `disabled`, or `unresolved`. The index adds the
captured Lime `loadTarget`, `loadProfileComplete`, and one load-profile record
for each actual library namespace. Each profile preserves its source order,
Project preload and embed attributes, a `standard-file` / `unknown` /
`unsupported` state, and a diagnostic. Bare `<library>` declarations still do
not create a runtime namespace; the list is derived from actual Lime asset
partitions plus `default`.

The compatibility target is the pinned local Lime 8.3.2 source under
`.haxelib/lime/8,3,2`. `ProjectXMLParser.hx` sets `Library.preload=false`,
`generate=false`, `embed=null`, and `prefix=""` when those attributes are
absent. `AssetHelper.getAssetData()` defines effective entry preload behavior:

- Flash/AIR write a preload value only for an explicitly nonembedded asset
  assigned to a library, using that library's preload setting.
- HTML5 always preloads fonts. Other types preload when the asset is not
  explicitly nonembedded, or when an explicitly assigned library is marked
  preload. Same-stem sound/music entries become `pathGroup` records; this
  sidecar does not encode those groups, so that library is marked unsupported.
- WebAssembly preloads assets whose embed setting is not false, or when an
  explicitly assigned library is marked preload.
- Other pinned targets do not add an entry preload value. Lime's
  `processLibraries()` sets the standard `default` library's preload to true,
  but `getAssetData()` applies library preload only when the asset itself has
  a non-null library assignment.

The profile stores an explicit supported Lime `Platform` target only. It does
not infer a build target from the machine running the importer. When target
context is missing or invalid, the sidecar retains identity data, sets
`loadProfileComplete=false`, and leaves target-dependent entry preload
unresolved. With an explicit target and complete receipt-bound Project/build
context, standard libraries record per-entry preload based on the Lime rules
above. Project library `embed` is preserved as source metadata; it does not
prove that Lime's build embedded or registered a generated manifest at
startup.

Only ordinary file-backed libraries with no source path or custom library
type are marked `standard-file`. Custom handlers, source-backed libraries,
custom types, generation, prefixes, unresolved preload/embed fields, unknown
library declarations, and unrepresented HTML5 sound path groups do not receive
a standard-file claim. The runtime consumer can still use v1 indexes for
identity/getter/list operations; v1 indexes synthesize unavailable load
metadata, so owner-declared `loadLibrary` must report that metadata is
unavailable until the importer refreshes the receipt.

This profile covers explicit per-owner file-backed loading. It does not claim
source-identical automatic embedded-manifest registration or startup
`getLibrary()` visibility. Bundle/template/custom handlers, packed-library
formats, MovieClip/class bindings, dynamic global registration, complete
external/Haxelib build inputs, and mapped sibling-owner handoff remain separate
gaps. The project embed field is retained but is not used to invent those
runtime behaviors.

The profile parser version is 4 and Psych/Nightmare Vision importer revisions
are 9. The revision bump causes revision-8 imports to regenerate from their
retained source, because their v1 identity sidecars cannot provide the new load
metadata. The focused retained-profile test captures and verifies a real source
snapshot and checks library attribute/default handling, including an inactive
handler and an unresolved preload. The identity test exercises v2 warm/lazy
preload publication and validation, rejects unsupported targets, and confirms
that a v1 sidecar remains readable without gaining load claims. A separate
runtime acceptance fixture is being added by the integration agent; its result
is not included in these focused checks.

Focused checks run:

```text
CAMMIE_TEST_TMP=C:/t/cammie-test .tools/python/python.exe -X utf8 tools/run_tests.py --jobs 1 --pattern test_psych_asset_profile.py
CAMMIE_TEST_TMP=C:/t/cammie-test .tools/python/python.exe -X utf8 tools/run_tests.py --jobs 1 --pattern test_source_lime_asset_identity.py
CAMMIE_TEST_TMP=C:/t/cammie-test .tools/python/python.exe -X utf8 tools/run_tests.py --jobs 1 --pattern test_import_revision.py
```

No application build, full suite, or native game launch was performed for this
package.
