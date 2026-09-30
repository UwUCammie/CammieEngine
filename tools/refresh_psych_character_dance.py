#!/usr/bin/env python3
"""Plan or apply a provenance-checked refresh of generated Psych dance scripts.

Only byte-identical output from the old standard Psych converter is eligible.
The current Haxe renderer supplies both old and new bytes; customized scripts
are skipped. Apply saves verified backups under this repository's tmp folder.
"""

import argparse
import base64
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"
HAXE = ROOT / ".tools/haxe/haxe"
TJSON = ROOT / ".haxelib/tjson/1,4,0"
RENDERER = ROOT / "source/PsychCharacterDanceCompat.hx"
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


def within(path, root):
    return path.resolve().is_relative_to(root.resolve())


def namespace_for(donor):
    root = donor.resolve()
    label = re.sub(r"[^a-z0-9]+", "-", root.name.lower()).strip("-")
    return "assets/imported_mods/psych-engine-" + label + "-" + hashlib.md5(str(root).encode()).hexdigest()[:10]


def selected_songs(runtime, namespace):
    songs = []
    data = runtime / "assets/data"
    if not data.is_dir():
        return songs
    for folder in sorted(data.iterdir()):
        manifest = folder / "compatScripts.json"
        if not folder.is_dir() or not manifest.is_file():
            continue
        try:
            parsed = json.loads(manifest.read_text())
        except (OSError, ValueError):
            continue
        if parsed.get("selectedRoot") != namespace:
            continue
        roots = parsed.get("roots") or []
        if any(isinstance(entry, dict) and entry.get("path") == namespace
               and entry.get("engine") == "Psych Engine" for entry in roots):
            songs.append(folder.name)
    return songs


def character_definitions(donor):
    content = donor / "assets" if (donor / "assets").is_dir() else donor
    seen = set()
    for root in (content, content / "shared"):
        folder = root / "characters"
        if not folder.is_dir():
            continue
        for source in sorted(folder.iterdir()):
            if not source.is_file() or source.suffix.lower() != ".json":
                continue
            name = source.stem
            if not SAFE_ID.fullmatch(name) or name.lower() in seen or not within(source, donor):
                continue
            seen.add(name.lower())
            yield name, source


def render_scripts(sources):
    """Run the exact engine renderer in the portable Haxe interpreter."""
    if not HAXE.is_file() or not TJSON.is_dir():
        raise ValueError("portable Haxe and TJSON dependencies are required")
    TMP.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="psych-dance-render-", dir=TMP) as scratch:
        folder = Path(scratch)
        (folder / "PsychCharacterDanceCompat.hx").write_bytes(RENDERER.read_bytes())
        (folder / "Render.hx").write_text('''import haxe.Json;
import sys.io.File;
import tjson.TJSON;
class Render {
  static function main() {
    var paths:Array<String> = Json.parse(File.getContent(Sys.args()[0]));
    var result:Array<Dynamic> = [];
    for (path in paths) {
      var data:Dynamic = TJSON.parse(File.getContent(path));
      result.push({path:path,
        pair:PsychCharacterDanceCompat.hasDancePair(data),
        legacy:PsychCharacterDanceCompat.renderStandardScript(data, false, false, false, true),
        current:PsychCharacterDanceCompat.renderStandardScript(data, false, false, false)});
    }
    File.saveContent(Sys.args()[1], Json.stringify(result));
  }
}
''')
        input_path = folder / "input.json"
        output_path = folder / "output.json"
        input_path.write_text(json.dumps([str(path) for path in sources]))
        command = [str(HAXE), "-cp", str(folder), "-cp", str(TJSON), "--run", "Render",
                   str(input_path), str(output_path)]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                env={**os.environ, "TMPDIR": str(TMP)})
        if result.returncode:
            raise ValueError("Psych renderer failed: " + result.stdout + result.stderr)
        return {Path(item["path"]): item for item in json.loads(output_path.read_text())}


