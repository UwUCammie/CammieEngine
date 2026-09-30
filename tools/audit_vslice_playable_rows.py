#!/usr/bin/env python3
"""Compare inventoried V-Slice rows with the notes its two-strumline source plays.

V-Slice 0.3.2 PlayState.regenNoteData routes only strumline indices 0 and 1.
SongNoteData.getStrumlineIndex divides the authored d lane by four. Keep the
raw note total in the inventory while reporting the source gameplay total
separately; this does not claim that scripts cannot mutate notes at load time.
"""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def row_count(path: Path) -> int:
    song = json.loads(path.read_text(encoding="utf-8"))["song"]
    return sum(len(section["sectionNotes"]) for section in song["notes"])


def source_counts(chart: dict, difficulty: str) -> tuple[int, int, str]:
    notes = chart["notes"][difficulty]
    if not isinstance(notes, list):
        raise ValueError(f"source notes for {difficulty} are not a list")
    playable = sum(
        isinstance(note, dict) and isinstance(note.get("d"), int)
        and not isinstance(note.get("d"), bool) and 0 <= note["d"] < 8
        for note in notes
    )
    return len(notes), playable, chart.get("generatedBy", "")


def audit(matrix: dict, inventory: dict, runtime: Path,
          preview: Path | None = None) -> list[dict]:
    packages = {entry["id"]: Path(entry["sourceRoot"])
                for entry in inventory["vSlicePackages"]}
    result = []
    for row in matrix["rows"]:
        if row.get("group") != "V-Slice":
            continue
        package = packages[row["package"]]
        source_relative = Path(row["sourceChart"])
        runtime_relative = Path(row["runtimeChart"])
        if (source_relative.is_absolute() or ".." in source_relative.parts
                or runtime_relative.is_absolute() or ".." in runtime_relative.parts):
            raise ValueError("unsafe chart path in inventory")
        chart = json.loads((package / source_relative).read_text(encoding="utf-8"))
        raw, playable, version = source_counts(chart, row["difficulty"])
        if raw != row["sourceNoteCount"]:
            raise ValueError(f"stale source inventory: {package / source_relative}")
        live_path = runtime / runtime_relative
        preview_path = preview / runtime_relative if preview else None
        live = row_count(live_path) if live_path.is_file() else None
        converted = row_count(preview_path) if preview_path and preview_path.is_file() else None
        result.append({
            "package": row["package"], "song": row["song"],
            "difficulty": row["difficulty"], "variant": row.get("variant"),
            "sourceChart": row["sourceChart"],
            "runtimeChart": row["runtimeChart"], "generatedBy": version,
            "sourceRawRows": raw, "sourceGameplayRows": playable,
            "sourceUnroutedRows": raw - playable, "liveRows": live,
            "previewRows": converted, "liveGameplayCountMatches": live == playable,
            "previewGameplayCountMatches": converted == playable if preview else None,
        })
    return result


def annotate_matrix(matrix: dict, audited: list[dict]) -> dict:
    """Keep raw inventory counts and add the source engine's gameplay count."""
    by_chart = {(row["package"], row["sourceChart"], row["runtimeChart"],
                 row["difficulty"], row.get("variant")): row
                for row in audited}
    if len(by_chart) != len(audited):
        raise ValueError("duplicate V-Slice inventory row")
    for row in matrix["rows"]:
        if row.get("group") != "V-Slice":
            continue
        detail = by_chart[row["package"], row["sourceChart"], row["runtimeChart"],
                          row["difficulty"], row.get("variant")]
        row["sourceGameplayNoteCount"] = detail["sourceGameplayRows"]
        row["sourceUnroutedNoteCount"] = detail["sourceUnroutedRows"]
        row["sourceGameplayNoteCountMatched"] = detail["liveGameplayCountMatches"]
        row["sourceNoteCountMatched"] = detail["liveRows"] == detail["sourceRawRows"]
        row["runtimeNoteCount"] = detail["liveRows"]
    return matrix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path,
                        default=ROOT / "tmp/example_mods_chart_matrix.json")
    parser.add_argument("--inventory", type=Path,
                        default=ROOT / "tmp/inventory_vslice_fnas.json")
    parser.add_argument("--runtime", type=Path,
                        default=ROOT / "export/release/linux/bin")
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "tmp/vslice-playable-row-audit.json")
    parser.add_argument("--annotated-matrix", type=Path,
                        help="write a matrix snapshot with source gameplay counts")
    args = parser.parse_args()
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    rows = audit(matrix,
                 json.loads(args.inventory.read_text(encoding="utf-8")),
                 args.runtime, args.preview)
    summary = {
        "difficultyRows": len(rows),
        "unroutedSourceRows": sum(row["sourceUnroutedRows"] for row in rows),
        "liveGameplayCountMatched": sum(row["liveGameplayCountMatches"] for row in rows),
        "previewGameplayCountMatched": sum(row["previewGameplayCountMatches"] is True for row in rows),
    }
    payload = {"sourceSemantics": "Funkin v0.3.2 PlayState.regenNoteData: only strumline 0/1",
               "summary": summary, "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.annotated_matrix is not None:
        args.annotated_matrix.parent.mkdir(parents=True, exist_ok=True)
        args.annotated_matrix.write_text(
            json.dumps(annotate_matrix(matrix, rows), indent=2) + "\n",
            encoding="utf-8")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
