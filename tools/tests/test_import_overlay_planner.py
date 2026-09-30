"""Focused coverage for the bounded Polymod-style overlay planner.

The Haxe fixture runs the real standalone planner through the portable
interpreter.  Mounted fixtures are read-only assertions: this suite never
writes into FNF-Example-Mods.
"""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
EXAMPLES = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
SEO_ROOT = EXAMPLES / "SeoS"
TAKEOVER_ROOT = EXAMPLES / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE"


def haxe_string(value: str) -> str:
    return json.dumps(str(value))


class ImportOverlayPlannerTest(unittest.TestCase):
    def run_fixture(self, main_source: str, *args: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            main_path = Path(folder) / "Main.hx"
            main_path.write_text(main_source)
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            return subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder,
                 "--run", "Main", *args],
                cwd=ROOT,
                capture_output=True,
                text=True,
                env=env,
            )

    def test_synthetic_plan_is_deterministic_and_applies_supported_operations(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder) / "donor"
            (root / "mods/alpha/_append/data").mkdir(parents=True)
            (root / "mods/alpha/_replace/data").mkdir(parents=True)
            (root / "mods/alpha/_merge/data").mkdir(parents=True)
            (root / "mods/alpha/_delete").mkdir(parents=True)
            (root / "mods/beta/_merge/data").mkdir(parents=True)
            (root / "mods/modList.txt").write_text(
                "# comments are inert\nalpha\n../escape\nbeta\nalpha\nmissing\n"
            )
            (root / "mods/alpha/_append/data/intro.txt").write_bytes(b"tail\r\n")
            (root / "mods/alpha/_append/data/bad:name.txt").write_bytes(b"bad")
            (root / "mods/alpha/_append/data/binary.bin").write_bytes(b"\x00\x01")
            (root / "mods/alpha/_replace/data/blob.bin").write_bytes(b"\x00\x01")
            (root / "mods/alpha/_merge/data/players.json").write_text(json.dumps([
                {"op": "add", "path": "/ownedChars/-", "value": "pico-doki"},
                {"op": "add", "path": "/a~1b/~0key", "value": 2},
                {"op": "replace", "path": "/name", "value": "new"},
                {"op": "remove", "path": "/remove"},
            ]))
            (root / "mods/beta/_merge/data/bad.json").write_text(
                '[{"op":"copy","path":"/x","from":"/y"}]'
            )
            (root / "mods/beta/_merge/data/malformed.json").write_text("not-json")
            (root / "mods/beta/_merge/data/object.json").write_text('{"op":"add"}')
            (root / "mods/beta/_merge/data/type.json").write_text('[{"op":1,"path":"/x","value":1}]')

            main = r'''import haxe.Json;
import haxe.io.Bytes;
import ImportOverlayPlanner.ImportOverlayEntry;
import ImportOverlayPlanner.ImportOverlayPlan;

class Main {
  static function fail(message:String):Void throw message;
  static function hasCode(plan:ImportOverlayPlan, code:String):Bool {
    for (finding in plan.diagnostics) if (finding.code == code) return true;
    return false;
  }
  static function main() {
    var plan = ImportOverlayPlanner.plan(Sys.args()[0]);
    if (plan.activeMods.length != 3 || plan.activeMods[0] != "alpha"
      || plan.activeMods[1] != "beta" || plan.activeMods[2] != "missing")
      fail("modList order/validation: " + plan.activeMods.join("|"));
    if (!ImportOverlayPlanner.validateModName("introMod")
      || ImportOverlayPlanner.validateModName("../escape")) fail("mod name validator");
    if (ImportOverlayPlanner.validateRelativePath("../escape.txt") != null
      || ImportOverlayPlanner.validateRelativePath("/absolute.txt") != null
      || ImportOverlayPlanner.validateRelativePath("data/../escape.txt") != null)
      fail("relative path traversal validator");
    if (!hasCode(plan, "unsafe-mod-name") || !hasCode(plan, "duplicate-mod")
      || !hasCode(plan, "missing-mod") || !hasCode(plan, "unsupported-overlay-operation")
      || !hasCode(plan, "unsafe-overlay-path") || !hasCode(plan, "unsupported-append-type")
      || !hasCode(plan, "unsupported-json-patch-op") || !hasCode(plan, "malformed-json-patch")
      || !hasCode(plan, "json-patch-not-array") || !hasCode(plan, "json-patch-op-type"))
      fail("diagnostics: " + [for (finding in plan.diagnostics) finding.code].join(","));

    var append:ImportOverlayEntry = null;
    var replace:ImportOverlayEntry = null;
    var merge:ImportOverlayEntry = null;
    for (entry in plan.entries) {
      if (entry.relativePath == "data/intro.txt") append = entry;
      if (entry.relativePath == "data/blob.bin") replace = entry;
      if (entry.relativePath == "data/players.json") merge = entry;
    }
    if (append == null || append.kind != ImportOverlayPlanner.KIND_TEXT_APPEND
      || append.provenance != "alpha/_append/data/intro.txt"
      || append.sourceBytes.toString() != "tail\r\n") fail("append entry");
    if (replace == null || replace.kind != ImportOverlayPlanner.KIND_REPLACE
      || replace.sourceBytes.length != 2 || replace.sourceBytes.get(0) != 0)
      fail("replace bytes");
    if (merge == null || merge.kind != ImportOverlayPlanner.KIND_JSON_PATCH
      || merge.patches == null || merge.patches.length != 4)
      fail("merge entry");
    var merged = ImportOverlayPlanner.applyJsonPatch(
      Json.parse('{"ownedChars":["bf"],"a/b":{"~key":1},"name":"old","remove":true}'),
      cast merge.patches);
    if (!merged.ok) fail("merge apply");
    var value:Dynamic = merged.value;
    var chars:Array<Dynamic> = cast value.ownedChars;
    if (chars.length != 2 || chars[1] != "pico-doki" || value.name != "new"
      || value.remove != null
      || Reflect.field(Reflect.field(value, "a/b"), "~key") != 2)
      fail("merge semantics");
    var appended = ImportOverlayPlanner.applyTextAppend(
      Bytes.ofString("head\n"), [append]);
    if (appended.toString() != "head\ntail\r\n") fail("append semantics");
  }
}'''
            result = self.run_fixture(main, str(root))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_json_pointer_escaping_array_dash_and_rejection(self):
        main = r'''import haxe.Json;
import ImportOverlayPlanner.ImportOverlayPatch;
class Main {
  static function fail(message:String):Void throw message;
  static function main() {
    var patches:Array<ImportOverlayPatch> = [
      {op:"add", path:"/items/-", value:"last"},
      {op:"add", path:"/a~1b/~0key", value:3},
      {op:"replace", path:"/items/0", value:"first"},
      {op:"remove", path:"/remove"}
    ];
    var result = ImportOverlayPlanner.applyJsonPatch(
      Json.parse('{"items":["old"],"a/b":{"~key":1},"remove":true}'), patches);
    if (!result.ok) fail("valid pointer operations rejected");
    var value:Dynamic = result.value;
    if (value.items.length != 2 || value.items[0] != "first" || value.items[1] != "last"
      || Reflect.field(Reflect.field(value, "a/b"), "~key") != 3
      || value.remove != null) fail("pointer semantics");

    var bad:Array<ImportOverlayPatch> = [{op:"add", path:"/items/-/nested", value:1}];
    var rejected = ImportOverlayPlanner.applyJsonPatch(Json.parse('{"items":[]}'), bad);
    if (rejected.ok || rejected.diagnostics.length == 0
      || rejected.diagnostics[0].code != "invalid-json-pointer") fail("bad pointer accepted");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(SEO_ROOT.is_dir(), "mounted FNF-Example-Mods/SeoS is unavailable")
    def test_mounted_seos_append_is_planned_without_mutating_donor(self):
        mod_list_before = (SEO_ROOT / "mods/modList.txt").read_bytes()
        append_path = SEO_ROOT / "mods/introMod/_append/data/introText.txt"
        append_before = append_path.read_bytes()
        main = f'''import haxe.io.Bytes;
