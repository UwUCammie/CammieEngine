#!/usr/bin/env python3
"""Plan/apply a reviewed Codename note-provenance refresh.

Only an untouched pre-metadata note array is eligible. The current
CodenameImporter re-renders the selected owner's authored rows; every row and
section must match the old importer projection (including its deterministic
positive-millisecond timestamp truncation) before column 13 is added. The
donor is read-only, and all chart bytes outside song.notes are preserved.
"""

import argparse
import base64
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import refresh_codename_events as shared


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"
HAXE = ROOT / ".tools/haxe/haxe"
RENDERER = ROOT / "tools/CodenameNoteRefreshRender.hx"
DEPENDENCIES = ("CodenameImporter.hx", "CodenameNoteMetadata.hx",
                "CompatScriptManifest.hx", "ImportEngine.hx", "EngineCompat.hx",
                "VSliceImporter.hx", "VSliceAstcAdapter.hx")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    return digest(path.read_bytes())


def fingerprint_inputs():
    paths = (Path(__file__), RENDERER, ROOT / "tools/refresh_codename_events.py",
             *(ROOT / "source" / name for name in DEPENDENCIES))
    return {str(path.relative_to(ROOT)): file_digest(path) for path in paths}


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def notes_span(text):
    """Find exactly song.notes, rejecting duplicate JSON object keys."""
    parsed = json.loads(text, object_pairs_hook=unique_pairs)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("song"), dict):
        raise ValueError("native chart has no song object")
    top = shared._object_fields(text, shared._skip_space(text, 0))
    if "song" not in top:
        raise ValueError("native chart has no song field")
    song = shared._object_fields(text, top["song"][0])
    if "notes" not in song or not isinstance(parsed["song"].get("notes"), list):
        raise ValueError("native chart has no song.notes array")
    return song["notes"], parsed["song"]["notes"]


def array_spans(text, start):
    """Return the byte-free character spans of an array's direct values."""
    if text[start] != "[":
        raise ValueError("expected JSON array")
    values = []
    pos = shared._skip_space(text, start + 1)
    while pos < len(text) and text[pos] != "]":
        end = shared._value_end(text, pos)
        values.append((pos, end))
        pos = shared._skip_space(text, end)
        if text[pos] == ",":
            pos = shared._skip_space(text, pos + 1)
        elif text[pos] != "]":
            raise ValueError("expected JSON array delimiter")
    if pos >= len(text) or text[pos] != "]":
        raise ValueError("unterminated JSON array")
    return values


def notes_layout(text):
    """Return parsed notes plus each row's section, value, and source span."""
    (notes_start, _), notes = notes_span(text)
    section_spans = array_spans(text, notes_start)
    if len(section_spans) != len(notes):
        raise ValueError("native section spans do not match parsed notes")
    rows = []
    for section_index, ((section_start, _), section) in enumerate(zip(section_spans, notes)):
        if not isinstance(section, dict) or not isinstance(section.get("sectionNotes"), list):
            raise ValueError("native notes contain a malformed section")
        fields = shared._object_fields(text, section_start)
        if "sectionNotes" not in fields:
            raise ValueError("native section has no sectionNotes field")
        note_start, _ = fields["sectionNotes"]
        row_spans = array_spans(text, note_start)
        if len(row_spans) != len(section["sectionNotes"]):
            raise ValueError("native row spans do not match parsed section notes")
        for row_index, (span, row) in enumerate(zip(row_spans, section["sectionNotes"])):
            rows.append({"section": section_index, "row": row_index,
                         "value": row, "span": span})
    return notes, rows


