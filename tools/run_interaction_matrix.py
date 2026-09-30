#!/usr/bin/env python3
"""Plan or run per-row pause and cross-owner switch interaction smokes.

The default is a plan-only JSONL receipt. Native execution is opt-in with
``--execute`` and holds the same exclusive runtime lock as ``run.sh`` for the
whole serialized batch. Rows stay tied to their matrix index, selected chart
path, difficulty and import owner; inventory blockers are emitted explicitly.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import fcntl
import json
import math
from pathlib import Path, PurePosixPath
import re
from typing import Any

from run_example_full_playthrough import (
    DEFAULT_MATRIX,
    load_rows,
    preflight,
    process_timeout_for_ready_window,
)
from run_runtime_smoke_matrix import (
    DEFAULT_BINARY,
    LOG_ROOT,
    ROOT,
    SmokeCase,
    parse_markers,
    run_case,
)


@dataclass(frozen=True)
class MatrixCase:
    index: int
    row: dict[str, Any]
    case: SmokeCase
    owner: str


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.casefold()).strip("-") or "chart"


def _inventory_blockers(row: dict[str, Any]) -> list[str]:
    problems = []
    for field in ("runtimeChartPresent", "ownerMatched", "sourceVariantImported"):
        if row.get(field) is not True:
            problems.append(f"inventory does not establish {field}")
    if row.get("group") == "V-Slice":
        if row.get("sourceGameplayNoteCountMatched") is not True:
            problems.append("inventory does not establish sourceGameplayNoteCountMatched")
    elif row.get("sourceNoteCountMatched") is not True:
        problems.append("inventory does not establish sourceNoteCountMatched")

    route = row.get("runtimeChart")
    if not isinstance(route, str) or not route:
        problems.append("inventory has no runtimeChart route")
    else:
        path = PurePosixPath(route)
        if (path.is_absolute() or ".." in path.parts or len(path.parts) != 4
                or path.parts[:2] != ("assets", "data") or path.suffix.casefold() != ".json"):
            problems.append(f"unsafe or unsupported runtimeChart route: {route}")
    if not isinstance(row.get("difficulty"), str) or not row["difficulty"].strip():
        problems.append("inventory has no selected difficulty")
    if not isinstance(row.get("group"), str) or not row["group"].strip():
        problems.append("inventory has no engine group")
    if not isinstance(row.get("runtimeOwner"), str) or not row["runtimeOwner"].strip():
        problems.append("inventory has no selected runtime owner")
    if row.get("runtimeOwnerRootPresent") is False:
        problems.append("selected runtime owner root is absent")
    return problems


def _case_for_row(index: int, row: dict[str, Any], timeout_seconds: float) -> SmokeCase:
    route = PurePosixPath(str(row["runtimeChart"]))
    folder = route.parts[2]
    chart = route.stem
    identity = _slug(f"{index:03d}-{folder}-{chart}-{row['difficulty']}")
    return SmokeCase(
        f"matrix-row-{identity}", str(row["group"]), folder, chart,
        str(row["difficulty"]), timeout_seconds,
    )


def _round_robin_owners(cases: list[MatrixCase]) -> tuple[list[MatrixCase], str | None]:
    """Build one cyclic order whose every neighboring selected owner differs."""

    if len(cases) < 2:
        return [], "cross-owner switch plan needs at least two runnable rows"
    owner_counts = Counter(item.owner for item in cases)
    if max(owner_counts.values()) > len(cases) // 2:
        return [], "selected-owner distribution cannot form a fully cross-owner cycle"

    owner_groups: dict[str, list[MatrixCase]] = {}
    for item in cases:
        owner_groups.setdefault(item.owner, []).append(item)
    ordered = [
        item
        for owner in sorted(owner_groups, key=lambda key: (-owner_counts[key], key))
        for item in sorted(owner_groups[owner], key=lambda row: row.index)
    ]
    positions = [*range(0, len(cases), 2), *range(1, len(cases), 2)]
    slots: list[MatrixCase | None] = [None] * len(cases)
    for item, position in zip(ordered, positions):
        slots[position] = item
    cycle = [item for item in slots if item is not None]
    if len(cycle) != len(cases) or any(
        cycle[index].owner == cycle[(index + 1) % len(cycle)].owner
        for index in range(len(cycle))
    ):
        return [], "could not construct a cyclic cross-owner switch plan"
    return cycle, None


def build_interaction_plan(
    rows: list[dict[str, Any]],
    mode: str,
    timeout_seconds: float = 120,
    external_blockers: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Build stable per-inventory-row receipts without launching the game."""

    if mode not in {"pause", "switch"}:
        raise ValueError(f"unsupported interaction mode: {mode}")
    external_blockers = external_blockers or {}
    cases: dict[int, MatrixCase] = {}
    receipts: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        blockers = _inventory_blockers(row)
        if index in external_blockers:
            blockers.append(external_blockers[index])
        case: SmokeCase | None = None
        if not blockers:
            case = _case_for_row(index, row, timeout_seconds)
            cases[index] = MatrixCase(index, row, case, str(row["runtimeOwner"]))
        receipts.append({
            "type": "row",
            "mode": mode,
            "matrixIndex": index,
            "identity": {key: row.get(key) for key in (
                "group", "package", "song", "variant", "difficulty", "runtimeChart",
                "runtimeOwner",
            )},
            "status": "blocked" if blockers else "planned",
            "blockers": blockers,
            "case": asdict(case) if case is not None else None,
            "nextMatrixIndex": None,
            "nextCase": None,
            "executionOrder": None,
        })

    execution_indices: list[int] = []
    cycle_error: str | None = None
    if mode == "pause":
        execution_indices = list(cases)
    else:
        cycle, cycle_error = _round_robin_owners(list(cases.values()))
        if cycle_error:
            for receipt in receipts:
                if receipt["status"] == "planned":
                    receipt["status"] = "blocked"
                    receipt["blockers"].append(cycle_error)
            cases = {}
        else:
            execution_indices = [item.index for item in cycle]
            for order, source in enumerate(cycle):
                target = cycle[(order + 1) % len(cycle)]
                if source.owner == target.owner:
                    raise AssertionError("switch cycle contains a same-owner edge")
                receipt = receipts[source.index]
                receipt["nextMatrixIndex"] = target.index
                receipt["nextCase"] = asdict(target.case)
                receipt["executionOrder"] = order

    summary = {
        "type": "summary",
        "schema": 1,
        "mode": mode,
        "totalRows": len(rows),
        "plannedRows": sum(receipt["status"] == "planned" for receipt in receipts),
        "blockedRows": sum(receipt["status"] == "blocked" for receipt in receipts),
        "executionOrder": execution_indices,
        "crossOwnerCycle": mode == "switch" and cycle_error is None,
        "cycleError": cycle_error,
        "nativeLaunched": False,
    }
    return {"summary": summary, "receipts": receipts, "cases": cases}


