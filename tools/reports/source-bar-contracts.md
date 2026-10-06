# Source Bar group contracts

Typed group subset and connected source HUD integration passed the integrated acceptance recorded below. This does not complete Phase 2 or certify older Psych HealthBar/FlxBar variants.

## Source and implementation

Psych source is revision `5c67ced`, `source/objects/Bar.hx` (1.0.4). NV source is `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `source/funkin/objects/Bar.hx`. Both are native FlxSpriteGroups with actual leftBar/rightBar/bg children in that order. Their source constructors take x, y, image, optional value function and bounds. Host classes `PsychSourceBar` and `NightmareVisionBar` add a seventh `SourceBarOwner` dependency containing owner-local image and current antialiasing callbacks. It is used during construction rather than retained as a global owner.

`SourceBarLayout` shares the source clip split, physical fill alignment, barCenter computation and explicit clipRect reassignment. It does not read the value callback or clamp direct percentage writes. Each class retains source constructor ordering, width/height setter regeneration, unchanged-percent optimization, unconditional direction update, nullable colors/value function, enabled update semantics and native child ownership.

Psych exposes writable children and Dynamic bounds, obtains antialiasing three times during construction and resizes existing fill graphics during regeneration. NV keeps final children, real FlxBounds, bgOffset/setBGOffset, default sprite antialiasing, frame-dimension-sensitive regeneration and source-spelled alphaMultipler. Repeated NV offset calls add each input to background position while fill alignment subtracts the latest stored offset. Repeated multiplier assignments reapply the multiplier to current alpha; they are not made idempotent. Equal/reversed bounds and direct percentages outside 0-100 retain executable donor math rather than host normalization.

The types are actual native groups, not wrapper objects with synthetic children. The implementation relies on the pinned Flixel inherited transform, camera, update/draw and destruction behavior. No source assets, retained mods, charts or donors were edited.

NV Bar also implements `NightmareVisionIUiSprite`, matching the complete pinned `funkin/game/IUiSprite.hx` interface: `public var alphaMultipler(default, set):Float`. The fixture verifies actual `Std.isOfType` identity and setter dispatch through that interface, including C++ generation. Psych Bar does not acquire this NV identity. This does not establish the interface on any other HUD sprite class.

## Focused evidence

`.tools/python/python.exe tools/run_tests.py --jobs 1 --pattern test_source_bar_contract.py` passes one fixture, zero skips/failures (0.5 seconds). It compiles both complete immutable donor Bar classes and actual host classes, comparing eighteen finite scenarios. Checks cover constructor child order/dimensions, callback-derived percentage and physical boundary, direct percentage/direction, offsets/sizes, disabled and missing value functions, reversed/equal bounds, physical colors, native group x/y/alpha propagation, changing background frame dimensions, updateBar not reading the value callback, NV repeated background offsets/multiplier, Psych child-field replacement and bounds replacement. Selected image/antialiasing callback counts are also checked.

The fixture executes the pinned actual FlxGroup add/update/destroy and FlxSpriteGroup preAdd/add/transformChildren/x/y/alpha/update methods against small native-shaped graphic/rect/point dependencies. Children are destroyed exactly once by actual group traversal. Group members are accessed through a typed getter, preserving the native accessor boundary. It deliberately does not model the complete Flixel graphic/GPU implementation, arbitrary group APIs or camera/scale callback-point propagation. Those require native acceptance.

A second pass generates C++ using `-D no-compilation`, actual typed bar setters and an Int-backed FlxColor shape with nullable optional arguments. No native compiler, full build or smoke launch was run by this agent.

The primary agent's private probe has been reviewed for constructor arguments, value callback counts, updateBar/disabled behavior, physical clip/barCenter checks, NV repeated multiplier/background-offset semantics and Psych field replacement without group membership replacement. Connected source HUD identity, alias/reflection routes, actual displayed groups, background assets and native clip output remain pending their integrated gate. Older Psych generations are a separate inventory contract; exposing these classes does not claim their differing HealthBar APIs are identical.

The first private native receipt `ec1a1de5` was rejected because the probe expected unrounded clip widths. Pinned FlxSprite.set_clipRect rounds the provided rectangle via FlxRect.round. The shared headless fixture now executes those actual methods (with only a clip-assignment test counter added). Fractional percent/offset cases compare both donors and hosts: physical clip widths/coordinates round independently while barCenter retains the floating boundary computed before reassignment. Core eval/C++ generation passes after this test correction. Production layout is unchanged; the rejected private assertion is not an engine failure.

## Integrated acceptance

Accepted bounded source Bar checkpoint, development 0.0.15. Canonical Windows build passed (`tmp/source-bar-build-final.log`). Final full suite: 2273 tests across 741 modules in 144.7 seconds, 345 documented platform/corpus skips, zero failures (`tmp/source-bar-full-tests-final.log`). Compiler PATH was supplied. The earlier five extraction fixture failures were corrected without weakening their behavioral assertions.

Muted native checks passed two visits per engine at both 60 and unlimited FPS. Psych passed twelve markers per visit, including actual constructor/child identity, clip/resize/value behavior, shared Lua/HScript aliases, transparent stock-frame center, authored intro movement, hidden/recovered opponent notes and extra actor visibility. NV passed three combined markers per visit for actual group/interface/dialect behavior, physical HUD layout and value ownership. Root reviewed all eight final gameplay captures. Every run preserved seventy protected files and removed temporary probes.

Visual review caught a real integration defect after the first behavior passes: the old opaque host frame covered source fills. Owner-first stock-frame fallback now uses four byte-identical source PNGs in engine-owned compatibility assets; custom owner images and native assets are unchanged. The final Psych captures show purple/blue health fills. Private probe corrections for clip rounding and nonexistent FlxRect.clone are recorded in the root review, not counted as engine fixes.

- psych 60 FPS: `psych-pass-swag-messiah-f49c6cff`, 96.581 seconds, 12 markers each twice.
- psych unlimited FPS: `psych-pass-swag-messiah-1e7fa172`, 94.58 seconds, 12 markers each twice.
- nv 60 FPS: `psych-pass-darnell--nightmare-vision-54e1fc6dd6-898cd5ce`, 135.628 seconds, 3 markers each twice.
- nv unlimited FPS: `psych-pass-darnell--nightmare-vision-54e1fc6dd6-d590cbad`, 134.012 seconds, 3 markers each twice.

Executable SHA256: `8E4F9C12C81D76342ADCB47D76E48E18001DF79C4A7A1BB14D6FA9BF99A280A9`. Receipt: `tmp/source-bar-checkpoint.json`. Phase 2 remains incomplete. Next connected package is source health setter/update bounds and icon-frame policy (`tmp/source-health-next-proposal.md`); full source HUD and historical Psych variants remain open. No donor/mod/chart edits or release publication.