def _number(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def _old_int(value):
    """Haxe Std.int semantics for finite values, including negatives."""
    return math.trunc(value)


def row_key(row):
    if (not isinstance(row, list) or len(row) < 3 or len(row) > 4
            or not _number(row[0]) or not _number(row[1]) or not _number(row[2])
            or isinstance(row[1], bool) or row[1] != math.trunc(row[1])):
        raise ValueError("note row is not an untouched three/four-column Codename row")
    extras = row[3:]
    return (_old_int(row[0]), int(row[1]), _old_int(row[2]), shared.canonical(extras))


def source_note(chart, origin):
    try:
        lines = chart["strumLines"]
        line = lines[origin["lineIndex"]]
        notes = line["notes"]
        note = notes[origin["noteIndex"]]
    except (KeyError, IndexError, TypeError):
        raise ValueError("rendered note identity is outside its donor chart")
    if note is None:
        raise ValueError("rendered note identity points to a null donor row")
    return note


def section_properties(section):
    return {key: value for key, value in section.items() if key != "sectionNotes"}


def match_note_rows(present, current, donor_chart):
    """Map old native rows to current source origins without trusting row order.

    Equal-time sort order was unstable in the previous native importer. A
    duplicate is accepted only when all source note payloads and actor-routing
    fields are identical except for noteIndex; those notes are indistinguishable
    and receive indices in donor order.
    """
    if not isinstance(present, list) or not isinstance(current, list):
        raise ValueError("notes value is not an array")
    if len(present) > len(current):
        extra = present[len(current):]
        if any(section.get("sectionNotes") for section in extra):
            raise ValueError("native chart has extra nonempty note sections")
    if len(present) < len(current):
        extra = current[len(present):]
        if any(section.get("sectionNotes") for section in extra):
            raise ValueError("current import has missing nonempty note sections")
    common = min(len(present), len(current))
    for index in range(common):
        if (not isinstance(present[index], dict) or not isinstance(current[index], dict)
                or shared.canonical(section_properties(present[index]))
                != shared.canonical(section_properties(current[index]))):
            raise ValueError("note section fields differ at section " + str(index))
    # A changed number of trailing empty sections has no note identity to attach.
    # Require the extra sections to have the same non-note fields as the last
    # common section; leave the installed section layout exactly as authored.
    if common:
        reference = shared.canonical(section_properties(present[common - 1]))
        for sections in (present[common:], current[common:]):
            for section in sections:
                if (not isinstance(section, dict) or section.get("sectionNotes")
                        or shared.canonical(section_properties(section)) != reference):
                    raise ValueError("trailing section differences are not empty importer padding")
    elif present or current:
        raise ValueError("cannot verify section metadata without a common section")

    assignments = []
    for section_index in range(common):
        old_rows = present[section_index].get("sectionNotes")
        new_rows = current[section_index].get("sectionNotes")
        if not isinstance(old_rows, list) or not isinstance(new_rows, list) or len(old_rows) != len(new_rows):
            raise ValueError("note row count differs in section " + str(section_index))
        expected = {}
        actual = {}
        for row in new_rows:
            if not isinstance(row, list) or len(row) <= 13 or not isinstance(row[13], dict):
                raise ValueError("current note row has no provenance metadata")
            origin = row[13]
            if origin.get("engine") != "codename" or origin.get("version") != 1:
                raise ValueError("current note row has malformed provenance")
            key = row_key(row[:_base_row_length(row)])
            note = source_note(donor_chart, origin)
            expected.setdefault(key, []).append({"row": row, "origin": origin,
                                                  "payload": shared.canonical(note)})
        for row_index, row in enumerate(old_rows):
            if not isinstance(row, list):
                raise ValueError("native note row is not an array")
            if len(row) > 13:
                if len(row) != 14 or not isinstance(row[13], dict):
                    raise ValueError("native note row has unexpected trailing fields")
                if row[13].get("engine") != "codename":
                    raise ValueError("native note row has a non-Codename column 13")
                base = row[:13]
                while base and base[-1] is None:
                    base.pop()
            else:
                base = row
            key = row_key(base)
            actual.setdefault(key, []).append({"row": row, "rowIndex": row_index})
        if expected.keys() != actual.keys():
            raise ValueError("note timing/lane/sustain/type multiset differs in section "
                             + str(section_index))
        for key, expected_group in expected.items():
            actual_group = actual[key]
            if len(expected_group) != len(actual_group):
                raise ValueError("duplicate note count differs in section " + str(section_index))
            expected_group.sort(key=lambda entry: entry["origin"]["noteIndex"])
            if len(expected_group) > 1:
                first = expected_group[0]
                stable_origin = {name: value for name, value in first["origin"].items()
                                 if name != "noteIndex"}
                for entry in expected_group[1:]:
                    other_origin = {name: value for name, value in entry["origin"].items()
                                    if name != "noteIndex"}
                    if (entry["payload"] != first["payload"]
                            or shared.canonical(other_origin) != shared.canonical(stable_origin)):
                        raise ValueError("ambiguous duplicate note provenance in section "
                                         + str(section_index))
            actual_group.sort(key=lambda entry: entry["rowIndex"])
            for old_entry, fresh_entry in zip(actual_group, expected_group):
                if not old_row_matches(old_entry["row"], fresh_entry["row"]):
                    raise ValueError("note fields differ beyond documented legacy numeric projection")
                if (len(old_entry["row"]) == 14
                        and shared.canonical(old_entry["row"][13])
                        != shared.canonical(fresh_entry["origin"])):
                    raise ValueError("existing note provenance differs from current importer")
                assignments.append({"section": section_index,
                                    "row": old_entry["rowIndex"],
                                    "origin": fresh_entry["origin"],
                                    "tagged": len(old_entry["row"]) == 14})
    if len(assignments) != sum(len(section["sectionNotes"]) for section in present[:common]):
        raise ValueError("not every installed note row received a provenance assignment")
    tagged = [item["tagged"] for item in assignments]
    if any(tagged) and not all(tagged):
        raise ValueError("native chart has mixed note provenance")
    return assignments, bool(tagged) and all(tagged)


def _base_row_length(row):
    end = 13
    while end > 3 and row[end - 1] is None:
        end -= 1
    return end


def old_row_matches(actual, current):
    """Check all note fields; only time and sustain may retain old truncation."""
    if not isinstance(actual, list) or not isinstance(current, list) or len(current) <= 13:
        return False
    if len(actual) == 14:
        actual_base = actual[:13]
        while actual_base and actual_base[-1] is None:
            actual_base.pop()
    else:
        actual_base = actual
    expected_base = current[:_base_row_length(current)]
    if len(actual_base) != len(expected_base) or len(expected_base) not in (3, 4):
        return False
    if not _number(actual_base[0]) or not _number(actual_base[2]):
        return False
    if (actual_base[0] not in (expected_base[0], _old_int(expected_base[0]))
            or actual_base[2] not in (expected_base[2], _old_int(expected_base[2]))):
        return False
    return (shared.canonical([actual_base[1], *actual_base[3:]])
            == shared.canonical([expected_base[1], *expected_base[3:]]))


def append_metadata(text, row_layouts, assignments):
    by_position = {(item["section"], item["row"]): item["origin"] for item in assignments}
    changes = []
    for layout in row_layouts:
        origin = by_position.get((layout["section"], layout["row"]))
        if origin is None:
            continue
        start, end = layout["span"]
        row = layout["value"]
        if len(row) == 14:
            continue
        if len(row) > 13:
            raise ValueError("cannot append provenance to a row with extra columns")
        padding = [None] * (13 - len(row))
        suffix = "," + ",".join(json.dumps(value, separators=(",", ":"))
                                 for value in padding + [origin])
        inner_end = end - 1
        while inner_end > start and text[inner_end - 1] in " \t\r\n":
            inner_end -= 1
        trailing = text[inner_end:end - 1]
        changes.append((inner_end, end, suffix + trailing + "]"))
    for start, end, replacement in reversed(changes):
        text = text[:start] + replacement + text[end:]
    return text


def render(donor, charts):
    request = {"donorRoot": str(donor), "charts": charts}
    TMP.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codename-notes-render-", dir=TMP) as work:
        path = Path(work) / "request.json"
        path.write_text(json.dumps(request))
        run = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(ROOT / "tools"),
                              "--run", "CodenameNoteRefreshRender", str(path)],
                             cwd=ROOT, text=True, capture_output=True, timeout=120)
        if run.returncode:
            raise ValueError("Codename note renderer failed: " + run.stderr.strip())
        return json.loads(run.stdout, object_pairs_hook=unique_pairs)


