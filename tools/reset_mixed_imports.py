#!/usr/bin/env python3
"""Move mixed-owner song imports to a recoverable local backup for reimport.

This tool leaves shared imported media and settings alone. Dry-run is the
default; --apply requires both runtime locks and a stopped game.
"""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
OWNER_PREFIX = "assets/imported_mods/"


def contained(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def safe_tree(path: Path, root: Path) -> None:
    """Reject symlink components and descendants before any directory move."""
    if not contained(path, root):
        raise ValueError(f"path leaves runtime: {path}")
    current = path
    while current != root:
        if current.is_symlink():
            raise ValueError(f"symlink in runtime path: {current}")
        current = current.parent
    if path.is_symlink():
        raise ValueError(f"symlink target: {path}")
    if path.is_dir():
        for base, dirs, files in os.walk(path, followlinks=False):
            for name in dirs + files:
                entry = Path(base) / name
                if entry.is_symlink():
                    raise ValueError(f"symlink in runtime tree: {entry}")


def tree_stamp(path: Path) -> str:
    """Bounded metadata inventory for detecting changes between plan and apply."""
    digest = hashlib.sha256()
    for base, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        for name in ["."] + dirs + files:
            entry = Path(base) if name == "." else Path(base) / name
            stat = entry.lstat()
            relative = entry.relative_to(path).as_posix()
            digest.update(f"{relative}\0{stat.st_mode}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())
    return digest.hexdigest()


def freeplay_entries(document):
    if not isinstance(document, list):
        raise ValueError("freeplay registry must be an array")
    for category in document:
        if not isinstance(category, dict) or not isinstance(category.get("songs"), list):
            raise ValueError("invalid freeplay category")
        for item in category["songs"]:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise ValueError("invalid freeplay song entry")
            yield item


def plan_reset(runtime_root: Path, owner: str) -> dict:
    runtime = runtime_root.resolve(strict=True)
    if not owner.startswith(OWNER_PREFIX) or owner == OWNER_PREFIX or ".." in Path(owner).parts \
            or Path(owner).is_absolute() or owner.endswith("/"):
        raise ValueError("owner must be one assets/imported_mods/<namespace> path")
    if not (runtime / owner).is_dir():
        raise ValueError("owner namespace is absent from runtime")
    data_root = runtime / "assets/data"
    songs_root = runtime / "assets/songs"
    registry = data_root / "freeplaySongJson.jsonc"
    safe_tree(registry, runtime)
    raw_registry = registry.read_bytes()
    document = json.loads(raw_registry)
    freeplay_names = {item["name"].casefold() for item in freeplay_entries(document)}
    candidates = []
    skipped = []
    for song_dir in sorted(data_root.iterdir()):
        if not song_dir.is_dir() or song_dir.is_symlink():
            continue
        manifest_path = song_dir / "compatScripts.json"
        if not manifest_path.exists():
            continue
        safe_tree(manifest_path, runtime)
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("selectedRoot") != owner:
            continue
        roots = manifest.get("roots")
        if not isinstance(roots, list) or not any(isinstance(root, dict) and root.get("path") == owner for root in roots):
            skipped.append({"song": song_dir.name, "reason": "selected owner missing from roots"})
            continue
        foreign = sorted({root.get("path") for root in roots if isinstance(root, dict)
                          and isinstance(root.get("path"), str) and root["path"] != owner})
        if not foreign:
            continue
        name = song_dir.name
        if name.casefold() not in freeplay_names:
            skipped.append({"song": name, "reason": "song absent from freeplay registry"})
            continue
        default_chart = song_dir / f"{name}.json"
        if not default_chart.is_file():
            skipped.append({"song": name, "reason": "default chart is absent"})
            continue
        safe_tree(default_chart, runtime)
        chart = json.loads(default_chart.read_text())
        audio_name = chart.get("song", {}).get("song") if isinstance(chart, dict) else None
        if not isinstance(audio_name, str) or audio_name.casefold() != name.casefold():
            skipped.append({"song": name, "reason": "chart audio identity differs from song folder"})
            continue
        matches = [entry for entry in songs_root.iterdir() if entry.name.casefold() == name.casefold()] if songs_root.exists() else []
        if len(matches) > 1:
            skipped.append({"song": name, "reason": "ambiguous case-folded song media directories"})
            continue
        paths = [song_dir] + matches
        for path in paths:
            safe_tree(path, runtime)
        candidates.append({"song": name, "foreignRoots": foreign,
                           "paths": [str(path.relative_to(runtime)) for path in paths],
                           "stamps": {str(path.relative_to(runtime)): tree_stamp(path) for path in paths}})
    return {"version": 1, "runtimeRoot": str(runtime), "owner": owner,
            "registrySha256": hashlib.sha256(raw_registry).hexdigest(),
            "candidates": candidates, "skipped": skipped}


def running_funkin() -> bool:
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            if (proc / "comm").read_text().strip() == "Funkin":
                return True
        except (OSError, UnicodeError):
            pass
    return False


def apply_reset(plan: dict, *, repo_root: Path = ROOT) -> Path | None:
    repo_root = repo_root.resolve()
    lock_dir = repo_root / ".tools"
    lock_dir.mkdir(parents=True, exist_ok=True)
    locks = []
    try:
        for mode in ("0", "1"):
            lock = (lock_dir / f"runtime-{mode}.lock").open("a+")
            locks.append(lock)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if running_funkin():
            raise RuntimeError("Funkin is running; close it before applying")
        current = plan_reset(Path(plan["runtimeRoot"]), plan["owner"])
        if current != plan:
            raise RuntimeError("runtime import plan changed; run dry-run again")
        if not plan["candidates"]:
            return None
        runtime = Path(plan["runtimeRoot"])
        registry = runtime / "assets/data/freeplaySongJson.jsonc"
        document = json.loads(registry.read_text())
        selected = {candidate["song"].casefold() for candidate in plan["candidates"]}
        removals = 0
        for category in document:
            before = len(category["songs"])
            category["songs"] = [item for item in category["songs"]
                                 if item["name"].casefold() not in selected]
            removals += before - len(category["songs"])
        if removals < len(selected):
            raise RuntimeError("a planned song is missing from freeplay registry")
        local_tmp = repo_root / "tmp"
        backup_base = local_tmp / "import-reset-backups"
        if local_tmp.is_symlink() or backup_base.is_symlink():
            raise RuntimeError("repo-local backup path must not be a symlink")
        backup_base.mkdir(parents=True, exist_ok=True)
        if backup_base.stat().st_dev != runtime.stat().st_dev:
            raise RuntimeError("backup and runtime must share a filesystem for atomic moves")
        backup = backup_base / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])
        backup.mkdir()
        moved = []
        registry_bytes = registry.read_bytes()
        try:
            (backup / "freeplaySongJson.jsonc").write_bytes(registry_bytes)
            (backup / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
            for candidate in plan["candidates"]:
                for relative in candidate["paths"]:
                    source = runtime / relative
                    target = backup / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source.rename(target)
                    moved.append((source, target))
            staged = backup / "freeplaySongJson.updated.jsonc"
            staged.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
            os.replace(staged, registry)
            return backup
        except Exception:
            for source, target in reversed(moved):
                source.parent.mkdir(parents=True, exist_ok=True)
                target.rename(source)
            registry.write_bytes(registry_bytes)
            raise
    finally:
        for lock in reversed(locks):
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--owner", required=True, help="assets/imported_mods/<namespace>")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        plan = plan_reset(args.runtime_root, args.owner)
        if args.apply:
            backup = apply_reset(plan)
            print(json.dumps({"applied": bool(backup), "backup": str(backup) if backup else None,
                              "songs": [candidate["song"] for candidate in plan["candidates"]]}, indent=2))
        else:
            print(json.dumps(plan, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"reset_mixed_imports: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
