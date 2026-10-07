# NV family publication and source configuration, 0.0.16 development

This checkpoint extends the import availability work without changing donor
charts, scripts or media. Pending packages remain unavailable; unrelated fully
published packages remain playable during background imports.

## Implemented scope

The v2 family catalog binds package labels, exact retained source paths and
installed namespaces to one authenticated source snapshot. The staged importer
publishes configured siblings with runtime files even when they contain no
charts. It copies their package-local metadata and creates no artificial
Freeplay rows. Changed-source recapture reuses a namespace only after validating
the old and new source relationships under the same import record. NV importer
revision 4 regenerates older imports from retained sources through the existing
transaction and conflict-preservation rules.

Source configuration now has a typed application core and a native host.
Selected-package options, title, icon, RPC identity, font and UI prefixes follow
the pinned donor's application order and partial-failure semantics. A shared
Discord backend owns SDK commands on its existing daemon. Native configuration
restores prior title, icon and RPC identity when the owner retires.

Source ModOptions and ModOption share an owner-private live service, including
selected-package save isolation, ordering, validation, callback-bearing settings
and source-shaped construction. Failed save binding cannot flush another
package's save. Failed final persistence still retires option handles and
restores native configuration. Persistent and current-song Paths receive the
same selected configuration without accumulating old scene references.

Transition values are assigned to the source session and exposed through the
source enum. This does not execute the complete source state factory, TitleState
or scripted transition lifecycle. Those remain the next coherent work package;
see [the source-state audit](nv-source-title-transition-contracts.md).

## Verification

- Final Windows build: `tmp/nv-family-config-build-final.log`.
- Related config/options/path/RPC checks: 24 tests, zero skips, 9.588 seconds
  (`tmp/nv-mod-config-related-focused-final.log`). The corrected stage seed
  fixture also passed its four checks.
- Importer contracts: 67 tests, three environment-dependent skips, 51.97
  seconds; revision/catalog rerun: eight tests, 3.50 seconds. Tests exercise
  transaction publication, changed-snapshot namespace reuse, chartless siblings,
  metadata/core ownership and manager lifecycle.
- Final full suite: 2,374 tests across 774 modules in 312.4 seconds, 343 existing
  platform/corpus skips, zero failures
  (`tmp/nv-family-config-full-tests-final.log`). Windows native filesystem
  import/recovery fixtures passed.
- The first full run exposed three stale fixture contracts and two manager
  checks that exceeded their existing timeouts with eight workers. Fixtures
  were repaired. Both manager checks and the full manager module passed
  serially; the complete suite then passed with four workers, without changing
  cases, timeouts or skips. Scheduling contention is a possible explanation,
  not an established diagnosis or a speed improvement.
- Muted native family/config/options component probes passed two visits each
  at 60 FPS and unlimited FPS. They exercise actual window/icon/font effects,
  live callbacks, save isolation, selected/borrowed assets and teardown.
  Runner logs: `tmp/nv-family-config-native-60.log` and
  `tmp/nv-family-config-native-unlimited.log`. Four captures were reviewed.
  These generated probes construct an authorized family session directly;
  they do not certify the complete native importer-to-title pipeline.
- Required donor audit passed (`tmp/nv-family-config-source-audit.log`). All
  70 protected inputs retained their hashes. The 23 development/API policy
  checks passed (`tmp/nv-family-config-policy-final.log`). Runtime hashes and
  bounded evidence are recorded in `tmp/nv-family-config-checkpoint.json`.

## Remaining scope

Phase 2 stays open. Complete source Init/state-factory ownership, built-in and
scripted states, TitleState/reset/transition ordering, and clean whole-chart
family-switch acceptance still need implementation and native verification.
Independent retained snapshots are not joined by matching names or parents.
Missing config/runtime outputs do not authorize a family member.

The RPC checks use a fake SDK driver and native compilation; external Discord
connection acceptance is not claimed. Invalid/null option-setting edge cases,
complete source profile/core semantics and broader platform behavior remain
open. Large-library refresh latency still needs measured profiling. No graphics
quality reduction, chart/mod-specific production branches or release publication
is part of this checkpoint.
