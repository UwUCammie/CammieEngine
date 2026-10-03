#!/usr/bin/env python3
"""Back up and repair one base song polluted by an older foreign import.

The engine/importer fix owns future collisions. This tool repairs an existing
installation after a complete offscreen native import has put the foreign song
in its qualified destination. It defaults to a read-only plan.
"""

from __future__ import annotations

import argparse
try:
    from tools import file_lock as fcntl
except ModuleNotFoundError:
    import file_lock as fcntl  # Direct python tools/<script>.py invocation.
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "export/release/linux/bin"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def owned_import(runtime: Path, song: str, namespace: str) -> bool:
    manifest = runtime / "assets/data" / song / "compatScripts.json"
    if not manifest.is_file():
        return False
    try:
        return json.loads(manifest.read_text()).get("selectedRoot") == namespace
    except (OSError, ValueError):
        return False


def generated_note_subset(old: Path, qualified: Path, source: Path) -> bool:
    """Recognize an older generated note registry copied into a base folder.

    A later owner-qualified refresh may add more entries, so byte identity is
    too strict. Keep any authored base registry or any entry absent from the
    qualified owner's registry.
    """
    if source.exists():
        return False
    try:
        old_entries = json.loads(old.read_text())
        qualified_entries = json.loads(qualified.read_text())
    except (OSError, ValueError):
        return False
    if not isinstance(old_entries, list) or not old_entries or not isinstance(qualified_entries, list):
        return False
    qualified_keys = {json.dumps(entry, sort_keys=True) for entry in qualified_entries}
    if all(json.dumps(entry, sort_keys=True) in qualified_keys for entry in old_entries):
        return True
    # A later refresh can assign new generated indexes when it merges other
    # note types first. Compare the entire generated definition except that
    # index-bearing id; never use this path for authored/unknown entries.
    def generated(entry: object) -> bool:
        return (isinstance(entry, dict)
                and entry.get("sourceEngine") == "Codename Engine"
                and isinstance(entry.get("id"), str)
                and entry["id"].startswith("codename:"))

    if not all(generated(entry) for entry in old_entries):
        return False
    def definition(entry: dict) -> str:
        return json.dumps({key: value for key, value in entry.items() if key != "id"},
                          sort_keys=True)

    qualified_defs = {definition(entry) for entry in qualified_entries if generated(entry)}
    return all(definition(entry) in qualified_defs for entry in old_entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_song", help="engine-owned base song folder")
    parser.add_argument("qualified_song", help="already-imported owner-qualified folder")
    parser.add_argument("owner_namespace", help="destination-only assets/imported_mods/... namespace")
    parser.add_argument("--restore-chart", action="append", required=True,
                        help="base chart filename to restore (repeat for each changed difficulty)")
    parser.add_argument("--runtime", type=Path, default=RUNTIME)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    lock = None
    if args.apply:
        lock = (ROOT / ".tools/runtime-0.lock").open("a+")
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SystemExit("runtime build/game lock is held; repair refused") from error

    protected = set(json.loads((ROOT / "assets/data/baseSongKeys.json").read_text()))
    if args.base_song not in protected or "/" in args.base_song or "\\" in args.base_song:
        raise SystemExit("base song must be an engine-owned folder")
    if not args.qualified_song.startswith(args.base_song + "--") or "/" in args.qualified_song:
        raise SystemExit("qualified song does not match the base key")
    if not args.owner_namespace.startswith("assets/imported_mods/") or ".." in Path(args.owner_namespace).parts:
        raise SystemExit("unsafe owner namespace")
    chart_names = list(dict.fromkeys(args.restore_chart))
    if any(Path(name).name != name or not name.endswith(".json") for name in chart_names):
        raise SystemExit("restore chart must be a JSON filename")

    runtime = args.runtime.resolve()
    base_data = runtime / "assets/data" / args.base_song
    qualified_data = runtime / "assets/data" / args.qualified_song
    base_audio = runtime / "assets/songs" / args.base_song
    qualified_audio = runtime / "assets/songs" / args.qualified_song
    charts: list[tuple[str, Path, Path, Path]] = []
    for name in chart_names:
        if name != args.base_song + ".json" and not name.startswith(args.base_song + "-"):
            raise SystemExit("chart filename must match the protected base song")
        source_chart = ROOT / "assets/data" / args.base_song / name
        target_chart = base_data / name
        qualified_chart = qualified_data / (args.qualified_song + name[len(args.base_song):])
        if not source_chart.is_file() or not target_chart.is_file() or not qualified_chart.is_file():
            raise SystemExit("source, installed base, and qualified charts must all exist")
        if sha(source_chart) == sha(target_chart):
            raise SystemExit("base chart already matches its engine source; nothing to restore: " + name)
        charts.append((name, source_chart, target_chart, qualified_chart))
    if not owned_import(runtime, args.base_song, args.owner_namespace):
        raise SystemExit("base folder does not carry the expected old foreign owner")
    if not owned_import(runtime, args.qualified_song, args.owner_namespace):
        raise SystemExit("qualified folder does not carry the selected owner")

    removable: list[tuple[Path, Path]] = []
    for name in ("compatScripts.json", "noteInfo.json"):
        old, new = base_data / name, qualified_data / name
        if old.is_file() and new.is_file() and (sha(old) == sha(new)
                or (name == "noteInfo.json" and generated_note_subset(
                    old, new, ROOT / "assets/data" / args.base_song / name))):
            removable.append((old, new))
    for name in ("Inst.ogg", "Voices.ogg"):
        old, new = base_audio / name, qualified_audio / name
        # A seed-owned Inst/Voices file can legitimately match the imported
        # copy. Never remove audio that the base library itself supplies.
        if not (ROOT / "assets/songs" / args.base_song / name).exists() \
                and old.is_file() and new.is_file() and sha(old) == sha(new):
            removable.append((old, new))

    report = {
        "baseSong": args.base_song,
        "qualifiedSong": args.qualified_song,
        "ownerNamespace": args.owner_namespace,
        "sourceChartHashes": {name: sha(source) for name, source, _, _ in charts},
        "installedChartHashesBefore": {name: sha(target) for name, _, target, _ in charts},
        "qualifiedChartHashes": {name: sha(qualified) for name, _, _, qualified in charts},
        "removeOnlyAfterBackup": [str(old.relative_to(runtime)) for old, _ in removable],
        "apply": args.apply,
    }
    if not args.apply:
        print(json.dumps(report, indent=2))
        return 0

    backup = ROOT / "tmp/import-refresh-backups" / (time.strftime("%Y%m%dT%H%M%S") + "-base-collision-" + args.base_song)
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copytree(base_data, backup / "data")
    shutil.copytree(base_audio, backup / "songs")
    shutil.copy2(runtime / "assets/data/options.json", backup / "options.json")
    shutil.copy2(runtime / "assets/data/freeplaySongJson.jsonc", backup / "freeplaySongJson.jsonc")
    options_before = sha(runtime / "assets/data/options.json")
    registry_before = sha(runtime / "assets/data/freeplaySongJson.jsonc")
    for _, source_chart, target_chart, _ in charts:
        shutil.copy2(source_chart, target_chart)
    for old, _ in removable:
        old.unlink()
    report.update({
        "backup": str(backup),
        "installedChartHashesAfter": {name: sha(target) for name, _, target, _ in charts},
        "optionsUnchanged": sha(runtime / "assets/data/options.json") == options_before,
        "freeplayRegistryUnchanged": sha(runtime / "assets/data/freeplaySongJson.jsonc") == registry_before,
    })
    (backup / "repair-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report["installedChartHashesAfter"] != report["sourceChartHashes"] or not report["optionsUnchanged"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
