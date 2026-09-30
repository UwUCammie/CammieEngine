#!/usr/bin/env python3
"""Refresh current installed evidence for an existing Example Mods chart matrix.

The source chart keys and note counts come from the reviewed inventory. This
tool checks those keys against the mounted donors, then rechecks the selected
runtime chart, owner, and gameplay note count. It never changes an import.
Explicitly undeclared source keys with zero note rows are retained in a
separate non-playable diagnostic list and are not paired with runtime charts.
Unknown packages still need a separate source inventory before adding rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXAMPLES = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
DEFAULT_RUNTIME = ROOT / "export/release/linux/bin"
DEFAULT_MATRIX = ROOT / "tmp/example_mods_current_chart_matrix_after_fnas_install.json"
DEFAULT_INVENTORY = ROOT / "tmp/example_mods_nonchart_entity_inventory_20260929.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_child(root: Path, relative: str) -> Path:
    if not isinstance(relative, str):
        raise ValueError(f"relative path is not text: {relative!r}")
    part = Path(relative)
    if not relative or part.is_absolute() or ".." in part.parts:
        raise ValueError(f"unsafe relative path: {relative!r}")
    target = (root / part).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"path escapes root: {relative!r}")
    return target


def catalog_package(packages: list[dict], label: str) -> dict:
    matched = [package for package in packages if label.casefold() in (
        str(package.get("name", "")).casefold(),
        Path(str(package.get("sourceRoot", ""))).name.casefold(),
    )]
    if len(matched) != 1:
        raise ValueError(f"package catalog match is not unique for {label!r}: {len(matched)}")
    return matched[0]


def source_root(package: dict, examples: Path) -> Path:
    recorded = Path(str(package["sourceRoot"]))
    if recorded.exists():
        resolved = recorded.resolve()
        if not resolved.is_relative_to(examples.resolve()):
            raise ValueError(f"catalog source root escapes examples: {recorded}")
        return resolved
    # Packages may move between the top level and an engine category. Match
    # only the exact recorded basename in these two bounded positions.
    name = recorded.name
    candidates = [examples / name]
    candidates.extend(parent / name for parent in examples.iterdir() if parent.is_dir())
    found = sorted({path.resolve() for path in candidates if path.exists()})
    if len(found) != 1:
        raise ValueError(f"moved source root is not unique for {name!r}: {len(found)}")
    return found[0]


def source_bytes(root: Path, relative: str) -> tuple[bytes, str]:
    if root.is_file() and root.suffix.lower() == ".zip":
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError(f"unsafe archive member: {relative!r}")
        with zipfile.ZipFile(root) as archive:
            return archive.read(relative), str(root) + "!" + relative
    direct = safe_child(root, relative)
    if direct.is_file():
        return direct.read_bytes(), str(direct)
    # Some installations contain the actual mod one or two folders below the
    # selected installation directory. Do not recursively search its assets.
    candidates: list[Path] = []
    for child in root.iterdir():
        if not child.is_dir() or not child.resolve().is_relative_to(root.resolve()):
            continue
        first = safe_child(child, relative)
        if first.is_file():
            candidates.append(first)
        for grandchild in child.iterdir():
            if grandchild.is_dir() and grandchild.resolve().is_relative_to(root.resolve()):
                second = safe_child(grandchild, relative)
                if second.is_file():
                    candidates.append(second)
    found = sorted(set(candidates))
    if len(found) != 1:
        raise FileNotFoundError(f"source chart is not unique under {root}: {relative} ({len(found)})")
    return found[0].read_bytes(), str(found[0])


def runtime_chart_data(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    payload = json.loads(data.decode("utf-8").rstrip("\x00\t\r\n "))
    sections = payload["song"]["notes"]
    if not isinstance(sections, list):
        raise ValueError("chart notes are not an array")
    count = 0
    for section in sections:
        rows = section["sectionNotes"]
        if not isinstance(rows, list):
            raise ValueError("sectionNotes is not an array")
        count += len(rows)
    return sha256(data), count


def is_undeclared_raw_key(row: dict) -> bool:
    """Identify an undeclared source key without guessing from names."""
    count = row.get("sourceNoteCount")
    return (row.get("declaredDifficulty") is False
            and isinstance(count, (int, float)) and not isinstance(count, bool) and count >= 0)


def vslice_metadata_stem(source_chart: str) -> str | None:
    """Map `<song>-chart[-variation].json` to its sibling metadata stem."""
    path = PurePosixPath(source_chart)
    if path.suffix.lower() not in {".json", ".jsonc"}:
        return None
    stem = path.stem
    marker = "-chart"
    marker_index = stem.rfind(marker)
    if marker_index < 0:
        return None
    variation_suffix = stem[marker_index + len(marker):]
    if variation_suffix and not variation_suffix.startswith("-"):
        return None
    metadata_name = stem[:marker_index] + "-metadata" + variation_suffix
    return (path.parent / metadata_name).as_posix()


def _vslice_difficulty_names(value: object) -> list[str]:
    play_data = value.get("playData") if isinstance(value, dict) else None
    listed = play_data.get("difficulties") if isinstance(play_data, dict) else None
    if not isinstance(listed, list):
        return []
    result = []
    seen: set[str] = set()
    for name in listed:
        if isinstance(name, str) and name.strip():
            normalized = name.strip().casefold()
            if normalized not in seen:
                seen.add(normalized)
                result.append(name.strip())
    return result


def derive_vslice_declared_difficulty(
    root: Path, source_chart: str, difficulty: str, chart_bytes: bytes,
) -> tuple[bool | None, str, str | None, str | None]:
    """Mirror V-Slice's metadata-first difficulty declaration for one chart pair."""
    metadata_stem = vslice_metadata_stem(source_chart)
    if metadata_stem is None:
        return None, "unavailable", None, "could not derive a sibling metadata path from the V-Slice chart name"

    metadata_bytes = None
    metadata_path = None
    last_error = None
    for extension in (".json", ".jsonc"):
        relative = metadata_stem + extension
        try:
            metadata_bytes, metadata_path = source_bytes(root, relative)
            break
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            last_error = error
    if metadata_bytes is None:
        detail = "sibling V-Slice metadata is unavailable"
        if last_error is not None:
            detail += f": {last_error}"
        return None, "unavailable", None, detail

    try:
        metadata = json.loads(metadata_bytes.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as error:
        return None, "unavailable", metadata_stem, f"sibling V-Slice metadata is invalid: {error}"

    declared_names = _vslice_difficulty_names(metadata)
    if declared_names:
        declared = any(name.casefold() == difficulty.casefold() for name in declared_names)
        return declared, "source-metadata", metadata_path, None

    # VSliceImporter falls back to chart note-map keys only when metadata has
    # no nonempty difficulty list. Keep inventory declaration semantics aligned.
    try:
        chart = json.loads(chart_bytes.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as error:
        return None, "unavailable", metadata_path, f"V-Slice chart fallback could not be parsed: {error}"
    note_map = chart.get("notes") if isinstance(chart, dict) else None
    if isinstance(note_map, dict) and note_map:
        declared = any(isinstance(name, str) and name.casefold() == difficulty.casefold()
                       for name in note_map)
        return declared, "source-chart-fallback", metadata_path, None
    return None, "unavailable", metadata_path, "metadata and chart contain no difficulty declarations"


def refresh(baseline: dict, inventory: dict, examples: Path, runtime: Path) -> dict:
    if baseline.get("schema") != 1 or not isinstance(baseline.get("rows"), list):
        raise ValueError("baseline must be a schema-1 chart matrix")
    packages = inventory.get("packages")
    if not isinstance(packages, list):
        raise ValueError("source inventory has no package catalog")
    rows: list[dict] = []
    non_playable_diagnostics: list[dict] = []
    problems: list[dict] = []
    roots: dict[str, Path] = {}
    seen: set[tuple[str, str, str]] = set()
    for index, old in enumerate(baseline["rows"]):
        label = old["package"]
        key = (label, old["sourceChart"], old["difficulty"])
        if key in seen:
            raise ValueError(f"duplicate source chart key: {key}")
        seen.add(key)
        row = {field: old[field] for field in (
            "group", "package", "song", "variant", "difficulty", "sourceChart",
            "runtimeChart", "runtimeOwner", "sourceNoteCount", "referenceOnly",
            "sourceGameplayNoteCount", "sourceUnroutedNoteCount", "declaredDifficulty",
            "declaredDifficultySource", "declaredDifficultySourceFile", "inventoryDiagnostic",
        ) if field in old}
        row["matrixIndex"] = index
        source_root_path = None
        source_data = None
        try:
            if label not in roots:
                roots[label] = source_root(catalog_package(packages, label), examples)
            source_root_path = roots[label]
            source_data, source_path = source_bytes(source_root_path, row["sourceChart"])
            current_source_hash = sha256(source_data)
            old_hash = old.get("sourceChartSha256")
            row.update(sourceChartPresent=True, sourceChartSha256=current_source_hash,
                       sourceChartResolved=source_path,
                       sourceHashMatchesBaseline=(old_hash == current_source_hash) if old_hash is not None else None)
            if old_hash is not None and old_hash != current_source_hash:
                problems.append({"index": index, "kind": "source-hash-drift", "chart": row["sourceChart"]})
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
            row.update(sourceChartPresent=False, sourceHashMatchesBaseline=False)
            problems.append({"index": index, "kind": "source-unavailable", "detail": str(error)})

        if "declaredDifficulty" in old:
            row.setdefault("declaredDifficultySource", "baseline")
        elif row.get("group") == "V-Slice":
            declaration = None
            declaration_source = "unavailable"
            metadata_file = None
            declaration_error = None
            difficulty = row.get("difficulty")
            if (source_root_path is not None and source_data is not None
                    and isinstance(difficulty, str)):
                declaration, declaration_source, metadata_file, declaration_error = (
                    derive_vslice_declared_difficulty(
                        source_root_path, row["sourceChart"], difficulty, source_data,
                    )
                )
            row["declaredDifficulty"] = declaration
            row["declaredDifficultySource"] = declaration_source
            if metadata_file is not None:
                row["declaredDifficultySourceFile"] = metadata_file
            if declaration_error is not None:
                problems.append({"index": index, "kind": "source-difficulty-metadata",
                                 "chart": row.get("sourceChart"), "detail": declaration_error})

        if is_undeclared_raw_key(row):
            # Keep the source/key evidence, but move any old runtime pairing out
            # of the playable row model. Undeclared keys are diagnostics whether
            # empty or populated; a nonempty one still needs manual review.
            empty_key = row["sourceNoteCount"] == 0
            reason = "empty-undeclared-raw-key" if empty_key else "nonempty-undeclared-raw-key"
            coverage = ("nonplayable-empty-undeclared-key" if empty_key
                        else "nonplayable-nonempty-undeclared-key")
            candidate = {}
            if old.get("runtimeChart") is not None:
                candidate["chart"] = old["runtimeChart"]
            if old.get("runtimeOwner") is not None:
                candidate["owner"] = old["runtimeOwner"]
            row.pop("runtimeChart", None)
            row.pop("runtimeOwner", None)
            row.update({
                "playable": False,
                "nonPlayableReason": reason,
                "coverageStatus": coverage,
                "sourceVariantImported": None,
                "structurallyCovered": None,
            })
            if not row.get("inventoryDiagnostic"):
                row["inventoryDiagnostic"] = ("empty" if empty_key else "nonempty") + (
                    " source note-map key is not declared as a playable difficulty"
                )
            if candidate:
                row["rejectedRuntimeCandidate"] = candidate
            non_playable_diagnostics.append(row)
            continue

        try:
            if not isinstance(row["runtimeChart"], str):
                raise FileNotFoundError("source row has no installed chart candidate")
            chart = safe_child(runtime, row["runtimeChart"])
            row["runtimeChartPresent"] = chart.is_file()
            if not chart.is_file():
                raise FileNotFoundError(f"installed chart candidate is absent: {row['runtimeChart']}")
            owner = safe_child(runtime, row["runtimeOwner"])
            row["runtimeOwnerRootPresent"] = owner.is_dir()
            chart_hash, count = runtime_chart_data(chart)
            row.update(runtimeChartSha256=chart_hash, runtimeNoteCount=count,
                       sourceNoteCountMatched=count == row["sourceNoteCount"])
            if "sourceGameplayNoteCount" in row:
                row["sourceGameplayNoteCountMatched"] = count == row["sourceGameplayNoteCount"]
            manifest = chart.parent / "compatScripts.json"
            selected = json.loads(manifest.read_text(encoding="utf-8"))["selectedRoot"]
            row["ownerMatched"] = selected == row["runtimeOwner"] and row["runtimeOwnerRootPresent"]
        except (OSError, ValueError, KeyError, TypeError) as error:
            row.setdefault("runtimeChartPresent", False)
            row.setdefault("runtimeOwnerRootPresent", False)
            row.update(ownerMatched=False, sourceNoteCountMatched=False)
            if "sourceGameplayNoteCount" in row:
                row["sourceGameplayNoteCountMatched"] = False
            problems.append({"index": index, "kind": "runtime-unavailable", "detail": str(error)})
        playable_count_matches = row.get("sourceGameplayNoteCountMatched",
                                         row.get("sourceNoteCountMatched", False))
        row["playable"] = True
        row["sourceVariantImported"] = bool(old.get("sourceVariantImported")
            and row.get("sourceChartPresent") and row.get("sourceHashMatchesBaseline") is not False
            and row.get("runtimeChartPresent") and row.get("ownerMatched")
            and playable_count_matches)
        row["structurallyCovered"] = row["sourceVariantImported"]
        row["coverageStatus"] = "installed-structural" if row["structurallyCovered"] else "needs-review"
        rows.append(row)
    return {"schema": 1, "rows": rows,
        "nonPlayableDiagnostics": non_playable_diagnostics, "refresh": {
        "baselineRows": len(baseline["rows"]), "refreshedRows": len(rows),
        "nonPlayableDiagnosticRows": len(non_playable_diagnostics),
        "totalProcessedRows": len(rows) + len(non_playable_diagnostics),
        "sourceRoots": {label: str(root) for label, root in sorted(roots.items())},
        "problems": problems,
    }}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--examples-root", type=Path, default=DEFAULT_EXAMPLES)
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    tmp_root = (ROOT / "tmp").resolve()
    if not output.is_relative_to(tmp_root):
        parser.error("output must be under repository tmp/")
    if output == args.baseline.expanduser().resolve():
        parser.error("output must not replace the baseline")
    payload = refresh(json.loads(args.baseline.read_text(encoding="utf-8")),
                      json.loads(args.inventory.read_text(encoding="utf-8")),
                      args.examples_root.expanduser().resolve(),
                      args.runtime_root.expanduser().resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent,
                                     prefix=output.name + ".", suffix=".tmp", delete=False) as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
        file.write("\n")
        temporary = Path(file.name)
    os.replace(temporary, output)
    summary = payload["refresh"]
    print(json.dumps({"output": str(output), "rows": summary["refreshedRows"],
                      "nonPlayableDiagnostics": summary["nonPlayableDiagnosticRows"],
                      "structurallyCovered": sum(row["structurallyCovered"] for row in payload["rows"]),
                      "problems": len(summary["problems"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
