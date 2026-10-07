# Receipt-bound mapped media policy

`SourceMappedMediaPolicy` supplies class-scoped decisions to the shared `SourceMappedAssetPublisher`. The caller selects a policy only after binding the profile to the exact authenticated source root. Psych uses `psych()`. Nightmare Vision uses `nightmareVision("package")` for a package root or `nightmareVision("core")` for the authenticated game-assets root. If an NV profile is receipt-bound but its package/core origin cannot be proved, use `nightmareVisionUnresolved()`; it defers media without guessing a destination and requests a broad preservation check. The scope is never inferred from a directory basename.

The policy preserves Lime's authored `mappedPath`. It treats Lime's `library` as asset identity metadata and `embed` as metadata, not as a filesystem prefix or a reason to drop a file. Psych package outputs remain relative to the imported owner root. NV package outputs do too. NV core outputs are placed below `__nmv_core`, matching `NightmareVisionPaths.CORE_DIRECTORY`; this keeps package lookup and core lookup separate.

The before-hash filter selects by both mapped path and candidate metadata. It includes standard runtime media paths and recognized media extensions anywhere under `assets/`. A `Project.xml` candidate typed as image, sound, music, font, shader, video, or animation can also select files at an authored target outside a conventional media directory. This is candidate-aware so the walker can skip unrelated files in mixed asset trees before hashing. For explicitly typed assets, format support is checked against the receipt-bound source extension, as Lime does; a PNG renamed to a `.bin` target remains a PNG asset and keeps the authored `.bin` destination. The generic two-path filter remains available to other consumers.

Known runtime formats are classified as follows:

| Runtime class | Verified file forms |
| --- | --- |
| Raster images | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif` |
| Atlas and Animate metadata | `.xml`, `.txt`, `.json` under image/animation mappings; `Animation.json` is recognized at an authored target |
| Sounds and music | `.ogg`, `.mp3`, `.wav` |
| Fonts | `.ttf`, `.otf` |
| Shaders | `.frag`, `.vert` |
| Psych videos | `.mp4` |
| Nightmare Vision videos | `.mp4`, `.mov`, `.webm` |

Unknown extensions under a known media path or explicitly typed media mapping are deferred and protected as managed outputs. Lime `template` and `manifest` candidates remain with their existing consumers when their source and target are not media-shaped. If one replaces a media-shaped mapping, the policy selects and defers it to preserve prior media output. Song, chart, and script paths remain with their specialized converters, including after a rename. The policy preserves the target, `type`, `embed`, and `library` fields on each receipt-verified event.

The profile carries Lime's file and nested identity rules. A top-level `id` applies only when its source is a file; directory declarations ignore that attribute. Nested `id` wins over nested `name`, and nested `name` supplies the asset id when no explicit id exists. When a Lime id differs from the authored target, publication is deferred because there is no verified owner alias index yet. An id equal to the target is safe to publish.

The profile walker exposes candidate-aware deferred, disabled, and ambiguous projections in addition to its existing path arrays. This protects typed nonstandard targets when a source is absent, unresolved, or collides. An unresolved Project source/target variable is never treated as a literal destination: the typed projection leaves its owner path unknown so the publisher uses its broad preservation check. A known target remains narrow when only its condition is unresolved. Disabled-only mappings block legacy fallback but can be pruned by a clean refresh; unresolved and ambiguous projections preserve prior managed bytes.

The policy does not claim full source asset publication. It handles receipt-bound runtime media mappings and preserves unresolved/disabled projections through the shared planner. An unresolved NV package/core scope is deliberately conservative because existing output manifests do not retain enough information to assign arbitrary prior paths to one media class. Direct legacy v1 profiles remain outside the receipt-bound contract. Automatic capture of every source build flag/value/command remains incomplete; callers must provide explicit profile context. Custom Lime id aliases remain deferred until an identity index is implemented.

Focused eval validation ran `test_psych_asset_profile` and `test_source_mapped_media_policy`: 29 tests passed. The shared asset publisher projection suite previously passed 21 tests in forced eval; the parent agent is rerunning publisher and manager fixtures against the final symbolic-target changes. No native build, game build, or full suite was run for this package.
