# Psych Alphabet integration contracts

Development v0.0.16 replaces the Psych-only native Alphabet alias with the actual source Alphabet, AlphaCharacter, Alignment enum and AttachedText classes. Native, Codename and Nightmare Vision aliases retain their existing routes. Core geometry, glyph animation and group recycling comparisons are recorded separately in `source-alphabet-contracts.md`.

## Connected source routes

`SourceNativeClassScope` keeps actual Class and Enum identities. Interpreter field reads/writes, explicit Reflect/Type imports, resolved Reflect/Type class methods, extracted reflection callables and Type.createInstance reach the same owner scope. Canonical source runtime names are returned for registered classes/enums. Haxe secondary-module imports remain distinct from runtime type names: `objects.Alphabet.AlphaCharacter` is an import, while `objects.AlphaCharacter` is the Lua/runtime class name. The latter does not manufacture a flat Haxe import.

The Psych Lua reflection overlay shares the same generic scope for getPropertyFromClass, setPropertyFromClass, callMethodFromClass and createInstance. Embedded runHaxeCode uses the real SourceIrisBridge preset installer and the captured Paths facade. Bare `allLetters` is not introduced. Ordinary reflection and type operations delegate to their native implementations; class schemas and object identities remain actual typed native objects.

The scoped map preserves explicitly authored null values. Regular static loader methods reject reflective writes without throwing, matching the generated Windows C++ __SetStatic and pinned hxcpp Class_obj::__SetField implementation. Haxe eval alone differs here and permits mutation of regular static functions; the connected test therefore also inspects the actual generated C++ setter. Native delete behavior is retained. The loader has stable function identity within an owner and distinct identity between owners.

## Owner and lifecycle

`PsychAlphabetRegistry` follows the existing primary Psych ClientPrefs lease. A primary owner transition, including transition to null, releases all contexts. Same-owner retries preserve metadata and loader identity. Dependency owner contexts coexist until that transition. Each interpreter has its own class scope; releasing one interpreter or Lua overlay does not release another scope or the shared metadata context.

Cached static loader calls follow the latest shared owner IO view; they do not capture the library view of the interpreter which first stored the method. The connected fixture executes the complete pinned donor AlphaCharacter loader, caches it with Paths IO A, selects IO B, then calls the cached method and verifies B metadata. The host case retains the same owner-local method identity and follows the most recently configured owner view. Static map reads/writes, loader retrieval and construction from an earlier interpreter do not rebind IO. Registry.get during scope setup selects the shared owner view for this bounded checkpoint. The paused call-preparation experiment was removed.

New contexts explicitly load default metadata once, corresponding to the source Language/Title bootstrap. Constructors do not implicitly repair or reload the map. Scope setup may rebind the shared resource view while preserving all authored mutations. IO closures capture the Paths facade and preference object instead of the PlayState. The exact stock Alphabet PNG/XML/JSON defaults use the engine-owned immutable source copies; owner channels win independently, matching the donor Paths atlas lookup. Custom paths use the captured owner facade and are not rewritten to the host font.

## Focused verification

`python -m unittest discover -s tools/tests -p test_source_alphabet_integration.py`: 4 passed in 2.15 seconds, no skips. These execute actual typed classes and Iris, the actual Lua reflection overlay, the extracted real embedded preset, captured IO and C++ generation. They cover actual constructors/class and enum round trips, same-owner and cross-owner state, static reads/writes/load calls, null-map preservation, extracted/alternative reflection paths, native regular-method write/delete behavior (both donor and adapter C++ setter inspection), cached-loader latest shared IO behavior compared with the complete donor, independent scope teardown and primary session transitions.

Combined connected and adjacent command `python -m unittest test_source_alphabet_integration test_psych_reflection_bindings test_psych_hscript_countdown_preset test_source_hud_bar_integration test_psych_property_paths test_psych_runtime_bindings test_source_attachment_integration` (PYTHONPATH=tools/tests): 16 cases in 6.53 seconds, 15 passed and 1 existing donor-location skip. Related fixture maintenance preserves prior behavior assertions: test_psych_reflection_bindings (1 passed), test_psych_hscript_countdown_preset (1 passed), test_source_hud_bar_integration (2 passed), and test_psych_property_paths (4 passed, 1 existing donor-location skip). Their Alphabet dependency seams are explicitly inactive; actual source routes are exercised in the connected integration fixture.

Canonical build/full suite and native component acceptance passed the bounded root-owned gates recorded below. Private probes are prepared in `tmp/source-alphabet-a-native.hx` and `tmp/source-alphabet-b-native.hx`; no game was launched by this implementation agent.

## Limits

This checkpoint does not complete Phase 2 or port full source menus, Language localization, arbitrary interpreted subclasses or all Flixel parent behavior. Type.getInstanceFields still exposes actual host implementation details such as the owner context seam; this is not a claim of identical private metadata. Shared global Paths.currentLevel mutation semantics across owner facades require separate source-derived work; setup-time resource rebinding is not full per-facade global state parity, and this package does not expand PsychOwnerPaths global state. Type.createEmptyInstance delegates to native empty allocation without owner/context initialization and remains an explicit open initialization contract. The verified constructor routes are ordinary new, Type.createInstance and Lua createInstance. Unscoped native AlphaCharacter static loading requires an explicit context and reports a diagnostic otherwise. The donor recycle(AlphaCharacter, true) argument conflicts with both pinned Flixel 5.6.1 and host 6.1.2 signatures; the core adapter uses an explicit owner factory and force flag, as recorded in the core report.

## Integrated acceptance

Accepted bounded Psych 1.0.4 Alphabet/AlphaCharacter/Alignment/AttachedText checkpoint, development 0.0.16, 6 October 2026. Canonical Windows build passed (`tmp/source-alphabet-build-final.log`). Full suite passed 2291 tests across 750 modules in 137.6 seconds, 345 reported skips, zero failures (`tmp/source-alphabet-full-tests.log`). Actual Iris and Lua/embedded reflection routes use native classes and owner metadata.

Muted private Tutorial component checks passed two visits at 60/unlimited FPS. Four named markers each occurred twice; explicit metadata initialization and retained-metadata markers each occurred once per run. Root reviewed four captures showing normal multiline glyphs and bold tracked text. Raw receipts have two nonempty framebuffer readbacks with backend cap 60 or zero. Gated executable/lime hashes match export/private runtime. Seventy protected files stayed unchanged; private chart/options/version/tag were restored to verified v0.0.15 ZIP bytes, and temporary inputs removed. Stock font assets are byte-identical donor copies; owner metadata variants are generated private probes. This is controlled source-class evidence, not full-chart/menu or NV Alphabet acceptance.

- Psych 60 FPS: `source-alphabet-psych-ab516f75`, 27.411 seconds, two visits.

- Psych unlimited FPS: `source-alphabet-psych-4004fa3e`, 27.406 seconds, two visits.

Receipt: `tmp/source-alphabet-checkpoint.json`. NV Alphabet/typewriter, full menus/Language, empty-instance initialization, shared per-owner currentLevel, wider private/inherited parity and Phase 2 remain open. No original mod/chart changes or v0.0.16 publication.
