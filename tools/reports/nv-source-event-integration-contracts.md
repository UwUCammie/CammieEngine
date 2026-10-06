# Nightmare Vision source event integration

Accepted bounded EventTimeline integration checkpoint. No donor, chart, mod or asset edits were made. This is a bounded EventTimeline package, not Phase 2 completion.

Pinned source: Nightmare Vision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `funkin/game/modchart/events/{BaseEvent,ModEvent,SetEvent,EaseEvent,CallbackEvent,StepCallbackEvent}.hx`, and ModManager registration/queue methods.

All six event types have actual runtime inheritance and bare/qualified interpreter imports. BaseEvent exposes manager, executionStep, ignoreExecution and finished, with an inherited no-op run. ModEvent retains its constructor-time modifier reference while SetEvent and EaseEvent write through the live manager/name. EaseEvent exposes independently writable endStep, startVal, easeFunc and latched length; direct explicit start values are honored, endpoints retire only afterward, and duration changes are not recomputed. Manager queueEase intentionally omits its accepted start argument when constructing the event, matching source. Named ease resolution returns the actual FlxEase method; supplied callable identity is retained. Existing callable-style support is retained as a host extension to the source string-style queue interface.

ModManager has one public writable timeline. Its deprecated readonly modifierTimeline alias resolves to that same current instance, so replacement does not create a second scheduler. QueueSet/queueEase create real event instances and expand player -1 over current lanes. Unknown names can be queued; SetEvent receives the existing manager diagnostic when run and EaseEvent can throw while capturing a missing modifier. Accepted modifier registration resets its named bucket; same-kind rejection returns before reset. The pure standalone ModchartTimeline remains unchanged except comments now clearly describe its legacy standalone behavior.

Direct callback run invokes the actual callback and marks a one-shot finished only after return. Invalid direct callbacks throw and remain unfinished. Step callbacks invoke through the inclusive endStep. Manager queue callback validation remains an explicit host safeguard. Manager-created timelines inject callback-only containment: a failed CallbackEvent is finished, reported and later events continue. A directly constructed EventTimeline has no reporter and retains source throws; modifier/BaseEvent failures always propagate. No catch-all modifier-event policy was added. Equal-step callback insertion order is not promised because the donor comparator truncates step differences and has no tie breaker.

Manager teardown clears both the current timeline and its initially owned timeline if scripts replaced the public field. This releases pending queue references and makes those schedulers inert. Intermediate script-owned replacements that are no longer current remain script-owned. Scheduler arrays/maps and finite raw mutation semantics are documented and compared separately in `nv-event-timeline-contracts.md`. No PlayState clock or dispatch placement changed.

## Focused evidence

Commands: `.tools/python/python.exe tools/run_tests.py --pattern <module> --jobs 1`.

- `test_nv_source_events.py`: 4 passed in 2.3s, no skips. Real Iris imports and constructors/inheritance; direct callback failure state; captured modifier/live replacement writes; mutable Ease fields and callable identity; queue omission; accepted/rejected registration; authoritative timeline replacement; original/current teardown; callback-only containment and propagated modifier failures.
- `test_nv_custom_modifier_registration.py`: 6 passed in 2.6s, no skips.
- `test_nightmare_vision_modchart_core.py`: 4 passed in 0.5s, no skips; pure standalone timeline preserved.
- `test_nightmare_vision_mod_manager.py`: 1 passed in 0.6s; 2 existing content-dependent fixtures skipped because their selected donor/owner paths are unavailable. Existing actual timing, seek, argument, error and teardown assertions remain, with source comparator/unknown-queue expectations corrected.
- Peer `test_nv_event_timeline_contract.py`: 1 passed in 0.2s, no skips; full pinned scheduler compared across finite mutation scenarios.

Total: 16 passed and 2 existing skips across five modules. Arbitrary interpreted event subclass inheritance remains unverified; compiled virtual dispatch and actual six imported classes are supported. Native gameplay and full canonical verification passed as recorded below.

## Root acceptance

The canonical Windows gate passed 2,260 tests across 734 modules in 175.8 seconds, with 345 skips and zero failures (`tmp/nv-event-timeline-accepted-gate.log`). Binary SHA256: `2DFA97B6DC5DF1C3DC0D0F8A0A8A7FFB2E301362392AE9A9DC31F85A2EDC182F`.

Muted private two-visit checks passed at 60 FPS (`7d6598a3`, 140.664 seconds) and unlimited FPS (`592d0649`, 142.614 seconds). Each run produced both assertions twice: imported direct event behavior/live schedules/cleanup, and a callback on the native gameplay source clock. Root reviewed all four captures with notes, receptors, HUD and scene visible. All 70 protected files remained unchanged; both donor Git trees are clean. Logs: `tmp/nv-event-timeline-native-60.log`, `tmp/nv-event-timeline-native-unlimited.log`. Receipt: `tmp/nv-event-timeline-checkpoint.json`.

The first full suite rejected an old strict fractional-order expectation. The corrected decimal-step fixture compiles the full donor EventTimeline and compares exact order and firing times at 60/240/480 FPS. It retains BPM, offset, seek, never-early, no-miss and no-repeat assertions; its one-frame bound uses the donor's sorted-prefix blocking frontier. Production code did not change after the native binary was built. This is source behavior, not a relaxation to hide missing callbacks.

These checks do not complete Phase 2 or certify arbitrary callback class declarations. Source inspection found no executable ordinary class-declaration runtime in the supplied Psych/NV callback dialects; separate compiled-module support remains distinct. The next confirmed source gap is NV SustainSplash lifecycle, proposed in `tmp/nv-sustain-splash-next-proposal.md`.
