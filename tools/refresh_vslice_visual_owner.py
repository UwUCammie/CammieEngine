#!/usr/bin/env python3
"""Plan/apply a backed-up V-Slice visual-only refresh for one imported owner.

Planning is read-only apart from its plan file under the repository's ``tmp``.
Application requires an explicitly reviewed plan and holds the release runtime
lock while it invokes the native import-smoke transaction from
``prepare_runtime_smoke_fixture.py``. The transaction is accepted only when it
adds files below the selected owner's namespace and leaves pre-existing owner,
chart, menu, settings, and global note-style files unchanged.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
import time
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
ENGINE = "V-Slice"
SCHEMA = 1
LOCK_RELATIVE = ".tools/runtime-0.lock"
AUDIO_EXTENSIONS = {"ogg", "mp3", "wav", "flac", "m4a", "aac"}
MAX_FINGERPRINT_CHARTS = 2048
MAX_FINGERPRINT_CHART_BYTES = 8 * 1024 * 1024
MAX_FINGERPRINT_TOTAL_BYTES = 128 * 1024 * 1024
MAX_FINGERPRINT_AUDIO_ENTRIES = 256
MAX_FINGERPRINT_PACKAGE_CHARTS = 16384
MAX_FINGERPRINT_PACKAGE_BYTES = 256 * 1024 * 1024
MAX_FINGERPRINT_PACKAGE_ENTRIES = 32768


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strip_jsonc(text: str) -> str:
    """Remove JSONC comments and trailing commas without touching strings."""
    out = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue
        if char == "/" and index + 1 < len(text) and text[index + 1] == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and index + 1 < len(text) and text[index + 1] == "*":
            index += 2
            end = text.find("*/", index)
            if end < 0:
                raise ValueError("unterminated JSONC block comment")
            out.extend("\n" for newline in text[index:end] if newline == "\n")
            index = end + 2
            continue
        out.append(char)
        index += 1
    text = "".join(out)
    out = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue
        if char == ",":
            look = index + 1
            while look < len(text) and text[look].isspace():
                look += 1
            if look < len(text) and text[look] in "]}":
                index += 1
                continue
        out.append(char)
        index += 1
    return "".join(out)


def parse_json(path: Path, *, jsonc: bool = False):
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(_strip_jsonc(raw) if jsonc else raw,
                          object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"invalid JSON at {path}: {error}") from error


def _safe_relative(value: str) -> PurePosixPath:
    relative = PurePosixPath(value.replace("\\", "/"))
    if (relative.is_absolute() or not relative.parts
            or any(part in ("", ".", "..") for part in relative.parts)):
        raise ValueError(f"unsafe relative path: {value}")
    return relative


def _safe_path(root: Path, relative: str, *, require_file: bool = False) -> Path:
    rel = _safe_relative(relative)
    root = root.resolve()
    candidate = root.joinpath(*rel.parts)
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink in protected path: {relative}")
    if not candidate.resolve(strict=False).is_relative_to(root):
        raise ValueError(f"path escapes protected root: {relative}")
    if require_file and (not candidate.is_file() or candidate.is_symlink()):
        raise ValueError(f"missing regular file: {candidate}")
    return candidate


def _is_regular(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _case_child(parent: Path, name: str, *, directory: bool | None = None) -> Path | None:
    if not parent.is_dir() or parent.is_symlink():
        return None
    matches = []
    for item in parent.iterdir():
        if item.name.casefold() != name.casefold():
            continue
        if directory is True and not item.is_dir():
            continue
        if directory is False and not _is_regular(item):
            continue
        matches.append(item)
    if len(matches) > 1:
        raise ValueError(f"case-insensitive path collision below {parent}: {name}")
    return matches[0] if matches else None


def _safe_tree(root: Path, *, include_hashes: bool = True) -> tuple[list[dict], list[str]]:
    """List regular files and directories without following any symlink."""
    if not root.exists():
        return [], []
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"protected tree is not a safe directory: {root}")
    files: list[dict] = []
    directories: list[str] = []
    stack = [(root, PurePosixPath("."))]
    while stack:
        folder, relative = stack.pop()
        try:
            entries = sorted(folder.iterdir(), key=lambda path: (path.name.casefold(), path.name))
        except OSError as error:
            raise ValueError(f"could not enumerate protected tree {folder}: {error}") from error
        for child in entries:
            rel = child.name if str(relative) == "." else (relative / child.name).as_posix()
            if child.is_symlink():
                raise ValueError(f"symlink in protected tree: {child}")
            if child.is_dir():
                directories.append(rel)
                stack.append((child, PurePosixPath(rel)))
            elif child.is_file():
                row = {"path": rel, "size": child.stat().st_size}
                if include_hashes:
                    row["sha256"] = sha256_file(child)
                files.append(row)
            else:
                raise ValueError(f"non-regular entry in protected tree: {child}")
    files.sort(key=lambda row: (row["path"].casefold(), row["path"]))
    directories.sort(key=lambda value: (value.casefold(), value))
    return files, directories


def _direct_directories(root: Path) -> list[str]:
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"unsafe directory inventory root: {root}")
    names = []
    for item in sorted(root.iterdir(), key=lambda path: (path.name.casefold(), path.name)):
        if item.is_symlink():
            raise ValueError(f"symlink in directory inventory: {item}")
        if not item.is_dir():
            continue
        names.append(item.name)
    return names


def _directory(root: Path, name: str) -> Path | None:
    return _case_child(root, name, directory=True)


def _resolve_vslice_layout(source_root: Path) -> tuple[Path, Path, Path | None]:
    """Mirror ImportRootScanner's V-Slice content/data/audio layout choices."""
    if source_root.is_symlink() or not source_root.is_dir():
        raise ValueError(f"source root is not a regular directory: {source_root}")
    content = _directory(source_root, "assets") or source_root
    base_game = _directory(content, "base_game")
    if base_game is not None:
        shared = _directory(base_game, "shared")
        songs = _directory(base_game, "songs")
        data = _directory(base_game, "data")
        if data is None and shared is not None:
            data = _directory(shared, "data")
        if shared is not None and songs is not None and data is not None:
            content = base_game
    data_root = _directory(content, "data")
    shared = _directory(content, "shared")
    if data_root is None and shared is not None:
        data_root = _directory(shared, "data")
    if data_root is None:
        raise ValueError("selected source root has no V-Slice data directory")
    songs_root = _directory(data_root, "songs")
    if songs_root is None:
        raise ValueError("selected source root has no data/songs directory")
    audio_root = _directory(content, "songs") or _directory(content, "music")
    return content, songs_root, audio_root


def _suffix_file(folder: Path, suffix: str) -> Path | None:
    if not folder.is_dir() or folder.is_symlink():
        return None
    matches = [path for path in folder.iterdir()
               if path.name.casefold().endswith(suffix.casefold()) and _is_regular(path)]
    matches.sort(key=lambda path: (path.name.casefold(), path.name))
    return matches[0] if matches else None


def _named_file(folder: Path, stem: str) -> Path | None:
    for extension in (".json", ".jsonc"):
        match = _case_child(folder, stem + extension, directory=False)
        if match is not None:
            return match
    return None


def _safe_variation_suffix(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9_-]+", "-", lowered)
    lowered = re.sub(r"-+", "-", lowered).strip("-")
    return lowered


def _metadata_song_name(metadata: object, chart: object) -> str:
    for document, field in ((metadata, "songName"), (metadata, "song"), (chart, "songName")):
        if isinstance(document, dict):
            value = document.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return "v-slice-song"


