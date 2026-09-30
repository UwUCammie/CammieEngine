#!/usr/bin/env python3
"""Prepare native runtime-smoke assets without touching donors.

The default path orchestrates the already-built game with an opt-in
``--smoke-import-source`` command line.  That runs the complete native
``ImportWorkflow``/``ModuleFunctions.importSongsFromPath`` transaction in the
binary's runtime directory, preserving full HxcCompat/LuaCompat conversion,
real media, registries, and dependency planners.  The Python command only
captures markers and writes a report below project ``tmp``; it does not build
or launch a chart smoke case.

``--structural-only`` remains an explicit fallback for a source-only audit.
That mode uses the bounded extractor, writes marker media/stubbed converters,
and is *not* launchable.  Its manifest is rejected by
``run_runtime_smoke_matrix.py``.  Named regression charts are copied only in
that evidence mode and remain clearly separate from the native import.

The normal invocation can be expensive because it reads mounted chart/audio
files.  ``--dry-run`` validates both read-only sources and the project-local
destination without creating a directory, starting Haxe, or copying bytes.
All retained output must be below ``<checkout>/tmp``; an existing non-empty
destination is rejected rather than overwritten.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "tools" / "audit_mounted_auto_import.py"
DEFAULT_SOURCE = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
DEFAULT_REGRESSION_SOURCE = Path("/run/media/cammie/External Storage/modding-plus-fnf")
DEFAULT_OUTPUT = ROOT / "tmp" / "runtime-smoke" / "structural-fixture"
DEFAULT_NATIVE_REPORT = ROOT / "tmp" / "runtime-smoke" / "native-import"
DEFAULT_BINARY = ROOT / "export" / "release" / "linux" / "bin" / "Funkin"
MANIFEST_NAME = "runtime-smoke-manifest.json"


def _external_regression_cases(matrix: object) -> tuple:
    """Cases whose charts are supplied by the separate legacy donor root."""

    return tuple(case for case in matrix.SMOKE_MATRIX if case.family == "named regression")


# These are the same bounded script families that PlayState/HxcScriptDiscovery
# can load from a destination-only compatibility namespace.  Keep this list
# deliberately small: postflight must prove the files the engine can actually
# discover, not bless an arbitrary file dropped next to a chart.
_COMPAT_SCRIPT_SUFFIXES = {".hxc", ".hscript", ".hxs", ".lua"}


def _safe_manifest_relative(value: object) -> Path | None:
    """Return a safe destination-relative path from a compat manifest.

    CompatScriptManifest stores destination paths with forward slashes even on
    Windows.  Normalize that spelling before checking it; otherwise a
    backslash traversal can pass a Linux ``Path`` check and become unsafe when
    the same manifest is opened by a Windows build.
    """

    if not isinstance(value, str):
        return None
    raw = value.strip().replace("\\", "/")
    if not raw or "\x00" in raw:
        return None
    path = PurePosixPath(raw)
    if path.is_absolute() or ":" in path.parts[0]:
        return None
    if any(part in ("", "..") for part in path.parts):
        return None
    # A manifest path is a relative destination key, not a path with a
    # platform-specific drive/UNC spelling hidden in a later component.
    if any("\x00" in part or ":" in part for part in path.parts):
        return None
    return Path(*path.parts)


def _safe_manifest_path(runtime_root: Path, value: object) -> Path | None:
    """Resolve a manifest path while rejecting symlink/path escapes."""

    relative = _safe_manifest_relative(value)
    if relative is None:
        return None
    root = runtime_root.resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        return None
    return candidate


def _normalize_dependency_token(value: object) -> str:
    """Match HXC discovery's case-insensitive alphanumeric token rule."""

    if not isinstance(value, str):
        return ""
    return "".join(character.lower() for character in value if character.isascii() and character.isalnum())


def _safe_walk_files(root: Path) -> Iterable[Path]:
    """Walk one manifest-owned tree without following symlinks."""

    if not root.is_dir() or root.is_symlink():
        return
    root_resolved = root.resolve()
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            name
            for name in directories
            if not (current_path / name).is_symlink()
            and _safe_manifest_path(root_resolved, (current_path / name).resolve().relative_to(root_resolved).as_posix()) is not None
        )
        for name in sorted(files):
            path = current_path / name
            if path.is_symlink():
                continue
            try:
                resolved = path.resolve()
                if resolved != root_resolved and root_resolved not in resolved.parents:
                    continue
            except OSError:
                continue
            yield path


