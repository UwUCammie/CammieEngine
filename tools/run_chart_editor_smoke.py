#!/usr/bin/env python3
"""Run one offscreen native ChartingState companion-event round-trip smoke."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_runtime_smoke_matrix import SmokeCase, _binary_default, run_case


def run_chart_editor_case(
    binary: Path,
    song: str,
    chart: str,
    difficulty: str = "normal",
    *,
    case_id: str = "chart-editor",
    runtime_root: Path | None = None,
    timeout_seconds: float = 30,
    duration_ms: int | None = None,
    wine: bool = False,
    strict_diagnostics: bool = False,
) -> dict:
    """Run one isolated chart-editor edit/delete/autosave/reload round-trip."""

    case = SmokeCase(case_id, "editor round-trip", song.strip().lower(), chart.strip().lower(),
                     difficulty, timeout_seconds)
    return run_case(
        binary.resolve(),
        case,
        duration_ms=(duration_ms if duration_ms is not None
                     else max(5000, int(timeout_seconds * 1000) - 5000)),
        timeout_seconds=timeout_seconds,
        wine=wine,
        runtime_root=runtime_root,
        strict_diagnostics=strict_diagnostics,
        chart_editor=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=_binary_default())
    parser.add_argument("--runtime-root", type=Path,
                        help="optional runtime root containing assets/; defaults to the binary directory")
    parser.add_argument("--song", required=True, help="selected imported chart data folder")
    parser.add_argument("--chart", required=True, help="selected chart filename without .json")
    parser.add_argument("--difficulty", default="normal")
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument("--wine", action="store_true", help="launch the built binary through wine")
    parser.add_argument("--strict-diagnostics", action="store_true")
    args = parser.parse_args()

    if args.timeout_seconds < 5:
        parser.error("--timeout-seconds must be at least 5")
    result = run_chart_editor_case(
        args.binary.resolve(),
        args.song,
        args.chart,
        args.difficulty,
        runtime_root=args.runtime_root,
        timeout_seconds=args.timeout_seconds,
        wine=args.wine,
        strict_diagnostics=args.strict_diagnostics,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