def _display_name_info(source_root: Path) -> tuple[str, bool]:
    """Mirror ImportSongOwnership.displayNameInfo for the smoke name prompt."""
    roots = [source_root]
    inner_name = None
    mods = _directory(source_root, "mods")
    if mods is not None:
        roots.insert(0, mods)
        children = [path for path in mods.iterdir() if path.is_dir() and not path.is_symlink()]
        if len(children) == 1:
            inner_name = children[0].name
            roots.insert(0, children[0])
    for root in roots:
        for filename in ("_polymod_meta.json", "pack.json", "mod.json"):
            path = _case_child(root, filename, directory=False)
            if path is None or path.stat().st_size > 131072:
                continue
            try:
                data = parse_json(path)
            except ValueError:
                continue
            if isinstance(data, dict):
                for field in ("title", "name", "displayName"):
                    value = data.get(field)
                    if isinstance(value, str) and value.strip() and value.strip().lower() != "null":
                        return value.strip(), True
    if inner_name is None:
        project = _case_child(source_root, "Project.xml", directory=False)
        if project is not None and project.stat().st_size <= 131072:
            try:
                import xml.etree.ElementTree as ET
                for app in ET.parse(project).getroot().iter("app"):
                    value = (app.get("title") or "").strip()
                    if value and value.lower() != "null" and "$" not in value:
                        return value, True
            except (OSError, ET.ParseError):
                pass
    return (inner_name or source_root.name), False


def _v_slice_source_pairs(source_root: Path, songs_root: Path, audio_root: Path | None) -> list[dict]:
    results = []
    source_folders = []
    seen_destination = set()
    for folder in sorted(songs_root.iterdir(), key=lambda path: (path.name.casefold(), path.name)):
        if folder.is_symlink():
            raise ValueError(f"symlink in V-Slice data/songs: {folder}")
        if not folder.is_dir():
            continue
        base_metadata = _suffix_file(folder, "-metadata.json")
        base_chart = _suffix_file(folder, "-chart.json")
        if base_metadata is None or base_chart is None:
            continue
        if folder.name in (".", "..") or any(char in folder.name for char in "/\\:\0"):
            raise ValueError(f"unsafe V-Slice song folder name: {folder.name}")
        if folder.name.casefold() in source_folders:
            raise ValueError(f"case-insensitive duplicate V-Slice song folder: {folder.name}")
        source_folders.append(folder.name.casefold())
        metadata = parse_json(base_metadata, jsonc=False)
        if not isinstance(metadata, dict):
            raise ValueError(f"V-Slice metadata must be an object: {base_metadata}")
        chart = parse_json(base_chart, jsonc=False)
        if not isinstance(chart, dict):
            raise ValueError(f"V-Slice chart must be an object: {base_chart}")
        pairs = [(base_metadata, base_chart, "")]
        play_data = metadata.get("playData") if isinstance(metadata.get("playData"), dict) else {}
        raw_variations = play_data.get("songVariations", [])
        if raw_variations is not None and not isinstance(raw_variations, list):
            raise ValueError(f"V-Slice songVariations must be an array: {base_metadata}")
        seen_variations = set()
        for raw_variation in raw_variations or []:
            if not isinstance(raw_variation, str) or not raw_variation.strip():
                continue
            variation = raw_variation.strip()
            if variation.casefold() in seen_variations:
                continue
            seen_variations.add(variation.casefold())
            suffix = _safe_variation_suffix(variation)
            if not suffix:
                continue
            variation_meta = _named_file(folder, folder.name + "-metadata-" + variation)
            variation_chart = _named_file(folder, folder.name + "-chart-" + variation)
            # ImportRootScanner's song importer only fingerprints complete pairs.
            if variation_meta is None or variation_chart is None:
                continue
            pairs.append((variation_meta, variation_chart, variation))
        for metadata_path, chart_path, variation in pairs:
            pair_metadata = metadata if metadata_path == base_metadata else parse_json(metadata_path)
            pair_chart = chart if chart_path == base_chart else parse_json(chart_path)
            audio_folder = _directory(audio_root, folder.name) if audio_root is not None else None
            if audio_folder is None and audio_root is not None:
                audio_folder = _directory(audio_root, _metadata_song_name(pair_metadata, pair_chart))
            if audio_folder is not None and audio_folder.is_symlink():
                raise ValueError(f"symlink in V-Slice audio folder: {audio_folder}")
            output_name = folder.name.lower()
            if variation:
                output_name += "-" + _safe_variation_suffix(variation)
            if output_name in seen_destination:
                raise ValueError(f"duplicate V-Slice destination song key: {output_name}")
            seen_destination.add(output_name)
            paths = []
            for path in (metadata_path, chart_path):
                if path not in paths:
                    paths.append(path)
            if len(paths) > MAX_FINGERPRINT_CHARTS:
                raise ValueError(f"too many chart inputs for {folder.name}")
            total_chart_bytes = 0
            fingerprint_entries = []
            source_hashes = []
            for path in paths:
                if path.is_symlink() or not path.is_file():
                    raise ValueError(f"V-Slice chart input is not a regular file: {path}")
                resolved = path.resolve()
                if not resolved.is_relative_to(source_root):
                    raise ValueError(f"V-Slice chart input escapes source root: {path}")
                size = path.stat().st_size
                if size < 0 or size > MAX_FINGERPRINT_CHART_BYTES:
                    raise ValueError(f"V-Slice chart input exceeds importer fingerprint limit: {path}")
                total_chart_bytes += size
                if total_chart_bytes > MAX_FINGERPRINT_TOTAL_BYTES:
                    raise ValueError(f"V-Slice song chart inputs exceed fingerprint budget: {folder.name}")
                relative = path.relative_to(source_root).as_posix()
                content = path.read_bytes()
                fingerprint_entries.append("chart|" + relative + "|" + md5_bytes(content))
                source_hashes.append({"path": relative, "sha256": hashlib.sha256(content).hexdigest(),
                                      "size": len(content)})
            fingerprint_entries.append("song|" + folder.name.lower())
            if audio_folder is None:
                fingerprint_entries.append("audio|none")
            else:
                audio_files = []
                audio_entries = sorted(audio_folder.iterdir(), key=lambda path: (path.name.casefold(), path.name))
                if len(audio_entries) > MAX_FINGERPRINT_AUDIO_ENTRIES:
                    raise ValueError(f"too many audio entries for V-Slice song {folder.name}")
                for audio in audio_entries:
                    if audio.is_symlink():
                        raise ValueError(f"symlink in V-Slice audio folder: {audio}")
                    if not audio.is_file() or audio.suffix.lower().lstrip(".") not in AUDIO_EXTENSIONS:
                        continue
                    if not audio.resolve().is_relative_to(source_root):
                        raise ValueError(f"V-Slice audio input escapes source root: {audio}")
                    audio_files.append(audio)
                if len(audio_files) > MAX_FINGERPRINT_AUDIO_ENTRIES:
                    raise ValueError(f"too many audio entries for V-Slice song {folder.name}")
                audio_manifest = []
                for audio in audio_files:
                    audio_manifest.append(audio.relative_to(source_root).as_posix()
                                          + "|" + str(audio.stat().st_size))
                audio_manifest.sort()
                fingerprint_entries.extend("audio|" + value for value in audio_manifest)
            results.append({
                "sourceFolder": folder.name,
                "destinationFolder": output_name,
                "metadata": metadata_path.relative_to(source_root).as_posix(),
                "chart": chart_path.relative_to(source_root).as_posix(),
                "variation": variation,
                "audioFolder": (audio_folder.relative_to(source_root).as_posix()
                                if audio_folder is not None else None),
                "sourceAudioFiles": ([{"path": audio.relative_to(source_root).as_posix(),
                                        "size": audio.stat().st_size,
                                        "mtimeNs": audio.stat().st_mtime_ns,
                                        "inode": audio.stat().st_ino}
                                       for audio in audio_files]
                                      if audio_folder is not None else []),
                "sourceFiles": source_hashes,
                "fingerprintEntries": fingerprint_entries,
            })
    if not results:
        raise ValueError("no importable V-Slice metadata/chart pairs were found")
    total_chart_files = sum(len(song["sourceFiles"]) for song in results)
    total_chart_bytes = sum(row["size"] for song in results for row in song["sourceFiles"])
    if total_chart_files > MAX_FINGERPRINT_PACKAGE_CHARTS:
        raise ValueError("selected V-Slice package exceeds importer chart-count fingerprint limit")
    if total_chart_bytes > MAX_FINGERPRINT_PACKAGE_BYTES:
        raise ValueError("selected V-Slice package exceeds importer fingerprint byte limit")
    entry_count = sum(len(song["fingerprintEntries"]) for song in results)
    if entry_count > MAX_FINGERPRINT_PACKAGE_ENTRIES:
        raise ValueError("selected V-Slice package exceeds importer fingerprint entry limit")
    return results


