#!/usr/bin/env python3
"""Run resumable native ChartingState round-trips for an installed chart matrix.

This driver reads chart ownership from the matrix and each selected chart's
``compatScripts.json``. It never builds, modifies imported charts, or accesses
donor paths. Each native case uses the disposable private overlay provided by
``run_chart_editor_smoke.py``. Use ``--dry-run`` to inspect the selected range
without launching a game or taking the runtime lock.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
try:
    from tools import file_lock as fcntl
except ModuleNotFoundError:
    import file_lock as fcntl  # Direct python tools/<script>.py invocation.
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Callable, Iterable, Iterator

import run_chart_editor_smoke as chart_editor_smoke
from run_runtime_smoke_matrix import DEFAULT_BINARY, ROOT, SmokeCase


DEFAULT_MATRIX = ROOT / "tmp" / "example_mods_chart_matrix_runtime_20260929.json"
REPORT_SCHEMA = 1
SAFE_TOKEN = re.compile(r"[a-z0-9_.()\-]+")


def _relative_parts(raw: object, expected_prefix: tuple[str, ...], field: str) -> tuple[str, ...]:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"matrix row has no {field}")
    if "\\" in raw:
        raise ValueError(f"matrix {field} must use relative POSIX paths: {raw!r}")
    candidate = PurePosixPath(raw)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError(f"matrix {field} is not a safe relative path: {raw!r}")
    parts = candidate.parts
    if parts[:len(expected_prefix)] != expected_prefix:
        raise ValueError(f"matrix {field} must start with {'/'.join(expected_prefix)}: {raw!r}")
    return parts


def load_matrix(path: Path) -> tuple[dict[str, Any], bytes, str]:
    raw = path.read_bytes()
    try:
        matrix = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"could not parse chart matrix {path}: {error}") from error
    if not isinstance(matrix, dict) or matrix.get("schema") != 1:
        raise ValueError(f"unsupported chart matrix schema: {path}")
    rows = matrix.get("rows")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"chart matrix has no valid rows array: {path}")
    return matrix, raw, hashlib.sha256(raw).hexdigest()


def selected_rows(rows: list[dict[str, Any]], start: int = 0,
                  limit: int | None = None) -> list[tuple[int, dict[str, Any]]]:
    if start < 0:
        raise ValueError("--start must be zero or greater")
    if limit is not None and limit < 0:
        raise ValueError("--limit must be zero or greater")
    stop = None if limit is None else start + limit
    return list(enumerate(rows))[start:stop]


def case_for_row(index: int, row: dict[str, Any]) -> SmokeCase:
    runtime_chart = row.get("runtimeChart")
    parts = _relative_parts(runtime_chart, ("assets", "data"), "runtimeChart")
    if len(parts) != 4 or not parts[3].endswith(".json"):
        raise ValueError(f"matrix runtimeChart must be assets/data/<folder>/<chart>.json: {runtime_chart!r}")
    folder = parts[2]
    chart = parts[3][:-5]
    for field, token in (("runtime chart folder", folder), ("runtime chart name", chart)):
        if token != token.lower() or not SAFE_TOKEN.fullmatch(token):
            raise ValueError(f"{field} has unsupported characters or case: {token!r}")
    difficulty = row.get("difficulty")
    if not isinstance(difficulty, str) or not difficulty.strip():
        raise ValueError("matrix row has no valid difficulty")
    group = row.get("group")
    family = group if isinstance(group, str) else "imported chart"
    return SmokeCase(
        f"chart-editor-matrix-row-{index:04d}",
        family,
        folder,
        chart,
        difficulty,
    )


def _row_record(index: int, row: dict[str, Any], status: str,
                reason: str | None = None, case: SmokeCase | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "row_index": index,
        "id": f"chart-editor-matrix-row-{index:04d}",
        "status": status,
        # Retain all matrix identity and source provenance without opening any
        # donor path. runtimeChart/runtimeOwner are the installed identities.
        "matrix_row": row,
    }
    if reason:
        record["reason"] = reason
    if case is not None:
        record["case"] = case.__dict__
    return record


def inspect_row(index: int, row: dict[str, Any], runtime_root: Path) -> dict[str, Any]:
    """Preflight one row and prove its installed chart still names its owner."""

    runtime_root = runtime_root.resolve()
    raw_chart = row.get("runtimeChart")
    if raw_chart is None:
        detail = ("reference-only source row has no installed runtimeChart"
                  if row.get("referenceOnly") else "matrix row has no installed runtimeChart")
        return _row_record(index, row, "skipped", detail)

    try:
        case = case_for_row(index, row)
        chart_parts = _relative_parts(raw_chart, ("assets", "data"), "runtimeChart")
    except ValueError as error:
        return _row_record(index, row, "failed", str(error))

    chart_path = runtime_root.joinpath(*chart_parts)
    try:
        chart_resolved = chart_path.resolve(strict=False)
        if chart_resolved != runtime_root and runtime_root not in chart_resolved.parents:
            return _row_record(index, row, "failed", "runtimeChart resolves outside the runtime root", case)
    except OSError as error:
        return _row_record(index, row, "failed", f"could not resolve runtimeChart: {error}", case)

    if not chart_path.is_file():
        if row.get("sourceVariantImported") is False:
            return _row_record(index, row, "skipped",
                               f"runtime chart is absent and source variant is not imported: {raw_chart}", case)
        if row.get("runtimeChartPresent") is True:
            return _row_record(index, row, "failed",
                               f"matrix says runtime chart is installed but file is absent: {raw_chart}", case)
        return _row_record(index, row, "skipped", f"runtime chart is not installed: {raw_chart}", case)
    if row.get("sourceVariantImported") is False:
        return _row_record(index, row, "skipped",
                           f"source chart variant is not imported at runtime: {raw_chart}", case)
    if row.get("runtimeChartPresent") is False:
        return _row_record(index, row, "failed",
                           f"runtime chart exists but matrix marks it uninstalled: {raw_chart}", case)
    if row.get("runtimeOwnerRootPresent") is False:
        return _row_record(index, row, "failed",
                           f"matrix marks import owner as uninstalled: {row.get('runtimeOwner')}", case)
    if row.get("ownerMatched") is False:
        return _row_record(index, row, "failed",
                           f"matrix does not match the imported chart to its source owner: {raw_chart}", case)
    if any(runtime_root.joinpath(*chart_parts[:depth]).is_symlink()
           for depth in range(1, len(chart_parts) + 1)):
        return _row_record(index, row, "failed", f"runtimeChart path contains a symlink: {raw_chart}", case)

    raw_owner = row.get("runtimeOwner")
    try:
        owner_parts = _relative_parts(raw_owner, ("assets", "imported_mods"), "runtimeOwner")
        if len(owner_parts) != 3:
            raise ValueError(f"matrix runtimeOwner must name one imported_mods directory: {raw_owner!r}")
    except ValueError as error:
        return _row_record(index, row, "failed", str(error), case)

    owner_path = runtime_root.joinpath(*owner_parts)
    try:
        owner_resolved = owner_path.resolve(strict=False)
        if owner_resolved != runtime_root and runtime_root not in owner_resolved.parents:
            return _row_record(index, row, "failed", "runtimeOwner resolves outside the runtime root", case)
    except OSError as error:
        return _row_record(index, row, "failed", f"could not resolve runtimeOwner: {error}", case)
    if not owner_path.is_dir():
        return _row_record(index, row, "failed", f"import owner directory is absent: {raw_owner}", case)
    if any(runtime_root.joinpath(*owner_parts[:depth]).is_symlink()
           for depth in range(1, len(owner_parts) + 1)):
        return _row_record(index, row, "failed", f"import owner path contains a symlink: {raw_owner}", case)

    song_folder = runtime_root / "assets" / "data" / case.folder
    owner_manifest = song_folder / "compatScripts.json"
    if owner_manifest.is_symlink():
        return _row_record(index, row, "failed",
                           f"compatScripts.json is a symlink: {owner_manifest.relative_to(runtime_root)}", case)
    if not owner_manifest.is_file():
        return _row_record(index, row, "failed",
                           f"cannot verify import owner: missing {owner_manifest.relative_to(runtime_root)}", case)
    try:
        manifest = json.loads(owner_manifest.read_text(encoding="utf-8"))
        roots = manifest.get("roots", []) if isinstance(manifest, dict) else None
        if not isinstance(roots, list):
            raise ValueError("roots is not an array")
        selected_root = manifest.get("selectedRoot") if isinstance(manifest, dict) else None
        declared = {
            item.get("path") for item in roots
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return _row_record(index, row, "failed", f"could not verify compatScripts.json ownership: {error}", case)
    if selected_root != raw_owner:
        return _row_record(index, row, "failed",
                           f"compatScripts.json selectedRoot {selected_root!r} does not match matrix owner {raw_owner}",
                           case)
    if raw_owner not in declared:
        return _row_record(index, row, "failed",
                           f"chart folder does not declare matrix import owner {raw_owner}", case)

    record = _row_record(index, row, "ready", case=case)
    record["owner_verified"] = True
    record["owner_manifest"] = str(owner_manifest.relative_to(runtime_root))
    return record


@contextmanager
def runtime_lock(binary: Path) -> Iterator[None]:
    """Hold the same exclusive lock as run.sh while the native matrix runs."""

    if os.name == "nt":
        raise RuntimeError("the native chart-editor matrix requires Linux runtime locking")
    debug_build = "debug" in {part.lower() for part in binary.resolve().parts}
    lock_path = ROOT / ".tools" / ("runtime-1.lock" if debug_build else "runtime-0.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def run_rows(
    selected: Iterable[tuple[int, dict[str, Any]]],
    binary: Path,
    runtime_root: Path,
    duration_ms: int,
    timeout_seconds: float,
    *,
    wine: bool = False,
    strict_diagnostics: bool = False,
    dry_run: bool = False,
    jobs: int = 1,
    on_result: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Preflight a range, then run each ready row in its own private overlay."""

    selected = list(selected)
    results: list[dict[str, Any]] = []

    def report(record: dict[str, Any]) -> None:
        results.append(record)
        if on_result is not None:
            on_result(record)

    if dry_run:
        for index, row in selected:
            record = inspect_row(index, row, runtime_root)
            if record["status"] == "ready":
                record["dry_run"] = True
                record["binary"] = str(binary.resolve())
                record["runtime_root"] = str(runtime_root.resolve())
                record["duration_ms"] = duration_ms
            report(record)
        return results

    if not selected:
        return results
    if not binary.is_file():
        for index, row in selected:
            record = inspect_row(index, row, runtime_root)
            if record["status"] == "ready":
                record["status"] = "failed"
                record["reason"] = f"built binary not found: {binary}"
            report(record)
        return results

    # Keep the installed binary and asset tree stable across preflight and all
    # row launches. run.sh uses this same lock before it can copy Lime files.
    def run_one(index: int, row: dict[str, Any]) -> dict[str, Any]:
        record = inspect_row(index, row, runtime_root)
        if record["status"] != "ready":
            return record
        case_data = record["case"]
        case = SmokeCase(**case_data)
        result = chart_editor_smoke.run_chart_editor_case(
            binary,
            case.folder,
            case.chart,
            case.difficulty,
            case_id=case.id,
            runtime_root=runtime_root,
            timeout_seconds=timeout_seconds,
            duration_ms=duration_ms,
            wine=wine,
            strict_diagnostics=strict_diagnostics,
        )
        matrix_row = record["matrix_row"]
        record.update(result)
        record["row_index"] = int(record["row_index"])
        record["matrix_row"] = matrix_row
        record["case"] = case_data
        record["owner_verified"] = True
        return record

    # Each case owns its Xvfb display, runtime overlay, log, and chart copy.
    # The parent keeps the build lock across all workers so run.sh cannot
    # replace the binary or synced assets between parallel editor visits.
    with runtime_lock(binary):
        if jobs == 1:
            for index, row in selected:
                report(run_one(index, row))
        else:
            with ThreadPoolExecutor(max_workers=jobs) as pool:
                futures = [pool.submit(run_one, index, row) for index, row in selected]
                for future in as_completed(futures):
                    report(future.result())
    results.sort(key=lambda record: record["row_index"])
    return results


