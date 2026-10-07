# NV shared sprite helper integration

Development version 0.0.16. This checkpoint connects the five pinned `FlxMacro.buildFlxSprite` conveniences to actual supported sprite objects. Windows, full regression and bounded native gates passed; complete source parent/API parity remains open.

## Source contract and implementation

The reference is `fnf_sources/NightmareVision/source/funkin/backend/macro/FlxMacro.hx`, method `buildFlxSprite`: `loadFromSheet`, `loadAtlasFrames`, `makeScaledGraphic`, `setScale` and `centerOnObject` return the actual receiver. The shared typed helper preserves virtual `frames`, `makeGraphic` and `updateHitbox` dispatch, source animation deactivation, cache key, axis flags and borrowed frame ownership. It does not promote live scale into `baseScale` or `defScale`.

Targeted build annotations expose actual compiled methods on NV plain sprites, generic group factory results, Bopper, MeshRender, Video, AttachedSprite, Alphabet/AlphaCharacter, Bar/HealthIcon and the shared splash parent. BGSprite and tap/sustain splashes inherit those methods. NV Bar physical children and the existing FIELD/SCREEN underlays use actual NV sprite wrappers. Mixed native Note, Character, Strumline and StrumNote also receive real methods; their borrowed atlas provider is bound only from the NV creation/configuration route.

`NightmareVisionSpriteRegistry` captures an owner-local Paths resolver. Preset/scene setup rebinds an existing provider; constructors only capture or create a missing provider. Atlas methods never consult current PlayState or a process-wide selected owner. Primary-owner changes release providers after old persistent plugins finish `onDestroy`; same-owner retries preserve them. Sprites clear their own borrowed cells after their complete destruction body, without releasing another sprite's shared provider or borrowed frames.

Source constructor factories provide Paths before NV plain/Bopper/BG/Video constructor asset work, including scoped `Type.createInstance`. Canonical runtime names are registered for supported own classes. The generic FlxSpriteGroup binding remains the actual native group Class, with a factory returning an actual helper-enabled subclass.

The pinned NV PlayState sustain body calculation at line 1874 reads live `frameHeight` after `modManager.updateObject`. Source renderer body stretch and clipping now consume live frame dimensions at that phase; standalone primitive rendering retains its existing cached path. No geometry cache invalidation or scale baseline promotion was added.

## Focused evidence

- `test_nv_sprite_macros.py`: 4 tests pass, including immutable donor helper comparison, actual parent virtual dispatch, compatible inherited signatures, native member exports and destruction return/throw/super ordering.
- `test_nv_sprite_integration.py`: 3 tests pass. Actual Iris and C++ generation cover typed plain/group/glyph/attached execution, captured constructor/reflection routes, atlas owner isolation, setup-only provider rebinding, retry/release and the extracted PlayState plugin-before-provider lease order. Bopper/Video constructor signatures use isolated stubs here. The canonical build compiles their actual types, but this native component does not instantiate Bopper/Video or decode media, so those runtime paths remain unverified.
- `test_nv_modifier_execution_bridge.py`: 1 test passes, retaining ordered execution assertions and adding callback-mutated sustain frame dimensions. Exact endpoint distance survives; body scale and clip width/height use the new frames.
- Adjacent NV Alphabet integration (3), source attachment integration (2), source Bar contract (1), and source HealthIcon contract (1) pass. Fixture changes supply only newly needed native-shaped dependencies, preserving existing donor and ownership assertions.

The connected and adjacent batch comprises 15 tests across 7 modules, with no skips or failures. Eval and C++ generation are headless verification, not native display proof.

## Accepted integrated gate

Root's repaired canonical Windows build passed (`tmp/source-nv-sprite-build-repaired.log`); its receipt is `tmp/source-nv-sprite-build-runtime.json`. The full suite passed 2,302 tests across 754 modules in 142.5 seconds, 345 existing skips and zero failures (`tmp/source-nv-sprite-full-tests-repaired.log`). The first full run found nineteen obsolete fixture dependency/extraction failures; minimal repairs retained donor bodies and behavior assertions. No production change followed the accepted native build, so that build and its captures were retained.

Root executed `tmp/test-source-nv-sprite-native.ps1` with `tmp/source-nv-sprite-native.hx`. Muted two-visit checks passed at 60 FPS (`source-nv-sprite-b1f79616`, 29.223 seconds) and unlimited (`source-nv-sprite-4d1277e6`, 27.161 seconds). All four markers occurred twice per run; each visit supplied a real 1280x720 nonempty framebuffer, backend/draw rate 60 or zero and matching unlimited mode. All four captures were reviewed. The runner copied 38 byte-identical private source dependencies per run, preserved seventy protected files and restored its private version/tag/options/chart and script inputs. Receipt: `tmp/source-nv-sprite-checkpoint.json`.

The probe checks typed constructors and extracted methods, group virtual behavior and child scaling, real glyph/HUD child/effect helpers, source icon hitbox offsets, inherited BG cleanup/deactivation, unsupported raw native receiver rejection, borrowed receptor atlas identity with immediate animation restoration, real Character/Strumline/receptor/FIELD helpers, and a next-update source scale reset that leaves baseline values unchanged. SCREEN geometry retains focused actual-wrapper coverage; its helpers were not independently invoked by this native probe. Its private overlay provides component visual evidence rather than an authored donor chart/menu acceptance claim. The source macro reference runs against actual host Flixel 6.1.2 dependencies; the supplied NV Project does not pin a historical Flixel version, so historical dependency parity is not claimed.

## Remaining scope

This is not complete NV sprite or parent-class identity parity. The source plain FlxSprite alias is an actual wrapper; mixed native Note/Character/StrumNote do not inherit that wrapper. Generic group factory-result class enumeration/resolveClass roundtrips remain incomplete. `NightmareVisionCharacterGroupCompat` is a non-sprite facade and deliberately has no fake helper bridge; the next actual typed-group migration is planned in `tmp/source-nv-character-group-next-proposal.md`.

Common-preset native FlxText and unported SpectogramSprite, ABotVis, MenuCharacter, MenuItem, Checkbox, DialogueBox and RGBSprite have separate parent/API integration gaps. The current matrix does not imply they expose all five helpers. Wider standard-base metadata, source Paths global state, constructor-bypassed empty instances and complete Phase 2 parity remain open.