def _source_fingerprint(songs: list[dict]) -> str:
    entries = [entry for song in songs for entry in song["fingerprintEntries"]]
    entries.sort()
    return md5_bytes("\n".join(entries).encode("utf-8"))


def _source_snapshot(source_root: Path) -> dict:
    """Recompute only donor chart/audio state; runtime manifests may change during import."""
    source_root = source_root.resolve()
    content_root, songs_root, audio_root = _resolve_vslice_layout(source_root)
    songs = _v_slice_source_pairs(source_root, songs_root, audio_root)
    source_rows = [row for song in songs for row in song["sourceFiles"]]
    unique_rows = {row["path"]: row for row in source_rows}
    source_files = sorted(unique_rows.values(), key=lambda row: (row["path"].casefold(), row["path"]))
    source_songs = [{key: value for key, value in song.items() if key != "fingerprintEntries"}
                    for song in songs]
    return {"contentRoot": str(content_root), "sourceFingerprint": _source_fingerprint(songs),
            "sourceFiles": source_files, "sourceSongs": source_songs}


def _metadata_identity(source_root: Path) -> dict | None:
    roots = [source_root]
    mods = _directory(source_root, "mods")
    inner_name = None
    if mods is not None:
        child_dirs = [path for path in mods.iterdir() if path.is_dir() and not path.is_symlink()]
        if len(child_dirs) == 1:
            inner_name = child_dirs[0].name
            roots.insert(0, child_dirs[0])
    for root in roots:
        for filename in ("_polymod_meta.json", "pack.json", "mod.json", "metadata.json"):
            path = _case_child(root, filename, directory=False)
            if path is None or path.stat().st_size > 131072:
                continue
            try:
                data = parse_json(path)
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue
            for field in ("id", "modId", "modID", "uuid", "packageId", "packageID"):
                value = data.get(field)
                if isinstance(value, str) and value.strip() and len(value.strip()) <= 256:
                    return {"kind": "id", "value": value.strip()}
            for field in ("title", "name", "displayName"):
                value = data.get(field)
                if isinstance(value, str) and value.strip() and len(value.strip()) <= 256:
                    return {"kind": "package-name", "value": value.strip()}
    if inner_name:
        return {"kind": "inner-package-name", "value": inner_name}
    display_name, display_authored = _display_name_info(source_root)
    if display_authored:
        return {"kind": "package-title", "value": display_name}
    project = _case_child(source_root, "Project.xml", directory=False)
    if project is not None and project.stat().st_size <= 131072:
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(project)
            for app in tree.getroot().iter("app"):
                value = (app.get("title") or "").strip()
                if value and "$" not in value:
                    return {"kind": "package-title", "value": value}
        except (OSError, ET.ParseError):
            pass
    return None


def _slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def _path_namespace(source_root: Path) -> str:
    normalized = source_root.resolve().as_posix().rstrip("/")
    basename = source_root.name
    return "assets/imported_mods/v-slice-" + _slug(basename) + "-" + hashlib.md5(
        normalized.encode("utf-8")).hexdigest()[:10]


def _source_identity(source_root: Path, package_name: str | None,
                     existing_provenance: list[dict]) -> str | None:
    info = _metadata_identity(source_root)
    inferred_name = package_name.strip() if package_name and package_name.strip() else None
    if inferred_name is None:
        for record in existing_provenance:
            if record.get("nameSource") == "user" and isinstance(record.get("modName"), str):
                inferred_name = record["modName"].strip() or None
                if inferred_name:
                    break
    if inferred_name and (info is None or info.get("kind") not in ("id", "package-name")):
        return "v-slice|user-name|" + inferred_name.casefold()
    if info is None:
        return None
    return "v-slice|" + str(info["kind"]).casefold() + "|" + str(info["value"]).casefold()


def _read_manifest(folder: Path) -> tuple[dict, dict]:
    manifest_path = folder / "compatScripts.json"
    provenance_path = folder / "importProvenance.json"
    if manifest_path.is_symlink() or provenance_path.is_symlink():
        raise ValueError(f"symlink in ownership metadata: {folder}")
    if not manifest_path.is_file():
        raise ValueError(f"selected V-Slice chart has no compatibility ownership manifest: {folder}")
    manifest = parse_json(manifest_path)
    provenance = parse_json(provenance_path) if provenance_path.is_file() else {}
    if not isinstance(manifest, dict) or not isinstance(provenance, dict):
        raise ValueError(f"ownership metadata must be JSON objects: {folder}")
    return manifest, provenance


def _owner_row(manifest: dict, owner: str) -> dict | None:
    roots = manifest.get("roots")
    if not isinstance(roots, list):
        return None
    matches = [entry for entry in roots if isinstance(entry, dict) and entry.get("path") == owner
               and str(entry.get("engine", "")).casefold() == ENGINE.casefold()]
    return matches[0] if len(matches) == 1 else None


def _validate_owner_name(owner: object) -> str:
    if not isinstance(owner, str):
        raise ValueError("selected owner path is missing")
    rel = _safe_relative(owner)
    if (len(rel.parts) != 3 or rel.parts[0] != "assets" or rel.parts[1] != "imported_mods"
            or rel.parts[2] in ("", ".", "..")):
        raise ValueError(f"selected owner must be below assets/imported_mods: {owner}")
    return rel.as_posix()