def _find_manifest_script(root: Path, family: str, requested: str) -> list[Path]:
    """Find an HXC family member using the same stem matching as the engine."""

    wanted = _normalize_dependency_token(requested)
    if not wanted:
        return []
    matches: list[Path] = []
    family_dirs = {
        "character": {"characters", "character"},
        "stage": {"stages"},
    }.get(family, set())
    for path in _safe_walk_files(root):
        if path.suffix.lower() not in _COMPAT_SCRIPT_SUFFIXES:
            continue
        parent_names = {part.lower() for part in path.relative_to(root).parts[:-1]}
        if not (parent_names & family_dirs):
            continue
        if _normalize_dependency_token(path.stem) == wanted:
            matches.append(path)
    matches.sort(key=lambda path: (path.as_posix().lower(), path.as_posix()))
    return matches


def _find_case_insensitive_file(root: Path, relative: str) -> Path | None:
    """Resolve a native/manifest asset without assuming Linux case spelling."""

    parts = [part for part in relative.replace("\\", "/").split("/") if part]
    current = root
    for part in parts:
        if not current.is_dir() or current.is_symlink():
            return None
        try:
            entries = sorted(current.iterdir(), key=lambda item: (item.name.lower(), item.name))
        except OSError:
            return None
        selected = next((entry for entry in entries if entry.name.lower() == part.lower()), None)
        if selected is None:
            return None
        current = selected
    return current if current.is_file() and not current.is_symlink() else None


def _manifest_asset_exists(root: Path, reference: str) -> bool:
    """Check a HXC asset against the namespace's ``images`` tree."""

    clean = str(reference or "").strip().replace("\\", "/")
    while clean.startswith("./"):
        clean = clean[2:]
    if clean.lower().startswith("assets/"):
        clean = clean[7:]
    if clean.lower().startswith("images/"):
        clean = clean[7:]
    if not clean or any(part in ("", "..") for part in PurePosixPath(clean).parts):
        return False
    stem = clean.rsplit(".", 1)[0] if "." in clean.rsplit("/", 1)[-1] else clean
    for suffix in (".png", ".xml", ".json", ".txt", ".astc"):
        if _find_case_insensitive_file(root / "images", stem + suffix) is not None:
            return True
    return _find_case_insensitive_file(root / "images", clean) is not None


def _compat_definition_is_instantiable(
    path: Path, runtime_root: Path, family: str, compat_root: Path | None = None
) -> bool:
    """Prove that a selected HXC companion reaches a native adapter boundary.

    A filename alone is not enough.  CharacterInfo/BaseStage definitions are
    data-extracted by HxcCompat and then applied to a native Character/Stage;
    malformed or unrelated scripts must remain diagnostics.  This check is
    intentionally conservative and only accepts the literal forms the runtime
    adapter recognizes, plus the referenced native image when one is declared.
    """

    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    if not source.strip():
        return False
    if family == "character":
        if not re.search(r"\b(?:CharacterInfoBase|CharacterInfo|SparrowCharacter)\b", source):
            return False
        sprite = re.search(r"\binfo\s*\.\s*spritePath\s*=\s*[\"']([^\"']+)[\"']", source)
        if sprite is None:
            return False
        # HxcCompatRuntime.addCharacterAtlasAnimations resolves the authored
        # ``characters/...`` path against native assets/images first, then the
        # selected manifest root.  Mirror both locations here.
        reference = sprite.group(1).strip()
        native = runtime_root / "assets" / "images"
        if not _manifest_asset_exists(native.parent, reference) and not (
            compat_root is not None and _manifest_asset_exists(compat_root, reference)
        ):
            return False
        return True
    if family == "stage":
        # Psych/Kade stage scripts are translated by PsychStageCompat rather
        # than HxcCompat's BaseStage adapter.  Require an actual creation hook
        # or native sprite helper before accepting the manifest file.
        if path.suffix.lower() == ".lua":
            return bool(
                re.search(r"\bfunction\s+(?:onCreate|start)\s*\(", source)
                or re.search(r"\bmake(?:Animated)?LuaSprite\s*\(", source)
            )
        if not re.search(r"\b(?:BaseStage|Stage)\b", source):
            return False
        # Stages with no literal BGSprite are still valid: their generated
        # lifecycle may only alter cameras/actors.  If one is declared, ensure
        # the native adapter can resolve its image instead of accepting a
        # dead script file.
        references = re.findall(r"(?:BGSprite|FlxSprite)\s*\(\s*[\"']([^\"']+)[\"']", source)
        if references and not any(
            _manifest_asset_exists(runtime_root / "assets", ref)
            or _manifest_asset_exists(path.parents[2], ref)
            for ref in references
        ):
            return False
        return True
    return False


