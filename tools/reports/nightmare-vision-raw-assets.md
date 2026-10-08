# Nightmare Vision raw Assets bindings

The pinned Nightmare Vision donor is commit `733165c42ca71eb0961a70e4173b2d81ba4a29ea`.
`source/funkin/scripts/FunkinScript.hx` assigns `Assets` to `lime.utils.Assets` and
`OpenFlAssets` to `openfl.utils.Assets` for every script in `preset()`. It does not
select these APIs from `modFolder` or script origin. The pinned `Project.xml` declares
compiled `assets/embeds` first, then `assets/game`, then the non-embedded `content`
tree under the project conditions. Package content can therefore override a duplicate
compiled asset identity declared by the engine project.

`NightmareVisionAssetsBindings.install()` is called from
`PlayState.seedNightmareVisionCommon()` after the source globals are seeded and before
the rest of the script bindings are installed. It binds the same selected-owner Lime
and OpenFL proxies to the bare aliases, their fully qualified imports, and the
interpreter-local `Type.resolveClass` table. The shared context is
`SourceOwnerAssetContext.nightmareVisionAssets(paths.root)`: it queries the receiver's
authenticated package and core identity records, with package identity taking
precedence for duplicate `(library, id)` entries. It does not use process-global
registries or loose host files. `FunkinAssets` and `Paths` remain separate source
mod-folder APIs.

The focused Haxe eval fixture uses the real `NightmareVisionScriptInterp` and
`NightmareVisionScriptParser` with isolated owner-context/facade doubles. It verifies
bare accesses, explicit aliases for both qualified class names in one interpreter,
scoped `Type.resolveClass`, and isolation between interpreters. Iris 1.1.3 returns
early on a second import with the same leaf name before registering its explicit
alias. The interpreter now handles explicit aliases for resolvable imports while
leaving the already-selected leaf import intact. Resolution follows the existing
owner-aware `getOrImportClass` path, including exact `importBindings`,
`SourceNativeClassScope`, and Iris's normal Haxe class resolver. Blocklisted imports
still use Iris's rejection path; unresolvable imports keep Iris's normal diagnostics.

`RuntimeNvAssetsProbe` adds an opt-in native test through
`tools/run_nv_assets_native.ps1`. Its generated source has one outer provider and two
content roots that declare the same library and IDs. The probe calls the real scanner
and retained importer with an explicit Windows source build context, then checks the
committed package and authenticated core handoff indexes before seeding actual
Nightmare Vision interpreters through `PlayState.seedNightmareVisionCommon`. It checks
bare and qualified imports, all three OpenFL import spellings, reflected type lookup,
package-over-core resolution, typed mismatch and missing-path behavior, Lime/OpenFL
pixel decoding, local library Futures, cache isolation/clear, owner-local events, and
teardown. The generated fixture does not edit source inputs or user saves. The native
runner requires a private runtime and expected executable SHA-256. Root's integrated
Windows run passed the real retained-import probe on 8 October 2026. The receipt is
`tmp/v20-release-native-final.log`, for executable SHA-256
`7727753a2484c5e0f2ecf827cc32295692679542dbf12e3f0072dbefc4f313d4`.

Focused validation: `python tools/tests/test_nightmare_vision_assets_bindings.py`
passed 2 tests, `python tools/tests/test_runtime_nv_assets_probe.py` passed 2 tests,
and `python tools/tests/test_runtime_smoke_harness.py` passed 42 tests with 7
platform-specific skips. `test_nightmare_vision_script_interp.py` and
`test_nightmare_vision_script_parser.py` passed 1 test each. The native probe
also verifies three actual scanned roots, receipt-bound package/core handoff,
decoded pixels and library Futures, exact event counts, local cache clearing, and
owner retirement while the other owner stays usable. The final release checkpoint
records the acceptance run for its exact published executable.
