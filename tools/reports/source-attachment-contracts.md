# Typed source attachment contracts

Development 0.0.16. Core classes and focused fixtures are frozen; connected imports/factories, canonical build and native acceptance remain pending. This is a bounded source attachment API checkpoint, not full menu, Alphabet, inherited sprite or Phase 2 parity.

Pinned sources: Psych 1.0.4 `5c67ced49e5a98535298a6daa3f8f4ec79ac8399`, complete `source/objects/AttachedSprite.hx`; NightmareVision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, complete `source/funkin/objects/nodes/AttachedNode.hx` including its secondary AttachedSprite class.

`PsychSourceAttachedSprite` is an actual FlxSprite. Its four public source constructor arguments retain static-image or Sparrow-prefix loading, parent-folder forwarding, idle animation at 24 FPS with authored loop, preference antialiasing and zero scrollFactor. A fifth host-only owner dependency captures image/atlas/preferences for the selected interpreter. Construction consumes this dependency without retaining an owner reference. Missing host owner is an explicit diagnostic. The anim branch still requests the atlas if file is null, as the donor does. After parent update, a live sprTracker supplies position and scrollFactor; copyAngle/copyAlpha default true and copyVisible false. Disabled flags and null tracker preserve previous values.

`NightmareVisionAttachedNode` is an actual FlxBasic with nullable public FlxObject root/tracked pointers and pinned FlxAxes. It preserves each selected axis, visibility/angle/alpha defaults, pooled offsets and source after-parent update order. Alpha copying requires both borrowed objects to be actual FlxSprite instances. It does not copy scrollFactor. The node destroys only its offset; root/tracked remain borrowed and their public pointers are not cleared by an invented disposal policy. `NightmareVisionAttachedSprite` is an actual FlxSprite with a writable typed attachedNode; it owns its current node, updates it after parent sprite update and destroys it before parent destruction. Null tracker remains valid. No extra idempotence or destroyed-object guard was introduced.

The donor's secondary module type is `funkin.objects.nodes.AttachedNode.AttachedSprite`; source files import the primary module then use the secondary short name. Connected binding tests must prove this module surface and separate Psych/NV short aliases. Core classes use `@:keep`; C++ generation verifies reflective exports for tracker/offset/flags and node pointer fields. NV node retains source `@:nullSafety` and real FlxAxes, whose X/Y/XY/NONE values and x/y getters are not replaced with generic bit tests.

Focused command: `.tools/python/python.exe tools/run_tests.py --jobs 1 --pattern test_source_attachment_contract.py`. One fixture passes in 0.5 seconds, zero skips/failures, executing eval and C++ generation with `-D no-compilation`. It compiles complete immutable donor classes alongside actual host classes, changing only packages/class names/import wiring and override visibility for the fixture.

Comparisons cover five Psych constructor cases with exact owner logs, empty/static/animated/null-file construction, parent folder, loop, AA and native animation fields; forty tracker flag cases; null trackers; image/atlas failure ordering; 128 NV combinations of axes, flags and actual object/sprite types; root/tracker replacement, null pointers, borrowed teardown and pooled-offset return; wrapper update/ownership and reflection. Instrumented parent updates pin the live pointer reads after parent callbacks. Existing actual pinned animation add/play/frame callbacks, FlxSignal, FlxSprite alpha setter and complete FlxAxes execute in the reusable fixture. Typed FlxObject positional dependencies, parent callback instrumentation and atlas frame-selection helpers are native-shaped fixture support, not a complete Flixel renderer or atlas parser. Offset pooling return is instrumented; native pool/context behavior remains part of the gate.

Reusable support is `source_attachment_fixture_support.py:attachment_fixture_files()`. Connected fixtures should use real classes and interpreter import/constructor paths, not substitute short-name shape stubs. Native checks must establish actual display-list updates, animated owner loading, per-axis/flag effects, borrowed-object lifetime and visible copied/uncopied references at 60/unlimited FPS. Secondary imports, Psych AttachedText/Alphabet, whole source Controls/Credits/options state restoration, arbitrary atlas visuals and full inherited behavior remain outside this core proof.

No full build, full suite or native launch was run by this agent. No donor, mod, chart or authored content changed. No roadmap completion claim is made.

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
