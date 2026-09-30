#!/usr/bin/env python3
"""Plan/apply a reviewed Codename event-provenance refresh.

Only an untouched pre-metadata event array is eligible. The replacement uses
the current source-authored event times and adds row[4] without editing notes
or any other chart bytes. Never modify the donor.
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


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"
HAXE = ROOT / ".tools/haxe/haxe"
RENDERER = ROOT / "tools/CodenameEventRefreshRender.hx"
DEPENDENCIES = ("CodenameImporter.hx", "CodenameEventMetadata.hx",
                "CompatScriptManifest.hx", "ImportEngine.hx", "EngineCompat.hx",
                "VSliceImporter.hx", "VSliceAstcAdapter.hx")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    return digest(path.read_bytes())


def within(path, root):
    return path.resolve().is_relative_to(root.resolve())


def safe_segment(value):
    """Match ModuleFunctions.validModuleName for a single source/dest id."""
    return (isinstance(value, str) and value.strip() not in ("", ".", "..")
            and all(char not in value for char in ("/", "\\", ":", "\0")))


def fingerprint_inputs():
    return {str(path.relative_to(ROOT)): file_digest(path) for path in
            (Path(__file__), RENDERER, *(ROOT / "source" / name for name in DEPENDENCIES))}


def safe_stem(value):
    """Mirror VSliceImporter.safeStem for destination filename collision checks."""
    value = value.strip().lower().replace(" ", "-")
    return "".join(c for c in value if c.isascii() and (c.isalnum() or c in "-_")) or "song"


def _skip_space(text, pos):
    while pos < len(text) and text[pos] in " \t\r\n":
        pos += 1
    return pos


def _string_end(text, pos):
    if pos >= len(text) or text[pos] != '"':
        raise ValueError("expected JSON string")
    pos += 1
    while pos < len(text):
        if text[pos] == "\\":
            pos += 2
        elif text[pos] == '"':
            return pos + 1
        else:
            pos += 1
    raise ValueError("unterminated JSON string")


def _value_end(text, pos):
    if text[pos] == '"':
        return _string_end(text, pos)
    if text[pos] in "{[":
        stack = ["}" if text[pos] == "{" else "]"]
        pos += 1
        while stack:
            if pos >= len(text):
                raise ValueError("unterminated JSON value")
            char = text[pos]
            if char == '"':
                pos = _string_end(text, pos)
                continue
            if char in "{[":
                stack.append("}" if char == "{" else "]")
            elif char in "]}":
                if stack.pop() != char:
                    raise ValueError("malformed JSON nesting")
            pos += 1
        return pos
    while pos < len(text) and text[pos] not in ",]} \t\r\n":
        pos += 1
    return pos


def _object_fields(text, pos):
    if text[pos] != "{":
        raise ValueError("expected JSON object")
    pos = _skip_space(text, pos + 1)
    fields = {}
    while pos < len(text) and text[pos] != "}":
        end = _string_end(text, pos)
        key = json.loads(text[pos:end])
        if key in fields:
            raise ValueError("duplicate JSON key: " + key)
        pos = _skip_space(text, end)
        if text[pos] != ":":
            raise ValueError("expected JSON colon")
        start = _skip_space(text, pos + 1)
        end = _value_end(text, start)
        fields[key] = (start, end)
        pos = _skip_space(text, end)
        if text[pos] == ",":
            pos = _skip_space(text, pos + 1)
        elif text[pos] != "}":
            raise ValueError("expected JSON delimiter")
    return fields


def events_span(text):
    """Find the one song.events value; callers splice this span only."""
    parsed = json.loads(text)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("song"), dict):
        raise ValueError("native chart has no song object")
    top = _object_fields(text, _skip_space(text, 0))
    if "song" not in top:
        raise ValueError("native chart has no song field")
    song = _object_fields(text, top["song"][0])
    if "events" not in song or not isinstance(parsed["song"].get("events"), list):
        raise ValueError("native chart has no events array")
    return song["events"], parsed["song"]["events"]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


_FOCUS_OPTION_KEYS = frozenset(("cancelMovement", "duration", "ease", "easeDir",
                                "char", "forced", "codenameParams"))


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate event option key: " + key)
        value[key] = item
    return value


def equivalent_focus_options(left, right):
    """Permit only Haxe object-key iteration drift in generated Focus Camera v3.

    CodenameImporter.packEventOptions/packWithChar use Json.stringify on a
    Dynamic object. Its property order can differ between hxcpp and --interp;
    CoolUtil.stringifyJson stores that resulting string without normalizing it.
    Every key, nested value, JSON type, and array order still has to match.
    """
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    try:
        a = json.loads(left, object_pairs_hook=_unique_pairs)
        b = json.loads(right, object_pairs_hook=_unique_pairs)
    except (ValueError, TypeError):
        return False
    return (isinstance(a, dict) and isinstance(b, dict)
            and bool(a) and set(a) <= _FOCUS_OPTION_KEYS
            and set(a) == set(b) and canonical(a) == canonical(b))


def equivalent_foreign_payload(left, right, event_name):
    """Accept serializer key order only for an importer-generated Codename payload."""
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    try:
        a = json.loads(left, object_pairs_hook=_unique_pairs)
        b = json.loads(right, object_pairs_hook=_unique_pairs)
    except (ValueError, TypeError):
        return False
    return (isinstance(a, dict) and isinstance(b, dict)
            and set(a) == set(b) and set(a) in ({"engine", "name"},
                                                {"engine", "name", "params"})
            and a.get("engine") == b.get("engine") == "codename"
            and a.get("name") == b.get("name") == event_name
            and canonical(a) == canonical(b))


def legacy_matches(present, expected):
    """Return (match, serializer-only differences) for the old native rows."""
    if not isinstance(present, list) or len(present) != len(expected):
        return False, 0
    normalized = 0
    for actual_group, expected_group in zip(present, expected):
        if (not isinstance(actual_group, list) or len(actual_group) != 2
                or isinstance(actual_group[0], bool)
                or not isinstance(actual_group[0], (int, float))
                or not math.isfinite(actual_group[0])
                or actual_group[0] != expected_group[0]
                or not isinstance(actual_group[1], list)
                or len(actual_group[1]) != len(expected_group[1])):
            return False, 0
        for actual_row, expected_row in zip(actual_group[1], expected_group[1]):
            if not isinstance(actual_row, list) or len(actual_row) != 4:
                return False, 0
            for slot in range(4):
                if actual_row[slot] == expected_row[slot]:
                    continue
                if (slot == 3 and actual_row[0] == expected_row[0] == "Focus Camera"
                        and equivalent_focus_options(actual_row[slot], expected_row[slot])):
                    normalized += 1
                    continue
                if (slot == 1 and actual_row[0] == expected_row[0]
                        and equivalent_foreign_payload(actual_row[slot], expected_row[slot],
                                                       expected_row[0])):
                    normalized += 1
                    continue
                return False, 0
    return True, normalized


def selected_songs(runtime, namespace):
    for folder in sorted((runtime / "assets/data").iterdir()):
        if not folder.is_dir() or not safe_segment(folder.name):
            continue
        manifest = folder / "compatScripts.json"
        if not manifest.is_file() or not within(manifest, runtime):
            continue
        try:
            data = json.loads(manifest.read_text())
            roots = data.get("roots")
            if data.get("selectedRoot") != namespace or not isinstance(roots, list) or not any(
                isinstance(entry, dict) and entry.get("engine") == "Codename Engine"
                and entry.get("path") == namespace for entry in roots
            ):
                continue
            yield folder, manifest
        except (OSError, ValueError, TypeError):
            continue


def source_plan(runtime, namespace, folder):
    """Resolve the owner script plan by provenance, not sanitized chart folder.

    Imports may qualify a native chart folder to avoid collisions while the
    selected owner's source song keeps its original folder name. A verified
    importProvenance record is the only authority for that mapping; malformed
    or foreign provenance fails closed instead of falling back to a basename.
    """
    runtime = Path(runtime).resolve()
    folder = Path(folder)
    songs = runtime / namespace / "songs"
    if (not songs.is_dir() or songs.is_symlink() or not within(songs, runtime)
            or folder.is_symlink() or not folder.is_dir() or not within(folder, runtime)):
        return None
    manifest = folder / "compatScripts.json"
    if not manifest.is_file() or manifest.is_symlink() or not within(manifest, runtime):
        return None
    try:
        manifest_value = json.loads(manifest.read_text(), object_pairs_hook=_unique_pairs)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(manifest_value, dict):
        return None
    roots = manifest_value.get("roots")
    if not isinstance(roots, list):
        return None
    selected = [entry for entry in roots if isinstance(entry, dict)
                and entry.get("path") == namespace and entry.get("engine") == "Codename Engine"]
    if (manifest_value.get("selectedRoot") != namespace or len(roots) != 1
            or len(selected) != 1 or manifest_value.get("overlays") not in (None, [])):
        return None

    provenance_path = folder / "importProvenance.json"
    if provenance_path.exists():
        if (not provenance_path.is_file() or provenance_path.is_symlink()
                or not within(provenance_path, runtime)):
            return None
        try:
            provenance = json.loads(provenance_path.read_text(), object_pairs_hook=_unique_pairs)
        except (OSError, ValueError, TypeError):
            return None
        if (not isinstance(provenance, dict) or isinstance(provenance.get("version"), bool)
                or provenance.get("version") != 1
                or provenance.get("sourceOwner") != namespace
                or provenance.get("sourceEngine") != "Codename Engine"
                or provenance.get("destinationFolder") != folder.name
                or not safe_segment(provenance.get("sourceFolder"))):
            return None
        source_name = provenance["sourceFolder"]
        require_exact_name = True
    else:
        source_name = folder.name
        require_exact_name = False

    matches = []
    for source in songs.iterdir():
        if (not source.is_dir() or source.is_symlink() or not safe_segment(source.name)
                or (source.name != source_name if require_exact_name
                    else source.name.strip().lower() != source_name.strip().lower())):
            continue
        plan = source / "__cammie_compat_scripts.json"
        if not plan.is_file() or plan.is_symlink() or not within(plan, runtime):
            continue
        try:
            value = json.loads(plan.read_text(), object_pairs_hook=_unique_pairs)
            if (isinstance(value, dict) and not isinstance(value.get("version"), bool)
                    and value.get("version") == 1 and value.get("song") == source.name):
                matches.append((source.name, plan))
        except (OSError, ValueError, TypeError):
            pass
    return matches[0] if len(matches) == 1 else None


def donor_charts(donor, song):
    """Resolve source-mod or compiled-mod content without foreign fallback."""
    contents = []
    mods = donor / "mods"
    if mods.is_dir() and within(mods, donor):
        # ImportRootScanner gives compiled-release mods precedence over embedded
        # sample songs. A duplicate source song across mods is ambiguous.
        contents = [entry for entry in sorted(mods.iterdir())
                    if entry.is_dir() and within(entry, donor) and (entry / "songs").is_dir()]
    else:
        contents = [donor / "assets", donor]
    matches = []
    for content in contents:
        folder = content / "songs" / song
        if not folder.is_dir() or not within(folder, donor):
            continue
        charts = folder / "charts"
        if not charts.is_dir() or not within(charts, donor):
            continue
        meta = folder / "meta.json"
        if not meta.is_file() or not within(meta, donor):
            continue
        matches.append((folder, charts, meta))
    return matches[0] if len(matches) == 1 else None


def render(donor, charts):
    request = {"donorRoot": str(donor), "charts": charts}
    TMP.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codename-events-render-", dir=TMP) as work:
        path = Path(work) / "request.json"
        path.write_text(json.dumps(request))
        run = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(ROOT / "tools"),
                              "--run", "CodenameEventRefreshRender", str(path)],
                             cwd=ROOT, text=True, capture_output=True, timeout=120)
        if run.returncode:
            raise ValueError("Codename event renderer failed: " + run.stderr.strip())
        return json.loads(run.stdout)


def make_plan(donor_root, runtime_root):
    donor, runtime = donor_root.resolve(), runtime_root.resolve()
    if not donor.is_dir() or not (runtime / "assets/data").is_dir() or not HAXE.is_file():
        raise ValueError("donor, runtime assets/data, or portable Haxe is missing")
    songs = []
    issues = []
    # The renderer computes ownership through the engine's real helper.
    owner = render(donor, [])["namespace"]
    chart_inputs = []
    for folder, manifest in selected_songs(runtime, owner):
        mapping = source_plan(runtime, owner, folder)
        if mapping is None:
            issues.append({"song": folder.name, "reason": "missing or ambiguous source song plan"})
            continue
        source_song, source_plan_path = mapping
        located = donor_charts(donor, source_song)
        if located is None:
            issues.append({"song": folder.name, "reason": "donor song/meta/charts missing"})
            continue
        source_folder, charts_dir, meta = located
        sidecar = source_folder / "events.json"
        if sidecar.exists() and (not sidecar.is_file() or not within(sidecar, donor)):
            issues.append({"song": folder.name, "reason": "unsafe event sidecar"})
            continue
        names = set()
        for chart in sorted(charts_dir.iterdir()):
            if not chart.is_file() or chart.suffix.lower() != ".json":
                continue
            difficulty = chart.stem
            if not safe_segment(difficulty) or not within(chart, donor):
                issues.append({"song": folder.name, "difficulty": difficulty, "reason": "unsafe donor chart"})
                continue
            native_name = folder.name + ("" if safe_stem(difficulty) == "normal"
                                         else "-" + safe_stem(difficulty)) + ".json"
            if native_name in names:
                issues.append({"song": folder.name, "difficulty": difficulty,
                               "reason": "multiple donor difficulties map to one native chart"})
                chart_inputs = [item for item in chart_inputs if item["target"] != str(folder / native_name)]
                continue
            names.add(native_name)
            target = folder / native_name
            if not target.is_file() or not within(target, runtime):
                issues.append({"song": folder.name, "difficulty": difficulty, "reason": "native chart missing"})
                continue
            chart_inputs.append({"id": folder.name + "/" + difficulty, "chart": str(chart),
                                 "sidecar": str(sidecar) if sidecar.is_file() else None,
                                 "difficulty": difficulty, "target": str(target),
                                 "manifest": str(manifest), "sourcePlan": str(source_plan_path),
                                 "meta": str(meta)})
    if not list(selected_songs(runtime, owner)):
        raise ValueError("no song selects the exact Codename donor namespace")
    output = render(donor, [{key: item[key] for key in ("id", "chart", "sidecar", "difficulty")}
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
            (start, end), present = events_span(raw)
        except (UnicodeError, ValueError) as error:
            issues.append({"chart": item["id"], "reason": "unpatchable native chart: " + str(error)})
            continue
        current = converted["current"]
        if canonical(present) == canonical(current):
            continue
        matches, json_order_changes = legacy_matches(present, converted["legacy"])
        if not matches:
            issues.append({"chart": item["id"], "reason": "events differ from pre-metadata conversion"})
            continue
        replacement = json.dumps(current, ensure_ascii=False, separators=(",", ":"))
        after = (raw[:start] + replacement + raw[end:]).encode("utf-8")
        sources = {key: {"path": item[key], "sha256": file_digest(Path(item[key]))}
                   for key in ("chart", "manifest", "sourcePlan", "meta")}
        if item["sidecar"]:
            sources["sidecar"] = {"path": item["sidecar"], "sha256": file_digest(Path(item["sidecar"]))}
        candidates.append({"id": item["id"], "target": str(target), "difficulty": item["difficulty"],
                           "beforeSha256": digest(before), "afterSha256": digest(after),
                           "afterBase64": base64.b64encode(after).decode(), "sources": sources,
                           "legacyProjection": "epsilon-exclusive-source-order",
                           "jsonFieldOrderChanges": json_order_changes,
                           "oldTimes": [group[0] for group in present],
                           "newTimes": [group[0] for group in current],
                           "oldRows": sum(len(group[1]) for group in present),
                           "newRows": sum(len(group[1]) for group in current)})
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
            if not within(target, runtime / "assets/data") or file_digest(target) != item["beforeSha256"]:
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
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".codename-events-", delete=False) as stage:
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
        if output.exists() or within(output, args.donor_root) or within(output, args.runtime_root):
            parser.error("plan output must be a new file outside donor and runtime roots")
        plan = make_plan(args.donor_root, args.runtime_root)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(plan, indent=2) + "\n")
        print(f"plan: {output}; candidates={len(plan['candidates'])}; skipped={len(plan['skipped'])}")
    else:
        plan = json.loads(args.plan.read_text())
        backup = apply_plan(plan, args.plan.resolve())
        print("applied; backup: " + str(backup) if backup else "no changes in plan")


if __name__ == "__main__":
    main()
