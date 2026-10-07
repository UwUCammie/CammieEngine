# Connected source attachment integration contracts

Development 0.0.16. This package connects actual source attachment types to owner-local gameplay script imports and constructor factories. Core donor comparisons are recorded in `source-attachment-contracts.md`. Canonical build, full regression suite and muted native acceptance remain pending root gates.

## Source interfaces and binding

Pinned Psych 1.0.4 `5c67ced`, `source/objects/AttachedSprite.hx`, uses `(file=null, anim=null, parentFolder=null, loop=false)`. The host factory appends its captured SourceAttachedSpriteOwner as the fifth argument. Its image and Sparrow callbacks forward both the file and nullable parentFolder directly to the existing PsychOwnerPaths proxy; the second String argument is the existing library/parent-folder route. No generic asset lookup or GPU policy is added. Antialiasing reads the constructing state's current source preference, independently of another state's bindings.

Pinned Nightmare Vision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `source/funkin/objects/nodes/AttachedNode.hx`, defines both the primary node and secondary AttachedSprite module type. Donor Credits/option code imports the primary module and uses both short names. The host installs distinct source-dialect globals and exact import paths:

| Dialect/import | Actual class |
|---|---|
| Psych `objects.AttachedSprite` | PsychSourceAttachedSprite |
| NV `funkin.objects.nodes.AttachedNode` | NightmareVisionAttachedNode |
| NV `funkin.objects.nodes.AttachedNode.AttachedSprite` | NightmareVisionAttachedSprite |

NV constructors have no owner resource dependency and use the actual class constructor route. Psych's owner factory is scoped to its interpreter, not a global constructor replacement. Both bare constructors and qualified module constructors execute through the existing Iris resolver. FlxAxes now exposes exact X/Y/XY/NONE constants; the attachment binder also binds `flixel.util.FlxAxes`. This is a constant facade, not a claim that every FlxAxes static helper is exposed.

The binding is installed alongside existing source Bar/Icon bindings for dedicated NV scopes and plain Psych gameplay/UI source scopes, using each script's captured PsychOwnerPaths facade. Native/Codename/V-Slice fields and their class bindings are not converted to Dynamic. No HUD pointer replacement is needed: created objects are actual FlxBasic/FlxSprite instances that scripts add to the state's real display hierarchy.

## Connected evidence

`test_source_attachment_integration.py` executes the production owner/binder methods, actual typed core classes, existing SourceIrisBridge and NightmareVisionScriptInterp/parser, real import/constructor resolution, native-shaped object inheritance and actual pinned FlxAxes/animation/alpha/group methods. Two cases pass eval and C++ generation with no compilation, zero skips/failures (2.3 seconds in the six-module focused run).

Psych evidence covers empty/static/animated construction, nullable parent-folder forwarding, loop/prefix fields, two independent captured image owners, current preference changes, real sprite/base identity, actual state membership and once-only update/destruction, post-super tracker mutation, copied angle/alpha/visibility/scroll factor, null tracker retention and owner load errors.

NV evidence covers primary and secondary module imports, qualified secondary construction, distinct node/sprite identities, wrapper-owned node pointers, exact X/NONE/XY values and reflected script assignments, post-super callback ordering, root/tracker replacement, actual FlxObject versus FlxSprite alpha gating, visible group membership, wrapper child update once, borrowed lifetime and instrumented point return on node/wrapper destruction.

Unrelated camera, save and video/zIndex seams are stubbed in the integration fixture. Resource facade calls are instrumented to prove captured argument forwarding; the fixture is not a full native atlas parser, renderer, filesystem or point pool. Actual native graphics, atlas loading, Flixel pooling and frame-to-frame source callbacks remain native gates.

Related focused checks used `.tools/python/python.exe tools/run_tests.py --pattern <module>.py --jobs 1`: source attachment core (1), attachment integration (2), health integration (2), source icon integration (3), source HUD Bar integration (2), source Bar core (1). All eleven cases passed across six modules, zero skips/failures. The Bar-only extracted fixture adds an inactive attachment binder seam and retains its original typed Bar assertions.

## Native component plan

Prepared only, not launched by this agent: `tmp/source-attachment-psych-native.hx` and `tmp/source-attachment-nv-native.hx`. Root owns the fresh private tutorial runtime, versioned manifest roots, controlled owner image/two-frame atlas and immutable NV core dependency. The probe uses options-style label/backdrop components rather than repeating previously verified imported chart flows. Each script emits exactly two independent pass markers per visit: constructor/import/flag/lifetime evidence and actual displayed live-following evidence.

Psych shows a Controls-style translucent attached label backdrop, a static owner image and an animated owner follower. NV shows a GameplayChangers-style attached value label and a wrapper backdrop. The staged onUpdatePost checks use host tick guards to avoid repeated source callbacks within one host frame. Flags, axis transitions, replacement/null trackers, non-sprite alpha gating and borrowed lifetime are asserted before final visible reference positions. No original chart/mod script is edited. Core files and native budgets are not weakened to bypass missing dependencies.

## Scope limits

Psych AttachedText/Alphabet, complete Controls/Credits/options states, arbitrary source menu flow, custom property-copy extensions and full inherited sprite/renderer behavior remain open. These helpers prove attachment construction/update/ownership, not restoration of entire source states or completion of Phase 2. Point pooling in the focused fixture is instrumented; native acceptance must verify the real lifetime path. No donor/mod/chart/content-specific production branch, compatibility fallback or asset mutation was introduced.

## Integrated acceptance

Accepted bounded source attachment checkpoint, development 0.0.16, 6 October 2026. Canonical Windows build passed (`tmp/source-attachment-build.log`). Final full suite: 2285 tests across 748 modules in 149.2 seconds, 345 reported skips, zero failures (`tmp/source-attachment-full-tests.log`). Real typed source constructors, module/short imports, Psych owner image/Sparrow/preference dependencies and NV node axes/borrowed lifetime run through the native interpreter and display list.

Muted private Tutorial component checks passed two visits at 60/unlimited FPS for both dialects, two named markers per visit. Root reviewed eight captures. Gated executable/lime hashes match the export and fresh private runtime (`tmp/source-attachment-build-runtime.json`). Seventy protected files stayed unchanged; private chart/options/version/tag were restored to verified v0.0.15 archive bytes and temporary component inputs removed. This is controlled component/startup evidence, not full-song or source menu acceptance.

Each raw runtime receipt contains exactly two nonempty note_render_readback events for visits one/two, with positive framebuffer dimensions and backend frame rate 60 or zero matching the requested cap. The private NV scene has a synthetic black background; no authored NV Tutorial stage or complete source menu fidelity is claimed.

The private NV owner received exact immutable stock core dependencies for noteskin, note/effect atlases, UI bars/icons/combo/ratings/countdown, fonts and sounds, preserving source paths. The receipt lists each donor path/hash. Controlled Psych atlas testing used an immutable stock face PNG with generated two-frame sourceFollow XML; no original donor/mod content was modified.

- psych 60 FPS: `source-attachment-psych-16714f4d`, 28.666 seconds, two markers each twice.
- psych unlimited FPS: `source-attachment-psych-c55570a8`, 27.375 seconds, two markers each twice.
- nv 60 FPS: `source-attachment-nv-3756d660`, 27.114 seconds, two markers each twice.
- nv unlimited FPS: `source-attachment-nv-feb6f6c2`, 27.031 seconds, two markers each twice.

Receipt: `tmp/source-attachment-checkpoint.json`. AttachedText/Alphabet, full menus, wider inherited rendering/atlas behavior and Phase 2 remain open. No donor/mod/chart edits or publication.
