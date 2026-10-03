#!/usr/bin/env python3
"""Plan or apply a reviewed, source-scoped V-Slice character/stage script refresh.

The normal importer is additive. This tool converts donor JSON with the current
VSliceImporter in an isolated Haxe interpreter, then replaces only reviewed
generated scripts whose source, destination and media hashes still match.
"""

import argparse
import base64
import difflib
try:
    from tools import file_lock as fcntl
except ModuleNotFoundError:
    import file_lock as fcntl  # Direct python tools/<script>.py invocation.
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
HAXE = ROOT / ".tools/haxe/haxe"
TJSON = ROOT / ".haxelib/tjson/1,4,0"
KINDS = {"character": "characters", "stage": "stages"}
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    return digest(path.read_bytes())


def within(path, root):
    return path.resolve().is_relative_to(root.resolve())


def namespace_for(source):
    source = source.resolve()
    label = re.sub(r"[^a-z0-9]+", "-", source.name.lower()).strip("-")
    return "assets/imported_mods/v-slice-" + label + "-" + hashlib.md5(str(source).encode()).hexdigest()[:10]


def chart_refs(chart):
    song = chart.get("song", {})
    if not isinstance(song, dict):
        return {kind: set() for kind in KINDS}
    refs = {"character": set(), "stage": set()}
    for field in ("player1", "player2", "gf"):
        value = song.get(field)
        if isinstance(value, str) and SAFE_ID.fullmatch(value):
            refs["character"].add(value)
    stage = song.get("stage")
    if isinstance(stage, str) and SAFE_ID.fullmatch(stage):
        refs["stage"].add(stage)
    # Imported event rows have [time, [[name, value1, value2], ...]].
    for group in song.get("events", []) or []:
        if not isinstance(group, list) or len(group) < 2 or not isinstance(group[1], list):
            continue
        for event in group[1]:
            if not isinstance(event, list) or len(event) < 2:
                continue
            name = re.sub(r"[ _-]", "", str(event[0]).lower())
            if name == "changecharacter" and len(event) >= 3:
                value = event[2]
                if isinstance(value, str) and SAFE_ID.fullmatch(value):
                    refs["character"].add(value)
            if name == "changestage":
                value = event[1]
                if isinstance(value, str) and SAFE_ID.fullmatch(value):
                    refs["stage"].add(value)
    return refs


def inventory(runtime):
    result = []
    for folder in (runtime / "assets/data").iterdir():
        if not folder.is_dir():
            continue
        manifest_path = folder / "compatScripts.json"
        owner = "__unowned__/" + folder.name
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text())
                selected = manifest.get("selectedRoot") or (manifest.get("roots") or [{}])[0].get("path")
                if isinstance(selected, str) and selected.startswith("assets/imported_mods/"):
                    owner = selected
            except (OSError, ValueError):
                pass
        refs = {kind: set() for kind in KINDS}
        for chart_path in folder.glob("*.json"):
            if chart_path.name in {"compatScripts.json", "events.json", "noteInfo.json"}:
                continue
            try:
                chart = json.loads(chart_path.read_text())
            except (OSError, ValueError):
                continue
            found = chart_refs(chart)
            for kind in KINDS:
                refs[kind].update(found[kind])
        result.append((owner, folder.name, refs))
    return result


def find_definition(donor, kind, reference):
    folders = [donor / "data" / KINDS[kind], donor / KINDS[kind],
               donor / "shared/data" / KINDS[kind], donor / "assets/data" / KINDS[kind],
               donor / "assets/shared/data" / KINDS[kind]]
    wanted = (reference + ".json").lower()
    for folder in folders:
        if not folder.is_dir():
            continue
        for child in folder.iterdir():
            if child.is_file() and child.name.lower() == wanted and within(child, donor):
                return child
    return None


