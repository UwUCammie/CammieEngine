# Windows updater repair revision 2

The real failed installation ended with `Could not delete
Templates/funkin.otf`, followed by a rollback failure on the same file.
The installed font and the published package's font were byte-identical.
The first updater repair fixed HTTPS downloads; it did not fix this later
installation failure.

The helper now compares existing replaceable files in bounded chunks and
leaves identical files untouched. It records rollback mutations after an
existing destination is actually deleted, rather than immediately after
making a backup. A locked destination that was never changed is consequently
excluded from rollback. Failed sibling staging files are removed, and errors
are shown in a native dialog even after the originating game's output pipe
has closed.

Native builds use streaming zlib with fixed-size input/output chunks, a
lookup-table CRC, reusable SHA-256 block workspace, and indexed archive
directory collision checks. All path, checksum, entry-size and required-file
validation remains active. `status.txt` retains its legacy phase names;
`progress.json` supplies throttled per-phase measurements to newer game UIs.
A separate Windows helper window reports verification, preparation,
installation and rollback progress for older installations as well.

Validation on 5 October 2026:

- Native Windows game and production helper builds passed.
- Full regression gate: 2,151 tests across 673 modules in 115.0 seconds,
  348 platform/fixture skips, zero failures.
- Six focused updater tests passed, including native locked identical and
  changed `Templates/funkin.otf` cases; the latter restores earlier executable
  changes without touching the locked file or leaving sibling temporary files.
- Native stored/deflated extraction passed; malformed CRC, truncated payload
  and file/directory collision cases were rejected and partial staging removed.
- The 720,725,314-byte revision-1 release package verified in 5.99 seconds and
  extracted in 5.28 seconds; observed peak working set was about 56 MB.
- The actual v0.0.10 installation updated to v0.0.12 in 18.06 seconds through
  the native local-install entrypoint using the verified published package.
  Both version markers and executable bytes match v0.0.12; settings and save
  hashes are unchanged. The identical font's timestamp is unchanged. The
  revision-2 helper was then installed so subsequent updates retain the repair.
- The release package keeps the original game and asset bytes. Only the helper
  and update notes change. Final ZIP integrity and unchanged-entry CRC/length
  checks passed.

The local-install entrypoint bypasses network and the ready-to-exit wait; its
installation, validation and rollback code is the same code used by the
production helper. Actual end-to-end download checks for URLMon are recorded
in the preceding repair checkpoint. This pass does not claim completion of
the broader source-engine compatibility roadmap.
