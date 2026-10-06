# Nightmare Vision EventTimeline queues

Accepted bounded EventTimeline checkpoint: canonical Windows build, full regression suite and native checks passed. Phase 2 remains unfinished.

Pinned source: `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `source/funkin/game/modchart/EventTimeline.hx`. No donor, chart, mod or asset content was edited.

`NightmareVisionEventTimeline` exposes writable live `modEvents` and `events` containers. `addMod` replaces the named queue unconditionally. `addEvent` uses actual ModEvent inheritance, preserves object identity, deduplicates in the selected array, and applies the source integer-difference comparator. `update` traverses current map keys, then the callback array, using the donor live cursor and removal by event identity. It invokes virtual run methods without callback-only assumptions or a separate value scheduler. Public array replacement takes effect according to the donor schedule-reference boundaries; recursive updates and authored raw mutations are not normalized.

Default construction preserves source exceptions and unfinished event state. A gameplay owner may explicitly supply a reporter: only CallbackEvent subclasses then receive the existing host policy of marking failures finished, reporting once and continuing. BaseEvent and ModEvent errors still propagate. Reporter failures are contained. This callback policy is an explicit source deviation, not donor parity. Owner destruction is also a host lifecycle safeguard: held queue arrays and maps are cleared, pending events marked finished, updates become inert and new enrollment is rejected.

Focused command: `.tools/python/python.exe tools/run_tests.py --jobs 1 --pattern test_nv_event_timeline_contract.py`. One executable fixture passed in 0.2 seconds, with no skips or failures. It compiles the full pinned donor timeline and the actual host timeline against the same lightweight event dependencies, then compares 12 finite scenarios: unconditional reset, identity deduplication, fractional ordering, ModEvent classification, modifier-before-callback order, BaseEvent no-op retention, ignored/finished entries, raw map/array replacement, callback insertion and reordering, self-removal, recursive update, array replacement during dispatch, mutable modName, thrown errors and bucket removal during iteration. Separate assertions validate callback-only containment and teardown with externally retained container references.

The fixture isolates queue behavior with small BaseEvent/ModEvent/CallbackEvent carriers. Real source-shaped event constructors, EaseEvent captured modifier state, owner manager wiring, interpreter imports and native behavior require the peer integration checks and parent gate. Map ordering is the actual Haxe Map behavior on both sides; the implementation does not impose registration order or promise a portable order between distinct modifier names.

## Root acceptance

The canonical Windows gate passed 2,260 tests across 734 modules in 175.8 seconds, with 345 skips and zero failures (`tmp/nv-event-timeline-accepted-gate.log`). Binary SHA256: `2DFA97B6DC5DF1C3DC0D0F8A0A8A7FFB2E301362392AE9A9DC31F85A2EDC182F`.

Muted private two-visit checks passed at 60 FPS (`7d6598a3`, 140.664 seconds) and unlimited FPS (`592d0649`, 142.614 seconds). Each run produced both assertions twice: imported direct event behavior/live schedules/cleanup, and a callback on the native gameplay source clock. Root reviewed all four captures with notes, receptors, HUD and scene visible. All 70 protected files remained unchanged; both donor Git trees are clean. Logs: `tmp/nv-event-timeline-native-60.log`, `tmp/nv-event-timeline-native-unlimited.log`. Receipt: `tmp/nv-event-timeline-checkpoint.json`.

The first full suite rejected an old strict fractional-order expectation. The corrected decimal-step fixture compiles the full donor EventTimeline and compares exact order and firing times at 60/240/480 FPS. It retains BPM, offset, seek, never-early, no-miss and no-repeat assertions; its one-frame bound uses the donor's sorted-prefix blocking frontier. Production code did not change after the native binary was built. This is source behavior, not a relaxation to hide missing callbacks.

These checks do not complete Phase 2 or certify arbitrary callback class declarations. Source inspection found no executable ordinary class-declaration runtime in the supplied Psych/NV callback dialects; separate compiled-module support remains distinct. The next confirmed source gap is NV SustainSplash lifecycle, proposed in `tmp/nv-sustain-splash-next-proposal.md`.