def haxe_convert(items, runtime):
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vslice-visual-refresh-", dir=ROOT / "tmp") as scratch:
        tmp = Path(scratch)
        shutil.copyfile(ROOT / "source/VSliceImporter.hx", tmp / "VSliceImporter.hx")
        shutil.copyfile(ROOT / "source/VSliceAstcAdapter.hx", tmp / "VSliceAstcAdapter.hx")
        cool_source = (ROOT / "source/CoolUtil.hx").read_text()
        start = cool_source.index("public static function parseJson(")
        end = cool_source.index("\n\tpublic static function stringifyJson(", start)
        # Copy the real parser method verbatim; the full CoolUtil imports
        # OpenFL/Flixel types unavailable under --interp.
        (tmp / "CoolUtil.hx").write_text("import tjson.TJSON;\nclass CoolUtil {\n"
                                          + cool_source[start:end] + "\n}\n")
        (tmp / "Main.hx").write_text('''import haxe.Json;
import sys.io.File;
class Main {
 static function main() {
  var input:Array<Dynamic> = cast Json.parse(File.getContent(Sys.args()[0]));
  var output:Array<Dynamic> = [];
  for (item in input) {
   var data:Dynamic = CoolUtil.parseJson(File.getContent(item.definition));
   var converted:Dynamic = item.kind == 'stage'
    ? VSliceImporter.convertStage(data,item.contentRoot,item.reference,item.definition)
    : VSliceImporter.convertCharacter(data,item.contentRoot,item.reference,true,item.definition);
   output.push({kind:item.kind,reference:item.reference,name:converted.name,
    hscript:converted.hscript,assets:converted.assets,diagnostics:converted.diagnostics});
  }
  File.saveContent(Sys.args()[1],Json.stringify(output));
 }
}''')
        input_path, output_path = tmp / "input.json", tmp / "output.json"
        input_path.write_text(json.dumps(items))
        command = [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(tmp),
                   "-cp", str(TJSON),
                   "--run", "Main", str(input_path), str(output_path)]
        completed = subprocess.run(command, cwd=runtime, capture_output=True, text=True,
                                   timeout=180, env={**os.environ, "TMPDIR": str(ROOT / "tmp")})
        if completed.returncode:
            raise RuntimeError("VSliceImporter interpreter failed:\n" + completed.stdout + completed.stderr)
        return json.loads(output_path.read_text())


def target_path(runtime, kind, name):
    base = "custom_chars" if kind == "character" else "custom_stages"
    return runtime / "assets/images" / base / (name + ".hscript")


def media_paths(runtime, donor, item):
    base = "custom_chars" if item["kind"] == "character" else "custom_stages"
    folder = runtime / "assets/images" / base / item["name"]
    for mapping in item.get("assets") or []:
        destination = mapping.get("destination", "")
        source = Path(mapping.get("source", ""))
        if not destination or Path(destination).is_absolute() or ".." in Path(destination).parts:
            raise ValueError("unsafe mapped media destination")
        target = folder / destination
        if not within(target, folder) or not within(source, donor) \
                or not source.is_file() or not target.is_file():
            raise ValueError("mapped media is missing: " + str(target))
        if mapping.get("requiresConversion") or file_digest(source) != file_digest(target):
            raise ValueError("mapped media differs or needs conversion: " + str(target))
        yield {"source": str(source.resolve()), "target": str(target.resolve()),
               "sha256": file_digest(source)}


