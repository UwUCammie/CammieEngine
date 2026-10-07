# Nightmare Vision private score migration

This migration copies a native chart's best score and the accuracy stored at
that same `best-score` key into the selected source owner's private
`NightmareVisionHighscore` maps. It reads from the native maps directly and
does not call native getters, insert missing zeros, or write the native ledger.
The source service keeps its strict-improvement behavior: an absent/lower
private score can be filled or improved, while an equal/higher value and its
rating remain untouched.

The caller supplies bounded entries from registered Freeplay charts. Each
entry contains its registered storage folder, native difficulty index, exact
destination chart path, parsed `importProvenance.json`, parsed
`CompatScriptManifestData`, and a lazy chart loader (or an already-loaded
chart). The migration checks that the receipt is Nightmare Vision provenance
for an authorized source root and that the selected manifest root is the same
owner with the Nightmare Vision engine before consulting the ledger. It then
checks the exact native `best-score` key and requires both score and accuracy.
Only paired entries parse charts. Their selected path must be the exact
`assets/data/<registered>/<registered><native-suffix>.json` or `.jsonc` file;
the loaded chart must retain that registered storage folder and expected stem,
and `Highscore.scoreSongIdForChart` must resolve to the registered folder.

Difficulty mapping uses the native suffix for non-default charts and the
configured native difficulty name for the unsuffixed default chart. The
receipt's `sourceSelectableDifficulties` list maps that name to the source
adapter slot. The actual loaded chart title supplies the private key. When
several distinct registered charts resolve to one sanitized source key, all
colliding candidates are skipped and reported as ambiguous; a same-named chart
from another owner cannot be used as a fallback.

The adapter's source menu and selected index are borrowed only while formatting
and saving, then restored on success or failure. Chart loading is deferred
until a paired native record exists, so charts with no saved score cause no
chart parse or `Song.loadFromJson` mutation of host statics. Collection remains
bounded to registered chart rows and performs no media-tree scan.

Focused check:

```powershell
$env:PYTHONPATH='tools/tests'
python -m unittest test_nightmare_vision_highscore_migration -v
```

The interpreter fixture passed with the actual migration, owner highscore,
difficulty adapter, and native `Highscore` implementations. Narrow host stubs
cover filesystem asset existence, manifest selection, difficulty metadata,
and unrelated native Highscore dependencies. The fixture checks paired
accuracy, lazy loading, configured default mapping, strict updates, owner
validation, ambiguity, native-ledger preservation, and adapter restoration
after an owner-save error. It is not a native build or a full application
bootstrap check; those gates remain with the integration owner.
