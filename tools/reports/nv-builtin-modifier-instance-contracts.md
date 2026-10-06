# Nightmare Vision builtin modifier instances

Status: accepted Windows, regression and bounded native checkpoint. This checkpoint follows the accepted custom registration/execution package; it does not complete all Nightmare Vision APIs.

The pinned Nightmare Vision classes under `funkin/game/modchart/modifiers` are exposed as real source adapters, including constructor arguments, class identity, order, submodifier maps, public helpers, and retained construction state. ModManager now creates those same classes for default registration. Ordinary children and `noteSpawnTime` are real MISC SubModifier instances with inherited identity position and no-op object callbacks, rather than named builtin formulas.

Ordered execution calls the actual instance's virtual methods. A compiled subclass override is therefore respected. Each builtin override delegates to the renderer/transform's shared single-leaf math; direct calls skip manager activation, base-position initialization, whole-chain execution, centering, sprite positioning, skin offsets and hitbox ownership. Constructors do not implicitly register instances. Reverse resolves live bank lengths; Rotate retains the caller origin; Path retains source point references and retracing state; Perspective and ReceptorScroll retain construction latches. Alpha uses its live static fade distance. The source-only chart key provider supplies indexed submodifier construction.

Native receptors and effects expose one persistent mutable baseline through baseScale/defScale. Successful NV skin application refreshes receptor/splash baselines without recapturing transformed scale every frame. Generic hold-cover construction captures its loaded baseline. Splash/cover noteData aliases refer to their actual direction. Effect RGB facades are actual per-sprite graphics, whose uniforms are applied when drawn; source splash skin reload preserves RGB identity, alpha and flash while refreshing palette and inEngineColoring. Lazy generic effect coloring starts disabled, so a facade does not recolor authored textures. PlayState's source visual bridge now recognizes both effect kinds. Native/Psych paths retain their existing rendering and alpha ownership unless an NV facade is explicitly used.

Note.garbage is reflected and cleared during NV fresh rating initialization; ReceptorScroll can set it. Pinned donor writes do not imply a general disposal pass. The host hold cover is not a full NV SustainSplash.watchTail implementation, so that missing consumer remains a separate gap.

## Focused evidence

All commands use `.tools/python/python.exe tools/run_tests.py --pattern <name> --jobs 1`:

- `test_nv_builtin_modifier_instances.py`: 4 passed, 1.6s. Actual Iris builtin imports/constructors; real children/no-ops; source state/helpers/direct calls; compiled virtual overrides; extracted actual native baseline and RGB draw methods.
- `test_nv_custom_modifier_registration.py`: 6 passed, 2.5s. Existing live identity, collision, activation, teardown and owner interpreter contracts.
- `test_note_rating_shape.py`: 1 passed, 0.2s. Includes bounded NV garbage reset.
- `test_nightmare_vision_note_skin_runtime.py`: 1 passed, 0.6s. Actual skin adapter with rendering stubs, stable baselines, preserved RGB state and coloring flags.
- `test_nightmare_vision_note_skin_wiring.py`: 2 passed, 0.2s.
- `test_nv_rgb_beat_zoom.py`: 1 passed, 0.2s.

These 15 tests have no skips. The peer's shared-leaf comparisons, execution bridge and pure core fixtures are recorded separately in `nv-builtin-modifier-leaf-contracts.md`. No full build or native launch was performed by this owner.

## Scope and limits

Builtin imported constructors run through the real Iris binding, but arbitrary Iris class inheritance is not certified. Compiled Haxe subclass overrides are verified. EventTimeline source-class APIs remain separate. Generic hold covers keep their existing pooling/end-time lifecycle; full source sustain-splash construction, skins and tail watching are not supplied by these aliases. This package does not establish arbitrary skin visual parity.

Shared direct evaluation currently creates a temporary object per request. This protects recursive evaluations and keeps callbacks independent, but allocation/caching optimization belongs to a later performance package. It is not a source allocation parity claim. Standalone headless managers use a default viewport for constructor-only tests; gameplay owners provide the live source viewport/preferences and current constructor context.

Canonical Windows build and all 2,255 tests across 732 modules completed in 157.0 seconds (345 skipped, zero failed). Evidence: `tmp/nv-builtin-instance-accepted-gate.log`.

## Root native verification

The Windows binary built successfully. Muted private two-visit probes passed at 60 FPS (`59fb511f`, 136.696 seconds) and unlimited FPS (`5145056c`, 135.214 seconds). All four assertions appeared twice: source registration identity/children, live ordered callbacks, direct imported constructors/vector/path/no-op behavior, and native receptor scale without position/origin/offset changes. Root reviewed all four captures; notes, receptors, HUD, scene and visualizers remained visible. The 70-file protected baseline was unchanged after both runs; both donor Git worktrees remain clean. Logs: `tmp/nv-builtin-native-60.log` and `tmp/nv-builtin-native-unlimited.log`.

Native direct splash callbacks are not separately asserted. Extracted native effect methods and headless four-kind formula tests cover the bounded aliases; full source sustain-splash lifecycle remains open. These gameplay captures are not a performance benchmark.

The first canonical suite exposed a shared-stub collision in the existing quant fixture. The fixture now reuses the shader declaration and extends the new RGB stub at a stable constructor anchor; all original quant assertions remain. Its focused checks pass. The final full-suite rerun passed: 2,255 tests across 732 modules in 157.0 seconds, 345 skipped and zero failed (`tmp/nv-builtin-instance-accepted-gate.log`).