def _locate_selected_owner(runtime_root: Path, source_root: Path, songs: list[dict], fingerprint: str,
                           package_name: str | None, owner_hint: str | None) -> tuple[str, list[dict]]:
    data_root = runtime_root / "assets/data"
    if data_root.is_symlink() or not data_root.is_dir():
        raise ValueError(f"runtime chart tree is missing or unsafe: {data_root}")
    target_names = {song["destinationFolder"].casefold() for song in songs}
    if len(target_names) != len(songs):
        raise ValueError("source package has duplicate native chart folder keys")
    owner_candidates: dict[str, list[tuple[Path, dict, dict]]] = {}
    for folder in sorted(data_root.iterdir(), key=lambda path: (path.name.casefold(), path.name)):
        if folder.is_symlink():
            raise ValueError(f"symlink in runtime chart tree: {folder}")
        if not folder.is_dir():
            continue
        manifest_path = folder / "compatScripts.json"
        provenance_path = folder / "importProvenance.json"
        if not manifest_path.exists():
            continue
        manifest, provenance = _read_manifest(folder)
        if (provenance.get("sourceEngine") != ENGINE
                or provenance.get("sourceFingerprint") != fingerprint):
            continue
        owner = _validate_owner_name(provenance.get("sourceOwner"))
        if (provenance.get("destinationFolder") != folder.name
                or manifest.get("selectedRoot") != owner
                or _owner_row(manifest, owner) is None):
            continue
        owner_candidates.setdefault(owner, []).append((folder, manifest, provenance))
    legacy_manifest_owner = not owner_candidates
    if owner_candidates:
        if owner_hint is not None:
            owner_hint = _validate_owner_name(owner_hint)
            if owner_hint not in owner_candidates:
                raise ValueError("requested owner has no chart manifest with the current source fingerprint")
            owner = owner_hint
        elif len(owner_candidates) == 1:
            owner = next(iter(owner_candidates))
        else:
            raise ValueError("multiple selected owners match the source fingerprint; pass --owner to disambiguate")
    else:
        # Older imports predate per-chart importProvenance.json. Recover only
        # the historical path-derived owner, and require every donor chart's
        # compatibility manifest to select that exact owner. The current donor
        # fingerprint remains pinned and is rechecked immediately before apply.
        owner = _path_namespace(source_root)
        if owner_hint is not None and _validate_owner_name(owner_hint) != owner:
            raise ValueError("legacy manifests can only be refreshed through their path-derived owner")
        for song in songs:
            target = song["destinationFolder"]
            matches = [folder for folder in data_root.iterdir()
                       if folder.is_dir() and not folder.is_symlink()
                       and folder.name.casefold() == target.casefold()]
            if len(matches) != 1:
                raise ValueError(f"legacy source chart folder is missing or ambiguous: {target}")
            manifest, provenance = _read_manifest(matches[0])
            if manifest.get("selectedRoot") != owner or _owner_row(manifest, owner) is None:
                raise ValueError(f"legacy chart manifest does not select the donor path-derived owner: {target}")
            if provenance and (provenance.get("sourceEngine") != ENGINE
                               or provenance.get("sourceOwner") != owner
                               or provenance.get("sourceFingerprint") != fingerprint):
                raise ValueError(f"legacy chart has conflicting newer source provenance: {target}")

    selected = []
    for song in songs:
        target = song["destinationFolder"]
        matches = [folder for folder in data_root.iterdir()
                   if folder.is_dir() and not folder.is_symlink() and folder.name.casefold() == target.casefold()]
        if len(matches) != 1:
            raise ValueError(f"source chart folder is missing or ambiguous in runtime: {target}")
        folder = matches[0]
        manifest, provenance = _read_manifest(folder)
        if manifest.get("selectedRoot") != owner or _owner_row(manifest, owner) is None:
            raise ValueError(f"source chart folder is not selected by the fingerprint-matched owner: {folder.name}")
        roots = manifest.get("roots")
        root_paths = []
        if isinstance(roots, list):
            for entry in roots:
                if not isinstance(entry, dict):
                    continue
                root_path = _validate_owner_name(entry.get("path"))
                root_paths.append(root_path)
        paths = set(root_paths)
        if len(paths) < 1:
            raise ValueError(f"chart has no selected owner rows: {folder.name}")
        if not legacy_manifest_owner and not provenance:
            raise ValueError(f"fingerprint-matched source provenance is missing: {folder.name}")
        if provenance and (provenance.get("sourceEngine") != ENGINE or provenance.get("sourceOwner") != owner
                           or provenance.get("sourceFingerprint") != fingerprint
                           or provenance.get("destinationFolder") != folder.name):
            raise ValueError(f"chart provenance does not prove the selected owner: {folder.name}")
        selected.append({
            "sourceFolder": song["sourceFolder"],
            "destinationFolder": target,
            "runtimeFolder": folder.name,
            "manifest": (folder / "compatScripts.json").relative_to(runtime_root).as_posix(),
            "provenance": ((folder / "importProvenance.json").relative_to(runtime_root).as_posix()
                           if (folder / "importProvenance.json").is_file() else None),
            "ownerCount": len(roots) if isinstance(roots, list) else 0,
            "visualOnlyBranchExpected": isinstance(roots, list) and len(roots) >= 2,
        })
    # Every discovered source entry must resolve to one selected-owner chart.
    if len(selected) != len(songs):
        raise ValueError("not every donor song resolves to an existing mixed-owner chart")
    return owner, selected


def _snapshot_one(scope: str, root: Path, relative: str) -> dict:
    path = _safe_path(root, relative)
    if not path.exists():
        return {"scope": scope, "path": relative, "exists": False}
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"protected target is not a regular file: {path}")
    return {"scope": scope, "path": relative, "exists": True,
            "size": path.stat().st_size, "sha256": sha256_file(path)}


def _add_snapshot(snapshots: dict, scope: str, root: Path, relative: str) -> None:
    key = scope + ":" + relative
    snapshots[key] = _snapshot_one(scope, root, relative)


def _tree_snapshot(snapshots: dict, scope: str, root: Path, relative: str) -> dict:
    tree = _safe_path(root, relative)
    files, directories = _safe_tree(tree)
    for item in files:
        _add_snapshot(snapshots, scope, root,
                      (PurePosixPath(relative) / PurePosixPath(item["path"])).as_posix())
    return {"scope": scope, "path": relative,
            "exists": tree.exists(),
            "files": [item["path"] for item in files],
            "directories": directories}


def _package_visual_identity(source_root: Path, package_name: str | None,
                             selected_charts: list[dict], runtime_root: Path,
                             fingerprint: str, owner: str) -> tuple[str | None, str | None, bool, str]:
    records = []
    for row in selected_charts:
        if row["provenance"] is None:
            continue
        provenance = parse_json(_safe_path(runtime_root, row["provenance"], require_file=True))
        if isinstance(provenance, dict):
            records.append(provenance)
    identities = {record.get("sourceIdentity") for record in records
                  if isinstance(record.get("sourceIdentity"), str)}
    if len(identities) > 1:
        raise ValueError("selected owner's chart provenance has inconsistent source identities")
    effective_name = package_name
    if effective_name is None:
        labels = {record.get("modName", "").strip() for record in records
                  if record.get("nameSource") == "user" and isinstance(record.get("modName"), str)
                  and record.get("modName", "").strip()}
        if len(labels) > 1:
            raise ValueError("selected owner's user-confirmed package labels are inconsistent")
        effective_name = next(iter(labels), None)
    display_name, display_authored = _display_name_info(source_root)
    if package_name is not None and display_authored:
        raise ValueError("--package-name is valid only when the source importer would ask for an unnamed package")
    if not display_authored and not effective_name:
        raise ValueError("this source package requires its original user-confirmed import label")
    if effective_name and (len(effective_name) > 80 or any(ord(char) < 32 or ord(char) == 127
                                                           for char in effective_name)):
        raise ValueError("package label is outside the import prompt's valid range")
    current_identity = _source_identity(source_root, effective_name, records)
    old_identity = next(iter(identities), None)
    legacy_without_provenance = all(row["provenance"] is None for row in selected_charts)
    if legacy_without_provenance and _path_namespace(source_root) != owner:
        raise ValueError("legacy ownership metadata cannot be recovered by source path")
    if current_identity is not None:
        if not legacy_without_provenance and old_identity != current_identity:
            raise ValueError("donor package identity does not match the fingerprint-matched owner")
    elif old_identity is not None:
        raise ValueError("donor identity is unavailable; pass the original --package-name for this owner")
    elif _path_namespace(source_root) != owner:
        raise ValueError("owner cannot be reselected safely by source path or package identity")
    return current_identity or old_identity, effective_name, display_authored, display_name


