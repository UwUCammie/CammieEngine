# Windows updater alpha.8 verification

The two failed Wine update jobs under the user's Wine prefix ended with
`Update failed: The release ZIP contains a duplicate path.` The URLMon and
SChannel `fixme` messages accompanied the download but were not the failure.
The alpha.7 ZIP contained 136 case-insensitive duplicate audio paths created
by Linux song-folder case mirrors. Each duplicate pair had the same size and
CRC. Windows resolves those pairs to one path, and the updater correctly
refused to extract ambiguous entries.

The release packager now writes one copy of byte-identical case mirrors and
rejects conflicting files. It validates every final ZIP entry using the
updater's case-insensitive path rule before publishing. The updater keeps its
job state when Settings closes. A download bar and later status/error text are
shown in Settings, Main Menu, and Freeplay browsing only.

Verification on this checkout:

- `python3 tools/run_tests.py`: 1,695 tests across 510 modules; 65 skipped,
  zero failed. This includes case-mirror and live status-file progress tests.
- `./build-windows-release.sh v0.0.1-alpha.8`: Windows x64 build and package
  succeeded. The ZIP is 767,390,912 bytes with SHA-256
  `920f6526de56d0367f971cf54e3b604a51a40f9a05a1543af75d7ba1e0c5360d`.
- Final ZIP: 1,725 entries, zero case-insensitive duplicate paths, all member
  CRCs valid, SHA-256 matches `dist/SHA256SUMS.txt`.
- Offscreen Wine smoke with dummy audio: the Windows game remained running
  throughout the 20-second startup window.

The full release ZIP has not been installed through a published GitHub update
in this check. A native Windows user should still verify the in-game download
and bar after alpha.8 is published. The wider example-mod compatibility goal
also remains open; this report only covers the updater failure and progress UI.