def make_plan(donor_root, runtime_root):
    donor = donor_root.resolve()
    runtime = runtime_root.resolve()
    if not donor.is_dir() or not runtime.is_dir():
        raise ValueError("donor and runtime roots must be directories")
    namespace = namespace_for(donor)
    songs = selected_songs(runtime, namespace)
    if not songs:
        raise ValueError("no song selects this Psych donor namespace")
    sources = list(character_definitions(donor))
    rendered = render_scripts([path for _, path in sources])
    candidates = []
    skipped = []
    for name, source in sources:
        target = runtime / namespace / "images/custom_chars" / (name + ".hscript")
        if not within(target, runtime):
            continue
        item = rendered[source]
        if not target.is_file():
            skipped.append({"name": name, "reason": "generated script missing"})
            continue
        before = target.read_bytes()
        legacy = item["legacy"].encode()
        after = item["current"].encode()
        if before == after:
            continue
        if before != legacy:
            skipped.append({"name": name, "reason": "script differs from legacy generated bytes"})
            continue
        candidates.append({"name": name, "source": str(source), "sourceSha256": file_sha(source),
                           "target": str(target), "beforeSha256": sha(before),
                           "afterSha256": sha(after), "afterBase64": base64.b64encode(after).decode()})
    return {"version": 1, "donorRoot": str(donor), "runtimeRoot": str(runtime),
            "selectedRoot": namespace, "songs": songs, "rendererSha256": file_sha(RENDERER),
            "toolSha256": file_sha(Path(__file__)), "candidates": candidates, "skipped": skipped}


def apply_plan(plan, plan_path):
    donor = Path(plan["donorRoot"]).resolve()
    runtime = Path(plan["runtimeRoot"]).resolve()
    namespace = plan.get("selectedRoot")
    if plan.get("version") != 1 or namespace_for(donor) != namespace:
        raise ValueError("plan version or donor namespace changed")
    if file_sha(RENDERER) != plan.get("rendererSha256") or file_sha(Path(__file__)) != plan.get("toolSha256"):
        raise ValueError("renderer or tool changed since planning")
    locks = []
    try:
        for mode in ("0", "1"):
            lock = (ROOT / ".tools" / ("runtime-" + mode + ".lock")).open("a+")
            locks.append(lock)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not plan["candidates"]:
            return None
        if not set(plan["songs"]).issubset(selected_songs(runtime, namespace)):
            raise ValueError("selected Psych owner changed")
        definitions = dict(character_definitions(donor))
        for item in plan["candidates"]:
            if not SAFE_ID.fullmatch(item["name"]):
                raise ValueError("unsafe character id in plan")
            target = Path(item["target"])
            expected = runtime / namespace / "images/custom_chars" / (item["name"] + ".hscript")
            source = Path(item["source"])
            if (target != expected or not within(target, runtime)
                    or definitions.get(item["name"]) != source):
                raise ValueError("target or source path changed")
            if file_sha(source) != item["sourceSha256"] or file_sha(target) != item["beforeSha256"]:
                raise ValueError("source or installed script changed")
            if sha(base64.b64decode(item["afterBase64"], validate=True)) != item["afterSha256"]:
                raise ValueError("planned script bytes changed")
        rendered = render_scripts([Path(item["source"]) for item in plan["candidates"]])
        for item in plan["candidates"]:
            source = Path(item["source"])
            target = Path(item["target"])
            if target.read_bytes() != rendered[source]["legacy"].encode():
                raise ValueError("installed script is not the exact legacy generated output: " + str(target))
            if base64.b64decode(item["afterBase64"], validate=True) != rendered[source]["current"].encode():
                raise ValueError("planned script differs from current renderer: " + str(target))
        backup = TMP / "import-refresh-backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup.mkdir(parents=True, exist_ok=False)
        shutil.copy2(plan_path, backup / "plan.json")
        for item in plan["candidates"]:
            target = Path(item["target"])
            saved = backup / target.relative_to(runtime)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            if file_sha(saved) != item["beforeSha256"]:
                raise ValueError("backup verification failed: " + str(saved))
        replaced = []
        try:
            for item in plan["candidates"]:
                target = Path(item["target"])
                if TMP.stat().st_dev != target.parent.stat().st_dev:
                    raise ValueError("repo tmp and runtime target are on different filesystems")
                after = base64.b64decode(item["afterBase64"], validate=True)
                with tempfile.NamedTemporaryFile(dir=TMP, prefix="psych-dance-refresh-", delete=False) as staged:
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
        if output.exists() or not within(output, TMP) or within(output, args.runtime_root) or within(output, args.donor_root):
            parser.error("plan output must be a new file under repo tmp, outside donor and runtime roots")
        plan = make_plan(args.donor_root, args.runtime_root)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(plan, indent=2) + "\n")
        print(f"plan: {output}; candidates={len(plan['candidates'])}; skipped={len(plan['skipped'])}")
    else:
        plan_path = args.plan.resolve()
        if not within(plan_path, TMP):
            parser.error("plan must be under repo tmp")
        backup = apply_plan(json.loads(plan_path.read_text()), plan_path)
        print("applied; backup: " + str(backup) if backup else "no script changes in plan")


if __name__ == "__main__":
    main()