import sys.io.File;
import haxe.io.Path;
class Main {{
  static function fail(message:String):Void throw message;
  static function main() {{
    var root = Sys.args()[0];
    var plan = ImportOverlayPlanner.plan(root);
    if (plan.activeMods.length != 1 || plan.activeMods[0] != "introMod")
      fail("SeoS mod list: " + plan.activeMods.join("|"));
    if (plan.entries.length != 1) fail("SeoS entry count: " + plan.entries.length);
    var entry = plan.entries[0];
    if (entry.operation != "_append" || entry.kind != ImportOverlayPlanner.KIND_TEXT_APPEND
      || entry.relativePath != "data/introText.txt") fail("SeoS append identity");
    if (entry.sourceBytes.toString() != "swagshit--moneymoney") fail("SeoS append bytes");
    var base = File.getBytes(Path.join([root, "assets/data/introText.txt"]));
    var combined = ImportOverlayPlanner.applyTextAppend(base, plan.entries);
    if (combined.length != base.length + entry.sourceBytes.length) fail("SeoS append length");
    if (combined.toString().substr(base.length) != "swagshit--moneymoney") fail("SeoS append output");
  }}
}}'''
        result = self.run_fixture(main, str(SEO_ROOT))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(mod_list_before, (SEO_ROOT / "mods/modList.txt").read_bytes())
        self.assertEqual(append_before, append_path.read_bytes())

    @unittest.skipUnless(TAKEOVER_ROOT.is_dir(), "mounted TAKEOVER V-Slice root is unavailable")
    def test_mounted_takeover_owned_chars_merge_is_planned_without_mutating_donor(self):
        patch_path = TAKEOVER_ROOT / "_merge/data/players/pico.json"
        patch_before = patch_path.read_bytes()
        main = r'''import haxe.Json;
import sys.io.File;
import ImportOverlayPlanner.ImportOverlayEntry;
class Main {
  static function fail(message:String):Void throw message;
  static function main() {
    var root = Sys.args()[0];
    var plan = ImportOverlayPlanner.plan(root);
    if (plan.entries.length != 1)
      fail("TAKEOVER entry count: " + plan.entries.length);
    var entry = plan.entries[0];
    if (entry.operation != "_merge" || entry.relativePath != "data/players/pico.json"
      || entry.kind != ImportOverlayPlanner.KIND_JSON_PATCH) fail("TAKEOVER merge identity");
    if (entry.patches == null || entry.patches.length != 1
      || entry.patches[0].op != "add" || entry.patches[0].path != "/ownedChars/-"
      || entry.patches[0].value != "pico-doki") fail("TAKEOVER patch");
    var base:Dynamic = Json.parse('{"ownedChars":["bf"]}');
    var applied = ImportOverlayPlanner.applyJsonPatch(base, cast entry.patches);
    if (!applied.ok) fail("TAKEOVER merge apply");
    var chars:Array<Dynamic> = cast applied.value.ownedChars;
    if (chars.length == 0 || chars[chars.length - 1] != "pico-doki") fail("ownedChars append");
  }
}'''
        result = self.run_fixture(main, str(TAKEOVER_ROOT))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(patch_before, patch_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
