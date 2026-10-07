# Codename owner save flush policy

Checkpoint date: 7 October 2026.

`CodenameOwnerSaveStorage.create(autoFlushWrites:Bool = true)` now captures a
per-backend write policy. The default preserves the historical behavior: each
write JSON-clones the value into the same native save namespace and flushes
immediately. Passing `false` keeps the clone, validation, and owner isolation
behavior while changing only persistence timing. Its `flush()` delegate still
flushes the active native save, so callers can follow their source-defined
explicit save boundary without a flush on each field mutation.

The focused extracted-class test checks default immediate flushing, opt-in
batching, explicit flush, cloned values, separate owner buckets, and rejection
of malformed namespace data. No build or full suite was run for this change.

## Verification

- `python -m unittest test_codename_owner_save_storage -v`: passed (1 test).
