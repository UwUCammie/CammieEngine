#!/usr/bin/env python3
"""Reconcile the Bruce hotfix rows using exact owner and source payload evidence.

This is a metadata-only audit. It compares chart JSON note payloads and event
sidecars, and checks audio file presence/size without decoding or hashing media.
It never writes to donor or runtime trees; --write updates only the two tmp
inventory snapshots used by the example-mods report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "tmp" / "codename_psych_inventory.json"
MATRIX = ROOT / "tmp" / "example_mods_chart_matrix.json"
PACKAGE_NAME = "vs_brucedaworst_update_2_hotfix"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def namespace_for(source_root: str | Path, engine: str) -> str:
    """Mirror CompatScriptManifest.namespaceFor() for the current host."""
    normalized = os.path.normpath(str(source_root).replace("\\", "/"))
    if not os.path.isabs(normalized):
        normalized = os.path.abspath(normalized).replace("\\", "/")
    base = Path(normalized).name or "root"
    label = f"{_slug(engine)}-{_slug(base)}".strip("-") or "imported-root"
    digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()[:10]
    return f"assets/imported_mods/{label}-{digest}"


def _safe_join(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe relative path: {relative}")
    resolved_root = root.resolve()
    resolved = (resolved_root / path).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"path escapes root: {relative}")
    return resolved


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _song(chart: Any, path: Path) -> dict[str, Any]:
    if not isinstance(chart, dict) or not isinstance(chart.get("song"), dict):
        raise ValueError(f"chart song object missing: {path}")
    return chart["song"]


def _note_rows(song: dict[str, Any], path: Path) -> int:
    notes = song.get("notes")
    if not isinstance(notes, list):
        raise ValueError(f"chart notes array missing: {path}")
    total = 0
    for section in notes:
        if not isinstance(section, dict) or not isinstance(section.get("sectionNotes"), list):
            raise ValueError(f"invalid chart section: {path}")
        total += len(section["sectionNotes"])
    return total


def audit_row(row: dict[str, Any], content_root: Path, runtime_root: Path,
              expected_owner: str) -> dict[str, Any]:
    """Verify that one runtime chart and its audio match this exact donor root."""
    source_chart = _safe_join(content_root, str(row["sourceChart"]))
    runtime_chart = _safe_join(runtime_root, str(row["runtimeChart"]))
    source_song = _song(_read_json(source_chart), source_chart)
    runtime_song = _song(_read_json(runtime_chart), runtime_chart)

    chart_payload_match = source_song.get("notes") == runtime_song.get("notes")
    source_rows = _note_rows(source_song, source_chart)
    runtime_rows = _note_rows(runtime_song, runtime_chart)

    manifest_path = runtime_chart.parent / "compatScripts.json"
    manifest = _read_json(manifest_path) if manifest_path.is_file() else {}
    selected = manifest.get("selectedRoot")
    roots = manifest.get("roots")
    exact_owner = selected == expected_owner and isinstance(roots, list) and any(
        isinstance(item, dict) and item.get("path") == expected_owner
        and str(item.get("engine", "")).casefold() == "psych engine"
        for item in roots
    )

    source_song_folder = _safe_join(content_root, f"songs/{row['song']}")
    runtime_song_key = runtime_song.get("song")
    if not isinstance(runtime_song_key, str) or not runtime_song_key:
        runtime_song_key = runtime_chart.parent.name
    runtime_song_folder = _safe_join(runtime_root, f"assets/songs/{runtime_song_key}")
    audio_records: list[dict[str, Any]] = []
    audio_match = True
    for name in ("Inst.ogg", "Voices.ogg"):
        source = source_song_folder / name
        if not source.is_file():
            if name == "Voices.ogg" and source_song.get("needsVoices") is True:
                audio_match = False
                audio_records.append({"file": name, "required": True, "sourcePresent": False,
                                      "runtimePresent": False, "sizeMatch": False})
            continue
        runtime = runtime_song_folder / name
        present = runtime.is_file()
        size_match = present and source.stat().st_size == runtime.stat().st_size
        required = name == "Inst.ogg" or source_song.get("needsVoices") is True
        if required and (not present or not size_match):
            audio_match = False
        audio_records.append({
            "file": name,
            "required": required,
            "sourcePresent": True,
            "runtimePresent": present,
            "sourceBytes": source.stat().st_size,
            "runtimeBytes": runtime.stat().st_size if present else None,
            "sizeMatch": bool(size_match),
        })

    source_events = source_chart.parent / "events.json"
    runtime_events = runtime_chart.parent / "events.json"
    events_match = True
    if source_events.is_file():
        events_match = runtime_events.is_file() and _read_json(source_events) == _read_json(runtime_events)

    matched = exact_owner and chart_payload_match and audio_match and events_match
    return {
        "song": row["song"],
        "difficulty": row.get("difficulty"),
        "sourceChart": str(source_chart),
        "runtimeChart": str(runtime_chart),
        "runtimeChartPresent": runtime_chart.is_file(),
        "expectedOwner": expected_owner,
        "selectedOwner": selected,
        "ownerManifestExact": exact_owner,
        "sourceNoteRows": source_rows,
        "runtimeNoteRows": runtime_rows,
        "noteRowCountMatch": source_rows == runtime_rows,
        "sourceNotePayloadMatch": chart_payload_match,
        "sourceAudioMetadataMatch": audio_match,
        "audioFiles": audio_records,
        "sourceEventsMatch": events_match,
        "ownerProvenanceVerified": bool(matched),
    }


def reconcile(inventory: dict[str, Any], matrix: dict[str, Any], runtime_root: Path) -> dict[str, Any]:
    packages = inventory.get("packages")
    package = next((item for item in packages or [] if item.get("name") == PACKAGE_NAME), None)
    if package is None:
        raise ValueError(f"package not found in inventory: {PACKAGE_NAME}")
    content_root = Path(package["contentRoot"])
    expected_owner = namespace_for(content_root, package["engine"])
    rows = [row for row in matrix.get("rows", []) if row.get("package") == PACKAGE_NAME]
    by_source = {row.get("sourceChart"): row for row in rows}
    evidence: list[dict[str, Any]] = []
    for song in package.get("songs", []):
        for chart in song.get("charts", []):
            source_chart = chart.get("chartPath")
            row = by_source.get(source_chart)
            if row is None:
                raise ValueError(f"matrix row missing for source chart: {source_chart}")
            evidence.append(audit_row(row, content_root, runtime_root, expected_owner))

    stage_json = _safe_join(content_root, "stages/nullspace.json")
    stage_lua = _safe_join(content_root, "stages/nullspace.lua")
    runtime_owner_root = _safe_join(runtime_root, expected_owner)
    runtime_stage_json = runtime_owner_root / "stages/nullspace.json"
    runtime_stage_lua = runtime_owner_root / "stages/nullspace.lua"
    stage_json_match = runtime_stage_json.is_file() and _read_json(stage_json) == _read_json(runtime_stage_json)
    stage_lua_match = runtime_stage_lua.is_file() and stage_lua.read_text(encoding="utf-8") == runtime_stage_lua.read_text(encoding="utf-8")

    return {
        "package": PACKAGE_NAME,
        "sourceRoot": str(content_root),
        "expectedOwner": expected_owner,
        "runtimeRoot": str(runtime_root.resolve()),
        "charts": evidence,
        "stageSourceParity": {
            "stageJsonEqual": stage_json_match,
            "stageLuaEqual": stage_lua_match,
            "stageMediaPaths": package.get("stageMediaFiles", []),
            "screenParityVerified": False,
            "note": "File/config parity only; nullspace runtime callbacks still need native visual verification.",
        },
    }


def update_snapshots(inventory: dict[str, Any], matrix: dict[str, Any], evidence: dict[str, Any]) -> None:
    package = next(item for item in inventory["packages"] if item.get("name") == PACKAGE_NAME)
    by_song = {row["song"].casefold(): row for row in evidence["charts"]}
    for song in package.get("songs", []):
        proof = by_song[song["id"].casefold()]
        matched = proof["ownerProvenanceVerified"]
        song["runtimeOwnerCandidates"] = [evidence["expectedOwner"]] if proof["ownerManifestExact"] else []
        song["runtimeCoverage"] = {
            "allSourceDifficultiesPresentInRuntime": bool(matched),
            "candidateOwners": song["runtimeOwnerCandidates"],
            "status": "verified-exact-owner-chart-audio" if matched else "not-owner-source-verified",
        }
        song["ownerProvenanceEvidence"] = {
            "selectedRootMatchesNamespaceForContentRoot": proof["ownerManifestExact"],
            "sourceChartNotePayloadMatches": proof["sourceNotePayloadMatch"],
            "requiredAudioMetadataMatches": proof["sourceAudioMetadataMatch"],
            "sourceEventsMatch": proof["sourceEventsMatch"],
        }
        for chart in song.get("charts", []):
            match = next((row for row in evidence["charts"] if row["song"].casefold() == song["id"].casefold()), None)
            chart["runtimeCoverage"] = {
                "candidateOwners": [evidence["expectedOwner"]] if match and match["ownerManifestExact"] else [],
                "allSourceDifficultiesPresentInRuntime": bool(match and match["ownerProvenanceVerified"]),
                "sourceNotePayloadMatches": bool(match and match["sourceNotePayloadMatch"]),
                "sourceAudioMetadataMatches": bool(match and match["sourceAudioMetadataMatch"]),
            }

    package["runtimeOwnerCandidates"] = [evidence["expectedOwner"]] if all(
        row["ownerManifestExact"] for row in evidence["charts"]
    ) else []
    package["runtimeCoverage"] = {
        "ownerSongCount": sum(1 for row in evidence["charts"] if row["ownerProvenanceVerified"]),
        "sourceSongCount": len(package.get("songs", [])),
        "sourceSongsMatched": [row["song"] for row in evidence["charts"] if row["ownerProvenanceVerified"]],
        "sourceSongsUnmatched": [row["song"] for row in evidence["charts"] if not row["ownerProvenanceVerified"]],
        "selectedRoot": evidence["expectedOwner"],
        "matchRequires": ["exact selectedRoot namespace", "identical chart note payload",
                          "required audio file size match", "identical event sidecar when present"],
    }

    summary = inventory.setdefault("summary", {})
    matches = summary.setdefault("sourceSongsWithCurrentOwnerManifestMatch", {})
    unmatched = summary.setdefault("currentOwnerManifestUnmatchedSongs", {})
    matches[PACKAGE_NAME] = package["runtimeCoverage"]["ownerSongCount"]
    remaining = package["runtimeCoverage"]["sourceSongsUnmatched"]
    if remaining:
        unmatched[PACKAGE_NAME] = remaining
    else:
        unmatched.pop(PACKAGE_NAME, None)

    for row in matrix.get("rows", []):
        if row.get("package") != PACKAGE_NAME:
            continue
        proof = next(item for item in evidence["charts"] if item["song"].casefold() == row["song"].casefold())
        row["runtimeOwner"] = proof["selectedOwner"]
        row["runtimeChartPresent"] = proof["runtimeChartPresent"]
        row["ownerMatched"] = proof["ownerProvenanceVerified"]
        row["sourceVariantImported"] = proof["ownerProvenanceVerified"]
        row["runtimeNoteCount"] = proof["runtimeNoteRows"]
        row["sourceNoteCountMatched"] = proof["noteRowCountMatch"]
        row["sourceNotePayloadMatched"] = proof["sourceNotePayloadMatch"]
        row["sourceAudioMetadataMatched"] = proof["sourceAudioMetadataMatch"]
        row["sourceEventsMatched"] = proof["sourceEventsMatch"]
        row["structurallyCovered"] = bool(proof["runtimeChartPresent"] and proof["ownerProvenanceVerified"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=INVENTORY)
    parser.add_argument("--matrix", type=Path, default=MATRIX)
    parser.add_argument("--runtime-root", type=Path,
                        default=Path("export/release/linux/bin"))
    parser.add_argument("--write", action="store_true", help="update only the specified tmp JSON snapshots")
    parser.add_argument("--output", type=Path, help="write the full evidence JSON to this path")
    args = parser.parse_args()
    inventory = _read_json(args.inventory)
    matrix = _read_json(args.matrix)
    evidence = reconcile(inventory, matrix, args.runtime_root)
    if args.write:
        update_snapshots(inventory, matrix, evidence)
        args.inventory.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        args.matrix.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rendered = json.dumps(evidence, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if all(row["ownerProvenanceVerified"] for row in evidence["charts"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
