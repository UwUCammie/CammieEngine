#!/usr/bin/env python3
"""Play inventoried example charts to natural audio completion offscreen.

The chart matrix is an inventory snapshot, so each row is checked against the
current runtime owner and media before launch. A missing or mismatched row is
reported as blocked, never as a passing gameplay test. Each launch uses the
existing private default-options overlay and the same build lock as run.sh.
An opt-in direct mode reuses a physically isolated runtime under repository tmp.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import fcntl
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import subprocess
import sys

from run_runtime_smoke_matrix import (
    DEFAULT_BINARY,
    ROOT,
    SmokeCase,
    parse_markers,
    run_case,
    _run_case_in_overlay,
)


DEFAULT_MATRIX = ROOT / "tmp" / "example_mods_current_chart_matrix.json"
RESULTS = ROOT / "tmp" / "example-full-playthrough.jsonl"
SCRIPT_ERROR = re.compile(
    r"hscript error in |lua(?: script)? error|hxc(?: script)? error|"
	r"uncaught exception|Null Function Pointer|Invalid field:|EUnknownVariable\(|\[hscript-null-(?:access|operand|iterator)\]|\[hxc-window\]\s*missing icon:|\[codename-asset\]\s*Missing scoped asset|"
    r"\[(?:codename-[^]]*(?:error|unsupported)[^]]*|hxc-[^]]*(?:error|unsupported)[^]]*|"
    r"nightmare-vision-[^]]*(?:error|unsupported)[^]]*|"
    r"codename-character-source-fallback|codename-character-fallback-unavailable|"
    r"codename-native-character|"
    r"codename-actor-runtime|character-resolution|missing-donor-dependency|"
    r"psych-stage|psych-stage-video|psych-stage-unsupported-[^]]+|psych-stage-json-only|"
    r"hxc-video-missing|hxc-path-unsafe|"
    r"unsupported-engine-dependency)\]|unavailable imported class dependency",
    re.IGNORECASE,
)


def load_rows(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != 1 or not isinstance(payload.get("rows"), list):
        raise ValueError(f"invalid example chart matrix: {path}")
    return payload["rows"]


def _within(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe runtime path: {relative}")
    resolved = (root / path).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"runtime path escapes root: {relative}")
    return resolved


def _audio_duration(path: Path) -> float:
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if completed.returncode != 0:
        raise ValueError(f"cannot probe instrumental: {path}: {completed.stderr.strip()[:160]}")
    try:
        duration = float(completed.stdout.strip())
    except ValueError as error:
        raise ValueError(f"instrumental has no duration: {path}") from error
    if not 0 < duration < 3600:
        raise ValueError(f"unreasonable instrumental duration: {path}: {duration}")
    return duration


def script_errors(output: str, engine: str | None = None) -> list[str]:
    """Keep a bounded list of interpreter failures hidden by a native success.

    Codename deliberately substitutes its configured DEFAULT_CHARACTER when a
    requested character XML is absent. The importer reports that source
    behavior explicitly; it is informational only for Codename rows.
    """
    errors = [line[:400] for line in output.splitlines()
              if not line.startswith("RUNTIME_SMOKE|") and SCRIPT_ERROR.search(line)]
    if engine == "Codename Engine":
        errors = [line for line in errors if "[codename-character-source-fallback]" not in line]
    return errors[:20]


def input_delivered(output: str, key: str, trigger: str | None = None) -> bool:
    for line in output.splitlines():
        if not line.startswith("OFFSCREEN_INPUT|"):
            continue
        try:
            action = json.loads(line.split("|", 1)[1])
        except json.JSONDecodeError:
            continue
        if (action.get("key") == key and action.get("delivered") is True
                and (trigger is None or action.get("trigger") == trigger)):
            return True
    return False


def process_timeout_for_ready_window(window_seconds: float) -> float:
    """Cover native startup watchdog, full ready gameplay window, and teardown."""

    return 2 * window_seconds + 155.0


def psych_loaded_chart_mismatches(song: dict, markers: list[dict]) -> list[str]:
    """Compare the loaded chart before intro scripts can swap its actors."""
    loaded = next((marker for marker in markers if marker.get("event") == "playstate_start"), {})
    problems: list[str] = []
    for field, marker_field in (("player1", "chartPlayer1"), ("player2", "chartPlayer2"),
                                ("gf", "chartGf")):
        expected = song.get(field)
        if not isinstance(expected, str) or not expected.strip():
            continue
        observed = loaded.get(marker_field)
        if not isinstance(observed, str) or observed.casefold() != expected.casefold():
            problems.append(f"loaded {field} differs from selected chart: "
                            f"expected {expected!r}, got {observed!r}")
    return problems


def preflight(row: dict, runtime_root: Path) -> tuple[Path | None, float | None, str | None]:
    """Resolve only the current selected chart and its real instrumental."""
    for key in ("runtimeChartPresent", "ownerMatched", "sourceVariantImported"):
        if row.get(key) is not True:
            return None, None, f"inventory does not establish {key}"
    # V-Slice's two-strumline source runtime routes only d=0..7. Preserve
    # raw chart rows in the inventory, but compare native gameplay notes to
    # the source rows its PlayState actually forwards to a strumline.
    gameplay_count = row.get("sourceGameplayNoteCount")
    if (row.get("group") == "V-Slice" and isinstance(gameplay_count, int)
            and not isinstance(gameplay_count, bool)):
        if row.get("sourceGameplayNoteCountMatched") is not True:
            return None, None, "inventory does not establish sourceGameplayNoteCountMatched"
        expected_count = gameplay_count
    else:
        if row.get("sourceNoteCountMatched") is not True:
            return None, None, "inventory does not establish sourceNoteCountMatched"
        expected_count = row.get("sourceNoteCount")
    relative = row.get("runtimeChart", "")
    if not isinstance(relative, str) or not relative.startswith("assets/data/"):
        return None, None, "inventory has no safe runtime chart path"
    try:
        chart = _within(runtime_root, relative)
        if not chart.is_file():
            return None, None, f"runtime chart missing: {relative}"
        # Legacy fixed-buffer charts can carry terminal NUL padding. The
        # engine's JSON boundary trims it, so the preflight must judge the
        # same chart bytes that native gameplay accepts.
        chart_data = json.loads(chart.read_text(encoding="utf-8").rstrip("\x00\t\r\n "))
        song = chart_data["song"]
        if not isinstance(song, dict):
            return None, None, f"malformed chart song object: {relative}"
        sections = song.get("notes")
        if not isinstance(sections, list):
            return None, None, f"malformed chart notes: {relative}"
        if any(not isinstance(section, dict) or not isinstance(section.get("sectionNotes"), list)
               for section in sections):
            return None, None, f"malformed chart section notes: {relative}"
        current_count = sum(len(section["sectionNotes"]) for section in sections)
        if current_count != expected_count:
            return None, None, f"runtime note count changed for {relative}: {current_count}"
        manifest = chart.parent / "compatScripts.json"
        owner = json.loads(manifest.read_text(encoding="utf-8")).get("selectedRoot")
        if owner != row.get("runtimeOwner"):
            return None, None, f"selected owner changed for {relative}"
        song_name = song.get("song")
        if not isinstance(song_name, str) or not song_name or "/" in song_name or ".." in song_name:
            return None, None, f"invalid chart song audio key: {relative}"
        audio_names = (f"{song_name}_Inst.ogg", "Inst.ogg")
        # A collision-safe import can keep the source song title in the chart
        # while storing this owner's audio under its qualified chart folder.
        folder = _within(runtime_root, f"assets/songs/{chart.parent.name}")
        audio = next((folder / name for name in audio_names if (folder / name).is_file()), None)
        if audio is None:
            audio = next((runtime_root / "assets/music" / name for name in audio_names
                          if (runtime_root / "assets/music" / name).is_file()), None)
        if audio is None:
            return None, None, f"instrumental missing for {relative}"
        return chart, _audio_duration(audio), None
    except (OSError, ValueError, KeyError, TypeError) as error:
        return None, None, str(error)


def validate_direct_private_runtime(runtime_root: Path, binary: Path) -> None:
    """Never run direct-mode cases against the live export or linked assets."""
    private_root = (ROOT / "tmp").resolve()
    runtime = runtime_root.resolve()
    if runtime == private_root or not runtime.is_relative_to(private_root):
        raise ValueError("direct mode requires a runtime below repository tmp")
    if runtime_root.is_symlink() or not binary.resolve().is_relative_to(runtime):
        raise ValueError("direct runtime binary must be inside its private root")
    options = runtime / "assets/data/options.json"
    if not options.is_file() or options.is_symlink():
        raise ValueError("direct runtime needs its own regular options.json")
    if any((runtime / name).is_symlink() for name in ("xdg-data", "xdg-config")):
        raise ValueError("direct runtime save directories must not be symlinks")
    for path in runtime.rglob("*"):
        if path.is_symlink() and not path.resolve().is_relative_to(runtime):
            raise ValueError(f"direct runtime links outside its private root: {path}")


def direct_private_case(binary: Path, case: SmokeCase, duration_ms: int,
                        timeout_seconds: float, runtime_root: Path,
                        input_key: str | None, repeat_key: str | None,
                        extra_flags: tuple[str, ...],
                        input_trigger: str = "playstate_ready",
                        post_key: str | None = None) -> dict:
    # Every launch starts with the repository's default options and a fresh
    # OpenFL save scope. Shader/font caches may persist in the private copy.
    (runtime_root / "assets/data/options.json").write_bytes(
        (ROOT / "assets/data/options.json").read_bytes())
    for name in ("xdg-data", "xdg-config"):
        path = runtime_root / name
        if path.exists():
            shutil.rmtree(path)
        path.mkdir()
    for name in ("xdg-cache", "scratch"):
        (runtime_root / name).mkdir(exist_ok=True)
    return _run_case_in_overlay(
        binary, case, duration_ms, runtime_root, runtime_root,
        timeout_seconds=timeout_seconds, input_key=input_key,
        input_trigger=input_trigger, repeat_key=repeat_key, post_key=post_key,
        strict_diagnostics=True,
        extra_flags=extra_flags)


def file_sha256(path: Path) -> str | None:
    """Hash a selected test input, never a whole installed asset tree."""
    if not path.is_file():
        return None
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run_row(row: dict, index: int, runtime_root: Path, binary: Path, rate: float,
            input_key: str | None = None, repeat_key: str | None = None,
            direct_private: bool = False, dismiss_ending: bool = False,
            binary_sha256: str | None = None) -> dict:
    identity = {key: row.get(key) for key in ("group", "package", "song", "variant", "difficulty", "runtimeChart")}
    chart, audio_seconds, blocker = preflight(row, runtime_root)
    result = {**identity, "status": "blocked", "reason": blocker}
    if blocker is not None or chart is None or audio_seconds is None:
        return result
    # Capture inputs before launch. These hashes establish binary/chart identity,
    # not the identity or parity of every dependency in an imported package.
    provenance = {
        "recordedAt": datetime.now(timezone.utc).isoformat(),
        "binarySha256": binary_sha256 if binary_sha256 is not None else file_sha256(binary),
        "runtimeChartSha256": file_sha256(chart),
        "compatManifestSha256": file_sha256(chart.parent / "compatScripts.json"),
        "defaultOptionsSha256": file_sha256(ROOT / "assets/data/options.json"),
        "runtimeOwner": row.get("runtimeOwner"),
        "testMode": "accelerated-completion" if rate > 1 else "normal-speed-completion",
        "playbackRate": rate,
        "botplay": True,
        "practice": True,
        "allDependenciesFingerprinted": False,
    }
    chart_name = chart.stem
    folder = chart.parent.name
    safe_id = re.sub(r"[^a-z0-9-]+", "-", f"{index}-{folder}-{chart_name}".lower()).strip("-")
    case = SmokeCase(safe_id, str(row.get("group", "example")), folder, chart_name,
                     str(row.get("difficulty", "normal")))
    # Allow loading/countdown time in addition to the sped-up audio. The
    # harness itself requires the real song-end callback, so a short window
    # becomes a failure rather than a false pass.
    window_seconds = max(45.0, audio_seconds / rate * 1.5 + 25.0)
    if repeat_key is not None:
        window_seconds += 30.0  # bounded room for multi-line source dialogue
    # RuntimeSmokeHarness permits startup to consume one requested gameplay
    # window plus 120 seconds, then starts a fresh window at PlayState ready.
    # The process watchdog must encompass both windows and teardown or it
    # would still kill valid slow-loading charts before their natural ending.
    process_timeout_seconds = process_timeout_for_ready_window(window_seconds)
    flags = ("--smoke-song-rate", str(rate), "--smoke-practice",
             "--smoke-botplay", "--smoke-require-song-end")
    has_intro_input = input_key is not None or repeat_key is not None
    trigger = "song_end" if dismiss_ending and not has_intro_input else "playstate_ready"
    key = "Return" if dismiss_ending and not has_intro_input else input_key
    post_key = "Return" if dismiss_ending and has_intro_input else None
    if dismiss_ending:
        flags += ("--smoke-require-end-handoff",)
    if direct_private:
        smoke = direct_private_case(binary, case, round(window_seconds * 1000),
                                    process_timeout_seconds, runtime_root,
                                    key, repeat_key, flags, input_trigger=trigger,
                                    post_key=post_key)
    else:
        smoke = run_case(binary, case, round(window_seconds * 1000),
                         timeout_seconds=process_timeout_seconds,
                         runtime_root=runtime_root,
                         input_key=key,
                         input_trigger=trigger,
                         repeat_key=repeat_key,
                         post_key=post_key,
                         strict_diagnostics=True, extra_flags=flags)
    process_log = ROOT / "tmp/runtime-smoke/logs" / f"{safe_id}.process.log"
    process_output = process_log.read_text(encoding="utf-8") if process_log.is_file() else ""
    markers = parse_markers(process_output)
    endings = [marker for marker in markers if marker.get("event") == "song_end"]
    handoffs = [marker for marker in markers if marker.get("event") == "end_handoff"]
    interpreter_errors = script_errors(process_output, str(row.get("group", "")))
    problems: list[str] = []
    if smoke.get("status") != "passed":
        problems.append(str(smoke.get("reason", "native launch failed")))
    if len(endings) != 1:
        problems.append(f"expected one natural song_end marker, got {len(endings)}")
    elif endings[0].get("dispatchedEvents") != endings[0].get("dueEvents"):
        problems.append("natural ending left events due before audio completion undispatched")
    if dismiss_ending and len(handoffs) != 1:
        problems.append(f"expected one end_handoff marker after natural song_end, got {len(handoffs)}")
    elif dismiss_ending and endings:
        song_end_index = next(i for i, marker in enumerate(markers)
                              if marker.get("event") == "song_end")
        handoff_index = next(i for i, marker in enumerate(markers)
                             if marker.get("event") == "end_handoff")
        if handoff_index <= song_end_index:
            problems.append("end_handoff marker preceded native song_end")
    if interpreter_errors:
        problems.append(f"{len(interpreter_errors)} interpreter error line(s)")
    if row.get("group") == "Psych Engine":
        song = json.loads(chart.read_text(encoding="utf-8"))["song"]
        problems.extend(psych_loaded_chart_mismatches(song, markers))
    if input_key is not None and not input_delivered(process_output, input_key):
        problems.append("requested private intro input was not delivered")
    ending_input_delivered = dismiss_ending and input_delivered(
        process_output, "Return", trigger="song_end")
    if dismiss_ending and not ending_input_delivered:
        problems.append("requested ending Return was not delivered after native song_end")
    # Accept is offered only while a song remains behind dialogue. A song that
    # started before the first interval correctly needs no synthetic input.
    dialogue_input_delivered = repeat_key is not None and input_delivered(
        process_output, repeat_key, trigger="repeat until song_start")
    return {
        **identity, "status": "failed" if problems else "passed",
        "reason": "; ".join(problems) if problems else None,
        "provenance": provenance,
        "audioSeconds": audio_seconds, "songRate": rate,
        "native": smoke, "songEnd": endings[0] if endings else None,
        "endHandoff": handoffs[0] if len(handoffs) == 1 else None,
        "processLog": str(process_log), "interpreterErrors": interpreter_errors,
        "dialogueInputDelivered": dialogue_input_delivered,
        "endingInputDelivered": ending_input_delivered,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_BINARY.parent)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--package", action="append", help="case-insensitive package substring; repeatable")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--rate", type=float, default=5.0)
    parser.add_argument("--output", type=Path, default=RESULTS)
    parser.add_argument("--dry-run", action="store_true", help="preflight rows without launching the game")
    parser.add_argument("--direct-private-runtime", action="store_true",
                        help="reuse a physically isolated runtime below repository tmp")
    parser.add_argument("--skip-intro-dialogue", action="store_true",
                        help="send the default SECONDARY key in private Xvfb after PlayState is ready")
    parser.add_argument("--advance-dialogue", action="store_true",
                        help="press Accept at bounded intervals in private Xvfb until song_start")
    parser.add_argument("--dismiss-ending", action="store_true",
                        help="send Return after native song_end and require an end_handoff marker")
    args = parser.parse_args()
    if args.skip_intro_dialogue and args.advance_dialogue:
        parser.error("choose one intro input mode")
    if not 1 <= args.rate <= 50 or args.start < 0 or (args.limit is not None and args.limit < 1):
        parser.error("rate must be 1–50, start nonnegative, and limit positive")
    runtime_root = args.runtime_root.resolve()
    binary = args.binary.resolve()
    if args.direct_private_runtime and not args.dry_run:
        try:
            validate_direct_private_runtime(runtime_root, binary)
        except ValueError as error:
            parser.error(str(error))
    rows = load_rows(args.matrix)
    if args.package:
        needles = [value.casefold() for value in args.package]
        rows = [row for row in rows if any(needle in str(row.get("package", "")).casefold()
                                            for needle in needles)]
    rows = rows[args.start: args.start + args.limit if args.limit is not None else None]
    if not rows:
        parser.error("no inventory rows selected")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lock_name = "runtime-1.lock" if "/debug/" in str(binary) else "runtime-0.lock"
    # Dry-run only reads the current inventory and runtime files. It can
    # preflight during a build; the lock belongs to launches that map the
    # native binary and copied runtime assets.
    lock_context = nullcontext() if args.dry_run else (ROOT / ".tools" / lock_name).open("a+")
    with lock_context as lock, args.output.open("w", encoding="utf-8") as output:
        if lock is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        # One binary hash per locked batch avoids rereading it for every song.
        binary_sha256 = None if args.dry_run else file_sha256(binary)
        results = []
        for index, row in enumerate(rows, args.start):
            if args.dry_run:
                _, seconds, reason = preflight(row, runtime_root)
                result = {**{key: row.get(key) for key in ("package", "song", "variant", "difficulty")},
                          "status": "blocked" if reason else "ready",
                          "reason": reason, "audioSeconds": seconds}
            else:
                result = run_row(row, index, runtime_root, binary, args.rate,
                                 "e" if args.skip_intro_dialogue else None,
                                 "Return" if args.advance_dialogue else None,
                                 direct_private=args.direct_private_runtime,
                                 dismiss_ending=args.dismiss_ending,
                                 binary_sha256=binary_sha256)
            output.write(json.dumps(result, sort_keys=True) + "\n")
            output.flush()
            print(json.dumps(result, sort_keys=True), flush=True)
            results.append(result)
    counts = {name: sum(item["status"] == name for item in results)
              for name in ("ready", "passed", "failed", "blocked")}
    print(json.dumps({"full_playthrough_summary": counts}, sort_keys=True))
    return 0 if counts["failed"] == counts["blocked"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