class MatrixReport:
    """Atomically upsert completed row records, so later slices can resume."""

    def __init__(self, path: Path, matrix_path: Path, matrix_sha256: str):
        self.path = path
        self.matrix_path = matrix_path.resolve()
        self.matrix_sha256 = matrix_sha256
        self._ensure_compatible()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schema": REPORT_SCHEMA,
                "matrix": str(self.matrix_path),
                "matrix_sha256": self.matrix_sha256,
                "rows": [],
            }
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"could not read existing matrix report {self.path}: {error}") from error
        if not isinstance(payload, dict) or payload.get("schema") != REPORT_SCHEMA:
            raise ValueError(f"unsupported matrix report schema: {self.path}")
        if payload.get("matrix_sha256") != self.matrix_sha256:
            raise ValueError(f"matrix report belongs to a different matrix: {self.path}")
        if not isinstance(payload.get("rows"), list):
            raise ValueError(f"matrix report has no rows array: {self.path}")
        return payload

    def _ensure_compatible(self) -> None:
        self._read()

    def upsert(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_name(self.path.name + ".lock")
        with lock_path.open("a+") as report_lock:
            fcntl.flock(report_lock.fileno(), fcntl.LOCK_EX)
            try:
                payload = self._read()
                by_index = {
                    int(item["row_index"]): item for item in payload["rows"]
                    if isinstance(item, dict) and isinstance(item.get("row_index"), int)
                }
                by_index[int(record["row_index"])] = record
                payload["rows"] = [by_index[index] for index in sorted(by_index)]
                payload["summary"] = summarize(payload["rows"])
                _atomic_json(self.path, payload)
            finally:
                fcntl.flock(report_lock.fileno(), fcntl.LOCK_UN)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp",
                                                  dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            json.dump(payload, temporary, indent=2, ensure_ascii=False, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def summarize(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in ("passed", "failed", "skipped", "ready")}
    for record in records:
        status = record.get("status")
        if status in counts:
            counts[status] += 1
    counts["processed"] = sum(counts.values())
    return counts


def _check_report_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    tmp_root = (ROOT / "tmp").resolve()
    if resolved == tmp_root or tmp_root not in resolved.parents:
        raise ValueError(f"--report must be inside project tmp/: {resolved}")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--runtime-root", type=Path,
                        help="runtime root containing assets/; defaults to the binary directory")
    parser.add_argument("--start", type=int, default=0,
                        help="zero-based first matrix row (use with --limit to resume in slices)")
    parser.add_argument("--limit", type=int,
                        help="maximum number of matrix rows to process from --start")
    # Large source charts can need several seconds to build the editor grid
    # twice.  The smoke deadline must cover both loads, not just startup.
    parser.add_argument("--duration-ms", type=int, default=20000)
    parser.add_argument("--timeout-seconds", type=float, default=60)
    parser.add_argument("--wine", action="store_true")
    parser.add_argument("--strict-diagnostics", action="store_true")
    parser.add_argument("--jobs", type=int, default=1,
                        help="parallel private editor processes (default: one; replay failures serially)")
    parser.add_argument("--dry-run", action="store_true",
                        help="preflight rows and print planned cases without launching a game")
    parser.add_argument("--report", type=Path,
                        help="incrementally upsert row results to a resumable JSON report under tmp/")
    args = parser.parse_args(argv)

    if args.start < 0:
        parser.error("--start must be zero or greater")
    if args.limit is not None and args.limit < 0:
        parser.error("--limit must be zero or greater")
    if args.duration_ms < 250:
        parser.error("--duration-ms must be at least 250")
    if args.timeout_seconds < 5:
        parser.error("--timeout-seconds must be at least 5")
    if args.jobs < 1 or args.jobs > 4:
        parser.error("--jobs must be between 1 and 4")

    binary = args.binary.expanduser().resolve()
    runtime_root = (args.runtime_root or binary.parent).expanduser().resolve()
    if not runtime_root.is_dir() or not (runtime_root / "assets").is_dir():
        parser.error(f"runtime root has no assets directory: {runtime_root}")
    try:
        matrix, _, matrix_sha256 = load_matrix(args.matrix.expanduser().resolve())
        selected = selected_rows(matrix["rows"], args.start, args.limit)
        report = (MatrixReport(_check_report_path(args.report), args.matrix, matrix_sha256)
                  if args.report is not None else None)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    def on_result(result: dict[str, Any]) -> None:
        if report is not None:
            report.upsert(result)
        print(json.dumps(result, sort_keys=True))

    results = run_rows(
        selected,
        binary,
        runtime_root,
        args.duration_ms,
        args.timeout_seconds,
        wine=args.wine,
        strict_diagnostics=args.strict_diagnostics,
        dry_run=args.dry_run,
        jobs=args.jobs,
        on_result=on_result,
    )

    summary = summarize(results)
    summary.update({
        "matrix": str(args.matrix.expanduser().resolve()),
        "matrix_rows": len(matrix["rows"]),
        "start": args.start,
        "limit": args.limit,
        "dry_run": args.dry_run,
        "report": str(report.path) if report is not None else None,
    })
    print(json.dumps({"chart_editor_matrix_summary": summary}, sort_keys=True))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