def _load_matrix():
    spec = importlib.util.spec_from_file_location(
        "runtime_smoke_matrix_for_fixture", ROOT / "tools" / "run_runtime_smoke_matrix.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load runtime smoke matrix")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _resolve_source(value: Path) -> Path:
    # Donor paths are allowed anywhere on mounted read-only media, but must be
    # real directories before a transaction or copy starts.
    return value.expanduser().resolve()


def _paths_overlap(left: Path, right: Path) -> bool:
    left = left.resolve()
    right = right.resolve()
    return left == right or left in right.parents or right in left.parents


def _validate_output(value: Path) -> Path:
    audit_spec = importlib.util.spec_from_file_location("mounted_auto_audit_paths", AUDIT)
    if audit_spec is None or audit_spec.loader is None:
        raise RuntimeError("could not load mounted audit path validator")
    audit = importlib.util.module_from_spec(audit_spec)
    audit_spec.loader.exec_module(audit)
    return audit.validate_runtime_smoke_destination(value)


def _validate_empty(path: Path) -> None:
    audit_spec = importlib.util.spec_from_file_location("mounted_auto_audit_empty", AUDIT)
    if audit_spec is None or audit_spec.loader is None:
        raise RuntimeError("could not load mounted audit destination validator")
    audit = importlib.util.module_from_spec(audit_spec)
    audit_spec.loader.exec_module(audit)
    audit.validate_empty_runtime_smoke_destination(path)


