# NV modifier registration and source instance contracts

Development 0.0.15. Pinned donor: Nightmare Vision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`. Implementation and focused checks are complete; canonical Windows build/full suite and native verification are pending. This checkpoint does not complete Phase 2 or certify arbitrary custom classes.

## Source comparison and implementation

Donor PlayState:983-990 calls postReceptorGeneration, registers essential/default/scripted modifiers, publishes modifiersRegistered, then calls postModifierRegister with no arguments. The host now follows this sequence and finalizes current chart keys/lanes on the existing manager/registry before builtin generation. Repeated countdown requests retain the generatedFields guard; source callbacks can still explicitly reset it. Modifier updates use the existing source batch at the donor timeline/update phase, after registration: timeline precedes update, render-only frames run neither, catch-up ticks use tickElapsed. Native/Psych routes are unchanged.

Donor ModManager:90-197 defines instance registration and activation. The host preserves registered Modifier objects in public register/notemodRegister/miscmodRegister maps and modArray, returns their identity from get, constructs root children before registration, rejects same-kind duplicate names and permits donor cross-kind global-map overwrite. Active names remain the actual mutable source array; parent/submodifier predicates and source sorting apply on each manager setValue. Timeline values read and write those instances. Independent Modifier.active gates miscellaneous update callbacks, rather than being inferred from a nonzero value. Dimension finalization preserves manager, registry, timeline, custom instance and value identities.

The source adapters expose Modifier, NoteModifier, SubModifier, ScriptedModifier, ModifierType, ModifierOrder and Vector3 imports. ModManager(game) uses an owner-local constructor factory with a live owner check; secondary constructed managers are tracked and released by the scene. Registered custom overrides are real Haxe adapter methods. The compiled subclass fixture proves these overrides; it does not prove arbitrary interpreted class inheritance.

Donor ScriptedModifier:16-93 discovers function-based modifier modules through owner/core Paths resolution. Separate interpreters share the exact initialized gameplay group sharedFields map, bind their modifier as parent/this, load metadata and submods before onLoad(manager,name,prefix,parent), and dispatch position plus note/receptor/noteSplash/sustainSplash callbacks with the actual native object. Callback errors retain script/name/phase attribution and subsequent callbacks remain enabled. Missing or malformed files retain source fallback instances with diagnostics. Rejected duplicate scripts remain manager-owned, so teardown releases them once alongside registered scripts. All owned cleanup is attempted after a release error, bridges and callbacks detach, and the first error is retained for the scene reporter.

The shared transform interleaves builtin families and custom callbacks in the live source order. Registry values delegate to the manager; each resolved builtin entry reads its own instance values even after a cross-kind global-map replacement. Public manager getPos/updateObject uses the same evaluator, supports exclusions and supplied/replacement vector identity, and protects recursive request snapshots. Geometry/visual-time helpers use the source formulas. See [execution contracts](nv-custom-modifier-execution-contracts.md) for sprite mutation, endpoint and centering coverage.

Vector3 exposes the pinned donor math/result-alias API on the existing renderer vector type, using FlxPool in the game and a renderer-free pool in interpreter fixtures. The existing copy extension remains available. Public manager calls do not implicitly return vectors to the pool; source sustain future endpoints retain their separate caller-owned put behavior. Focused tests verify replacement identity, reuse, axes/clone and strict nearEquals. They do not individually certify every vector operation or arbitrary reference retention.

## Focused verification

Root integration acceptance: the final Windows gate passed 2,250 tests across 730 modules in 138.2 seconds, with 345 environment-dependent skips and zero failures (`tmp/nv-custom-modifier-accepted-gate.log`). Native private-owner probes passed two visits each at 60 FPS and unlimited FPS, including registration, shared child values, real note/receptor callbacks, misc updates and receptor writes surviving the native pass. Root reviewed all four captures; seventy protected files were unchanged. Receipt: `tmp/nv-custom-modifier-checkpoint.json`. This does not extend the explicit limits below or claim native splash assertions.

All commands use `.tools/python/python.exe tools/run_tests.py --pattern <module> --jobs 1`:

| Module | Result |
| --- | --- |
| test_nv_custom_modifier_registration.py | 6 tests, 2.1 seconds, no skips/failures |
| test_nv_receptor_generation_lifecycle.py | 5 tests, 0.4 seconds, no skips/failures |
| test_nv_multifield_routes.py | 1 test, 0.2 seconds, no skips/failures |
| test_nightmare_vision_decimal_step.py | 2 tests, 0.7 seconds, 1 existing donor-path skip, no failures |
| test_nightmare_vision_mod_manager.py | 3 tests, 0.5 seconds, 2 existing donor-path skips, no failures |

New executable fixtures cover threshold activation across nonzero values, child retention/deactivation, same-/cross-kind collisions, builtin root rejection before children, pre-existing custom values across dimension growth, custom timeline events, update active gating, actual Iris metadata/imports/receiver restoration and callbacks, module shareables and parse fallback, duplicate ownership, release failure, owner constructor rejection, public path exclusions/vector identity and source batch registration gating. Existing receptor/layout/input/RGB/countdown assertions remain active. The independent renderer owner additionally reports its core four tests and live execution bridge test passing.

## Explicit limits and source inconsistencies

Direct builtin-instance getPos/update callback formulas are not delegated: the gameplay evaluator applies those builtin formulas through the resolved execution entry. Direct calls produce an explicit unsupported diagnostic and remain listed by unimplementedModifierApis. Use of complete donor builtin classes through get(name), arbitrary interpreted subclasses, raw registry structural mutation, and the full donor EventTimeline public surface remain separate gaps. Wider-key complete graphics/layout and the full global draw stack are unchanged limits.

Source ScriptedModifier metadata/destroy calls pass this into the executeFunc parameter-array position, despite its retained Array<Dynamic>/receiver signature. The adapter explicitly calls these as zero-argument receiver callbacks. Source PlayState:1703 passes its scratch vector in getPos's exclusions position; the adapter uses correctly typed exclusions and position parameters. Source ModManager.setValue never sets Modifier.active; the host retains that independent gate. These concrete source inconsistencies are documented resolutions, not blind textual parity.

Before final receptor generation both primary and secondary source managers start with the donor four-key/two-lane defaults and empty registration. Finalization publishes live chart dimensions on those same objects; the additional focused fixture verifies a three-key/five-lane finalization and indexed default values. No donor, chart, mod script or asset content was edited.
