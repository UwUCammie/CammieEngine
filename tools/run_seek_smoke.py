#!/usr/bin/env python3
"""Run one marker-validated native offscreen in-song seek smoke."""

from __future__ import annotations

import argparse
import fcntl
import json
import math
from pathlib import Path

from run_runtime_smoke_matrix import DEFAULT_BINARY, LOG_ROOT, ROOT, SmokeCase, parse_markers, run_case


def _number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def validate_seek_markers(
    markers: list[dict],
    after_ms: float,
    target_ms: float,
    tolerance_ms: float = 150,
    minimum_crossed_events: int = 1,
    minimum_discarded_notes: int = 1,
    expect_vocals: bool = True,
) -> tuple[list[str], dict | None]:
    """Check the seek snapshot's clocks, event cursor, and note retirement."""

    seeks = [marker for marker in markers if marker.get("event") == "seek_complete"]
    if len(seeks) != 1:
        return [f"expected one seek_complete marker, found {len(seeks)}"], None
    snapshot = seeks[0]
    problems: list[str] = []
    song_starts = [marker for marker in markers if marker.get("event") == "song_start"]
    if len(song_starts) != 1:
        problems.append(f"expected one song_start marker before seek, found {len(song_starts)}")
    elif markers.index(song_starts[0]) > markers.index(snapshot):
        problems.append("seek_complete marker preceded song_start")
    elif song_starts[0].get("musicPlaying") is not True:
        problems.append("song_start marker did not observe playing instrumental audio")
    if snapshot.get("eventVideoActive") is not False:
        problems.append("seek did not prove that no event video was active")
    if expect_vocals and snapshot.get("hasVocals") is not True:
        problems.append("selected chart did not expose a vocal track")
    if expect_vocals and snapshot.get("sourceNeedsVoices") is not True:
        problems.append("source chart does not request vocals")
    # PlayState retains a silent FlxSound/VocalTracks placeholder even for
    # charts with needsVoices=false. The source flag, not object existence,
    # distinguishes an instrumental-only seek.
    if not expect_vocals and snapshot.get("sourceNeedsVoices") is not False:
        problems.append("source chart still requests vocals")

    clock_fields = ("fromMs", "targetMs", "musicTimeBeforeMs", "musicTimeMs",
                    "conductorPositionMs", "conductorLastPositionMs", "songTimeMs")
    if expect_vocals:
        clock_fields += ("vocalTimeMs",)
    invalid_clocks = False
    for key in clock_fields:
        if not _number(snapshot.get(key)):
            problems.append(f"seek snapshot has no finite {key}")
            invalid_clocks = True
    if invalid_clocks:
        return problems, snapshot

    if abs(snapshot["targetMs"] - target_ms) > tolerance_ms:
        problems.append("seek target did not match the requested landing time")
    if snapshot["musicTimeBeforeMs"] + tolerance_ms < after_ms:
        problems.append("seek ran before the instrumental crossed its trigger marker")
    if snapshot["fromMs"] > snapshot["musicTimeBeforeMs"] + tolerance_ms:
        problems.append("Conductor source position was ahead of the instrumental clock")
    if snapshot["targetMs"] <= snapshot["fromMs"]:
        problems.append("seek did not move forward from its source position")
    synchronized_clocks = ("musicTimeMs", "conductorPositionMs",
                           "conductorLastPositionMs", "songTimeMs")
    if expect_vocals:
        synchronized_clocks += ("vocalTimeMs",)
    for key in synchronized_clocks:
        if abs(snapshot[key] - target_ms) > tolerance_ms:
            problems.append(f"{key} did not resynchronize to the seek target")

    integer_fields = ("eventIndexBefore", "eventIndexAfter", "totalEvents", "crossedEvents",
                      "firedEvents", "skippedVideoEvents", "removedUnspawnNotes",
                      "removedActiveNotes", "discardedNotes", "staleUnspawnNotes",
                      "staleActiveNotes", "remainingNotes", "curStep", "curBeat", "curSection")
    invalid_integers = False
    for key in integer_fields:
        if type(snapshot.get(key)) is not int or snapshot[key] < 0:
            problems.append(f"seek snapshot has invalid {key}")
            invalid_integers = True
    if invalid_integers:
        return problems, snapshot

    before = snapshot["eventIndexBefore"]
    after = snapshot["eventIndexAfter"]
    total = snapshot["totalEvents"]
    crossed = snapshot["crossedEvents"]
    if before > total or after > total or after < before:
        problems.append("event cursor is outside the chart event list")
    if after - before != crossed:
        problems.append("event cursor delta does not match crossedEvents")
    if crossed < minimum_crossed_events:
        problems.append(f"seek crossed only {crossed} events; need {minimum_crossed_events}")
    if snapshot["firedEvents"] + snapshot["skippedVideoEvents"] != crossed:
        problems.append("crossed events do not reconcile with fired and skipped video events")

    discarded = snapshot["removedUnspawnNotes"] + snapshot["removedActiveNotes"]
    if snapshot["discardedNotes"] != discarded:
        problems.append("discardedNotes does not match the removed note counts")
    if discarded < minimum_discarded_notes:
        problems.append(f"seek discarded only {discarded} notes; need {minimum_discarded_notes}")
    if snapshot["staleUnspawnNotes"] or snapshot["staleActiveNotes"]:
        problems.append("notes earlier than the landing time remain active")
    if snapshot["remainingNotes"] < 1:
        problems.append("no note remains after the seek landing time")
    if not _number(snapshot.get("firstRemainingNoteMs")):
        problems.append("seek snapshot has no finite firstRemainingNoteMs")
    elif snapshot["firstRemainingNoteMs"] + tolerance_ms < target_ms:
        problems.append("first remaining note is earlier than the seek landing time")
    if snapshot["curBeat"] != snapshot["curStep"] // 4:
        problems.append("beat cursor does not match the updated step cursor")
    if not _number(snapshot.get("bpm")) or snapshot["bpm"] <= 0:
        problems.append("seek snapshot has an invalid BPM")
    return problems, snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song_folder")
    parser.add_argument("chart")
    parser.add_argument("difficulty")
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_BINARY.parent)
    parser.add_argument("--after-ms", type=float, default=2000,
                        help="instrumental source time that triggers the seek")
    parser.add_argument("--to-ms", type=float, default=20000,
                        help="forward landing time in the chart")
    parser.add_argument("--song-rate", type=float, default=10,
                        help="bounded playback acceleration while reaching the source marker")
    parser.add_argument("--tolerance-ms", type=float, default=150)
    parser.add_argument("--minimum-crossed-events", type=int, default=1)
    parser.add_argument("--minimum-discarded-notes", type=int, default=1)
    parser.add_argument("--expect-no-vocals", action="store_true",
                        help="require no vocal track and validate the remaining clocks")
    parser.add_argument("--timeout-seconds", type=float, default=60)
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/seek-smoke.json")
    parser.add_argument("--wine", action="store_true")
    args = parser.parse_args()

    for label, value in (("--after-ms", args.after_ms), ("--to-ms", args.to_ms)):
        if not math.isfinite(value) or not 0 <= value <= 600000:
            parser.error(f"{label} must be between 0 and 600000")
    if args.to_ms <= args.after_ms:
        parser.error("--to-ms must be greater than --after-ms")
    if not math.isfinite(args.song_rate) or not 1 <= args.song_rate <= 50:
        parser.error("--song-rate must be between 1 and 50")
    if not math.isfinite(args.tolerance_ms) or args.tolerance_ms < 0:
        parser.error("--tolerance-ms must be nonnegative")
    if args.minimum_crossed_events < 0 or args.minimum_discarded_notes < 0:
        parser.error("minimum event and note counts must be nonnegative")
    if args.timeout_seconds < 10:
        parser.error("--timeout-seconds must be at least 10")

    case = SmokeCase("in-song-seek", "general in-song seek", args.song_folder.strip().lower(),
                     args.chart.strip().lower(), args.difficulty, args.timeout_seconds)
    # Both operands are milliseconds. The accelerated source time must not be
    # multiplied by 1000 again, or the watchdog can outlive the whole song.
    duration_ms = max(10000, int(args.after_ms / args.song_rate) + 8000)
    flags = (
        "--smoke-practice", "--smoke-botplay", "--smoke-song-rate", str(args.song_rate),
        "--smoke-seek-after-ms", str(args.after_ms), "--smoke-seek-to-ms", str(args.to_ms),
    )
    lock_name = "runtime-1.lock" if "/debug/" in str(args.binary) else "runtime-0.lock"
    with (ROOT / ".tools" / lock_name).open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        native = run_case(
            args.binary.resolve(), case, duration_ms,
            timeout_seconds=args.timeout_seconds, wine=args.wine,
            runtime_root=args.runtime_root, extra_flags=flags,
            strict_diagnostics=True,
        )

    process_log = LOG_ROOT / f"{case.id}.process.log"
    output = process_log.read_text(encoding="utf-8") if process_log.is_file() else ""
    markers = parse_markers(output)
    problems: list[str] = []
    if native.get("status") != "passed":
        problems.append(native.get("reason", "native smoke failed"))
    marker_problems, seek = validate_seek_markers(
        markers, args.after_ms, args.to_ms, args.tolerance_ms,
        args.minimum_crossed_events, args.minimum_discarded_notes,
        expect_vocals=not args.expect_no_vocals,
    )
    problems.extend(marker_problems)
    result = {
        "status": "failed" if problems else "passed",
        "problems": problems,
        "songFolder": case.folder,
        "chart": case.chart,
        "difficulty": case.difficulty,
        "afterMs": args.after_ms,
        "targetMs": args.to_ms,
        "native": native,
        "seek": seek,
        "processLog": str(process_log),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "problems", "songFolder", "chart",
                                                   "difficulty", "processLog")}))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