def _assert_file(path: Path, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or non-regular {label}: {path}")
    if path.stat().st_size <= 0:
        raise ValueError(f"empty {label}: {path}")


def _safe_destination(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe fixture destination: {relative}")
    destination = (root / relative).resolve()
    resolved_root = root.resolve()
    if destination != resolved_root and resolved_root not in destination.parents:
        raise ValueError(f"fixture destination escaped root: {relative}")
    return destination


def _copy_file(source: Path, destination: Path) -> None:
    """Copy one donor file without ever replacing a destination file."""

    _assert_file(source, "donor file")
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"refusing to overwrite fixture file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_tree(source: Path, destination: Path) -> int:
    """Copy a small named regression tree, preserving donor-relative paths."""

    if not source.is_dir() or source.is_symlink():
        raise ValueError(f"missing or non-regular donor directory: {source}")
    copied = 0
    for current, directories, files in os.walk(source, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            name for name in directories if not (current_path / name).is_symlink()
        )
        for name in sorted(files):
            source_file = current_path / name
            if source_file.is_symlink():
                raise ValueError(f"symlink donor file is not allowed: {source_file}")
            relative = source_file.relative_to(source)
            _copy_file(source_file, _safe_destination(destination, relative))
            copied += 1
    return copied


def _chart_song_name(chart: Path, fallback: str) -> str:
    try:
        payload = json.loads(chart.read_text(encoding="utf-8"))
        song = payload.get("song", {}).get("song")
        if isinstance(song, str) and song.strip():
            return song.strip()
    except (OSError, ValueError, TypeError):
        # Imported legacy charts are often JSONC.  The chart parser used by
        # the engine accepts comments/trailing commas; this small fallback only
        # needs the authored display id for locating matching donor audio.
        try:
            match = re.search(r'"song"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', chart.read_text(encoding="utf-8"))
            if match:
                return bytes(match.group(1), "utf-8").decode("unicode_escape").strip()
        except (OSError, UnicodeError):
            pass
    return fallback


def _copy_named_regressions(
    donor: Path, destination: Path, cases: Iterable[object], matrix: object
) -> tuple[int, dict[str, str]]:
    """Copy data folders and matching music for the named matrix cases.

    This intentionally keeps the second source separate from the selected Auto
    root.  A data folder is copied whole (charts, events, modchart, preload,
    and authored small sidecars) so no donor chart is rewritten or projected
    into a different difficulty.  Audio is selected by the chart's authored
    song name and copied under ``assets/music``; unrelated multi-gigabyte donor
    image trees are not guessed or copied by this preparation command.
    """

    copied = 0
    case_sources: dict[str, str] = {}
    music_source = donor / "assets" / "music"
    for case in cases:
        folder = str(case.folder)
        chart_name = str(case.chart) + ".json"
        source_data = donor / "assets" / "data" / folder
        source_chart = source_data / chart_name
        _assert_file(source_chart, f"named regression chart for {case.id}")
        target_data = destination / "assets" / "data" / folder
        copied += _copy_tree(source_data, target_data)
        case_sources[case.id] = str(source_chart)

        song_name = _chart_song_name(source_chart, folder)
        wanted = {
            f"{song_name.lower()}_inst.ogg",
            f"{song_name.lower()}_voices.ogg",
            f"{folder.lower()}_inst.ogg",
            f"{folder.lower()}_voices.ogg",
        }
        normalized_names = {
            re.sub(r"[^a-z0-9]", "", value.lower())
            for value in (song_name, folder)
        }
        if music_source.is_dir():
            for audio in sorted(music_source.iterdir(), key=lambda path: path.name.lower()):
                lower_name = audio.name.lower()
                stem = lower_name.rsplit(".", 1)[0]
                stem = re.sub(r"_(inst|voices)$", "", stem)
                if lower_name not in wanted and (
                    not lower_name.endswith(("_inst.ogg", "_voices.ogg"))
                    or re.sub(r"[^a-z0-9]", "", stem) not in normalized_names
                ):
                    continue
                _copy_file(audio, _safe_destination(destination / "assets" / "music", Path(audio.name)))
                copied += 1
    return copied, case_sources


def _manifest(
    output: Path,
    source: Path,
    regression_source: Path,
    case_sources: dict[str, str],
    selected_root: Path,
    regression_root: Path,
    matrix: object,
) -> dict:
    selected_relative = selected_root.relative_to(output).as_posix()
    regression_relative = regression_root.relative_to(output).as_posix()
    named_ids = {case.id for case in _external_regression_cases(matrix)}
    return {
        "schema": 1,
        "kind": "native-runtime-smoke-structural-fixture",
        "transaction": "ModuleFunctions.importSong",
        "selected_source": str(source),
        "regression_source": str(regression_source),
        "selected_root": selected_relative,
        "case_roots": {
            case_id: regression_relative if case_id in named_ids else selected_relative
            for case_id in [case.id for case in matrix.SMOKE_MATRIX]
        },
        "named_regression_charts": case_sources,
        "media_mode": "bounded-audit-markers-for-selected; donor-audio-for-named",
        "runtime_matrix_eligible": False,
        "reason_not_runnable": (
            "selected output contains bounded audit media markers and narrow "
            "converter stubs; it is structural evidence, not a launch root"
        ),
        "donor_writes": False,
    }


def _dry_run_report(
    output: Path, source: Path, regression_source: Path, matrix: object
) -> dict:
    return {
        "runtime_smoke_structural_prepare": {
            "destination": str(output),
            "selected_root": str(output / "selected"),
            "regression_root": str(output / "regressions" / "modding-plus-fnf"),
            "source": str(source),
            "regression_source": str(regression_source),
            "selected_expected": 96,
            "named_cases": [case.id for case in _external_regression_cases(matrix)],
            "transaction": "ModuleFunctions.importSong",
            "donor_writes": False,
            "runtime_matrix_eligible": False,
            "reason_not_runnable": "structural-only audit output; no native launch is authorized",
            "dry_run": True,
        }
    }


def native_import_command(
    binary: Path,
    source: Path,
    import_type: str,
    timeout_ms: int,
    log_path: Path,
) -> list[str]:
    """Build the opt-in full-runtime importer command without launching it."""

    return [
        str(binary),
        "--smoke-import-source",
        str(source),
        "--smoke-import-type",
        import_type,
        "--smoke-import-timeout-ms",
        str(timeout_ms),
        "--smoke-import-log",
        str(log_path),
    ]


def parse_import_markers(output: str) -> list[dict]:
    markers: list[dict] = []
    for line in output.splitlines():
        if not line.startswith("RUNTIME_IMPORT_SMOKE|"):
            continue
        try:
            value = json.loads(line.split("|", 1)[1])
        except (IndexError, ValueError):
            continue
        if isinstance(value, dict):
            markers.append(value)
    return markers


def _native_asset_diagnostics(runtime_root: Path, matrix: object) -> list[str]:
    """Reject marker media and dependencies the native runtime cannot resolve.

    The live loader has three relevant resolution boundaries here: native
    registries/assets, a chart's destination-only compatibility manifest, and
    HXC's bounded ``scripts/characters``/``scripts/stages`` discovery.  The
    postflight mirrors those boundaries instead of assuming every visual is a
    custom-registry entry.  In particular, a declared HXC filename is not
    enough by itself: the literal definition must be one HxcCompat can lower
    and its referenced native/manifest image must exist.
    """

    diagnostics: list[str] = []
    runtime_root = runtime_root.resolve()
    chars_registry = runtime_root / "assets" / "images" / "custom_chars" / "custom_chars.jsonc"
    stages_registry = runtime_root / "assets" / "images" / "custom_stages" / "custom_stages.json"
    ui_registry = runtime_root / "assets" / "images" / "custom_ui" / "ui_packs" / "ui.json"
    for registry, label in (
        (chars_registry, "character registry"),
        (stages_registry, "stage registry"),
        (ui_registry, "UI registry"),
    ):
        if not registry.is_file() or registry.stat().st_size <= 0:
            diagnostics.append(f"missing or empty representative {label}: {registry}")

    songs_root = runtime_root / "assets" / "songs"
    if songs_root.is_dir():
        for path in songs_root.glob("**/Inst.ogg"):
            try:
                with path.open("rb") as stream:
                    prefix = stream.read(len(b"AUDIT_MEDIA_SOURCE_SIZE="))
                if prefix == b"AUDIT_MEDIA_SOURCE_SIZE=":
                    diagnostics.append(f"marker instrumental is not launchable: {path}")
            except OSError as error:
                diagnostics.append(f"could not inspect instrumental {path}: {error}")

    def registry_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8") if path.is_file() else ""
        except (OSError, UnicodeError):
            return ""

    def registry_has(path: Path, value: object) -> bool:
        if not isinstance(value, str) or not value.strip():
            return False
        return re.search(
            r"[\"']" + re.escape(value.strip()) + r"[\"']\s*:",
            registry_text(path),
            re.IGNORECASE,
        ) is not None

    def manifest_for(chart_path: Path, case: object) -> tuple[dict, Path | None, str | None, object]:
        """Read one chart manifest and return (data, selected root, engine, declaration)."""

        manifest_path = chart_path.parent / "compatScripts.json"
        if not manifest_path.is_file():
            return {}, None, None, None
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as error:
            diagnostics.append(f"invalid compatibility manifest {manifest_path}: {error}")
            return {}, None, None, None
        if not isinstance(raw, dict):
            diagnostics.append(f"invalid compatibility manifest object: {manifest_path}")
            return {}, None, None, None
        roots = raw.get("roots")
        if roots is None:
            roots = []
        if not isinstance(roots, list):
            diagnostics.append(f"invalid compatibility manifest roots: {manifest_path}")
            roots = []
        resolved_roots: list[tuple[dict, Path | None]] = []
        for entry in roots:
            if not isinstance(entry, dict):
                continue
            declared = entry.get("path")
            resolved = _safe_manifest_path(runtime_root, declared)
            if resolved is None:
                diagnostics.append(f"compatibility root escapes runtime: {declared}")
            resolved_roots.append((entry, resolved))
        selected_value = raw.get("selectedRoot")
        if not isinstance(selected_value, str) or not selected_value.strip():
            selected_value = roots[0].get("path") if roots and isinstance(roots[0], dict) else None
        selected_path = _safe_manifest_path(runtime_root, selected_value)
        if selected_value is not None and selected_path is None:
            diagnostics.append(f"compatibility root escapes runtime: {selected_value}")
        engine: str | None = None
        for entry, resolved in resolved_roots:
            if isinstance(selected_value, str) and entry.get("path") == selected_value:
                engine = str(entry.get("engine") or "")
                break
        if engine is None and roots and isinstance(roots[0], dict):
            engine = str(roots[0].get("engine") or "")
        return raw, selected_path, engine, selected_value

    def native_character_resolved(value: str) -> bool:
        # The engine's Character resolver is registry-backed.  Do not bless a
        # random images/characters/<name>.png as a native character.
        return registry_has(chars_registry, value)

    def native_stage_resolved(value: str) -> bool:
        if registry_has(stages_registry, value):
            return True
        # Psych/Kade stages intentionally bypass custom_stages and are loaded
        # from assets/stages/<id>.lua/.json by PlayState's compatibility route.
        for extension in (".lua", ".json", ".hscript", ".hxs"):
            if _find_case_insensitive_file(runtime_root / "assets" / "stages", value + extension) is not None:
                return True
        return False

    # Check all six family representatives for real charts and declared
    # character/stage/UI dependencies.  Only a V-Slice manifest with a
    # selected namespace needs a generated executable adapter; native/Kade/
    # Psych/Modding Plus/FPS rows can legitimately contain no such file.
    for case in matrix.SMOKE_MATRIX[:6]:
        data_root = runtime_root / "assets" / "data" / case.folder
        chart = data_root / f"{case.chart}.json"
        if not chart.is_file():
            diagnostics.append(f"missing representative chart: {chart}")
            continue
        try:
            chart_payload = json.loads(chart.read_text(encoding="utf-8"))
            if not isinstance(chart_payload, dict):
                diagnostics.append(f"invalid representative chart object: {chart}")
                continue
            song_payload = chart_payload.get("song", {})
            if not isinstance(song_payload, dict):
                diagnostics.append(f"invalid representative song object: {chart}")
                continue

            manifest, selected_path, engine, selected_value = manifest_for(chart, case)
            selected_exists = selected_path is not None and selected_path.is_dir()

            def compat_character(value: str) -> bool:
                if not selected_exists:
                    return False
                matches = _find_manifest_script(selected_path, "character", value)
                return any(
                    _compat_definition_is_instantiable(match, runtime_root, "character", selected_path)
                    for match in matches
                )

            def compat_stage(value: str) -> bool:
                if not selected_exists:
                    return False
                matches = _find_manifest_script(selected_path, "stage", value)
                return any(
                    _compat_definition_is_instantiable(match, runtime_root, "stage", selected_path)
                    for match in matches
                )

            for field, label in (
                ("player1", "player1 character"),
                ("player2", "player2 character"),
                ("gf", "girlfriend character"),
            ):
                value = song_payload.get(field)
                if isinstance(value, str) and value.strip() and not (
                    native_character_resolved(value) or compat_character(value)
                ):
                    diagnostics.append(f"missing representative {label} dependency: {value}")

            stage = song_payload.get("stage")
            if isinstance(stage, str) and stage.strip() and not (
                native_stage_resolved(stage) or compat_stage(stage)
            ):
                diagnostics.append(f"missing representative stage dependency: {stage}")

            ui_type = song_payload.get("uiType")
            if isinstance(ui_type, str) and ui_type.strip():
                ui_text = registry_text(ui_registry)
                if not registry_has(ui_registry, ui_type):
                    ui_dir = runtime_root / "assets" / "images" / "custom_ui" / "ui_packs" / ui_type
                    if not ui_dir.is_dir():
                        diagnostics.append(f"missing representative UI dependency: {ui_type}")

            requires_hxc = (engine or "").lower().replace("_", "-") in {"v-slice", "vslice"}
            # Older manifests did not persist engine names.  Keep the matrix's
            # first row as the compatibility probe for that legacy shape, but
            # never impose this requirement on unrelated engine families.
            if not engine and case.id == "family-vslice":
                requires_hxc = True
            if manifest and selected_path is None and requires_hxc:
                diagnostics.append(f"missing materialized compatibility root: {selected_value}")
            if requires_hxc and selected_exists:
                executable = [
                    path
                    for path in _safe_walk_files(selected_path)
                    if path.suffix.lower() in _COMPAT_SCRIPT_SUFFIXES
                    and path.stat().st_size > 0
                ]
                if not executable:
                    diagnostics.append(
                        f"compatibility root has no non-empty generated/script adapter: {selected_path}"
                    )
        except (OSError, ValueError, TypeError, UnicodeError) as error:
            diagnostics.append(f"invalid representative chart {chart}: {error}")
    return diagnostics


def _native_dry_run_report(
    binary: Path,
    runtime_root: Path,
    source: Path,
    regression_source: Path,
    report_root: Path,
    import_type: str,
    timeout_ms: int,
) -> dict:
    log_path = report_root / "import.log"
    return {
        "native_runtime_import_prepare": {
            "binary": str(binary),
            "runtime_root": str(runtime_root),
            "source": str(source),
            "named_regression_source": str(regression_source),
            "named_regressions_separate": True,
            "import_type": import_type,
            "timeout_ms": timeout_ms,
            "command": native_import_command(binary, source, import_type, timeout_ms, log_path),
            "report_root": str(report_root),
            "donor_writes": False,
            "chart_launch": False,
            "dry_run": True,
            "full_native_transaction": True,
        }
    }


def _run_native_import(
    binary: Path,
    runtime_root: Path,
    source: Path,
    report_root: Path,
    import_type: str,
    timeout_seconds: int,
    regression_source: Path,
    matrix: object,
) -> int:
    report_root.mkdir(parents=True, exist_ok=True)
    log_path = report_root / "import.log"
    command = native_import_command(
        binary,
        source,
        import_type,
        max(1000, timeout_seconds * 1000),
        log_path,
    )
    process = None
    try:
        command = matrix.offscreen_command(command)
        process = subprocess.Popen(
            command,
            cwd=runtime_root,
            env={
                **os.environ,
                "TMPDIR": str(ROOT / "tmp"),
                # Automated native validation must not wait on a user's Pulse/
                # PipeWire session. The importer itself does not use audio.
                "SDL_AUDIODRIVER": "dummy",
                "ALSOFT_DRIVERS": "null",
            },
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
        )
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        report = {
            "status": "failed",
            "reason": f"native importer did not complete: {error}",
            "binary": str(binary),
            "runtime_root": str(runtime_root),
            "source": str(source),
            "donor_writes": False,
            "chart_launch": False,
            "structural_only": False,
        }
        (report_root / "import-preparation.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, sort_keys=True))
        return 2

    output = result.stdout + result.stderr
    markers = parse_import_markers(output)
    events = {str(marker.get("event")) for marker in markers}
    diagnostics = []
    if result.returncode != 0:
        diagnostics.append(f"native importer exited {result.returncode}")
    if "success" not in events:
        diagnostics.append("missing RUNTIME_IMPORT_SMOKE success marker")
    if "failure" in events:
        diagnostics.append("native importer emitted failure marker")
    diagnostics.extend(_native_asset_diagnostics(runtime_root, matrix))
    report = {
        "status": "passed" if not diagnostics else "failed",
        "returncode": result.returncode,
        "binary": str(binary),
        "runtime_root": str(runtime_root),
        "source": str(source),
        "log": str(log_path),
        "markers": markers,
        "events": sorted(events),
        "diagnostics": diagnostics,
        "donor_writes": False,
        "chart_launch": False,
        "structural_only": False,
        "full_native_transaction": True,
        "named_regression_source": str(regression_source),
        "named_regressions_separate": True,
    }
    (report_root / "import-preparation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(output, end="")
    print(json.dumps(report, sort_keys=True))
    return 0 if not diagnostics else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--binary",
        type=Path,
        default=DEFAULT_BINARY,
        help="already-built native binary for the full importer transaction",
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        help="binary cwd containing the complete assets/ runtime tree (defaults to binary parent)",
    )
    parser.add_argument("--import-type", default="Auto", help="native importer type (default: Auto)")
    parser.add_argument(
        "--regression-source",
        type=Path,
        default=DEFAULT_REGRESSION_SOURCE,
        help="read-only donor root for the named runtime regressions",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="structural fixture or native report root; must be below project tmp",
    )
    parser.add_argument("--timeout", type=int, default=240, help="import transaction timeout")
    parser.add_argument(
        "--structural-only",
        action="store_true",
        help="required acknowledgement that the retained artifact is not launchable",
    )
    parser.add_argument("--dry-run", action="store_true", help="validate sources and print the plan")
    args = parser.parse_args(argv)

    try:
        source = _resolve_source(args.source)
        if not source.is_dir():
            raise ValueError(f"selected Auto donor is not a directory: {source}")
        matrix = _load_matrix()
        if args.structural_only:
            output = _validate_output(args.output_root or DEFAULT_OUTPUT)
            _validate_empty(output)
            regression_source = _resolve_source(args.regression_source)
            if not regression_source.is_dir():
                raise ValueError(f"named regression donor is not a directory: {regression_source}")
            # Validate all named chart sources before the first destination write.
            for case in _external_regression_cases(matrix):
                _assert_file(
                    regression_source / "assets" / "data" / case.folder / (case.chart + ".json"),
                    f"named regression chart for {case.id}",
                )
            if args.dry_run:
                print(json.dumps(_dry_run_report(output, source, regression_source, matrix), sort_keys=True))
                return 0

            selected_root = output / "selected"
            regression_root = output / "regressions" / "modding-plus-fnf"
            selected_root.mkdir(parents=True, exist_ok=True)
            audit_command = [
                sys.executable,
                str(AUDIT),
                str(source),
                "--prepare-runtime-smoke",
                "--output-root",
                str(selected_root),
                "--timeout",
                str(args.timeout),
            ]
            environment = {**os.environ, "TMPDIR": str(ROOT / "tmp")}
            try:
                audit_result = subprocess.run(
                    audit_command,
                    cwd=ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=args.timeout,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                print(f"selected Auto transaction did not complete: {error}", file=sys.stderr)
                return 2
            print(audit_result.stdout, end="")
            print(audit_result.stderr, end="", file=sys.stderr)
            if audit_result.returncode != 0:
                return audit_result.returncode

            copied, case_sources = _copy_named_regressions(
                regression_source,
                regression_root,
                _external_regression_cases(matrix),
                matrix,
            )
            manifest = _manifest(
                output,
                source,
                regression_source,
                case_sources,
                selected_root,
                regression_root,
                matrix,
            )
            (output / MANIFEST_NAME).write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            print(
                json.dumps(
                    {
                        "runtime_smoke_structural_fixture": {
                            "root": str(output),
                            "manifest": str(output / MANIFEST_NAME),
                            "selected_root": str(selected_root),
                            "regression_root": str(regression_root),
                            "named_files_copied": copied,
                            "runtime_matrix_eligible": False,
                            "donor_writes": False,
                        }
                    },
                    sort_keys=True,
                )
            )
            return 0

        binary = _resolve_source(args.binary)
        runtime_root = _resolve_source(args.runtime_root or binary.parent)
        report_root = _validate_output(args.output_root or DEFAULT_NATIVE_REPORT)
        if not binary.is_file() or binary.is_symlink():
            raise ValueError(f"built native binary is not available: {binary}")
        if not runtime_root.is_dir() or not (runtime_root / "assets").is_dir():
            raise ValueError(f"native runtime root must contain assets/: {runtime_root}")
        if _paths_overlap(source, runtime_root):
            raise ValueError(
                "selected donor and native runtime root overlap; refusing a transaction "
                "that could write back into the donor"
            )
        if args.timeout <= 0:
            raise ValueError("--timeout must be positive")
        timeout_ms = max(1000, args.timeout * 1000)
        if args.dry_run:
            print(
                json.dumps(
                    _native_dry_run_report(
                        binary,
                        runtime_root,
                        source,
                        _resolve_source(args.regression_source),
                        report_root,
                        args.import_type,
                        timeout_ms,
                    ),
                    sort_keys=True,
                )
            )
            return 0
        if report_root.exists() and any(report_root.iterdir()):
            raise ValueError(f"native report root is not empty (refusing overwrite): {report_root}")
        return _run_native_import(
            binary,
            runtime_root,
            source,
            report_root,
            args.import_type,
            args.timeout,
            _resolve_source(args.regression_source),
            matrix,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