def _pause_problems(native: dict[str, Any], case: SmokeCase) -> tuple[list[str], dict[str, Any]]:
    process_log = LOG_ROOT / f"{case.id}.process.log"
    output = process_log.read_text(encoding="utf-8") if process_log.is_file() else ""
    markers = parse_markers(output)
    pauses = [marker for marker in markers if marker.get("event") == "pause_open"]
    resumes = [marker for marker in markers if marker.get("event") == "pause_resume"]
    inputs: list[dict[str, Any]] = []
    for line in output.splitlines():
        if not line.startswith("OFFSCREEN_INPUT|"):
            continue
        try:
            item = json.loads(line.split("|", 1)[1])
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            inputs.append(item)

    problems = []
    if native.get("status") != "passed":
        problems.append(str(native.get("reason") or "native pause smoke failed"))
    if [item.get("key") for item in inputs if item.get("delivered") is True] != ["Escape", "Return"]:
        problems.append("private input pair was not delivered")
    if len(pauses) != 1 or len(resumes) != 1:
        problems.append(f"expected one pause/resume pair, got {len(pauses)}/{len(resumes)}")
    elif pauses[0].get("musicPlaying") is not False or resumes[0].get("musicPlaying") is not True:
        problems.append("music was not stopped during pause and playing after resume")
    elif (type(pauses[0].get("musicTimeMs")) not in (int, float)
          or type(resumes[0].get("musicTimeMs")) not in (int, float)
          or not math.isfinite(pauses[0]["musicTimeMs"])
          or not math.isfinite(resumes[0]["musicTimeMs"])
          or abs(resumes[0]["musicTimeMs"] - pauses[0]["musicTimeMs"]) > 250):
        problems.append("music clock advanced while paused")
    return problems, {"inputs": inputs, "pause": pauses, "resume": resumes,
                      "processLog": str(process_log)}


def _preflight_blockers(cases: dict[int, MatrixCase], runtime_root: Path) -> dict[int, str]:
    blockers: dict[int, str] = {}
    for index, item in cases.items():
        chart, duration, reason = preflight(item.row, runtime_root)
        if reason is not None or chart is None or duration is None:
            blockers[index] = f"runtime preflight: {reason or 'chart/audio unavailable'}"
    return blockers


