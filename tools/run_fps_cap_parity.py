#!/usr/bin/env python3
"""Compare native gameplay at the 60, 240, and 480 FPS caps.

Runs one chart to its natural audio ending on an isolated Xvfb display. Each
run gets a disposable runtime overlay whose only options change is ``fpsCap``;
the installed runtime and its personal settings are read-only. No build is
performed. The default target is the short base Tutorial chart; callers can
pass any imported chart and its expected due-event count.
"""

from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import statistics
import tempfile
from typing import Any

from run_runtime_smoke_matrix import (
    DEFAULT_BINARY,
    ROOT,
    SMOKE_ROOT,
    SmokeCase,
    _prepare_case_overlay,
    _run_case_in_overlay,
    parse_markers,
)


FPS_CAPS = (60, 240, 480)
DEFAULT_OUTPUT = ROOT / "tmp" / "runtime-smoke" / "fps-cap-parity.json"
SMOKE_FLAGS = ("--smoke-botplay", "--smoke-require-song-end", "--smoke-frame-stats")


def _runtime_options_snapshot(runtime_root: Path) -> bytes | None:
    try:
        return (runtime_root / "assets" / "data" / "options.json").read_bytes()
    except FileNotFoundError:
        return None


def _run_cap(
    binary: Path,
    runtime_root: Path,
    case: SmokeCase,
    cap: int,
    duration_ms: int,
    timeout_seconds: float,
    strict_diagnostics: bool,
) -> dict[str, Any]:
    """Run one cap against an owned overlay, then collect its smoke markers."""

    rate_case = SmokeCase(f"fps-cap-parity-{cap}", case.family, case.folder,
                          case.chart, case.difficulty, timeout_seconds=timeout_seconds)
    SMOKE_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"fps-cap-{cap}-", dir=SMOKE_ROOT) as temporary:
        overlay = Path(temporary)
        options_path = _prepare_case_overlay(runtime_root, overlay, rate_case)
        options = json.loads(options_path.read_text(encoding="utf-8"))
        if not isinstance(options, dict):
            raise ValueError("isolated default options are not an object")
        preserved_options = {key: value for key, value in options.items() if key != "fpsCap"}
        options["fpsCap"] = cap
        options_path.write_text(json.dumps(options, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")

        smoke = _run_case_in_overlay(
            binary,
            rate_case,
            duration_ms,
            overlay,
            runtime_root,
            timeout_seconds=timeout_seconds,
            extra_flags=SMOKE_FLAGS,
            strict_diagnostics=strict_diagnostics,
        )
        process_log = Path(smoke.get("log", "")).with_suffix(".process.log")
        output = process_log.read_text(encoding="utf-8") if process_log.is_file() else ""
        markers = parse_markers(output)
        startup = [row for row in markers if row.get("event") == "startup"]
        ends = [row for row in markers if row.get("event") == "song_end"]
        frame_stats = [row for row in markers
                       if row.get("event") == "frame_stats" and row.get("phase") == "gameplay"]
        fps_samples = [row.get("fps") for row in frame_stats
                       if isinstance(row.get("fps"), (int, float)) and row.get("fps") > 0]
        result: dict[str, Any] = {
            "fpsCap": cap,
            "status": smoke.get("status", "failed"),
            "reason": smoke.get("reason"),
            "smoke": smoke,
            "startup": startup[0] if len(startup) == 1 else startup,
            "songEnd": ends[0] if len(ends) == 1 else ends,
            "frameStats": frame_stats,
            "measuredFpsMedian": statistics.median(fps_samples) if fps_samples else None,
            "otherSettingsPreserved": {
                key: options.get(key) for key in preserved_options
            } == preserved_options,
            "processLog": str(process_log),
            "problems": [],
        }
        if not result["otherSettingsPreserved"]:
            result["problems"].append("the isolated cap override changed another saved option")
        if smoke.get("options_changed"):
            result["problems"].append("the runtime changed its disposable options.json")
        if smoke.get("status") != "passed":
            result["problems"].append(smoke.get("reason", "native smoke failed"))
        if len(startup) != 1:
            result["problems"].append(f"expected one startup marker, got {len(startup)}")
        else:
            for field in ("fpsCap", "updateFramerate", "drawFramerate"):
                if startup[0].get(field) != cap:
                    result["problems"].append(
                        f"startup {field} was {startup[0].get(field)!r}, expected {cap}"
                    )
        if len(ends) != 1:
            result["problems"].append(f"expected one natural song_end marker, got {len(ends)}")
        if not fps_samples:
            result["problems"].append("no gameplay frame_stats markers were captured")
        if smoke.get("status") == "passed" and smoke.get("diagnostic_count", 0):
            result["problems"].append(
                f"{smoke['diagnostic_count']} native script diagnostic(s)"
            )
        if result["problems"] and result["status"] == "passed":
            result["status"] = "failed"
        return result


def _check_parity(results: list[dict[str, Any]], expected_due_events: int | None,
                  tolerance_ms: float, minimum_fps_ratio: float) -> list[str]:
    problems: list[str] = []
    if len(results) != len(FPS_CAPS):
        return [f"expected {len(FPS_CAPS)} cap results, got {len(results)}"]
    for result, cap in zip(results, FPS_CAPS):
        if result.get("status") != "passed":
            problems.extend(f"{cap} FPS: {problem}" for problem in result.get("problems", []))
        median_fps = result.get("measuredFpsMedian")
        if isinstance(median_fps, (int, float)) and median_fps < cap * minimum_fps_ratio:
            result["rateAttainment"] = "inconclusive"
            result["problems"].append(
                f"measured median {median_fps:g} FPS is below the configured "
                f"{minimum_fps_ratio:.0%} cap-attainment threshold"
            )
        else:
            result["rateAttainment"] = "measured"

    ends = [row["songEnd"] for row in results if isinstance(row.get("songEnd"), dict)]
    if len(ends) != len(FPS_CAPS):
        return problems + ["natural song-end evidence is missing for one or more caps"]

    first_song = ends[0].get("song")
    event_counts = [(row.get("dispatchedEvents"), row.get("dueEvents"), row.get("totalEvents"))
                    for row in ends]
    if any(row.get("song") != first_song for row in ends):
        problems.append("different songs reached the natural end across cap runs")
    if len(set(event_counts)) != 1:
        problems.append(f"event counts changed across caps: {event_counts}")
    for cap, end in zip(FPS_CAPS, ends):
        dispatched = end.get("dispatchedEvents")
        due = end.get("dueEvents")
        if not isinstance(due, int) or due < 0:
            problems.append(f"{cap} FPS: due chart-event count is missing")
        elif expected_due_events is not None and due != expected_due_events:
            problems.append(f"{cap} FPS: due event count was {due}, expected {expected_due_events}")
        if not isinstance(dispatched, int) or not isinstance(due, int) or dispatched < due:
            problems.append(f"{cap} FPS: dispatched event count {dispatched!r} is below due count {due!r}")
        position = end.get("positionMs")
        length = end.get("songLengthMs")
        if not isinstance(position, (int, float)) or not isinstance(length, (int, float)):
            problems.append(f"{cap} FPS: song-end timing fields are missing")
        elif abs(position - length) > tolerance_ms:
            problems.append(
                f"{cap} FPS: song position differs from audio length by {abs(position - length):.1f} ms"
            )

    song_lengths = [float(row["songLengthMs"]) for row in ends
                    if isinstance(row.get("songLengthMs"), (int, float))]
    end_positions = [float(row["positionMs"]) for row in ends
                     if isinstance(row.get("positionMs"), (int, float))]
    if len(song_lengths) == len(FPS_CAPS) and max(song_lengths) - min(song_lengths) > tolerance_ms:
        problems.append("audio length varied beyond the configured timing tolerance")
    if len(end_positions) == len(FPS_CAPS) and max(end_positions) - min(end_positions) > tolerance_ms:
        problems.append("natural end position varied beyond the configured timing tolerance")
    return problems


def _runtime_lock(binary: Path):
    lock_name = "runtime-1.lock" if "/debug/" in str(binary) else "runtime-0.lock"
    return (ROOT / ".tools" / lock_name).open("a+")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song_folder", nargs="?", default="tutorial")
    parser.add_argument("chart", nargs="?", default="tutorial")
    parser.add_argument("difficulty", nargs="?", default="normal")
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--runtime-root", type=Path, default=None)
    parser.add_argument("--duration-ms", type=int, default=120_000,
                        help="smoke watchdog; natural song completion ends earlier")
    parser.add_argument("--timeout-seconds", type=float, default=150.0)
    parser.add_argument("--expected-due-events", type=int, default=0,
                        help="expected event count at natural song end; use -1 to accept any nonnegative count")
    parser.add_argument("--timing-tolerance-ms", type=float, default=100.0)
    parser.add_argument("--minimum-fps-ratio", type=float, default=0.75)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    binary = args.binary.expanduser().resolve()
    runtime_root = (args.runtime_root or binary.parent).expanduser().resolve()
    output = args.output.expanduser().resolve()
    project_tmp = (ROOT / "tmp").resolve()
    if output != project_tmp and project_tmp not in output.parents:
        parser.error("report output must be under the project tmp/ directory")
    if args.duration_ms < 250 or args.duration_ms > 600_000:
        parser.error("--duration-ms must be between 250 and 600000")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    if args.expected_due_events < -1:
        parser.error("--expected-due-events must be -1 or nonnegative")
    if args.timing_tolerance_ms < 0:
        parser.error("--timing-tolerance-ms cannot be negative")
    if not (0 < args.minimum_fps_ratio <= 1):
        parser.error("--minimum-fps-ratio must be in (0, 1]")

    case = SmokeCase("fps-cap-parity", "FPS cap parity", args.song_folder,
                     args.chart, args.difficulty, timeout_seconds=args.timeout_seconds)
    expected_events = None if args.expected_due_events == -1 else args.expected_due_events
    options_before = _runtime_options_snapshot(runtime_root)
    results: list[dict[str, Any]] = []
    with _runtime_lock(binary) as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        for cap in FPS_CAPS:
            results.append(_run_cap(
                binary,
                runtime_root,
                case,
                cap,
                args.duration_ms,
                args.timeout_seconds,
                strict_diagnostics=True,
            ))
    options_after = _runtime_options_snapshot(runtime_root)
    settings_unchanged = options_before == options_after
    problems = _check_parity(results, expected_events, args.timing_tolerance_ms,
                             args.minimum_fps_ratio)
    if not settings_unchanged:
        problems.append("installed runtime options.json changed during the parity run")
    rate_statuses = [result.get("rateAttainment") for result in results]
    status = "failed" if problems else (
        "inconclusive" if "inconclusive" in rate_statuses else "passed"
    )
    report = {
        "status": status,
        "problems": problems,
        "songFolder": args.song_folder,
        "chart": args.chart,
        "difficulty": args.difficulty,
        "expectedDueEvents": expected_events,
        "timingToleranceMs": args.timing_tolerance_ms,
        "installedSettingsUnchanged": settings_unchanged,
        "caps": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({
        "status": status,
        "problems": problems,
        "songFolder": args.song_folder,
        "chart": args.chart,
        "report": str(output),
        "measuredFps": {str(row["fpsCap"]): row.get("measuredFpsMedian") for row in results},
    }, sort_keys=True))
    return 0 if status == "passed" else (2 if status == "inconclusive" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
