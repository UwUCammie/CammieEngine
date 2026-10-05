# Psych opening visibility and scene API checkpoint

Verified locally on 5 October 2026 after v0.0.13, with GPT-6 Luna at Max reasoning. The supplied Psych source (`5c67ced`) and its Note receptor-following behavior establish the alpha contract. Source reflection-array conversion is also compared with Psych `2dfa27773a3668e0c1b043a3fb4348942c8a6fb3` and llua `46425aeccdd1d76e65782613a0710f96786c8b4c`.

## Implemented boundary

Psych moving notes now follow the alpha of their actual side/lane receptor, multiplied by multAlpha; sustain tails retain the source 0.6 multiplier. copyAlpha=false preserves explicit script control. Base, Nightmare Vision and Codename presentation paths retain their own behavior.

The general Lua translator now handles function-valued tables, returned closures, literal string keys including empty strings, table argument call syntax, and legal Lua identifiers that conflict with HScript keywords. Ordered table evaluation and nil/fallback behavior are preserved. Embedded Haxe placeholders remain unique across multiple runHaxeCode calls.

Psych source getters return fresh one-based Lua array snapshots while native HScript arrays retain their existing indexing. The scene exposes the shared modchartSprites registry, source actor-layer insertion helpers, default singAnimations and icon changeIcon routing. Embedded HScript-created actors are visible to subsequent Lua callbacks through the same registry.

All production changes are engine/compatibility APIs. Donor mod/chart files were not changed and no mod/song names were added as production behavior switches.

## Validation

Windows build and canonical run.bat test passed 2,212 tests across 713 modules in 142.9 seconds; 345 skipped, zero failed. Focused tests exercise alpha opt-out/recovery/sustain/mode isolation, Lua closures/table evaluation, source API array snapshots, registry identity and actor ordering.

The final getter-order wiring assertion was added after the full suite discovered its modules; its complete focused module passed 3/3 tests with zero skips afterward. Native Lua assertions also verify the effective installed getters on both scene entries at both caps.

Muted native checks of the reported opening passed at 60 and unlimited FPS, each over two song entries: both source-created wizards are alive, animated and correctly layered; enemy notes stay hidden during the opening and recover afterward. Opening captures were inspected. Related Nightmare Vision native sanity checks passed at both caps. 70 protected donor/import/settings hashes remain unchanged. Receipts, source/binary hashes and captures are recorded in tmp/psych-opening-checkpoint.json.

## Remaining scope

These checks certify the opening/reveal routes, not every later scripted event or full-song fidelity. Computed Lua constructor keys, exhaustive language parity, mutable singAnimations consumption by core hit/miss routines, and the source allowGPU cache policy remain open. The roadmap's broader Phase 2 acceptance gate remains unfinished. No release was published.

The follow-up report about the health bar and notes moving away expands the pending scope to composite HUD transforms and note positional following. This checkpoint certifies actor creation and note opacity; it does not certify those positional contracts.

The positional follow-up is verified within the boundary described in `psych-hud-contracts.md`; this earlier receipt remains unchanged.