def make_plan(donor, runtime):
    if not donor.is_dir() or not (runtime / "assets/data").is_dir() or not HAXE.is_file() or not TJSON.is_dir():
        raise ValueError("donor, runtime assets/data, or portable Haxe is missing")
    donor, runtime = donor.resolve(), runtime.resolve()
    owner = namespace_for(donor)
    entries = inventory(runtime)
    selected = [entry for entry in entries if entry[0] == owner]
    if not selected:
        raise ValueError("no chart manifest selects exact donor namespace " + owner)
    refs = {kind: set() for kind in KINDS}
    for _, _, found in selected:
        for kind in KINDS:
            refs[kind].update(found[kind])
    other = {(kind, value.lower()) for other_owner, _, found in entries if other_owner != owner
             for kind in KINDS for value in found[kind]}
    issues, inputs = [], []
    for kind in KINDS:
        for reference in sorted(refs[kind], key=str.lower):
            if (kind, reference.lower()) in other:
                issues.append({"kind":kind,"reference":reference,"reason":"ID referenced by another manifest owner"})
                continue
            definition = find_definition(donor, kind, reference)
            if definition is None:
                issues.append({"kind":kind,"reference":reference,"reason":"donor definition missing"})
                continue
            content_root = donor / "assets" if (donor / "assets").is_dir() and \
                definition.is_relative_to(donor / "assets") else donor
            inputs.append({"kind":kind,"reference":reference,"definition":str(definition),
                           "contentRoot":str(content_root),"sourceSha256":file_digest(definition)})
    converted = haxe_convert(inputs, runtime) if inputs else []
    if len(converted) != len(inputs):
        raise ValueError("converter returned a different number of visuals")
    ready = []
    seen_target = set()
    for original, item in zip(inputs, converted):
        kind, name = item["kind"], item["name"]
        if kind != original["kind"] or item["reference"] != original["reference"]:
            raise ValueError("converter result order or identity changed")
        if not isinstance(name, str) or not SAFE_ID.fullmatch(name):
            issues.append({"kind":kind,"reference":original["reference"],"reason":"unsafe converted name"})
            continue
        target = target_path(runtime, kind, name)
        if target in seen_target:
            issues.append({"kind":kind,"reference":original["reference"],
                           "reason":"multiple donor IDs convert to one target script"})
            continue
        seen_target.add(target)
        if not within(target, runtime) or not target.is_file():
            issues.append({"kind":kind,"reference":original["reference"],"reason":"existing target script absent"})
            continue
        before = target.read_bytes()
        marker = b"vSliceProp_" if kind == "stage" else b"char.vSliceDoesLoop"
        if marker not in before:
            issues.append({"kind":kind,"reference":original["reference"],"reason":"target is not a recognizable generated V-Slice script"})
            continue
        try:
            media = list(media_paths(runtime, donor, item))
        except ValueError as error:
            issues.append({"kind":kind,"reference":original["reference"],"reason":str(error)})
            continue
        after = item["hscript"].encode()
        if before == after:
            continue
        diff = "".join(difflib.unified_diff(before.decode(errors="replace").splitlines(True),
                                            after.decode(errors="replace").splitlines(True),
                                            fromfile="current/" + target.name, tofile="regenerated/" + target.name))
        ready.append({"kind":kind,"reference":original["reference"],"name":name,"target":str(target),
                      "definition":original["definition"],"sourceSha256":original["sourceSha256"],
                      "beforeSha256":digest(before),"afterSha256":digest(after),
                      "afterBase64":base64.b64encode(after).decode(),"diff":diff,"media":media})
    return {"version":1,"donorRoot":str(donor),"runtimeRoot":str(runtime),"selectedRoot":owner,
            "songs":[song for _,song,_ in selected],"converterSha256":file_digest(ROOT / "source/VSliceImporter.hx"),
            "toolSha256":file_digest(Path(__file__)),
            "dependencySha256":{name:file_digest(ROOT / "source" / name) for name in
                ("EngineCompat.hx", "HxcCompat.hx", "NoteTypeCompat.hx", "CoolUtil.hx", "VSliceAstcAdapter.hx")},
            "candidates":ready,"skipped":issues}