def make_plan(donor_root, runtime_root):
    donor, runtime = donor_root.resolve(), runtime_root.resolve()
    if not donor.is_dir() or not (runtime / "assets/data").is_dir() or not HAXE.is_file():
        raise ValueError("donor, runtime assets/data, or portable Haxe is missing")
    owner = render(donor, [])["namespace"]
    chart_inputs = []
    issues = []
    selected = list(shared.selected_songs(runtime, owner))
    if not selected:
        raise ValueError("no song selects the exact Codename donor namespace")
    for folder, manifest in selected:
        mapping = shared.source_plan(runtime, owner, folder)
        if mapping is None:
            issues.append({"song": folder.name, "reason": "missing or ambiguous source song plan"})
            continue
        source_song, source_plan_path = mapping
        located = shared.donor_charts(donor, source_song)
        if located is None:
            issues.append({"song": folder.name, "reason": "donor song/meta/charts missing"})
            continue
        source_folder, charts_dir, meta = located
        names = set()
        for chart in sorted(charts_dir.iterdir()):
            if not chart.is_file() or chart.suffix.lower() != ".json":
                continue
            difficulty = chart.stem
            if not shared.safe_segment(difficulty) or not shared.within(chart, donor):
                issues.append({"song": folder.name, "difficulty": difficulty,
                               "reason": "unsafe donor chart"})
                continue
            native_name = folder.name + ("" if shared.safe_stem(difficulty) == "normal"
                                         else "-" + shared.safe_stem(difficulty)) + ".json"
            target = folder / native_name
            if native_name in names:
                issues.append({"song": folder.name, "difficulty": difficulty,
                               "reason": "multiple donor difficulties map to one native chart"})
                chart_inputs = [item for item in chart_inputs if item["target"] != str(target)]
                continue
            names.add(native_name)
            if not target.is_file() or not shared.within(target, runtime / "assets/data"):
                issues.append({"song": folder.name, "difficulty": difficulty,
                               "reason": "native chart missing or outside assets/data"})
                continue
            chart_inputs.append({"id": folder.name + "/" + difficulty,
                                 "chart": str(chart), "difficulty": difficulty,
                                 "song": source_song,
                                 "meta": str(meta), "target": str(target),
                                 "manifest": str(manifest),
                                 "sourcePlan": str(source_plan_path)})

    output = render(donor, [{key: item[key] for key in ("id", "chart", "difficulty", "meta", "song")}
                            for item in chart_inputs])
    if output["namespace"] != owner or len(output["charts"]) != len(chart_inputs):
        raise ValueError("renderer ownership or chart count changed")
    candidates = []
    for item, converted in zip(chart_inputs, output["charts"]):
        if converted["id"] != item["id"]:
            raise ValueError("renderer chart order changed")
        expected_file = Path(item["target"]).parent.name + converted["nativeFile"][len("chart"):]
        if Path(item["target"]).name != expected_file:
            issues.append({"chart": item["id"], "reason": "native filename mapping changed"})
            continue
        target = Path(item["target"])
        before = target.read_bytes()
        try:
            raw = before.decode("utf-8")
            present, row_layouts = notes_layout(raw)
            source_chart = json.loads(Path(item["chart"]).read_text(encoding="utf-8"),
                                      object_pairs_hook=unique_pairs)
            assignments, already_complete = match_note_rows(
                present, converted["current"], source_chart)
        except (UnicodeError, ValueError) as error:
            issues.append({"chart": item["id"], "reason": "unpatchable native chart: " + str(error)})
            continue
        if already_complete:
            continue
        try:
            patched = append_metadata(raw, row_layouts, assignments)
            _, patched_notes = notes_span(patched)
            _, verified = match_note_rows(patched_notes, converted["current"], source_chart)
            if not verified:
                raise ValueError("provenance append did not round-trip")
        except (ValueError, IndexError) as error:
            issues.append({"chart": item["id"], "reason": "provenance refresh failed verification: " + str(error)})
            continue
        after = patched.encode("utf-8")
        sources = {key: {"path": item[key], "sha256": file_digest(Path(item[key]))}
                   for key in ("chart", "meta", "manifest", "sourcePlan")}
        candidates.append({"id": item["id"], "target": str(target),
                           "beforeSha256": digest(before), "afterSha256": digest(after),
                           "afterBase64": base64.b64encode(after).decode(), "sources": sources,
                           "legacyProjection": "hxcpp-positive-millisecond-truncation",
                           "oldRows": len(row_layouts), "newRows": len(row_layouts),
                           "oldSections": len(present), "renderedSections": len(converted["current"])})
    return {"version": 1, "donorRoot": str(donor), "runtimeRoot": str(runtime),
            "selectedRoot": owner, "inputsSha256": fingerprint_inputs(),
            "candidates": candidates, "skipped": issues}


