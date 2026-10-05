# Nightmare Vision source field construction checkpoint

Verified locally on 5 October 2026, after v0.0.13. This bounded package does not complete Phase 2. Source contract: Nightmare Vision revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `funkin.objects.note.PlayField` constructor and owner scene lifecycle. Implementation subtasks used GPT-6 Luna with Max reasoning.

## Implemented boundary

Bare and imported PlayField constructors resolve the matching live owner through the existing interpreter constructor registry. Local shadowing and other compiled class identities retain their normal behavior. Arguments preserve source defaults and independent player, playerControls, isPlayer and CPU flags. Native receptor-bank identity is separate from the source player number.

Constructed fields start with no receptors and are absent from the display/field collection. Explicit generation creates the supported receptor layout; explicit collection insertion attaches its native bank. Injected skin identity remains live during rendering and later skin changes. Every constructed field is scene-owned, including fields never attached to a collection. Unsupported wider-key and quant behavior retains a useful diagnostic rather than silently claiming parity.

Production changes are confined to compatibility/engine code: `NightmareVisionFieldConstructor`, `NightmareVisionPlayFieldBindings`, and PlayState integration. No chart/mod name checks or donor edits were added.

## Validation

- Executable focused tests exercise real Iris constructor resolution, owner replacement/isolation, local shadowing, raw argument forwarding, defaults/validation and extracted host construction with native hook fixtures.
- Canonical `run.bat test` built Windows and passed 2,199 tests across 703 modules in 148.8 seconds; 346 skipped, zero failed. Log: `tmp/nv-field-construction-tests.log`.
- Muted native checks passed at 60 and unlimited FPS, with background dim disabled. Both visits verified construction, empty/unattached state, independent flags, injected skin, generation, collection attachment/removal, field mutations and note membership. First-visit keyboard checks passed 128 assertions and 32 press/release callbacks; they are not second-visit keyboard certification. Unlimited input recorded 24 updates within the same millisecond.
- Final captures were inspected. Twenty-nine protected donor/import/settings hashes remained unchanged. An initial eight-second probe timed out before the source intro/input checks; the longer probe passed without engine changes. That failure remains recorded.

Exact binary/source hashes, native receipts and limitations: `tmp/nv-field-construction-checkpoint.json`. The refreshed `script-api-coverage.md` is a static inventory and is not a behavioral coverage percentage.

## Remaining contracts

Full source PlayField group/reflection, splash/underlay APIs and destruction timing remain open, as do quant receptor coloring/reload, wider-key layouts, physical controller checks and full hold/release lifecycle. Native probes are bounded constructor/input checks rather than exhaustive song or pixel-fidelity certification. No release was published for this checkpoint.
