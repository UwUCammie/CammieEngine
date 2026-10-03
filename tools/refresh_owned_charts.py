#!/usr/bin/env python3
"""Plan or apply a backed-up, owner-scoped chart refresh from a private preview."""

import argparse
try:
    from tools import file_lock as fcntl
except ModuleNotFoundError:
    import file_lock as fcntl  # Direct python tools/<script>.py invocation.
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"
LOCK = ROOT / ".tools/runtime-0.lock"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def within(root: Path, path: Path) -> bool:
    return path == root or root in path.parents


def checked_path(root: Path, relative: str) -> Path:
    item = Path(relative)
    if item.is_absolute() or ".." in item.parts or item.parts[:2] != ("assets", "data"):
        raise ValueError(f"unsafe chart path: {relative}")
    path = root / item
    if not within(root, path.resolve()) or path.is_symlink():
        raise ValueError(f"chart path escapes owner root: {relative}")
    return path


def selected_owner(path: Path) -> str:
    manifest = path.parent / "compatScripts.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError(f"missing regular owner manifest: {manifest}")
    owner = json.loads(manifest.read_text(encoding="utf-8")).get("selectedRoot")
    if not isinstance(owner, str):
        raise ValueError(f"invalid selected owner: {manifest}")
    return owner


def chart_song(path: Path) -> str:
    chart = json.loads(path.read_text(encoding="utf-8"))["song"]
    if not isinstance(chart, dict) or not isinstance(chart.get("song"), str):
        raise ValueError(f"invalid chart: {path}")
    if not isinstance(chart.get("notes"), list):
        raise ValueError(f"chart has no section notes: {path}")
    return chart["song"]


def make_plan(preview: Path, runtime: Path, owner: str,
              charts: list[str]) -> dict:
    preview = preview.resolve()
    runtime = runtime.resolve()
    if not within(TMP.resolve(), preview) or within(preview, runtime) or within(runtime, preview):
        raise ValueError("preview must be a distinct repository tmp tree")
    if not runtime.is_dir() or not charts:
        raise ValueError("runtime or chart list is missing")
    if not owner.startswith("assets/imported_mods/") or ".." in Path(owner).parts:
        raise ValueError("owner must be a selected imported namespace")
    rows = []
    for relative in charts:
        source = checked_path(preview, relative)
        target = checked_path(runtime, relative)
        if not source.is_file() or not target.is_file():
            raise ValueError(f"source or installed chart missing: {relative}")
        if selected_owner(source) != owner or selected_owner(target) != owner:
            raise ValueError(f"selected owner mismatch: {relative}")
        source_song = chart_song(source)
        target_song = chart_song(target)
        # Legacy imports can retain the source display case while the current
        # importer uses the storage key. Case-only changes resolve to the same
        # audio folder; keep all other identity changes behind the guard.
        if source_song != target_song and not (
            source_song.casefold() == target_song.casefold()
            and source_song.casefold() == source.parent.name.casefold()
        ):
            raise ValueError(f"chart audio identity differs: {relative}")
        rows.append({"relative": relative, "sourceSha256": digest(source),
                     "installedSha256": digest(target),
                     "sourceBytes": source.stat().st_size,
                     "installedBytes": target.stat().st_size})
    if len({row["relative"] for row in rows}) != len(rows):
        raise ValueError("duplicate chart path")
    return {"version": 1, "preview": str(preview), "runtime": str(runtime),
            "owner": owner, "charts": rows,
            "repoOptionsSha256": digest(ROOT / "assets/data/options.json"),
            "runtimeOptionsSha256": digest(runtime / "assets/data/options.json")}


def write_atomic(source: Path, target: Path, scratch: Path) -> None:
    shutil.copy2(source, scratch)
    os.replace(scratch, target)


def apply_plan(plan: dict, receipt_path: Path) -> dict:
    preview = Path(plan["preview"])
    runtime = Path(plan["runtime"])
    paths = [row["relative"] for row in plan["charts"]]
    current = make_plan(preview, runtime, plan["owner"], paths)
    if current != plan:
        raise ValueError("preview, selected owner, chart, or settings changed since plan")
    backup = TMP / "owned-chart-backups" / (str(int(time.time())) + "-" + str(os.getpid()))
    backup.mkdir(parents=True, exist_ok=False)
    replacements = []
    try:
        for row in plan["charts"]:
            relative = row["relative"]
            source = checked_path(preview, relative)
            target = checked_path(runtime, relative)
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            if digest(saved) != row["installedSha256"]:
                raise ValueError(f"backup changed before replacement: {relative}")
            scratch = backup / (relative + ".new")
            scratch.parent.mkdir(parents=True, exist_ok=True)
            write_atomic(source, target, scratch)
            replacements.append(relative)
            if digest(target) != row["sourceSha256"]:
                raise ValueError(f"replacement hash mismatch: {relative}")
        if (digest(ROOT / "assets/data/options.json") != plan["repoOptionsSha256"]
                or digest(runtime / "assets/data/options.json") != plan["runtimeOptionsSha256"]):
            raise ValueError("options changed during chart refresh")
    except Exception:
        for relative in reversed(replacements):
            saved = backup / relative
            target = checked_path(runtime, relative)
            scratch = backup / (relative + ".restore")
            write_atomic(saved, target, scratch)
        raise
    receipt = {"version": 1, "status": "applied", "owner": plan["owner"],
               "backup": str(backup), "charts": plan["charts"],
               "repoOptionsUnchanged": True, "runtimeOptionsUnchanged": True}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--runtime", type=Path,
                        default=ROOT / "export/release/linux/bin")
    parser.add_argument("--owner")
    parser.add_argument("--chart", action="append", default=[])
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    TMP.mkdir(exist_ok=True)
    with LOCK.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if args.apply:
            plan = json.loads(args.plan.read_text(encoding="utf-8"))
            receipt = apply_plan(plan, args.receipt or args.plan.with_suffix(".receipt.json"))
            print(json.dumps({"status": receipt["status"], "charts": len(receipt["charts"]),
                              "backup": receipt["backup"]}))
        else:
            if args.preview is None or args.owner is None:
                parser.error("--preview and --owner are required when planning")
            plan = make_plan(args.preview, args.runtime, args.owner, args.chart)
            args.plan.parent.mkdir(parents=True, exist_ok=True)
            args.plan.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": "planned", "charts": len(plan["charts"]),
                              "changed": sum(row["sourceSha256"] != row["installedSha256"]
                                             for row in plan["charts"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