def apply_plan(plan, plan_path):
    donor, runtime = Path(plan["donorRoot"]).resolve(), Path(plan["runtimeRoot"]).resolve()
    if plan.get("version") != 1 or plan.get("inputsSha256") != fingerprint_inputs():
        raise ValueError("refresh tool or converter changed since plan")
    locks = []
    try:
        for mode in ("0", "1"):
            lock = (ROOT / ".tools" / ("runtime-" + mode + ".lock")).open("a+")
            locks.append(lock)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fresh = make_plan(donor, runtime)
        if fresh["selectedRoot"] != plan.get("selectedRoot"):
            raise ValueError("selected owner changed")
        original = {item["id"]: item for item in plan["candidates"]}
        regenerated = {item["id"]: item for item in fresh["candidates"]}
        if original.keys() != regenerated.keys():
            raise ValueError("refresh candidates changed since plan")
        for identity, item in original.items():
            if item != regenerated[identity]:
                raise ValueError("donor or destination changed since plan: " + identity)
            target = Path(item["target"])
            if (not shared.within(target, runtime / "assets/data")
                    or target.is_symlink() or file_digest(target) != item["beforeSha256"]):
                raise ValueError("unsafe or changed destination: " + str(target))
            if digest(base64.b64decode(item["afterBase64"], validate=True)) != item["afterSha256"]:
                raise ValueError("planned output hash mismatch")
        if not original:
            return None
        backup = TMP / "import-refresh-backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup.mkdir(parents=True, exist_ok=False)
        shutil.copy2(plan_path, backup / "plan.json")
        for item in original.values():
            target = Path(item["target"])
            saved = backup / target.relative_to(runtime)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            if file_digest(saved) != item["beforeSha256"]:
                raise ValueError("backup verification failed: " + str(saved))
        replaced = []
        try:
            for item in original.values():
                target = Path(item["target"])
                after = base64.b64decode(item["afterBase64"], validate=True)
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".codename-notes-",
                                                 delete=False) as stage:
                    stage.write(after)
                    stage.flush()
                    os.fsync(stage.fileno())
                    staged = Path(stage.name)
                try:
                    os.chmod(staged, target.stat().st_mode)
                    os.replace(staged, target)
                finally:
                    staged.unlink(missing_ok=True)
                replaced.append(target)
        except Exception:
            for target in replaced:
                shutil.copy2(backup / target.relative_to(runtime), target)
            raise
        return backup
    finally:
        for lock in locks:
            lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    planning = commands.add_parser("plan")
    planning.add_argument("--donor-root", type=Path, required=True)
    planning.add_argument("--runtime-root", type=Path, required=True)
    planning.add_argument("--output", type=Path, required=True)
    applying = commands.add_parser("apply")
    applying.add_argument("--plan", type=Path, required=True)
    applying.add_argument("--reviewed", action="store_true", required=True)
    args = parser.parse_args()
    if args.command == "plan":
        output = args.output.resolve()
        if (output.exists() or shared.within(output, args.donor_root)
                or shared.within(output, args.runtime_root)):
            parser.error("plan output must be a new file outside donor and runtime roots")
        plan = make_plan(args.donor_root, args.runtime_root)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(plan, indent=2) + "\n")
        print(f"plan: {output}; candidates={len(plan['candidates'])}; skipped={len(plan['skipped'])}")
    else:
        plan = json.loads(args.plan.read_text(), object_pairs_hook=unique_pairs)
        backup = apply_plan(plan, args.plan.resolve())
        print("applied; backup: " + str(backup) if backup else "no changes in plan")


if __name__ == "__main__":
    main()
