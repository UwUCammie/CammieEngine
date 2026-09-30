#!/usr/bin/env python3
"""Run the bounded native runtime smoke matrix after a build.

This runner deliberately does not build, alter registries, or play charts to
completion. Each case starts the already-built binary in the project's
``tmp/runtime-smoke/logs`` directory and requires machine-readable
startup/PlayState/success markers. The optional second case exercises cleanup
and a switch to another imported song in the same native process.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Iterable, Optional


ROOT = Path(__file__).resolve().parents[1]
SMOKE_ROOT = ROOT / "tmp" / "runtime-smoke"
LOG_ROOT = SMOKE_ROOT / "logs"
DEFAULT_BINARY = ROOT / "export" / "release" / "linux" / "bin" / "Funkin"
PREPARED_MANIFEST = "runtime-smoke-manifest.json"
DEFAULT_OPTIONS = ROOT / "assets" / "data" / "options.json"
PRIVATE_DIRS = ("xdg-data", "xdg-config", "xdg-cache", "scratch")
CHART_EDITOR_FIXTURE = {
    "events": [
        [1000, [["__dp_chart_editor_smoke_edit__", "source-v1", "source-v2", "source-v3"]]],
        [2000, [["__dp_chart_editor_smoke_delete__", "delete-v1", "delete-v2", "delete-v3"]]],
    ]
}


@dataclass(frozen=True)
class SmokeCase:
    id: str
    family: str
    folder: str
    chart: str
    difficulty: str = "normal"
    timeout_seconds: float = 30.0


# The first six entries cover the six imported engine families recorded in
# tools/reports/port-assets.md.  The following named regressions are kept as
# explicit rows even when a family representative overlaps their donor pack:
# this makes the final gate's report self-explanatory and preserves the exact
# chart/difficulty spelling needed by each regression.
SMOKE_MATRIX: tuple[SmokeCase, ...] = (
    SmokeCase("family-vslice", "V-Slice", "dokidoggle", "dokidoggle"),
    # PERFEXION ships only resonance-hard.json; keep the explicit hard chart
    # so this representative cannot silently fall back to a missing base file.
    SmokeCase("family-psych", "Psych Engine", "resonance", "resonance-hard", "hard"),
    SmokeCase("family-kade", "Kade Engine", "tutorial", "tutorial"),
    SmokeCase("family-legacy", "Legacy FNF/Polymod", "thorns", "thorns"),
    SmokeCase("family-modding-plus", "Modding Plus", "slaughter", "slaughter"),
    SmokeCase("family-fps-plus", "FPS Plus", "ballistic", "ballistic"),
    SmokeCase("example-expurgation", "example regression", "expurgation", "expurgation-hard", "hard"),
    SmokeCase("example-wacky-hard", "example regression", "wacky-world", "wacky-world-hard", "hard"),
    SmokeCase("example-wacky-nightmare", "example regression", "wacky-world", "wacky-world-nightmare", "nightmare"),
    SmokeCase("example-rabbit-hole", "example regression", "rabbit-hole", "rabbit-hole"),
    SmokeCase("example-fantasy-girl-01", "example regression", "fantasy-girl-01", "fantasy-girl-01"),
    SmokeCase("example-vs-freddy", "example regression", "slaughter", "slaughter"),
    SmokeCase("example-ballistic", "example regression", "ballistic", "ballistic"),
    SmokeCase("example-future-sound", "example regression", "future-sound", "future-sound"),
    SmokeCase("example-resonance", "example regression", "resonance", "resonance-hard", "hard"),
    SmokeCase("example-cursed-expurgation", "example regression", "cursed-expurgation", "cursed-expurgation-hard", "hard"),
    SmokeCase("chaos", "named regression", "chaos", "chaos-hard", "hard"),
    SmokeCase("inquiry", "named regression", "inquiry", "inquiry-hard", "hard"),
    SmokeCase("locked", "named regression", "locked", "locked-hard", "hard"),
    SmokeCase("cycles-wrath", "named regression", "cycles-wrath", "cycles-wrath-hard", "hard"),
    SmokeCase(
        "cycles-encore-springless",
        "named regression",
        "cycles-encore-springless",
        "cycles-encore-springless-encore",
        "encore",
    ),
    SmokeCase("popipo", "named regression", "popipo", "popipo-hard", "hard"),
    SmokeCase("fnia-ugh", "named regression", "fnia-ugh", "fnia-ugh-hard", "hard"),
)

# Stable, read-only donor evidence for the six mappings above.  These paths
# are documentation/test evidence only; the smoke runner never reads or
# writes them and never mutates donor charts.  The mounted corpus report is
# the authority for the family totals; these concrete files pin the selected
# representative IDs and prevent a future chart-name swap.
ENGINE_FAMILY_EVIDENCE: dict[str, str] = {
    "V-Slice": "FNF-Example-Mods/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/data/songs/dokidoggle/dokidoggle-chart.json",
    "Psych Engine": "FNF-Example-Mods/PERFEXION Demo1/data/Resonance/resonance-hard.json",
    "Kade Engine": "FNF-Example-Mods/hellbeats_kade_engine/HellBeats Kade Engine/assets/data/tutorial/tutorial.json",
    "Legacy FNF/Polymod": "FNF-Example-Mods/SeoS/assets/data/thorns/thorns.json",
    "Modding Plus": "FNF-Example-Mods/vsfreddy_1_9_5/assets/data/slaughter/slaughter.json",
    "FPS Plus": "FNF-Example-Mods/whitty/data/songs/ballistic/ballistic.json",
}

NAMED_REGRESSION_EVIDENCE: dict[str, str] = {
    "chaos": "/run/media/cammie/External Storage/modding-plus-fnf/assets/data/chaos/chaos-hard.json",
    "inquiry": "/run/media/cammie/External Storage/modding-plus-fnf/assets/data/inquiry/inquiry-hard.json",
    "locked": "/run/media/cammie/External Storage/modding-plus-fnf/assets/data/locked/locked-hard.json",
    "cycles-wrath": "/run/media/cammie/External Storage/modding-plus-fnf/assets/data/cycles-wrath/cycles-wrath-hard.json",
    "cycles-encore-springless": "/run/media/cammie/External Storage/modding-plus-fnf/assets/data/cycles-encore-springless/cycles-encore-springless-encore.json",
    "popipo": "/run/media/cammie/External Storage/modding-plus-fnf/assets/data/popipo/popipo-hard.json",
    "fnia-ugh": "/run/media/cammie/External Storage/modding-plus-fnf/assets/data/fnia-ugh/fnia-ugh-hard.json",
}

# Source paths for the currently mounted example regressions. TAKEDOWN is
# retained in the acceptance report as unavailable: neither the mounted donor
# nor the installed runtime currently contains a matching chart.
EXAMPLE_REGRESSION_EVIDENCE: dict[str, str] = {
    "example-expurgation": "v-slice/Vs Tricky/data/songs/expurgation/expurgation-chart.json",
    "example-wacky-hard": "v-slice/Wacky World UPDATE [V-Slice]/data/songs/wacky-world/wacky-world-chart.json",
    "example-wacky-nightmare": "v-slice/Wacky World UPDATE [V-Slice]/data/songs/wacky-world/wacky-world-chart.json",
    "example-rabbit-hole": "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/data/songs/rabbit-hole/rabbit-hole-chart.json",
    "example-fantasy-girl-01": "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/data/songs/fantasy-girl-01/fantasy-girl-01-chart.json",
    "example-vs-freddy": "modding-plus/vsfreddy_1_9_5/assets/data/slaughter/slaughter.json",
    "example-ballistic": "psych/vswhitty/data/ballistic/ballistic.json",
    "example-future-sound": "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/data/songs/future-sound/future-sound-chart.json",
    "example-resonance": "psych/PERFEXION Demo1/data/Resonance/resonance-hard.json",
    "example-cursed-expurgation": "moddingpoop/cursed pergation/assets/data/cursed-expurgation/cursed-expurgation-hard.json",
}


def _binary_default() -> Path:
    configured = os.environ.get("FUNKIN_BINARY", "").strip()
    return Path(configured) if configured else DEFAULT_BINARY


def build_command(
    binary: Path,
    case: SmokeCase,
    duration_ms: int,
    log_path: Path,
    wine: bool = False,
    runtime_root: Optional[Path] = None,
) -> list[str]:
    """Build one smoke command without invoking a build or mutating options."""

    command: list[str] = []
    if wine:
        command.append("wine")
    command.extend(
        [
            str(binary),
            "--smoke-song",
            case.folder,
            "--smoke-chart",
            case.chart,
            "--smoke-difficulty",
            case.difficulty,
            "--smoke-duration-ms",
            str(duration_ms),
            "--smoke-log",
            str(log_path),
        ]
    )
    if runtime_root is not None:
        command.extend(["--smoke-runtime-root", str(runtime_root)])
    return command


def offscreen_command(command: list[str], launcher: Optional[str] = None) -> list[str]:
    """Fail closed when a native smoke cannot use an isolated display."""

    if os.name == "nt":
        raise RuntimeError("off-screen native smoke requires an isolated display")
    xvfb_run = launcher or shutil.which("xvfb-run")
    if not xvfb_run:
        raise RuntimeError("xvfb-run is required for off-screen native smoke")
    return [xvfb_run, "-a", "-s", "-screen 0 1280x720x24", *command]


def _options_snapshot(path: Path) -> Optional[bytes]:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _file_snapshot(path: Path) -> Optional[bytes]:
    """Read a file for post-smoke immutability checks, tolerating absence."""
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _prepare_case_overlay(source_root: Path, overlay_root: Path, case: Optional[SmokeCase] = None,
                          next_case: Optional[SmokeCase] = None) -> Path:
    """Link read-only content, but own the data directory and default options."""

    assets = source_root / "assets"
    if not assets.is_dir():
        raise ValueError(f"runtime root has no assets directory: {source_root}")
    default_options = DEFAULT_OPTIONS.read_bytes()
    # The seed is the current repository default, never a user's export copy.
    if not isinstance(json.loads(default_options), dict):
        raise ValueError(f"default options are not an object: {DEFAULT_OPTIONS}")
    for entry in source_root.iterdir():
        if entry.name != "assets" and entry.name not in PRIVATE_DIRS and entry != overlay_root:
            (overlay_root / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    overlay_assets = overlay_root / "assets"
    overlay_assets.mkdir()
    for entry in assets.iterdir():
        if entry.name not in {"data", "imported_mods", "scripts"}:
            (overlay_assets / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    # Script discovery canonicalizes file paths. The selected compatibility
    # root must therefore have real directories and real script files under
    # the overlay; a directory symlink would resolve outside Main.cwd.
    scripts = assets / "scripts"
    if scripts.is_dir():
        shutil.copytree(scripts, overlay_assets / "scripts")
    imported = assets / "imported_mods"
    if imported.is_dir():
        overlay_imported = overlay_assets / "imported_mods"
        overlay_imported.mkdir()
        selected_names: set[str] = set()
        for selected_case in (case, next_case):
            if selected_case is None:
                continue
            manifest = assets / "data" / selected_case.folder / "compatScripts.json"
            if manifest.is_file():
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                for item in payload.get("roots", []):
                    raw = item.get("path", "") if isinstance(item, dict) else ""
                    parts = Path(raw).parts
                    if len(parts) == 3 and parts[:2] == ("assets", "imported_mods"):
                        selected_names.add(parts[2])
        # A configured chart-free global Psych pack owns its own scripts and
        # media even though it is absent from every song's compat manifest.
        # Give that owner the same private real-directory treatment as the
        # selected song owner; canonical asset reads reject symlinks leaving
        # this offscreen runtime.
        provider_config = imported / "globalResultsProvider.json"
        if provider_config.is_file():
            try:
                provider = json.loads(provider_config.read_text(encoding="utf-8"))
                raw = provider.get("defaultOwner", "") if isinstance(provider, dict) else ""
                parts = Path(raw).parts
                if len(parts) == 3 and parts[:2] == ("assets", "imported_mods"):
                    selected_names.add(parts[2])
            except (OSError, ValueError):
                pass
        for entry in imported.iterdir():
            destination = overlay_imported / entry.name
            if entry.name in selected_names and entry.is_dir():
                # Asset resolution rejects paths whose canonical target leaves
                # the game's cwd. A symlinked PNG/audio/model under this owner
                # therefore looks missing even though the source file exists.
                # Copy the selected owner so both scripts and media resolve
                # inside the private runtime, without touching installed data.
                shutil.copytree(entry, destination)
            else:
                destination.symlink_to(entry, target_is_directory=entry.is_dir())
    overlay_data = overlay_assets / "data"
    overlay_data.mkdir()
    source_data = assets / "data"
    if source_data.is_dir():
        for entry in source_data.iterdir():
            if entry.name != "options.json":
                (overlay_data / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    (overlay_data / "options.json").write_bytes(default_options)
    for name in PRIVATE_DIRS:
        (overlay_root / name).mkdir()
    return overlay_data / "options.json"


def prepare_chart_editor_fixture(overlay_root: Path, source_root: Path,
                                 folder: str, chart: str) -> tuple[Path, bytes]:
    """Copy one selected chart owner into the private overlay and add smoke rows."""

    folder = folder.strip().lower()
    chart = chart.strip().lower()
    # Parentheses appear in imported chart identities such as ``song-(hq)``.
    # They are safe as single path components; slashes, traversal and absolute
    # paths remain rejected below.
    token_pattern = re.compile(r"[a-z0-9_.()\-]+")
    for label, value in (("song folder", folder), ("chart", chart)):
        if (not value or value in {".", ".."} or not token_pattern.fullmatch(value)):
            raise ValueError(f"invalid chart editor smoke {label}: {value!r}")

    source_data = source_root / "assets" / "data" / folder
    chart_path = source_data / f"{chart}.json"
    if not source_data.is_dir() or not chart_path.is_file():
        raise ValueError(f"selected chart does not exist: {chart_path}")

    overlay_data = overlay_root / "assets" / "data"
    overlay_song = overlay_data / folder
    if not overlay_song.is_symlink():
        raise ValueError(f"selected chart owner is not an isolated overlay link: {overlay_song}")
    overlay_song.unlink()
    shutil.copytree(source_data, overlay_song)

    sidecar_path = overlay_song / "events.json"
    sidecar_bytes = (json.dumps(CHART_EDITOR_FIXTURE, ensure_ascii=False,
                                separators=(",", ":")) + "\n").encode("utf-8")
    sidecar_path.write_bytes(sidecar_bytes)
    return sidecar_path, sidecar_bytes


def parse_markers(output: str) -> list[dict]:
    markers: list[dict] = []
    for line in output.splitlines():
        if not line.startswith("RUNTIME_SMOKE|"):
            continue
        raw = line.split("|", 1)[1]
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            markers.append(value)
    return markers


def runtime_diagnostics(output: str) -> list[str]:
    """Return native script failures that a startup/success marker cannot clear."""

    failures = ("[hscript-null-access]", "[hscript-null-operand]", "[hscript-null-iterator]",
				"[codename-asset] Missing", "[psych-stage]",
                "[psych-stage-video]", "[hxc-video-missing]", "[hxc-path-unsafe]",
				"[hxc-window] missing icon:",
				"Error : Null Object Reference", "Null Function Pointer", "Invalid field:",
                " modifier was not found !")
    return [line for line in output.splitlines()
            if not line.startswith("RUNTIME_SMOKE|") and (
                any(prefix in line for prefix in failures)
                or re.search(r"\b(?:hscript|lua(?: script)?|hxc(?: script)?) error\b|"
                             r"EUnknownVariable\(|uncaught exception", line, re.IGNORECASE)
            or any("error" in tag or "unsupported" in tag
                   for tag in re.findall(r"\[([a-z][a-z0-9_-]+)\]", line)))]


_UNEXPLAINED_ERROR_WORD = re.compile(
    r"(?<![A-Za-z0-9_-])(?:error|exception|fatal|uncaught|failed|unsupported)(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)
_UNEXPLAINED_ERROR_TAG = re.compile(r"\[(?=[^]]*(?:error|unsupported|failure))[^]]+\]", re.IGNORECASE)


def unexplained_error_lines(output: str, known_diagnostics: Iterable[str] = ()) -> list[str]:
    """Return uncategorized errors without treating hyphenated prose as an error.

    Explicit diagnostic tags such as ``[hxc-playback-error]`` remain errors;
    words joined into a descriptive token such as ``playback-error behavior``
    do not trigger the generic fallback classifier by themselves.
    """

    known = set(known_diagnostics)
    return [line[:500] for line in output.splitlines()
            if not line.startswith("RUNTIME_SMOKE|") and line not in known
            and (_UNEXPLAINED_ERROR_WORD.search(line) or _UNEXPLAINED_ERROR_TAG.search(line))]


def _marker_events(markers: Iterable[dict]) -> set[str]:
    return {str(marker.get("event")) for marker in markers}


def _output_text(value: object) -> str:
    """Normalize subprocess output from both text and byte-oriented APIs.

    ``Popen(..., text=True)`` normally returns strings, but
    ``TimeoutExpired.output`` is documented (and implemented on some Python
    versions) as the bytes collected before the timeout.  The post-kill
    ``communicate()`` call can then return a string, so concatenating the two
    values directly raises ``TypeError`` while handling the timeout—the very
    path that should preserve the diagnostic output.
    """

    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    return str(value)


def _case_environment(binary: Path, overlay_root: Path, wine: bool) -> dict[str, str]:
    """Keep native storage and video selection inside the private case."""

    environment = os.environ.copy()
    for key in ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "XAUTHORITY", "XDG_RUNTIME_DIR"):
        environment.pop(key, None)
    environment.update({
        "TMPDIR": str(overlay_root / "scratch"),
        "SDL_AUDIODRIVER": "dummy",
        "SDL_VIDEODRIVER": "x11",
        "ALSOFT_DRIVERS": "null",
        # OpenFL SharedObject uses Lime's applicationStorageDirectory; on
        # Linux the SDL preference path follows XDG_DATA_HOME.
        "XDG_DATA_HOME": str(overlay_root / "xdg-data"),
        "XDG_CONFIG_HOME": str(overlay_root / "xdg-config"),
        "XDG_CACHE_HOME": str(overlay_root / "xdg-cache"),
    })
    if not wine and os.name != "nt":
        # The executable's native libraries live beside the binary, not cwd.
        native_library_root = str(binary.parent)
        inherited_library_path = environment.get("LD_LIBRARY_PATH", "")
        environment["LD_LIBRARY_PATH"] = native_library_root + (
            os.pathsep + inherited_library_path if inherited_library_path else ""
        )
    return environment


def run_case(
    binary: Path,
    case: SmokeCase,
    duration_ms: int,
    timeout_seconds: Optional[float] = None,
    wine: bool = False,
    runtime_root: Optional[Path] = None,
    extra_flags: tuple[str, ...] = (),
    next_case: Optional[SmokeCase] = None,
    input_key: Optional[str] = None,
    input_trigger: str = "playstate_ready",
    input_delay_seconds: float = 4.0,
    followup_key: Optional[str] = None,
    followup_delay_seconds: float = 2.0,
    repeat_key: Optional[str] = None,
    repeat_start_delay_seconds: float = 12.0,
    repeat_interval_seconds: float = 0.6,
    post_key: Optional[str] = None,
    post_trigger: str = "song_end",
    post_delay_seconds: float = 4.0,
    strict_diagnostics: bool = False,
    chart_editor: bool = False,
) -> dict:
    """Run one case against an isolated disposable copy of its runtime root."""

    binary = binary.resolve()
    source_root = (runtime_root or binary.parent).resolve()
    SMOKE_ROOT.mkdir(parents=True, exist_ok=True)
    directory = tempfile.TemporaryDirectory(prefix=f"case-{case.id}-", dir=SMOKE_ROOT)
    overlay_root = Path(directory.name)
    source_chart_snapshot: Optional[bytes] = None
    source_sidecar_snapshot: Optional[bytes] = None
    source_options_snapshot: Optional[bytes] = None
    source_guard_captured = False
    try:
        try:
            _prepare_case_overlay(source_root, overlay_root, case, next_case)
            if chart_editor:
                if next_case is not None or input_key is not None or repeat_key is not None or post_key is not None:
                    raise ValueError("chart editor smoke does not support gameplay transitions or input driving")
                prepare_chart_editor_fixture(overlay_root, source_root, case.folder, case.chart)
                source_chart_snapshot = _file_snapshot(source_root / "assets" / "data"
                    / case.folder.lower() / f"{case.chart.lower()}.json")
                source_sidecar = source_root / "assets" / "data" / case.folder.lower() / "events.json"
                source_sidecar_snapshot = _file_snapshot(source_sidecar)
                source_options = source_root / "assets" / "data" / "options.json"
                source_options_snapshot = _file_snapshot(source_options)
                source_guard_captured = True
        except (OSError, ValueError) as error:
            result = {
                "id": case.id,
                "family": case.family,
                "folder": case.folder,
                "chart": case.chart,
                "difficulty": case.difficulty,
                "runtime_root": str(source_root),
                "status": "failed",
                "reason": f"could not prepare isolated runtime: {error}",
            }
        else:
            result = _run_case_in_overlay(
                binary, case, duration_ms, overlay_root, source_root,
                timeout_seconds=timeout_seconds, wine=wine,
                extra_flags=extra_flags + (("--smoke-playstate-visits", "2",
                    "--smoke-next-song", next_case.folder,
                    "--smoke-next-chart", next_case.chart,
                    "--smoke-next-difficulty", next_case.difficulty) if next_case is not None else ()),
                next_case=next_case,
                input_key=input_key,
                input_trigger=input_trigger,
                input_delay_seconds=input_delay_seconds,
                followup_key=followup_key,
                followup_delay_seconds=followup_delay_seconds,
                repeat_key=repeat_key,
                repeat_start_delay_seconds=repeat_start_delay_seconds,
                repeat_interval_seconds=repeat_interval_seconds,
                post_key=post_key,
                post_trigger=post_trigger,
                post_delay_seconds=post_delay_seconds,
                strict_diagnostics=strict_diagnostics,
                chart_editor=chart_editor,
            )
    finally:
        try:
            directory.cleanup()
        except OSError:
            # A concurrent final cache write can race rmtree; retry below.
            pass
        # Mesa can write a final shader-cache index just as the game process
        # exits. Remove only this exact per-case path if it was recreated.
        if overlay_root.exists():
            if overlay_root.parent.resolve() != SMOKE_ROOT.resolve() or not overlay_root.name.startswith(f"case-{case.id}-"):
                raise RuntimeError(f"unsafe residual overlay path: {overlay_root}")
            shutil.rmtree(overlay_root)
    if chart_editor and source_guard_captured:
        source_chart = source_root / "assets" / "data" / case.folder.lower() / f"{case.chart.lower()}.json"
        source_sidecar = source_root / "assets" / "data" / case.folder.lower() / "events.json"
        source_options = source_root / "assets" / "data" / "options.json"
        chart_changed = _file_snapshot(source_chart) != source_chart_snapshot
        sidecar_changed = _file_snapshot(source_sidecar) != source_sidecar_snapshot
        options_changed = _file_snapshot(source_options) != source_options_snapshot
        result["source_chart_changed"] = chart_changed
        result["source_sidecar_changed"] = sidecar_changed
        result["source_options_changed"] = options_changed
        result["editor_source_unchanged"] = not (chart_changed or sidecar_changed or options_changed)
        if chart_changed or sidecar_changed or options_changed:
            result["status"] = "failed"
            result["reason"] = "native editor smoke changed the installed chart, sidecar, or options"
    return result


def _run_case_in_overlay(
    binary: Path,
    case: SmokeCase,
    duration_ms: int,
    overlay_root: Path,
    source_root: Path,
    timeout_seconds: Optional[float] = None,
    wine: bool = False,
    extra_flags: tuple[str, ...] = (),
    next_case: Optional[SmokeCase] = None,
    input_key: Optional[str] = None,
    input_trigger: str = "playstate_ready",
    input_delay_seconds: float = 4.0,
    followup_key: Optional[str] = None,
    followup_delay_seconds: float = 2.0,
    repeat_key: Optional[str] = None,
    repeat_start_delay_seconds: float = 12.0,
    repeat_interval_seconds: float = 0.6,
    post_key: Optional[str] = None,
    post_trigger: str = "song_end",
    post_delay_seconds: float = 4.0,
    strict_diagnostics: bool = False,
    chart_editor: bool = False,
) -> dict:
    """Launch with the owned options file and private OpenFL save directory."""

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = LOG_ROOT / f"{case.id}.log"
    process_log_path = LOG_ROOT / f"{case.id}.process.log"
    runtime_cwd = overlay_root
    options_path = overlay_root / "assets" / "data" / "options.json"
    before_options = _options_snapshot(options_path)
    command = build_command(
        binary,
        case,
        duration_ms,
        log_path,
        wine=wine,
        runtime_root=overlay_root,
    )
    command.extend(extra_flags)
    if chart_editor:
        command.append("--smoke-chart-editor")
    if followup_key is not None and input_key is None:
        raise ValueError("followup_key requires input_key")
    if input_key is not None or repeat_key is not None or post_key is not None:
        # The driver receives DISPLAY only from xvfb-run below and sends one
        # or more bounded keyboard actions after PlayState is ready.
        log_path.unlink(missing_ok=True)
        command = [sys.executable, str(ROOT / "tools/drive_offscreen_input.py"),
                   "--marker-log", str(log_path),
                   "--trigger", input_trigger,
                   *(["--key", input_key] if input_key is not None else []),
                   "--delay-seconds", str(input_delay_seconds),
                   *(["--followup-key", followup_key, "--followup-delay-seconds",
                      str(followup_delay_seconds)] if followup_key is not None else []),
                   *(["--repeat-key", repeat_key, "--repeat-start-delay-seconds",
                      str(repeat_start_delay_seconds), "--repeat-interval-seconds",
                      str(repeat_interval_seconds)] if repeat_key is not None else []),
                   *(["--post-key", post_key, "--post-trigger", post_trigger,
                      "--post-delay-seconds", str(post_delay_seconds)] if post_key is not None else []),
                   "--", *command]
    try:
        command = offscreen_command(command)
    except RuntimeError as error:
        return {
            "id": case.id,
            "family": case.family,
            "folder": case.folder,
            "chart": case.chart,
            "difficulty": case.difficulty,
            "command": command,
            "log": str(log_path),
            "runtime_root": str(source_root),
            "status": "failed",
            "reason": str(error),
        }
    timeout = timeout_seconds if timeout_seconds is not None else case.timeout_seconds

    result: dict = {
        "id": case.id,
        "family": case.family,
        "folder": case.folder,
        "chart": case.chart,
        "difficulty": case.difficulty,
        "command": command,
        "log": str(log_path),
        "runtime_root": str(source_root),
        "status": "failed",
    }
    if not binary.exists():
        result["reason"] = f"built binary not found: {binary}"
        return result

    output = ""
    timed_out = False
    return_code: Optional[int] = None
    process_environment = _case_environment(binary, overlay_root, wine)
    try:
        process = subprocess.Popen(
            command,
            cwd=runtime_cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=process_environment,
            start_new_session=True,
        )
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            timed_out = True
            # xvfb-run starts both an X server and the game. Kill their
            # process group so a timeout cannot leave a window or server up.
            if os.name != "nt" and getattr(process, "pid", None) is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            tail, _ = process.communicate()
            captured = _output_text(error.output)
            finished = _output_text(tail)
            # Python may return the already-captured prefix again after a
            # timeout. Keep one copy so marker counts remain authoritative.
            output = finished if finished.startswith(captured) else captured + finished
        return_code = process.returncode
    except OSError as error:
        result["reason"] = f"could not launch binary: {error}"

    process_log_path.write_text(output, encoding="utf-8")
    changed_options = _options_snapshot(options_path) != before_options
    markers = parse_markers(output)
    events = _marker_events(markers)
    result["returncode"] = return_code
    result["timed_out"] = timed_out
    result["events"] = sorted(events)
    result["options_changed"] = changed_options

    required = ({"startup", "chart_editor_loaded", "chart_editor_edited",
                 "chart_editor_quicksave", "chart_editor_reloaded",
                 "chart_editor_runtime_collection", "chart_editor_sidecar_unchanged", "success"}
                if chart_editor else {"startup", "playstate_start", "playstate_ready", "success"})
    reasons: list[str] = []
    if timed_out:
        reasons.append(f"timeout after {timeout:g}s")
    if return_code not in (0, None):
        reasons.append(f"process exited {return_code}")
    if return_code is None and "reason" in result:
        reasons.append(str(result["reason"]))
    if "failure" in events:
        reasons.append("failure marker emitted")
    missing = sorted(required - events)
    if missing:
        reasons.append("missing markers: " + ", ".join(missing))
    if next_case is not None:
        for visit, selected_case in ((1, case), (2, next_case)):
            if not any(marker.get("event") == "visit_selection"
                       and marker.get("visit") == visit
                       and marker.get("songFolder") == selected_case.folder
                       and marker.get("chart") == selected_case.chart
                       and marker.get("difficulty") == selected_case.difficulty
                       for marker in markers):
                reasons.append(f"wrong cross-song selection: visit {visit}")
        for event, visit in (("playstate_start", 1), ("playstate_ready", 1),
                             ("playstate_destroyed", 1), ("playstate_start", 2),
                             ("playstate_ready", 2)):
            if not any(marker.get("event") == event and marker.get("visit") == visit
                       for marker in markers):
                reasons.append(f"missing cross-song marker: {event} visit {visit}")
    if chart_editor and not any(
        marker.get("event") == "chart_editor_reloaded"
        and marker.get("storageFolder") == case.folder.lower()
        and marker.get("chart") == case.chart.lower()
        and marker.get("difficulty") == case.difficulty
        for marker in markers
    ):
        reasons.append("editor round-trip did not preserve the selected owner chart and difficulty")
    if changed_options:
        reasons.append("runtime changed disposable default options.json")
    if strict_diagnostics:
        diagnostics = runtime_diagnostics(output)
        result["diagnostic_count"] = len(diagnostics)
        result["diagnostics"] = diagnostics[:10]
        if diagnostics:
            reasons.append(f"{len(diagnostics)} native script diagnostic(s)")
    if not reasons:
        result["status"] = "passed"
    else:
        result["reason"] = "; ".join(reasons)
    return result


def _case_selection(values: Optional[list[str]]) -> list[SmokeCase]:
    if not values:
        return list(SMOKE_MATRIX)
    by_id = {case.id: case for case in SMOKE_MATRIX}
    unknown = [value for value in values if value not in by_id]
    if unknown:
        raise SystemExit("unknown smoke case(s): " + ", ".join(unknown))
    return [by_id[value] for value in values]


def _fixture_path(root: Path, relative: str, field: str) -> Path:
    """Resolve one manifest root without allowing traversal or symlinks."""

    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"prepared fixture {field} is not relative: {relative}")
    raw_path = root / candidate
    if raw_path.is_symlink():
        raise ValueError(f"prepared fixture {field} may not be a symlink: {raw_path}")
    path = raw_path.resolve()
    resolved_root = root.resolve()
    if path != resolved_root and resolved_root not in path.parents:
        raise ValueError(f"prepared fixture {field} escapes root: {relative}")
    if not path.is_dir() or path.is_symlink() or not (path / "assets").is_dir():
        raise ValueError(f"prepared fixture {field} has no assets directory: {path}")
    return path


def load_prepared_fixture(
    root: Path, cases: Optional[Iterable[SmokeCase]] = None
) -> dict[str, Path]:
    """Load a retained preparation manifest into per-case runtime roots.

    The selected Auto transaction and named regression overlay intentionally
    remain separate.  First-six family cases use ``selected_root``; named
    regressions use their explicit ``case_roots`` entries.  This prevents a
    same-named chart from silently replacing another source and keeps the
    runtime process's cwd aligned with the assets it is meant to exercise.
    """

    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"prepared fixture root does not exist: {root}")
    manifest_path = root / PREPARED_MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(
            f"could not read prepared fixture manifest: {manifest_path}: {error}"
        ) from error
    if manifest.get("schema") != 1:
        raise ValueError(f"unsupported prepared fixture manifest: {manifest_path}")
    if manifest.get("kind") != "native-runtime-smoke-fixture":
        if manifest.get("kind") == "native-runtime-smoke-structural-fixture":
            raise ValueError(
                "prepared fixture is structural-only (bounded media/converter stubs); "
                "it is not a native runtime root"
            )
        raise ValueError(f"unsupported prepared fixture manifest: {manifest_path}")
    if manifest.get("runtime_matrix_eligible") is not True:
        raise ValueError(f"prepared fixture is not marked runtime_matrix_eligible: {manifest_path}")
    selected_relative = manifest.get("selected_root", "")
    if not isinstance(selected_relative, str):
        raise ValueError(f"prepared fixture selected_root is invalid: {manifest_path}")
    selected = _fixture_path(root, selected_relative, "selected_root")
    case_roots = manifest.get("case_roots")
    if not isinstance(case_roots, dict):
        raise ValueError(f"prepared fixture manifest has no case_roots: {manifest_path}")
    selected_cases = list(cases) if cases is not None else list(SMOKE_MATRIX)
    roots: dict[str, Path] = {}
    for case in selected_cases:
        relative = case_roots.get(case.id, selected_relative)
        if not isinstance(relative, str):
            raise ValueError(f"prepared fixture case root is invalid for {case.id}")
        roots[case.id] = (
            selected
            if relative == selected_relative
            else _fixture_path(root, relative, f"case_roots[{case.id}]")
        )
    return roots


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=_binary_default())
    parser.add_argument("--wine", action="store_true", help="prefix each launch with wine")
    parser.add_argument(
        "--runtime-root",
        type=Path,
        help="optional temporary/export root containing the runtime assets tree",
    )
    parser.add_argument(
        "--asset-root",
        type=Path,
        help="fixture root alias; accepts a directory containing assets/ or the assets directory itself",
    )
    parser.add_argument(
        "--prepared-root",
        "--fixture-root",
        dest="prepared_root",
        type=Path,
        help=(
            "retained preparation root containing runtime-smoke-manifest.json; "
            "routes selected families and named regressions to separate assets trees"
        ),
    )
    parser.add_argument("--duration-ms", type=int, default=5000)
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--strict-diagnostics", action="store_true",
                        help="fail on tagged script errors and unsupported APIs even after success")
    parser.add_argument("--case", action="append", help="run only this case id (repeatable)")
    parser.add_argument("--next-case", help="switch to this case on the second PlayState visit")
    parser.add_argument("--list", action="store_true", help="print the matrix and exit")
    args = parser.parse_args(argv)
    selected = _case_selection(args.case)
    if args.list:
        print(json.dumps([case.__dict__ for case in selected], indent=2))
        return 0
    if args.duration_ms < 250:
        parser.error("--duration-ms must be at least 250")
    next_case = None
    if args.next_case is not None:
        if len(selected) != 1:
            parser.error("--next-case requires exactly one --case")
        next_case = _case_selection([args.next_case])[0]

    if sum(
        value is not None
        for value in (args.runtime_root, args.asset_root, args.prepared_root)
    ) > 1:
        parser.error("use only one of --runtime-root, --asset-root, or --prepared-root")
    runtime_root = args.runtime_root
    prepared_roots: Optional[dict[str, Path]] = None
    if args.asset_root is not None:
        asset_root = args.asset_root.resolve()
        if asset_root.name.lower() == "assets":
            runtime_root = asset_root.parent
        elif (asset_root / "assets").is_dir():
            runtime_root = asset_root
        else:
            parser.error("--asset-root must contain assets/ or be named assets")
    if runtime_root is not None:
        runtime_root = runtime_root.resolve()
        if not runtime_root.is_dir():
            parser.error(f"runtime root does not exist: {runtime_root}")
    if args.prepared_root is not None:
        try:
            prepared_roots = load_prepared_fixture(args.prepared_root,
                selected + ([next_case] if next_case is not None else []))
        except ValueError as error:
            parser.error(str(error))
        if next_case is not None and prepared_roots[selected[0].id] != prepared_roots[next_case.id]:
            parser.error("--next-case requires both charts in the same prepared runtime root")

    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    for case in selected:
        result = run_case(
            args.binary.resolve(),
            case,
            args.duration_ms,
            timeout_seconds=args.timeout_seconds,
            wine=args.wine,
            runtime_root=(
                prepared_roots.get(case.id)
                if prepared_roots is not None
                else runtime_root
            ),
            next_case=next_case,
            strict_diagnostics=args.strict_diagnostics,
        )
        results.append(result)
        print(json.dumps(result, sort_keys=True))

    summary = {
        "passed": sum(result["status"] == "passed" for result in results),
        "failed": sum(result["status"] != "passed" for result in results),
        "logs": str(LOG_ROOT),
    }
    print(json.dumps({"runtime_smoke_summary": summary}, sort_keys=True))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
