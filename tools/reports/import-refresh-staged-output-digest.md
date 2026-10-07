# Import refresh staged output digest measurement

The importer hashed each generated staged asset in `ImportRefreshManager.regenerate`, then `ImportRefreshTransaction.apply` read and hashed the same bytes again before it could make conflict decisions. The manager now leaves the digest out for generated outputs. The transaction still validates the staged path and regular-file status, computes SHA-256 before publication, and carries that verified value through conflict checks and the manifest. Callers that supply a digest retain the old contract: malformed or mismatched values fail before publication.

`captureImport` and retained refresh both call `regenerate`, so the change covers first import and refresh. It does not change source snapshot hashing, archive retention, conflict baselines, staging rechecks, live-file rechecks, backups, recovery, or publication ordering. The import revision is unchanged because the generated outputs and invalidation semantics are unchanged.

## Controlled fixture

The primary native fixture generated 8 staged outputs of 8 MiB each (64 MiB total), performed an untimed initial publication, then timed the second transaction. For the old path, it computed all output digests immediately before `apply` and supplied them, matching the manager plus transaction behavior. For the new path, it omitted them and let the transaction compute them. The old path therefore reads an extra 64 MiB and makes 8 additional file-hash calls; both paths retain the same transaction validation and publication work. Changed and unchanged outputs were measured in three alternating pairs, each in a fresh temporary directory. Timing stops as soon as `apply` returns. Outside the timed interval, each run verifies every published file's size and SHA-256 against its staged counterpart and manifest entry; all old/new runs produced identical per-state outcome digests.

The standalone hxcpp executable used Haxe 4.3.6, hxcpp 4.3.2 and portable LLVM-MinGW. Its timed output-validation/publication results were:

| Output state | Explicit prehash samples | Computed-digest samples | Median change |
| --- | --- | --- | ---: |
| Changed | 2.742652, 2.705888, 2.689407 s | 2.342521, 2.307647, 2.336999 s | 2.705887 to 2.337000 s (13.63% lower) |
| Unchanged | 1.835098, 1.825877, 1.853469 s | 1.460942, 1.503713, 1.470457 s | 1.835098 to 1.470457 s (19.87% lower) |

The old native path's direct prehash phase took 0.3586–0.3602 s. It reads exactly one extra aggregate 64 MiB pass; the computed path removes that pass while keeping all transaction checks. The changed-output outcome digest was `436b5b049d2d378e3abf93ebce04e7eb77fede01fcf313e33837b3785a9d584f` in every mode and run; the unchanged-output digest was `bbf9771ff9a8cf087aae7942f779022e20c2e1f7fad42505be66d4b375f4d2a8`. These results measure the transaction output-validation/publication phase, not a complete importer run.

For comparison, an earlier 2 MiB native fixture (32 × 64 KiB) had these samples and showed substantially more timing noise:

| Output state | Explicit prehash samples | Computed-digest samples | Median change |
| --- | --- | --- | ---: |
| Changed | 0.356080, 0.356244, 0.365649 s | 0.360666, 0.445999, 0.379320 s | 0.356244 to 0.379320 s (no demonstrated improvement) |
| Unchanged | 0.114062, 0.090043, 0.092565 s | 0.084957, 0.081417, 0.084254 s | 0.092565 to 0.084254 s (9.0% lower) |

A 2 MiB Haxe interpreter fixture measured 32 extra hash calls in each old-path run. Its paired samples were 11.437/11.485 s versus 9.852/9.900 s for changed outputs (two-sample means 11.461/9.876 s), and 8.133/8.108 s versus 6.423/6.406 s for unchanged outputs (means 8.121/6.415 s). The interpreter timings are included as a secondary check; the larger native fixture is the more useful performance evidence.

All fixture timings exclude source enumeration, retained-source validation, archive reads, regeneration/conversion, and the UI. They support the measured saving in this large-output transaction phase, not a projected whole-import duration.

## Verification

The manager and transaction test modules passed together (39 tests, two skipped), including omitted-digest publication, explicit-digest mismatch rejection, staged tampering, conflict detection, and recovery. The manager cases cover the shared first-import and refresh path. The implementation agent ran these scoped checks; the root acceptance below records the integrated application build and full suite.

Root acceptance for the importer UX/speed pass: canonical Windows build passed (`tmp/importer-ux-speed-build.log`). The final full suite passed 2,330 tests across 764 modules in 165.5 seconds, with 344 existing platform/corpus skips and zero failures. The first suite exposed one stale assertion for the removed standalone progress bar; the fixture now checks the shared card, and the final suite passed. Required donor audit and all 23 development/API policy checks passed. Seventy protected files remained unchanged. `tmp/importer-ux-speed-checkpoint.json` records build hashes and evidence boundaries. No release was published.