def apply_plan(plan, plan_path):
    runtime = Path(plan["runtimeRoot"]).resolve()
    donor = Path(plan["donorRoot"]).resolve()
    if plan.get("version") != 1 or namespace_for(donor) != plan.get("selectedRoot"):
        raise ValueError("plan version or donor namespace changed")
    if file_digest(ROOT / "source/VSliceImporter.hx") != plan.get("converterSha256"):
        raise ValueError("VSliceImporter changed since plan")
    if file_digest(Path(__file__)) != plan.get("toolSha256"):
        raise ValueError("refresh tool changed since plan")
    if plan.get("dependencySha256") != {name:file_digest(ROOT / "source" / name) for name in
            ("EngineCompat.hx", "HxcCompat.hx", "NoteTypeCompat.hx", "CoolUtil.hx", "VSliceAstcAdapter.hx")}:
        raise ValueError("converter dependency changed since plan")
    locks = []
    try:
        for mode in ("0", "1"):
            lock = (ROOT / ".tools" / ("runtime-" + mode + ".lock")).open("a+")
            locks.append(lock)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not plan["candidates"]:
            return None
        current = inventory(runtime)
        selected = {song for owner,song,_ in current if owner == plan["selectedRoot"]}
        if not set(plan["songs"]).issubset(selected):
            raise ValueError("selected manifest owner changed")
        other = {(kind, value.lower()) for owner,_,found in current if owner != plan["selectedRoot"]
                 for kind in KINDS for value in found[kind]}
        for item in plan["candidates"]:
            if item["kind"] not in KINDS or not SAFE_ID.fullmatch(item["name"]):
                raise ValueError("plan contains unsafe visual identity")
            target = Path(item["target"])
            expected = target_path(runtime, item["kind"], item["name"])
            if (item["kind"], item["reference"].lower()) in other:
                raise ValueError("visual ID gained another owner")
            if target != expected or not within(target, runtime) or file_digest(target) != item["beforeSha256"]:
                raise ValueError("target path or bytes changed: " + str(target))
            if not within(Path(item["definition"]), donor) or file_digest(Path(item["definition"])) != item["sourceSha256"]:
                raise ValueError("donor definition changed")
            after = base64.b64decode(item["afterBase64"], validate=True)
            if digest(after) != item["afterSha256"]:
                raise ValueError("planned output hash mismatch")
            for media in item["media"]:
                if not within(Path(media["source"]), donor) or not within(Path(media["target"]), runtime) \
                        or file_digest(Path(media["source"])) != media["sha256"] \
                        or file_digest(Path(media["target"])) != media["sha256"]:
                    raise ValueError("mapped media changed")
        backup = ROOT / "tmp/import-refresh-backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup.mkdir(parents=True, exist_ok=False)
        shutil.copy2(plan_path, backup / "plan.json")
        for item in plan["candidates"]:
            target = Path(item["target"])
            saved = backup / target.relative_to(runtime)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            if file_digest(saved) != item["beforeSha256"]:
                raise ValueError("backup verification failed: " + str(saved))
        replaced = []
        try:
            for item in plan["candidates"]:
                target = Path(item["target"])
                after = base64.b64decode(item["afterBase64"], validate=True)
                if (ROOT / "tmp").stat().st_dev != target.parent.stat().st_dev:
                    raise ValueError("project tmp and runtime target are on different filesystems")
                with tempfile.NamedTemporaryFile(dir=ROOT / "tmp", prefix="vslice-refresh-", delete=False) as staged:
                    staged.write(after)
                    staged.flush()
                    os.fsync(staged.fileno())
                    staged_path = Path(staged.name)
                try:
                    os.chmod(staged_path, target.stat().st_mode)
                    os.replace(staged_path, target)
                finally:
                    staged_path.unlink(missing_ok=True)
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
    plan_cmd = commands.add_parser("plan", help="write a read-only refresh plan")
    plan_cmd.add_argument("--donor-root", type=Path, required=True)
    plan_cmd.add_argument("--runtime-root", type=Path, required=True)
    plan_cmd.add_argument("--output", type=Path, required=True)
    apply_cmd = commands.add_parser("apply", help="apply one explicitly reviewed plan")
    apply_cmd.add_argument("--plan", type=Path, required=True)
    apply_cmd.add_argument("--reviewed", action="store_true", required=True)
    args = parser.parse_args()
    if args.command == "plan":
        output = args.output.resolve()
        if output.exists() or within(output, args.runtime_root) or within(output, args.donor_root):
            parser.error("plan output must be a new file outside donor and runtime roots")
        plan = make_plan(args.donor_root, args.runtime_root)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(plan, indent=2) + "\n")
        print(f"plan: {output}; candidates={len(plan['candidates'])}; skipped={len(plan['skipped'])}")
    else:
        plan = json.loads(args.plan.read_text())
        backup = apply_plan(plan, args.plan.resolve())
        print("applied; backup: " + str(backup) if backup else "no script changes in plan")


if __name__ == "__main__":
    main()