def _execute(args: argparse.Namespace, rows: list[dict[str, Any]]) -> int:
    binary = args.binary.resolve()
    runtime_root = args.runtime_root.resolve()
    base = build_interaction_plan(rows, args.mode, args.timeout_seconds)
    lock_name = "runtime-1.lock" if "/debug/" in str(binary) else "runtime-0.lock"
    with (ROOT / ".tools" / lock_name).open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        blockers = _preflight_blockers(base["cases"], runtime_root)
        plan = build_interaction_plan(rows, args.mode, args.timeout_seconds, blockers)
        with args.output.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps({
                **plan["summary"],
                "nativeExecutionRequested": True,
                "nativeLaunched": False,
            }, sort_keys=True) + "\n")
            stream.flush()
            for receipt in plan["receipts"]:
                stream.write(json.dumps(receipt, sort_keys=True) + "\n")
            stream.flush()
            receipt_by_index = {item["matrixIndex"]: item for item in plan["receipts"]}
            native_launched = False
            for order, index in enumerate(plan["summary"]["executionOrder"]):
                item = plan["cases"][index]
                receipt = receipt_by_index[index]
                try:
                    if args.mode == "pause":
                        native = run_case(
                            binary, item.case, 25000,
                            timeout_seconds=process_timeout_for_ready_window(25),
                            runtime_root=runtime_root,
                            input_key="Escape", input_delay_seconds=5,
                            followup_key="Return", followup_delay_seconds=2,
                            strict_diagnostics=True,
                            extra_flags=("--smoke-practice", "--smoke-botplay"),
                        )
                        problems, evidence = _pause_problems(native, item.case)
                        result = {"status": "failed" if problems else "passed",
                                  "problems": problems, "native": native, **evidence}
                    else:
                        next_index = receipt["nextMatrixIndex"]
                        next_case = plan["cases"][next_index].case
                        native = run_case(
                            binary, item.case, 5000,
                            timeout_seconds=args.timeout_seconds,
                            runtime_root=runtime_root, next_case=next_case,
                            strict_diagnostics=True,
                        )
                        result = {"status": native.get("status", "failed"),
                                  "problems": [] if native.get("status") == "passed"
                                  else [str(native.get("reason") or "switch smoke failed")],
                                  "native": native}
                except Exception as error:
                    result = {"status": "failed", "problems": [f"runner exception: {error}"]}
                native_result = result.get("native", {})
                native_launched = native_launched or (
                    isinstance(native_result, dict)
                    and (native_result.get("returncode") is not None
                         or native_result.get("timed_out") is True)
                )
                receipt["status"] = result["status"]
                receipt["result"] = result
                stream.write(json.dumps({
                    "type": "result", "mode": args.mode, "matrixIndex": index,
                    "executionOrder": order, "caseId": item.case.id,
                    "nextMatrixIndex": receipt.get("nextMatrixIndex"), **result,
                }, sort_keys=True) + "\n")
                stream.flush()
                print(json.dumps({"matrixIndex": index, "mode": args.mode,
                                  "status": result["status"], "problems": result["problems"]}),
                      flush=True)
            final = {
                "type": "final-summary", "mode": args.mode,
                "passed": sum(item.get("status") == "passed" for item in plan["receipts"]),
                "failed": sum(item.get("status") == "failed" for item in plan["receipts"]),
                "blocked": sum(item.get("status") == "blocked" for item in plan["receipts"]),
                "planned": len(plan["summary"]["executionOrder"]),
                "nativeLaunched": native_launched,
            }
            stream.write(json.dumps(final, sort_keys=True) + "\n")
            stream.flush()
    print(json.dumps(final, sort_keys=True))
    return 0 if final["failed"] == 0 and final["blocked"] == 0 else 1


def _write_plan(path: Path, mode: str, plan: dict[str, Any], matrix: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = {**plan["summary"], "matrix": str(matrix), "nativeLaunched": False}
    with path.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(summary, sort_keys=True) + "\n")
        for receipt in plan["receipts"]:
            stream.write(json.dumps(receipt, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("pause", "switch"), required=True)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_BINARY.parent)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute", action="store_true",
                        help="run native cases; without this flag only write a plan")
    args = parser.parse_args(argv)
    if args.timeout_seconds < 10:
        parser.error("--timeout-seconds must be at least 10")
    if args.output is None:
        suffix = "run" if args.execute else "plan"
        args.output = ROOT / "tmp" / f"interaction-matrix-{args.mode}-{suffix}.jsonl"
    try:
        rows = load_rows(args.matrix)
        if args.execute:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            return _execute(args, rows)
        plan = build_interaction_plan(rows, args.mode, args.timeout_seconds)
        _write_plan(args.output, args.mode, plan, args.matrix.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps({**plan["summary"], "output": str(args.output)}, sort_keys=True))
    return 0 if not plan["summary"]["cycleError"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
