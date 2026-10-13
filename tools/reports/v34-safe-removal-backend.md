# v0.0.34 safe removal backend evidence

The removal backend is implemented in `ImportRemovalTransaction.hx`, with provenance-based aggregate partitioning in `ImportRemovalPartition.hx`. The asynchronous UI wrapper is owned separately. No real installed mod or donor was removed during these backend tests.

## Ownership and publication

- Preview reads the complete receipt-validated retained inventory and installed chart/namespace provenance. Legacy, ambiguous, locally edited, dependent and protected bundled packages fail closed. Unclaimed local files under a selected namespace/chart/audio directory block removal before publication.
- Confirmation must hold `ImportRefreshManager.reserveForRemoval`; execution rereads the inventory and checks the reviewed transaction versions, candidate hashes, shared claims and snapshot references.
- Ordinary aggregates can remove one independently attributable root. Selected namespace/chart/audio outputs are removed; unattributed/common outputs remain with survivors. Surviving receipts retain verified file digests without copying payloads. Registry reconciliation uses the existing three-way helper and preserves surviving entries/category names.
- Receipt-authenticated v2/v3 Nightmare Vision member catalogs can be partitioned. Shared core providers remain protected while members need them. A final family removal can include a virtual receipt-authenticated core root with no materialized namespace. Removed source roots persist in the survivor record and constrain subsequent scanning and family enumeration/publication.
- `LibraryIdentityArchive` preserves authored identity/fingerprint and chart destination reservations. User saves, scores, favorites, categories, difficulty preferences, settings and original donor folders are outside the deletion map.

## Recovery and private cleanup

The private preparation journal is durable before payload backup copying starts. Live publication retires selected state scopes into per-transaction quarantine and journals candidate removals, registry changes and retained pointer changes. A receipt is the commit point; its removal journal digest prevents an edited committed journal from authorizing cleanup.

Before commit, recovery verifies original retained manifest text, its original receipt, scope/selected-owner relationships, file claims and backup locations. It restores retired scopes and rolls back file operations. A surviving replacement scope can be removed only if its files exactly match the explicitly prepared metadata map. New or edited local files are preserved with a recovery diagnostic.

After commit, quarantine cleanup requires the remaining tree to be a subset of the recorded exact file/directory inventory with identical digests. Interrupted cleanup is repeatable; unfamiliar or modified quarantine remains preserved and reports `cleanup-pending`. The reused `ImportRefreshTransaction.cleanupCommittedBackups` helper deletes only explicitly mapped backup filenames below the private transaction backup directory; it does not recursively delete an installation, donor, owner root or snapshot. Missing backup files are acceptable in the private preparation phase because no live mutation has begun. The executor detects remaining backup storage rather than treating the helper's swallowed filesystem error as successful cleanup. Registry staging and empty managed directories receive their own constrained cleanup.

## Runtime exclusion

Runtime owner leases and importer writer reservations share one mutex. Acquisition expands committed provider dependencies in memory and rejects an invalid root or overlapping writer/recovery reservation. Source menu construction acquires these leases before loading resources; teardown releases them. Removal previews include active leases. Queued refreshes skip leased owner/family/provider roots and can continue for unrelated owners. Direct refresh/import and staging publication reject overlapping leases. The main-thread removal handoff validates its token before touching caches and publishes generation/readiness changes after durable worker completion.

## Validation

Backend tests use private short-path `C:/tfixtures` installations because Windows eval has path-length constraints. The tests compile current production Haxe filesystem/transaction code with the portable interpreter; the manager regeneration fixture supplies frontend/converter stubs while executing the actual manager regeneration and transaction implementations.

- `test_import_removal_transaction.py`: committed singleton removal, cancellation before work and during backup preparation, local edits, unclaimed local files, exact rollback, authored-ID/chart-destination reinstall, ordinary partial aggregates, v2/v3 family preservation, cleanup-pending with modified quarantine, byte-preserving blocked recovery and successful fresh-process retry. Fresh-process crashes cover preparation, prepared journal, file publication, scope retirement, replacement publication, removal marker and durable receipt. Both singleton and partial transactions recover/retry; original asset/state/pointer hashes are exact before commit. Edited committed journals are rejected without changing existing bytes.
- `test_import_removal_refresh.py`: reloads a real committed partitioned receipt in a fresh process and runs actual `ImportRefreshManager.refreshNow`; only the surviving beta root is converted, alpha assets stay absent and saved history remains. Also verifies atomic owner/provider exclusion, invalid mixed-root rejection, queued writer preservation and token validation before foreground cache mutation.
- `test_import_removal_v3_core.py`: creates a real captured Nightmare Vision source, publishes actual mapped core images/identity sidecars, commits a v3 family, blocks provider removal while receivers survive, removes alpha, verifies every beta receiver file hash, restarts and enumerates beta only, then removes the remaining family/core and cleans the now-unreferenced managed snapshot while preserving the original donor.
- Existing removal planner/inventory and independent partition safety probes cover shared claims/dependencies, source snapshot references, full-plus-partial/two-partial shared files and same-name categories with surviving membership.
- Existing refresh transaction regression suite: 23 tests passed, 1 platform-specific test skipped (49.595 seconds).

The backend tests do not claim GPU/menu rendering coverage, OS crash during an individual metadata write, or exhaustive hostile local filesystem races. Native menu/UI, full regression and release packaging gates are recorded by the release orchestrator separately. Recovery preserves malformed or locally modified metadata rather than guessing how to repair it.

## Final targeted results

- Removal transaction scenarios, including recreated local paths after interruption: passed (44.043 seconds).
- Real v3 capture/member removal/restart/final-family removal/managed snapshot cleanup: passed (9.084 seconds).
- Final `LibraryIdentityArchive` contracts: passed (16.554 seconds, all eight fixture modes).
- Fresh-process production manager regeneration and atomic lease/token/queue contracts: passed (3.068 seconds).
- Removal wildcard regressions before the extra real-v3 module: six tests passed (83.627 seconds).
- Shared refresh transaction suite: 23 tests passed, one platform-specific skip (49.595 seconds).

The stale automatic refresh test's initial and refreshed Psych revision expectations were updated from 13 to the current 14; its stale revision-9 input, automatic-queue behavior and new-song publication assertions remain intact. Final native rerun passed (70.360 seconds).
