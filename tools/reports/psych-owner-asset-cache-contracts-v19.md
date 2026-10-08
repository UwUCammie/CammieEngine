# Psych owner asset cache contract, v0.0.19

The selected-owner Lime and OpenFL facades now use per-owner cache objects for receipt-indexed asset IDs. Cache keys are the exact ID supplied to the facade, including a `library:` prefix. The objects are private to the normalized owner, engine, and scope. If a receipt proof is replaced, the cache objects are cleared and rebound in place so a retained facade's `cache` reference does not continue pointing at stale entries. The unindexed and native fallback paths keep their existing behavior.

Lime synchronous and asynchronous indexed reads honor `useCache` and `AssetCache.enabled`. Async cache writes follow Lime's load-start rule: Lime schedules a cache write only when caching is enabled when the request starts, then writes on completion. The callback also checks the captured owner identity before touching its cache. Library preload caches remain the underlying `AssetLibrary`'s responsibility.

OpenFL indexed conversions use the owner-local OpenFL cache. Synchronous bitmap, font, and sound getters use the exact passed ID as OpenFL does. Asynchronous bitmap and font loads check the OpenFL cache first; sound and music loads preserve the pinned implementation's completion-only OpenFL cache behavior. OpenFL bitmap/font/audio decoding delegates to the owner's Lime library view, so preloaded library assets remain reusable. `getMusic` follows the pinned Vorbis-file path and falls back to `getSound` when Vorbis is unavailable. OpenFL cache remove methods mirror matching removals into the same owner's Lime cache; they never remove a same-ID entry from the host Lime cache.

Verified owner libraries use a manifest-backed `PsychOwnerFileAssetLibrary`. Its Lime font getter and loader read the receipt-bound file bytes and call Lime `Font.fromBytes` / `Font.loadFromBytes`, while Lime keeps its normal `cachedFonts` and preload lifecycle. This avoids retaining a file handle to an owner output that refresh may atomically replace. The decoded face, glyph data, and metrics come from the same Lime font decoder. The Font's private `__fontPath` and path-derived basename are unset, so code that inspects those private provenance fields observes a difference. Lime does not expose an instance `Font.load()` method. No live Font is disposed during refresh.

The pinned behavior was checked against `.haxelib/lime/8,3,2/src/lime/utils/Assets.hx`, `.haxelib/lime/8,3,2/src/lime/utils/AssetCache.hx`, `.haxelib/lime/8,3,2/src/lime/utils/AssetLibrary.hx`, `.haxelib/openfl/9,5,2/src/openfl/utils/Assets.hx`, and `.haxelib/openfl/9,5,2/src/openfl/utils/AssetCache.hx`.

Focused eval validation:

```powershell
$env:PYTHONPATH='tools/tests'
$env:CAMMIE_FORCE_EVAL='1'
$env:CAMMIE_TEST_TMP='C:/t/cammie-test'
python -m unittest test_psych_owner_asset_library_lifecycle test_psych_owner_lime_assets test_psych_owner_asset_library_view
```

All three modules passed (four tests). The lifecycle fixture covers owner cache isolation, enabled-flag isolation, OpenFL-to-owner-Lime remove routing, prefix clear, and stable cache-object reuse after receipt proof replacement. The focused test also pins the byte-backed font method path.

The native acceptance record `tmp/v19-release-native-accepted.log` reports `verified: true` for the Windows executable SHA-256 `45dde13375c60d0bb9c5b227bc125816891b8fd71d28141aedb3ca308229857d`, run from the isolated runtime `C:/t/cammie-owner-library-v19-release-verified`. The retained-import probe verifies receipt-indexed SOUND, WAV MUSIC fallback, Vorbis MUSIC, and FONT outputs for two owners, including Lime/OpenFL cache behavior, distinct owner bytes, and same-name host-library preservation. It also holds old Font and Vorbis stream references while refreshing alpha's installed files in place, then checks new font glyph output and new stream PCM against refreshed bytes while the old stream still matches its original bytes. The fixture declares alpha's OGG as MUSIC and beta's same-ID OGG as SOUND, confirming the OpenFL path-based Vorbis behavior across Lime's SOUND/MUSIC lookup alias. These results establish the tested selected-owner file-backed paths, not general parity for embedded manifests, custom handlers, bundles, or dynamic library registration.
