# NV runtime skins and Psych countdown checkpoint

Verified locally on 5 October 2026, after v0.0.13. This bounded package does not complete Phase 2. Implementation subtasks used GPT-6 Luna with Max reasoning. Source contracts: Nightmare Vision revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `funkin.data.NoteSkin` and `NoteUtil`; Psych revision `5c67ced`, HScript preset and `backend.BaseStage.Countdown`.

## Implemented boundary

Nightmare Vision scripts receive the actual runtime NoteSkin class through the existing owner-local Iris constructor registry. Bare/imported constructors preserve source keys and player ID, type identity and local shadowing, and resolve the current owner rather than retaining a destroyed scene. Defaults are filled in place and only for null values. Authored blank values remain distinct from missing values. Missing skin JSON and JSON null use source defaults; malformed data and escaped owner paths produce diagnostics. Negative vector sizes, including the donor constructor's omitted-key default, remain errors.

Runtime texture names, animation tables, colors, sing animations and independent typed per-key offset vectors are live. Skin reloads refresh native frames, scales and existing RGB palette copies without compounding scale or losing alpha/flash state. Rendering reads the field's current skin and offset vectors; caches are keyed by actual field identity, so duplicate or changed public IDs do not redirect a field to another skin. Destroying a field releases its renderer and captured callbacks; plain collection detachment retains its live renderer. Texture changes invalidate their own prewarm cache, preserving unchanged atlas reuse. Shared Psych RGB graphics remain the rendering foundation.

Psych plain HScript and Lua's embedded HScript now receive the real source Countdown enum, including THREE, TWO, ONE, GO and START. Qualified import and local shadowing use the existing shared interpreter machinery. NV does not receive an invented Psych preset.

Production changes are confined to engine/compatibility code. No mod/chart name branches or donor edits were added.

## Validation

- Focused executable tests use real Iris constructor/type resolution, the production skin adapter with controlled atlas/rendering fixtures, actual typed offset vectors and extracted host ownership/skin wiring. They cover mutable scales/palettes/frames, source defaults, independent owners, A→B→A reloads, live offsets after ID/skin mutation, alpha preservation and renderer cleanup. The existing animation/dense-note/scroll fixtures were updated to the new production interfaces.
- Canonical `run.bat test` built Windows and passed 2,203 tests across 707 modules in 130.5 seconds; 345 skipped, zero failed. Log: `tmp/nv-skin-countdown-tests-final.log`. The earlier three fixture failures remain recorded.
- Muted NV native probes passed at 60 and unlimited FPS over two scene visits, checking constructor identity, skin isolation, runtime scales/colors, cached shader refresh, live note/vector reload, duplicate/mutable field IDs and renderer callback release. First-visit keyboard checks passed 128 assertions and 32 press/release callbacks; second-visit keyboard input is not certified by that probe.
- Muted Psych native probes passed at both caps for plain and embedded Countdown presets. Background dim was disabled and private save namespaces used. Captures were inspected; 29 protected donor/import/settings hashes remained unchanged.

Exact current binary/source hashes and native receipts: `tmp/nv-skin-countdown-checkpoint.json`. `script-api-coverage.md` remains a static exposure inventory, not a behavioral coverage percentage.

## Remaining contracts

Full PlayField group/reflection and splash/underlay APIs, quant receptor coloring/reload, wider-key/pixel-sheet geometry, physical controller checks and full hold/release lifecycle remain open. Exposing source splash fields is distinct from completing their native group/effect behavior. Source NoteSkin.destroy is a donor no-op; the host retains atlas cache ownership. Native probes do not certify exhaustive scene-resource cleanup, every chart or pixel equivalence. No release was published.
