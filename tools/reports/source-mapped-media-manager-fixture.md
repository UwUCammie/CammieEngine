# Mapped media manager transaction fixture

The manager fixture exercises the shared `SourceMappedMediaPublisher` through the real `ImportRefreshManager.importOnce` and `refreshNow` transaction paths. For each selected root it confirms that the active `ImportIO` profile is receipt-bound to that root and namespace before planning, then builds one combined Psych language and media plan and publishes the plan once into staging.

The focused cases verify two selected roots receive distinct owner namespaces, one media source fans out to two authored destinations per owner, and a refresh still succeeds after the donor folder is removed. They also verify that edited installed bytes cause a transaction conflict without changing the previous manifest or profile metadata; a typed unresolved mapping and a source collision both reject reimport while preserving prior outputs; a known disabled mapping blocks legacy fallback and allows clean outputs to be pruned; and cancellation leaves installed media bytes, manifest, and profile metadata unchanged.

Verification used the portable Haxe interpreter with `CAMMIE_FORCE_EVAL=1` and the short temp root `C:/t/cammie-test`:

- `tools/tests/test_source_mapped_asset_publisher.py`: 22 tests passed, including a real unresolved symbolic rename that protects prior custom-extension output anywhere under the exact owner when its destination cannot be enumerated.
- Five focused `ImportRefreshManagerTest` cases in `tools/tests/test_import_refresh_manager.py`: all passed.

No full suite, game build, or native launch was run for this fixture. The parent task owns native transaction verification.
