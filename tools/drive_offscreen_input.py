#!/usr/bin/env python3
"""Drive native smoke inputs inside an already private Xvfb display.

The caller supplies the game command after -- and owns the display, runtime
overlay, build lock, and timeout. This wrapper never connects to a desktop
display; it requires DISPLAY from the caller's isolated X server.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time


def marker_seen(path: Path, event: str) -> bool:
    if not path.is_file():
        return False
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.startswith("RUNTIME_SMOKE|"):
                continue
            try:
                payload = json.loads(line.split("|", 1)[1])
            except json.JSONDecodeError:
                continue
            if payload.get("event") == event:
                return True
    return False


def send_key(key: str, game_pid: int,
             env: dict[str, str] | None = None) -> tuple[bool, str, str]:
    """Focus the sole visible game window and hold through several frames."""
    windows = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(game_pid)],
                             capture_output=True, text=True, timeout=5, check=False, env=env)
    ids = [line.strip() for line in windows.stdout.splitlines() if line.strip().isdigit()]
    if windows.returncode or not ids:
        return False, "", "no visible window on private display"
    window = ids[-1]
    focus = subprocess.run(["xdotool", "windowfocus", "--sync", window],
                           capture_output=True, text=True, timeout=5, check=False, env=env)
    if focus.returncode:
        return False, window, focus.stderr.strip()[:200]
    down = subprocess.run(["xdotool", "keydown", "--clearmodifiers", key],
                          capture_output=True, text=True, timeout=5, check=False, env=env)
    time.sleep(0.25)
    up = subprocess.run(["xdotool", "keyup", "--clearmodifiers", key],
                        capture_output=True, text=True, timeout=5, check=False, env=env)
    return (down.returncode == 0 and up.returncode == 0, window,
            (down.stderr + up.stderr).strip()[:200])


def _forward_child_output(stream, output_lock: threading.Lock) -> None:
    """Forward complete child lines promptly, serialized with input receipts."""

    try:
        for line in iter(stream.readline, ""):
            with output_lock:
                sys.stdout.write(line)
                sys.stdout.flush()
    except BrokenPipeError:
        # The outer runner may close its capture pipe while terminating this
        # process group after a timeout.
        return


def _emit_input(payload: dict, output_lock: threading.Lock) -> None:
    """Keep wrapper records on whole lines between forwarded game lines."""

    line = "OFFSCREEN_INPUT|" + json.dumps(payload) + "\n"
    with output_lock:
        sys.stdout.write(line)
        sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marker-log", type=Path, required=True)
    parser.add_argument("--trigger", default="playstate_ready")
    parser.add_argument("--key")
    parser.add_argument("--delay-seconds", type=float, default=4.0)
    parser.add_argument("--followup-key")
    parser.add_argument("--followup-delay-seconds", type=float, default=2.0)
    parser.add_argument("--repeat-key")
    parser.add_argument("--repeat-start-delay-seconds", type=float, default=12.0)
    parser.add_argument("--repeat-interval-seconds", type=float, default=0.6)
    parser.add_argument("--repeat-until-marker", default="song_start")
    parser.add_argument("--repeat-limit", type=int, default=40)
    parser.add_argument("--post-key")
    parser.add_argument("--post-trigger", default="song_end")
    parser.add_argument("--post-delay-seconds", type=float, default=4.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if (not command or not os.environ.get("DISPLAY") or not (args.key or args.repeat_key or args.post_key)
            or not 0 <= args.delay_seconds <= 30
            or not 0 <= args.post_delay_seconds <= 30
            or not 0 <= args.followup_delay_seconds <= 30
            or not 0 <= args.repeat_start_delay_seconds <= 30
            or not 0.25 <= args.repeat_interval_seconds <= 10
            or not 1 <= args.repeat_limit <= 80):
        parser.error("a game command, private DISPLAY, and a 0–30 second delay are required")
    supported = {"e", "Return", "Escape", "space"}
    if ((args.key is not None and args.key not in supported)
            or (args.followup_key is not None and args.followup_key not in supported)
            or (args.repeat_key is not None and args.repeat_key not in supported)
            or (args.post_key is not None and args.post_key not in supported)
            or (args.followup_key is not None and args.key is None)):
        parser.error("unsupported test input key")
    game = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    if game.stdout is None:
        raise RuntimeError("could not capture game stdout")
    output_lock = threading.Lock()
    output_thread = threading.Thread(target=_forward_child_output,
                                     args=(game.stdout, output_lock), daemon=True)
    output_thread.start()
    sent = args.key is None
    followup_sent = args.followup_key is None
    triggered_at = None
    sent_at = None
    repeat_count = 0
    next_repeat_at = None
    repeat_delivered = True
    post_triggered_at = None
    post_sent = args.post_key is None
    while game.poll() is None:
        if triggered_at is None and marker_seen(args.marker_log, args.trigger):
            triggered_at = time.monotonic()
        if triggered_at is not None and not sent and time.monotonic() - triggered_at >= args.delay_seconds:
            sent, window, delivery_error = send_key(args.key, game.pid)
            _emit_input({"key": args.key, "trigger": args.trigger, "delivered": sent,
                         "window": window, "error": delivery_error}, output_lock)
            if not sent:
                break
            sent_at = time.monotonic()
        if (sent_at is not None and not followup_sent
                and time.monotonic() - sent_at >= args.followup_delay_seconds):
            followup_sent, window, delivery_error = send_key(args.followup_key, game.pid)
            _emit_input({"key": args.followup_key, "trigger": f"after {args.key}",
                         "delivered": followup_sent, "window": window,
                         "error": delivery_error}, output_lock)
            if not followup_sent:
                break
        if (args.repeat_key is not None and triggered_at is not None
                and repeat_count < args.repeat_limit
                and not marker_seen(args.marker_log, args.repeat_until_marker)):
            now = time.monotonic()
            if next_repeat_at is None:
                next_repeat_at = triggered_at + args.repeat_start_delay_seconds
            if now >= next_repeat_at:
                repeat_delivered, window, delivery_error = send_key(args.repeat_key, game.pid)
                repeat_count += 1
                next_repeat_at = time.monotonic() + args.repeat_interval_seconds
                _emit_input({"key": args.repeat_key,
                             "trigger": f"repeat until {args.repeat_until_marker}",
                             "attempt": repeat_count, "delivered": repeat_delivered,
                             "window": window, "error": delivery_error}, output_lock)
                if not repeat_delivered:
                    break
        if args.post_key is not None and post_triggered_at is None and marker_seen(args.marker_log, args.post_trigger):
            post_triggered_at = time.monotonic()
        if (post_triggered_at is not None and not post_sent
                and time.monotonic() - post_triggered_at >= args.post_delay_seconds):
            post_sent, window, delivery_error = send_key(args.post_key, game.pid)
            _emit_input({"key": args.post_key, "trigger": args.post_trigger,
                         "delivered": post_sent, "window": window,
                         "error": delivery_error}, output_lock)
            if not post_sent:
                break
        time.sleep(0.02)
    if game.poll() is None:
        game.terminate()
    try:
        game.wait(timeout=10)
    except subprocess.TimeoutExpired:
        game.kill()
        game.wait()
    output_thread.join(timeout=10)
    if not output_thread.is_alive():
        game.stdout.close()
    return game.returncode if ((sent and followup_sent and repeat_delivered and post_sent)
                            or (triggered_at is None and post_triggered_at is None)) else 1


if __name__ == "__main__":
    sys.exit(main())
