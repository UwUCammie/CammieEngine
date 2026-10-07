# Shared mapped media integration

Development v0.0.17 integrates the receipt-bound Project asset profile with the
normal Psych/Nightmare Vision importer and Psych global-pack importer. One
`SourceMappedAssetPublisher` walk plans language and media together before any
staged copy. Engine policies keep their runtime ownership rules, including
Nightmare Vision's authenticated package/core distinction, without duplicating
receipt verification or destination conflict handling.

The supported media policy preserves authored targets and raw bytes for images,
atlas/animation metadata, sounds/music, fonts, shaders and videos. Typed format
validation uses the source format, so a PNG renamed to a custom `.bin` target is
still imported without renaming it again. Disabled mappings suppress legacy
fallback; ambiguous or unresolved mappings protect prior managed outputs,
including custom extensions and unknown destinations. Clean refreshes retain
local-edit protection and transaction rollback. Psych and Nightmare Vision
importer revisions are now 6; existing imports regenerate from retained sources.

The importer smoke driver also waits for startup receipt inspection to finish
before starting a scanned import. This prevents a fast scan from racing the
manager's active inspection operation. Scan-only and timeout behavior retain
their separate paths.

## Native validation

The final Windows build is recorded in `tmp/v17-mapped-media-build-loader.log`.
Generated private donors were imported by the compiled manager at both 60 FPS
and unlimited FPS. Each check verified 16 published outputs against raw source
hashes, separate owner namespaces, and absence of unintended global copies.
Actual owner loaders decoded images, two-frame Sparrow atlases, audio and fonts;
native rendering compiled the mapped shaders. Image pixels retained their exact
colors and transparency. Video validation covers paths and byte identity only,
not playback. Both framebuffer captures were reviewed.

Evidence:

- `tmp/mapped-media-native-60.json` and `tmp/v17-mapped-media-native-60-loader.log`
- `tmp/mapped-media-native-unlimited.json` and `tmp/v17-mapped-media-native-unlimited.log`
- `tmp/v17-mapped-media-checkpoint.json` for the final suite, binary and source hashes

The native fixture uses the shared disk audio decoder for Psych paths. This
does not certify modern Psych's `Paths.sound/music` return-type parity: the
current owner facade still has its legacy path-string contract. No authored
chart was altered, and these generated checks do not measure heavy-chart FPS or
stuttering.

## Remaining contracts

Distinct Lime asset IDs still defer until a verified owner alias index exists.
Mapped assets across sibling/core receiver owners require an authenticated
receiver profile; the existing certified raw dependency collector remains in
that path. Complete automatic build-context capture, external/Haxelib inputs,
bundles, generated template outputs, Project object reflection, modern audio
getter types and remaining script APIs are still open. Phase 2 is incomplete;
this checkpoint does not publish a release.