def make_plan(source_root: Path, runtime_root: Path, *, repository_root: Path = ROOT,
              binary: Path | None = None, package_name: str | None = None,
              owner_hint: str | None = None, timeout: int = 240) -> dict:
    source_root = source_root.resolve()
    runtime_root = runtime_root.resolve()
    repository_root = repository_root.resolve()
    if not source_root.is_dir() or not runtime_root.is_dir():
        raise ValueError("source and runtime roots must both be existing directories")
    if source_root.is_relative_to(runtime_root) or runtime_root.is_relative_to(source_root):
        raise ValueError("source donor and native runtime roots overlap")
    if not (runtime_root / "assets").is_dir():
        raise ValueError(f"native runtime root must contain assets/: {runtime_root}")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    content_root, songs_root, audio_root = _resolve_vslice_layout(source_root)
    source_songs = _v_slice_source_pairs(source_root, songs_root, audio_root)
    fingerprint = _source_fingerprint(source_songs)
    owner, selected_charts = _locate_selected_owner(runtime_root, source_root, source_songs,
                                                     fingerprint, package_name, owner_hint)
    identity, effective_package_name, display_authored, display_name = _package_visual_identity(
        source_root, package_name, selected_charts, runtime_root, fingerprint, owner)

    # Catch additional V-Slice-like roots before the broad native scanner sees
    # the parent. The passed source path must be the one selected root; nested
    # independent roots would make a visual-only run import unrelated songs.
    extra_roots = _nested_vslice_roots(source_root, content_root)
    if extra_roots:
        raise ValueError("source selection contains additional V-Slice roots: "
                         + ", ".join(extra_roots))

    data_root = runtime_root / "assets/data"
    audio_runtime = runtime_root / "assets/songs"
    data_dirs = _direct_directories(data_root)
    audio_dirs = _direct_directories(audio_runtime)
    for song in source_songs:
        name = song["destinationFolder"]
        data_matches = [entry for entry in data_dirs if entry.casefold() == name.casefold()]
        if len(data_matches) != 1:
            raise ValueError(f"chart folder is not uniquely installed for {name}")
        audio_matches = [entry for entry in audio_dirs if entry.casefold() == name.casefold()]
        if len(audio_matches) != 1:
            raise ValueError(f"audio folder is missing or ambiguous for {name}")
        qualified = re.compile(r"^" + re.escape(name) + r"--v-slice-[0-9a-f]{10}$", re.IGNORECASE)
        if any(qualified.fullmatch(entry) for entry in data_dirs):
            raise ValueError(f"duplicate owner-qualified chart folder exists for {name}")

    snapshots: dict[str, dict] = {}
    owner_relative = owner
    owner_tree = _tree_snapshot(snapshots, "runtime", runtime_root, owner_relative)
    if not owner_tree["exists"]:
        raise ValueError("selected owner namespace is missing from the native runtime")
    chart_trees = []
    for folder in sorted({row["runtimeFolder"] for row in selected_charts}, key=str.casefold):
        chart_relative = "assets/data/" + folder
        tree = _tree_snapshot(snapshots, "runtime", runtime_root, chart_relative)
        chart_trees.append(tree)
    audio_trees = []
    for folder in sorted({row["destinationFolder"] for row in source_songs}, key=str.casefold):
        audio_relative = "assets/songs/" + folder
        tree = _tree_snapshot(snapshots, "runtime", runtime_root, audio_relative)
        if not tree["exists"]:
            raise ValueError(f"selected source audio folder is missing: {audio_relative}")
        audio_trees.append(tree)
    runtime_files = [
        "assets/data/freeplaySongJson.jsonc", "assets/data/freeplaySongJson.json",
        "assets/data/options.json",
        "assets/images/custom_chars/custom_chars.jsonc",
        "assets/images/custom_chars/custom_chars.json",
        "assets/images/custom_stages/custom_stages.json",
        "assets/images/custom_ui/ui_packs/ui.json",
    ]
    repo_files = [
        "assets/data/freeplaySongJson.jsonc", "assets/data/freeplaySongJson.json",
        "assets/data/options.json",
    ]
    for relative in runtime_files:
        _add_snapshot(snapshots, "runtime", runtime_root, relative)
    for relative in repo_files:
        _add_snapshot(snapshots, "repo", repository_root, relative)
    ui_tree = _tree_snapshot(snapshots, "runtime", runtime_root,
                             "assets/images/custom_ui/ui_packs")
    global_trees = [ui_tree]
    source_files = []
    for song in source_songs:
        source_files.extend(song["sourceFiles"])
    unique_source_files = {row["path"]: row for row in source_files}
    source_hashes = []
    for relative, prior in sorted(unique_source_files.items(), key=lambda item: item[0].casefold()):
        path = _safe_path(source_root, relative, require_file=True)
        current = {"path": relative, "size": path.stat().st_size, "sha256": sha256_file(path)}
        if current["size"] != prior["size"]:
            raise ValueError(f"source chart changed while planning: {relative}")
        source_hashes.append(current)

    owner_files = list(owner_tree["files"])
    binary_path = (binary or (repository_root / "export/release/linux/bin/Funkin")).resolve()
    if binary_path.parent != runtime_root:
        raise ValueError("native binary must be directly inside the selected runtime root")
    if not binary_path.is_file() or binary_path.is_symlink():
        raise ValueError(f"built native binary is missing or unsafe: {binary_path}")
    return {
        "schema": SCHEMA,
        "status": "planned",
        "dryRun": True,
        "createdUtc": datetime.now(timezone.utc).isoformat(),
        "projectRoot": str(repository_root),
        "sourceRoot": str(source_root),
        "contentRoot": str(content_root),
        "runtimeRoot": str(runtime_root),
        "binary": str(binary_path),
        "engine": ENGINE,
        "importType": ENGINE,
        "packageName": package_name,
        "effectivePackageName": effective_package_name,
        "packageNamePromptRequired": not display_authored,
        "displayName": display_name,
        "sourceIdentity": identity,
        "ownerAssociationMethod": ("chart-provenance-source-fingerprint"
                                    if all(chart["provenance"] is not None for chart in selected_charts)
                                    else "legacy-path-derived-owner-and-selectedRoot-manifests"),
        "selectedRoot": owner,
        "sourceFingerprint": fingerprint,
        "sourceFingerprintAlgorithm": "ImportSongOwnership.setSourceFingerprintHints V-Slice chart/audio projection (MD5)",
        "sourceFiles": source_hashes,
        "sourceSongs": [{key: value for key, value in song.items() if key != "fingerprintEntries"}
                        for song in source_songs],
        "selectedCharts": selected_charts,
        "ownerFiles": owner_files,
        "snapshots": list(snapshots.values()),
        "watchedTrees": [owner_tree, *chart_trees, *audio_trees, *global_trees],
        "runtimeDataDirectories": data_dirs,
        "runtimeAudioDirectories": audio_dirs,
        "timeoutSeconds": timeout,
        "preflight": {
            "allSourceSongsAreExistingOwnedCharts": True,
            "chartAndAudioDirectoryNamesAreUnique": True,
            "sourceFingerprintPersistedInChartProvenance": all(
                chart["provenance"] is not None for chart in selected_charts),
            "visualOnlyBranchExpectedForEveryChart": all(
                chart["visualOnlyBranchExpected"] for chart in selected_charts),
            "restoreEveryPreexistingFileAfterNativeImport": True,
            "existingFilesMayChangeDuringImportButAreRestoredBeforeValidation": True,
            "allowedAdditions": [owner],
        },
    }


def _nested_vslice_roots(source_root: Path, content_root: Path) -> list[str]:
    """Bounded directory-only check for independent nested V-Slice roots."""
    allowed = {source_root.resolve(), content_root.resolve()}
    base_game = _directory(content_root, "base_game")
    if base_game is not None:
        allowed.add(base_game.resolve())
    skip = {"images", "songs", "music", "videos", "shaders", "fonts", "sounds",
            ".git", ".tools", "node_modules", "export", "build", "bin", "target"}
    found = []
    queue = [(source_root, 0)]
    visited = 0
    while queue:
        folder, depth = queue.pop(0)
        visited += 1
        if visited > 8192:
            raise ValueError("nested V-Slice root preflight exceeded its directory budget")
        if depth > 10:
            continue
        if folder.resolve() == content_root.resolve() and folder.resolve() != source_root.resolve():
            continue
        if folder.resolve() not in allowed:
            nested_content = _directory(folder, "assets") or folder
            nested_data = _directory(nested_content, "data")
            nested_songs = _directory(nested_data, "songs") if nested_data is not None else None
            if nested_songs is not None and _has_vslice_pair(nested_songs):
                found.append(folder.relative_to(source_root).as_posix())
                continue
        try:
            children = sorted(folder.iterdir(), key=lambda path: (path.name.casefold(), path.name))
        except OSError as error:
            raise ValueError(f"could not inspect source package roots: {error}") from error
        for child in children:
            if child.is_symlink():
                continue
            if child.resolve() == content_root.resolve():
                continue
            if folder.resolve() == source_root.resolve() == content_root.resolve() \
                    and child.name.casefold() in {"assets", "data", "songs", "music", "images",
                                                   "shared", "videos", "sounds", "fonts", "shaders"}:
                continue
            if child.is_dir() and child.name.casefold() not in skip:
                queue.append((child, depth + 1))
    return sorted(set(found), key=str.casefold)


def _has_vslice_pair(songs_root: Path) -> bool:
    if songs_root.is_symlink() or not songs_root.is_dir():
        return False
    for folder in songs_root.iterdir():
        if folder.is_dir() and not folder.is_symlink():
            if (_suffix_file(folder, "-metadata.json") is not None
                    and _suffix_file(folder, "-chart.json") is not None):
                return True
    return False


def _fresh_preflight(plan: dict) -> dict:
    return make_plan(
        Path(plan["sourceRoot"]), Path(plan["runtimeRoot"]),
        repository_root=Path(plan["projectRoot"]), binary=Path(plan["binary"]),
        package_name=plan.get("packageName"), owner_hint=plan["selectedRoot"],
        timeout=int(plan.get("timeoutSeconds", 240)))


