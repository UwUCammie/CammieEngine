#!/usr/bin/env python3
"""Exercise a real pause/resume input pair on a private offscreen game instance."""

from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path

from run_example_full_playthrough import process_timeout_for_ready_window
from run_runtime_smoke_matrix import DEFAULT_BINARY, ROOT, SmokeCase, parse_markers, run_case


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("song_folder")
    parser.add_argument("chart")
    parser.add_argument("difficulty")
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_BINARY.parent)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/pause-resume-smoke.json")
    args = parser.parse_args()
    case = SmokeCase("pause-resume", "example", args.song_folder, args.chart,
                     args.difficulty)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lock_name = "runtime-1.lock" if "/debug/" in str(args.binary) else "runtime-0.lock"
    with (ROOT / ".tools" / lock_name).open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        smoke = run_case(args.binary, case, 25000,
                         timeout_seconds=process_timeout_for_ready_window(25),
                         runtime_root=args.runtime_root,
                         input_key="Escape", input_delay_seconds=5,
                         followup_key="Return", followup_delay_seconds=2,
                         strict_diagnostics=True,
                         extra_flags=("--smoke-practice", "--smoke-botplay"))
    process_log = ROOT / "tmp/runtime-smoke/logs" / "pause-resume.process.log"
    output = process_log.read_text(encoding="utf-8") if process_log.is_file() else ""
    markers = parse_markers(output)
    pause = [row for row in markers if row.get("event") == "pause_open"]
    resume = [row for row in markers if row.get("event") == "pause_resume"]
    inputs = []
    for line in output.splitlines():
        if line.startswith("OFFSCREEN_INPUT|"):
            try:
                inputs.append(json.loads(line.split("|", 1)[1]))
            except json.JSONDecodeError:
                pass
    problems = []
    if smoke.get("status") != "passed":
        problems.append(smoke.get("reason", "native smoke failed"))
    if [row.get("key") for row in inputs if row.get("delivered")] != ["Escape", "Return"]:
        problems.append("private input pair was not delivered")
    if len(pause) != 1 or len(resume) != 1:
        problems.append(f"expected one pause/resume pair, got {len(pause)}/{len(resume)}")
    elif (pause[0].get("musicPlaying") is not False
          or resume[0].get("musicPlaying") is not True):
        problems.append("music was not stopped during pause and playing after resume")
    elif (not isinstance(pause[0].get("musicTimeMs"), (int, float))
          or not isinstance(resume[0].get("musicTimeMs"), (int, float))
          or abs(resume[0]["musicTimeMs"] - pause[0]["musicTimeMs"]) > 250):
        problems.append("music clock advanced while paused")
    result = {"status": "failed" if problems else "passed", "problems": problems,
              "songFolder": args.song_folder, "chart": args.chart,
              "difficulty": args.difficulty, "native": smoke,
              "inputs": inputs, "pause": pause, "resume": resume,
              "processLog": str(process_log)}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "problems", "songFolder",
                                                "chart", "difficulty", "processLog")}))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