def _compare_fresh_plan(plan: dict, fresh: dict) -> None:
    for key in ("sourceFingerprint", "selectedRoot", "sourceIdentity", "sourceFiles",
                "sourceSongs", "selectedCharts", "ownerFiles", "snapshots",
                "watchedTrees", "runtimeDataDirectories", "runtimeAudioDirectories"):
        if plan.get(key) != fresh.get(key):
            raise ValueError(f"reviewed plan is stale: {key} changed")


def _path_for_scope(plan: dict, scope: str, relative: str) -> Path:
    root = Path(plan["runtimeRoot"] if scope == "runtime" else plan["projectRoot"])
    return _safe_path(root, relative)


def _backup_snapshots(plan: dict, backup: Path, plan_path: Path) -> None:
    for item in plan["snapshots"]:
        scope, relative = item["scope"], item["path"]
        source = _path_for_scope(plan, scope, relative)
        if not item["exists"]:
            continue
        target = backup / scope / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if sha256_file(target) != item["sha256"]:
            raise ValueError(f"backup verification failed: {scope}/{relative}")
    shutil.copy2(plan_path, backup / "reviewed-plan.json")


def _remove_path(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _restore_protected(plan: dict, backup: Path) -> list[str]:
    """Restore every protected pre-existing byte and remove protected absences."""
    errors = []
    for item in plan["snapshots"]:
        try:
            target = _path_for_scope(plan, item["scope"], item["path"])
            if item["exists"]:
                saved = backup / item["scope"] / item["path"]
                if not saved.is_file() or sha256_file(saved) != item["sha256"]:
                    raise ValueError(f"verified backup is missing or corrupt: {item['scope']}/{item['path']}")
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() or target.is_symlink():
                    _remove_path(target)
                shutil.copy2(saved, target)
                if sha256_file(target) != item["sha256"]:
                    raise ValueError(f"restoration hash mismatch: {item['scope']}/{item['path']}")
            elif target.exists() or target.is_symlink():
                _remove_path(target)
        except (OSError, ValueError) as error:
            errors.append(str(error))
    return errors


def _stage_default_test_options(plan: dict) -> str:
    repo = Path(plan["projectRoot"])
    runtime = Path(plan["runtimeRoot"])
    source = _safe_path(repo, "assets/data/options.json", require_file=True)
    target = _safe_path(runtime, "assets/data/options.json")
    if target.exists() and (target.is_symlink() or not target.is_file()):
        raise ValueError(f"runtime options file is unsafe: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if sha256_file(source) != sha256_file(target):
        raise ValueError("could not stage the repository's default test options")
    return sha256_file(source)


def _snapshot_now(plan: dict, item: dict) -> dict:
    path = _path_for_scope(plan, item["scope"], item["path"])
    if not path.exists():
        return {"scope": item["scope"], "path": item["path"], "exists": False}
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"protected file became unsafe: {path}")
    return {"scope": item["scope"], "path": item["path"], "exists": True,
            "size": path.stat().st_size, "sha256": sha256_file(path)}


def _tree_now(plan: dict, tree: dict) -> tuple[dict, set[str]]:
    root = Path(plan["runtimeRoot"] if tree["scope"] == "runtime" else plan["projectRoot"])
    path = _safe_path(root, tree["path"])
    files, directories = _safe_tree(path)
    file_paths = {item["path"] for item in files}
    return ({"scope": tree["scope"], "path": tree["path"], "exists": path.exists(),
             "files": sorted(file_paths, key=lambda value: (value.casefold(), value)),
             "directories": directories}, file_paths)


def _check_no_duplicate_folders(root: Path, selected_names: list[str]) -> bool:
    if not root.exists():
        return True
    if root.is_symlink() or not root.is_dir():
        return False
    counts = {name.casefold(): 0 for name in selected_names}
    for path in root.iterdir():
        if path.is_symlink():
            return False
        if path.is_dir():
            key = path.name.casefold()
            if key in counts:
                counts[key] += 1
    return all(count <= 1 for count in counts.values())


def _postflight(plan: dict, runner_result: dict) -> dict:
    changed = []
    for item in plan["snapshots"]:
        current = _snapshot_now(plan, item)
        if current != item:
            changed.append({"scope": item["scope"], "path": item["path"],
                            "before": item, "after": current})
    tree_changes = []
    new_owner_files = []
    for tree in plan["watchedTrees"]:
        current, current_files = _tree_now(plan, tree)
        before_files = set(tree["files"])
        before_dirs = set(tree["directories"])
        added = sorted(current_files - before_files, key=lambda value: (value.casefold(), value))
        deleted = sorted(before_files - current_files, key=lambda value: (value.casefold(), value))
        added_dirs = sorted(set(current["directories"]) - before_dirs,
                            key=lambda value: (value.count("/"), value.casefold(), value))
        deleted_dirs = sorted(before_dirs - set(current["directories"]),
                              key=lambda value: (value.count("/"), value.casefold(), value))
        if added or deleted or current["directories"] != tree["directories"]:
            tree_changes.append({"tree": tree["path"], "added": added, "deleted": deleted,
                                 "addedDirectories": added_dirs, "deletedDirectories": deleted_dirs})
        if tree["path"] == plan["selectedRoot"]:
            new_owner_files = added
    runtime = Path(plan["runtimeRoot"])
    data_dirs = _direct_directories(runtime / "assets/data")
    audio_dirs = _direct_directories(runtime / "assets/songs")
    selected_names = [song["destinationFolder"] for song in plan["sourceSongs"]]
    duplicate_folders = not (_check_no_duplicate_folders(runtime / "assets/data", selected_names)
                             and _check_no_duplicate_folders(runtime / "assets/songs", selected_names))
    new_data_dirs = sorted(set(data_dirs) - set(plan["runtimeDataDirectories"]), key=str.casefold)
    new_audio_dirs = sorted(set(audio_dirs) - set(plan["runtimeAudioDirectories"]), key=str.casefold)
    removed_data_dirs = sorted(set(plan["runtimeDataDirectories"]) - set(data_dirs), key=str.casefold)
    removed_audio_dirs = sorted(set(plan["runtimeAudioDirectories"]) - set(audio_dirs), key=str.casefold)
    expected_success = "success" in set(runner_result.get("events", []))
    violations = []
    if runner_result.get("status") != "passed" or not expected_success:
        violations.append("native importer did not report success")
    if changed:
        violations.append("pre-existing protected file bytes changed or a file appeared/disappeared")
    if duplicate_folders:
        violations.append("duplicate chart/audio folders were detected")
    if new_data_dirs or new_audio_dirs:
        violations.append("native visual-only import created a chart/audio folder")
    if removed_data_dirs or removed_audio_dirs:
        violations.append("native visual-only import removed a chart/audio folder")
    owner_tree = next(tree for tree in plan["watchedTrees"]
                      if tree["path"] == plan["selectedRoot"] and tree["scope"] == "runtime")
    global_tree_changes = [change for change in tree_changes
                           if change["tree"] != plan["selectedRoot"]]
    if global_tree_changes:
        violations.append("files changed outside the selected owner namespace")
    if not new_owner_files:
        violations.append("native visual-only import added no selected-owner files")
    return {
        "passed": not violations,
        "violations": violations,
        "changedProtectedFiles": changed,
        "treeChanges": tree_changes,
        "newOwnerFiles": new_owner_files,
        "newDataDirectories": new_data_dirs,
        "newAudioDirectories": new_audio_dirs,
        "removedDataDirectories": removed_data_dirs,
        "removedAudioDirectories": removed_audio_dirs,
        "duplicateFolders": duplicate_folders,
        "ownerTree": owner_tree,
    }


def _remove_empty_parents(path: Path, stop: Path) -> None:
    current = path.parent
    while current != stop and current.is_relative_to(stop):
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def _cleanup_additions(plan: dict) -> list[str]:
    _removed, errors = _cleanup_new_entries(plan, include_owner=True)
    return errors


def _transaction_song_folder_names(plan: dict) -> set[str]:
    """Return canonical and stable V-Slice owner-qualified destination names."""
    names = {str(song["destinationFolder"]).casefold() for song in plan["sourceSongs"]}
    owner_name = PurePosixPath(plan["selectedRoot"]).name
    owner_match = re.search(r"-([0-9a-f]{10})$", owner_name, re.IGNORECASE)
    if owner_match is not None:
        digest = owner_match.group(1).lower()
        names.update((str(song["destinationFolder"]) + "--v-slice-" + digest).casefold()
                     for song in plan["sourceSongs"])
    return names


def _cleanup_new_entries(plan: dict, *, include_owner: bool) -> tuple[list[str], list[str]]:
    """Remove entries absent from the reviewed baseline, optionally preserving owner output."""
    removed = []
    errors = []
    for tree in plan["watchedTrees"]:
        if not include_owner and tree["scope"] == "runtime" and tree["path"] == plan["selectedRoot"]:
            continue
        try:
            root = Path(plan["runtimeRoot"] if tree["scope"] == "runtime" else plan["projectRoot"])
            base = _safe_path(root, tree["path"])
            before_files = set(tree["files"])
            before_dirs = set(tree["directories"])
            if not base.exists() and not base.is_symlink():
                continue
            if base.is_symlink():
                base.unlink()
                removed.append(f"{tree['scope']}:{tree['path']}")
                continue
            if not base.is_dir():
                base.unlink()
                removed.append(f"{tree['scope']}:{tree['path']}")
                continue
            discovered = []
            walk_errors = []
            for directory, dirs, files in os.walk(base, topdown=False, followlinks=False,
                                                   onerror=walk_errors.append):
                directory_path = Path(directory)
                for filename in files:
                    candidate = directory_path / filename
                    relative = candidate.relative_to(base).as_posix()
                    if relative not in before_files:
                        discovered.append((candidate, relative, False))
                for dirname in dirs:
                    candidate = directory_path / dirname
                    relative = candidate.relative_to(base).as_posix()
                    if relative not in before_dirs or candidate.is_symlink():
                        discovered.append((candidate, relative, True))
            for error in walk_errors:
                errors.append(str(error))
            for candidate, relative, is_directory in sorted(
                    discovered, key=lambda row: (-row[1].count("/"), row[1].casefold())):
                try:
                    if candidate.is_symlink():
                        candidate.unlink()
                        removed.append(f"{tree['scope']}:{tree['path']}/{relative}")
                    elif is_directory and candidate.is_dir():
                        candidate.rmdir()
                        removed.append(f"{tree['scope']}:{tree['path']}/{relative}")
                    elif not is_directory and candidate.exists():
                        if candidate.is_dir():
                            errors.append(f"unexpected directory replaced file below protected tree: {candidate}")
                        else:
                            candidate.unlink()
                            removed.append(f"{tree['scope']}:{tree['path']}/{relative}")
                except OSError as error:
                    errors.append(str(error))
            if not tree["exists"] and base.exists():
                try:
                    base.rmdir()
                    removed.append(f"{tree['scope']}:{tree['path']}")
                except OSError as error:
                    errors.append(str(error))
        except (OSError, ValueError) as error:
            errors.append(str(error))

    runtime = Path(plan["runtimeRoot"])
    transaction_song_names = _transaction_song_folder_names(plan)
    for root_relative, original_names in (("assets/data", plan["runtimeDataDirectories"]),
                                          ("assets/songs", plan["runtimeAudioDirectories"])):
        try:
            parent = _safe_path(runtime, root_relative)
            original = {name.casefold() for name in original_names}
            for target in list(parent.iterdir()):
                if not target.is_dir() and not target.is_symlink():
                    continue
                if target.name.casefold() in original:
                    continue
                if target.name.casefold() not in transaction_song_names:
                    errors.append(f"preserved unrelated new entry outside refresh destinations: {target}")
                    continue
                if target.is_symlink() or target.is_dir():
                    _remove_path(target)
                    removed.append(f"runtime:{root_relative}/{target.name}")
                else:
                    errors.append(f"preserved unexpected non-directory at refresh destination: {target}")
        except (OSError, ValueError) as error:
            errors.append(str(error))
    return removed, errors


def _remove_outside_owner_additions(plan: dict) -> tuple[list[str], list[str]]:
    """Clean importer output outside the selected owner before selected-owner validation."""
    return _cleanup_new_entries(plan, include_owner=False)


def _rollback(plan: dict, backup: Path, postflight: dict | None = None) -> list[str]:
    errors = _cleanup_additions(plan)
    errors.extend(_restore_protected(plan, backup))
    return errors


def _importer_compatibility_diagnostics(native_result: dict) -> dict:
    """Preserve importer-reported dependency errors without conflating them with transaction status."""
    markers = native_result.get("markers", [])
    error_rows = []
    details = set()
    if isinstance(markers, list):
        for marker in markers:
            if not isinstance(marker, dict):
                continue
            raw_errors = marker.get("errors", 0)
            try:
                errors = max(0, int(raw_errors))
            except (TypeError, ValueError):
                errors = 0
            raw_details = marker.get("errorDetails", [])
            marker_details = sorted({item for item in raw_details if isinstance(item, str) and item}) \
                if isinstance(raw_details, list) else []
            if errors or marker_details:
                error_rows.append({"event": marker.get("event"), "errors": errors,
                                   "errorDetails": marker_details})
                details.update(marker_details)
    return {
        "evaluatedGameplayCompatibility": False,
        "reportedErrorCount": sum(row["errors"] for row in error_rows),
        "errorMarkers": error_rows,
        "unresolvedSourceDependencies": sorted(details),
    }


def _load_preparer():
    path = ROOT / "tools/prepare_runtime_smoke_fixture.py"
    spec = importlib.util.spec_from_file_location("vslice_owner_runtime_preparer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load prepare_runtime_smoke_fixture.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_native_import(plan: dict, report_root: Path) -> dict:
    helper = _load_preparer()
    report_root.mkdir(parents=True, exist_ok=False)
    log_path = report_root / "import.log"
    command = helper.native_import_command(
        Path(plan["binary"]), Path(plan["sourceRoot"]), ENGINE,
        max(1000, int(plan["timeoutSeconds"]) * 1000), log_path)
    if plan.get("packageNamePromptRequired"):
        command.extend(["--smoke-import-package-name", str(plan["effectivePackageName"])])
    process = None
    try:
        matrix = helper._load_matrix()
        command = matrix.offscreen_command(command)
        process = subprocess.Popen(
            command,
            cwd=plan["runtimeRoot"],
            env={**os.environ, "TMPDIR": str(Path(plan["projectRoot"]) / "tmp"),
                 "SDL_AUDIODRIVER": "dummy", "ALSOFT_DRIVERS": "null"},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", start_new_session=True)
        stdout, stderr = process.communicate(timeout=int(plan["timeoutSeconds"]))
        output = stdout + stderr
        markers = helper.parse_import_markers(output)
        events = sorted({str(marker.get("event")) for marker in markers})
        (report_root / "native-output.log").write_text(output, encoding="utf-8")
        return {"status": "passed" if process.returncode == 0 and "success" in events
                and "failure" not in events else "failed",
                "returncode": process.returncode, "events": events, "markers": markers,
                "command": command, "log": str(log_path),
                "stdoutLog": str(report_root / "native-output.log"),
                "reason": "" if process.returncode == 0 and "success" in events
                and "failure" not in events else "missing successful native import marker"}
    except subprocess.TimeoutExpired as error:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        return {"status": "failed", "reason": f"native import timed out: {error}",
                "events": [], "markers": [], "command": command}
    except (OSError, RuntimeError, ValueError) as error:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        return {"status": "failed", "reason": f"native import could not run: {error}",
                "events": [], "markers": [], "command": command}


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def apply_plan(plan: dict, plan_path: Path, *, runner: Callable | None = None) -> dict:
    if plan.get("schema") != SCHEMA or plan.get("status") != "planned":
        raise ValueError("plan schema/status is not applicable")
    project_root = Path(plan["projectRoot"]).resolve()
    plan_path = plan_path.resolve()
    if not plan_path.is_relative_to(project_root / "tmp"):
        raise ValueError("reviewed plan must be stored under the project tmp directory")
    if not plan_path.is_file() or plan_path.is_symlink():
        raise ValueError("reviewed plan file is missing or unsafe")
    if (plan.get("dryRun") is not True
            or plan.get("preflight", {}).get("restoreEveryPreexistingFileAfterNativeImport") is not True):
        raise ValueError("plan is not a read-only backed-up selected-owner transaction")
    lock_path = project_root / LOCK_RELATIVE
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = lock_path.open("a+")
    backup = None
    try:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError(f"release runtime lock is held: {lock_path}") from error
        fresh = _fresh_preflight(plan)
        _compare_fresh_plan(plan, fresh)
        backup_parent = project_root / "tmp/import-refresh-backups/vslice-visual-owner"
        backup_parent.mkdir(parents=True, exist_ok=True)
        backup = backup_parent / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup.mkdir(exist_ok=False)
        _backup_snapshots(plan, backup, plan_path)
        report_root = project_root / "tmp/vslice-visual-owner-imports" / backup.name
        default_options_sha256 = None
        native = {"status": "failed", "reason": "native import was not started",
                  "events": [], "markers": []}
        attempted = None
        attempted_error = ""
        transaction_error = ""
        source_unchanged = False
        source_checked = False
        source_error = ""
        restoration_errors = []
        outside_owner_removed = []
        outside_owner_cleanup_errors = []
        try:
            try:
                default_options_sha256 = _stage_default_test_options(plan)
                try:
                    native = runner(plan, report_root) if runner is not None else _run_native_import(plan, report_root)
                except Exception as error:
                    native = {"status": "failed", "reason": f"native import runner raised: {error}",
                              "events": [], "markers": []}
                try:
                    fresh_source = _source_snapshot(Path(plan["sourceRoot"]))
                    source_unchanged = (fresh_source["sourceFingerprint"] == plan["sourceFingerprint"]
                                        and fresh_source["sourceFiles"] == plan["sourceFiles"]
                                        and fresh_source["sourceSongs"] == plan["sourceSongs"])
                    source_checked = True
                except Exception as error:
                    source_unchanged = False
                    source_checked = True
                    source_error = str(error)
                try:
                    attempted = _postflight(plan, native)
                except Exception as error:
                    attempted_error = str(error)
            except Exception as error:
                transaction_error = f"post-backup transaction raised: {error}"
            finally:
                try:
                    restoration_errors = _restore_protected(plan, backup)
                except Exception as error:
                    restoration_errors = [f"protected-file restoration raised: {error}"]
                try:
                    outside_owner_removed, outside_owner_cleanup_errors = \
                        _remove_outside_owner_additions(plan)
                except Exception as error:
                    outside_owner_cleanup_errors = [f"outside-owner cleanup raised: {error}"]
        except Exception as error:
            # This outer guard keeps lock release and an explicit receipt even
            # if a future finally-path change itself raises unexpectedly.
            transaction_error = transaction_error or f"post-backup safety wrapper raised: {error}"

        final_postflight_error = ""
        try:
            result = _postflight(plan, native)
        except Exception as error:
            final_postflight_error = str(error)
            result = {"passed": False, "violations": ["post-restoration postflight failed"],
                      "changedProtectedFiles": [], "treeChanges": [], "newOwnerFiles": [],
                      "newDataDirectories": [], "newAudioDirectories": [],
                      "removedDataDirectories": [], "removedAudioDirectories": [],
                      "removedOutsideOwnerAdditions": [],
                      "outsideOwnerCleanupErrors": [],
                      "duplicateFolders": None}
        result["restorationErrors"] = restoration_errors
        result["removedOutsideOwnerAdditions"] = outside_owner_removed
        result["outsideOwnerCleanupErrors"] = outside_owner_cleanup_errors
        result["attemptedProtectedFileChanges"] = (attempted or {}).get("changedProtectedFiles", [])
        result["attemptedTreeChanges"] = (attempted or {}).get("treeChanges", [])
        if attempted_error:
            result["passed"] = False
            result["violations"].append("pre-restoration postflight failed")
            result["preRestorationPostflightError"] = attempted_error
        if final_postflight_error:
            result["passed"] = False
            result["finalPostflightError"] = final_postflight_error
        if transaction_error:
            result["passed"] = False
            result["violations"].append("post-backup transaction raised an exception")
            result["transactionError"] = transaction_error
        if restoration_errors:
            result["passed"] = False
            result["violations"].append("one or more backed-up files could not be restored")
        if outside_owner_cleanup_errors:
            result["passed"] = False
            result["violations"].append("one or more additions outside the selected owner could not be removed")
        if source_checked and not source_unchanged:
            result["passed"] = False
            result["violations"].append("source charts/audio changed during native import")
            result["sourceError"] = source_error
        rollback_errors = []
        if not result["passed"]:
            try:
                rollback_errors = _rollback(plan, backup, result)
            except Exception as error:
                rollback_errors = [f"rollback raised an exception: {error}"]
        receipt = {
            "schema": SCHEMA,
            "status": ("applied" if result["passed"] else
                       "rollback-incomplete" if rollback_errors else "rolled-back"),
            "selectedRoot": plan["selectedRoot"],
            "sourceRoot": plan["sourceRoot"],
            "sourceFingerprint": plan["sourceFingerprint"],
            "nativeImport": native,
            "compatibilityDiagnostics": _importer_compatibility_diagnostics(native),
            "postflight": result,
            "protectedFilesRestoredAfterImport": not restoration_errors,
            "defaultTestOptionsSha256": default_options_sha256,
            "rollbackErrors": rollback_errors,
            "backup": str(backup),
            "completedUtc": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(backup / "receipt.json", receipt)
        return receipt
    finally:
        lock.close()


def _project_tmp_path(value: Path, project_root: Path, *, must_not_exist: bool) -> Path:
    path = value.resolve()
    tmp = (project_root / "tmp").resolve()
    if not path.is_relative_to(tmp) or path == tmp:
        raise ValueError("plan and receipt files must be below repository ./tmp")
    if must_not_exist and path.exists():
        raise ValueError(f"refusing to overwrite existing output: {path}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan_command = commands.add_parser("plan", help="write a read-only review plan")
    plan_command.add_argument("--source-root", type=Path, required=True,
                              help="one V-Slice package root (not a parent containing several packages)")
    plan_command.add_argument("--runtime-root", type=Path, required=True,
                              help="built runtime directory containing assets/ and the game binary")
    plan_command.add_argument("--binary", type=Path, default=ROOT / "export/release/linux/bin/Funkin")
    plan_command.add_argument("--package-name", help="original import label for an unnamed package")
    plan_command.add_argument("--owner", help="disambiguate multiple fingerprint-matched owners")
    plan_command.add_argument("--timeout", type=int, default=240)
    plan_command.add_argument("--output", type=Path, required=True,
                              help="new plan file below repository ./tmp")
    apply_command = commands.add_parser("apply", help="apply one explicitly reviewed plan")
    apply_command.add_argument("--plan", type=Path, required=True)
    apply_command.add_argument("--reviewed", action="store_true", required=True,
                               help="confirm this exact plan was reviewed")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            output = _project_tmp_path(args.output, ROOT, must_not_exist=True)
            plan = make_plan(args.source_root, args.runtime_root, binary=args.binary,
                             package_name=args.package_name, owner_hint=args.owner,
                             timeout=args.timeout)
            _write_json(output, plan)
            print(json.dumps({"status": "planned", "plan": str(output),
                              "selectedRoot": plan["selectedRoot"],
                              "sourceFingerprint": plan["sourceFingerprint"],
                              "songs": len(plan["sourceSongs"]),
                              "protectedFiles": len(plan["snapshots"]),
                              "nativeImport": False}, sort_keys=True))
            return 0
        plan_path = _project_tmp_path(args.plan, ROOT, must_not_exist=False)
        plan = parse_json(plan_path)
        receipt = apply_plan(plan, plan_path)
        print(json.dumps(receipt, sort_keys=True))
        return 0 if receipt["status"] == "applied" else 1
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
