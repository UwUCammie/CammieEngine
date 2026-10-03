"""Selected-owner Codename package options XML import closure."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameOptionsXmlDependencyTest(unittest.TestCase):
    def test_known_and_nested_option_xml_copy_only_from_selected_owner(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("CodenameOptionsXmlDependencies.filesFor(sourceRoot)", source)
        self.assertIn("appendResolvedAsset(dependency.source, dependency.relative)", source)
        self.assertIn("[codename-options-dependency]", (ROOT / "source/CodenameOptionsXmlDependencies.hx").read_text())

        main = '''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
typedef ImportAssetMergeResult = {var copied:Int; var skipped:Int; var failed:Int; var errors:Array<String>;};
class Main {
''' + extract_method((ROOT / "source/ModuleFunctions.hx").read_text(), "static function ensureDirectory(") + '\n' + extract_method(
            (ROOT / "source/ModuleFunctions.hx").read_text(), "static function copyImportFileNonOverwriting(") + '''
 static function fail(message:String):Void throw message;
 static function main():Void {
  var selected = Sys.args()[0];
  var other = Sys.args()[1];
  var destination = Sys.args()[2];
  var plan = CodenameOptionsXmlDependencies.filesFor(selected);
  if (plan.files.length != 3) fail("wrong selected options plan size: " + plan.files.length);
  var expected = ["data/config/options.xml", "data/config/options/advanced.xml", "config/options.xml"];
  for (relative in expected) {
   var found = false;
   for (file in plan.files) if (file.relative == relative) {
    found = true;
    if (!CodenameScriptDiscovery.withinRoot(selected, file.source)) fail("source escaped selected owner: " + file.source);
    if (file.source.indexOf(other + "/") == 0) fail("borrowed other owner file: " + file.source);
   }
   if (!found) fail("missing staged option document: " + relative);
  }
  var result:ImportAssetMergeResult = {copied:0, skipped:0, failed:0, errors:[]};
  for (file in plan.files)
   copyImportFileNonOverwriting(file.source, Path.join([destination, file.relative]), result);
  if (result.failed != 0 || result.copied != 3) fail("copy result " + result.copied + "/" + result.failed);
  for (relative in expected) {
   var copied = Path.join([destination, relative]);
   if (!FileSystem.exists(copied) || File.getContent(copied) != "selected owner: " + relative)
    fail("not copied byte-for-byte: " + relative);
  }
  if (FileSystem.exists(Path.join([destination, "data/config/options/ignored.txt"])))
   fail("non-XML options file was staged");
  if (FileSystem.exists(Path.join([destination, "data/config/options/nested/hidden.xml"])))
   fail("file outside Codename's one-level options lookup was staged");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            selected, other, destination = base / "selected", base / "other", base / "destination"
            files = {
                selected: {
                    "data/config/options.xml": "selected owner: data/config/options.xml",
                    "data/config/options/advanced.xml": "selected owner: data/config/options/advanced.xml",
                    "data/config/options/ignored.txt": "ignore",
                    "data/config/options/nested/hidden.xml": "ignore deeper nesting",
                    "config/options.xml": "selected owner: config/options.xml",
                },
                other: {
                    "data/config/options.xml": "other owner options",
                    "data/config/options/advanced.xml": "other owner advanced",
                },
            }
            for root, entries in files.items():
                for relative, content in entries.items():
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, newline='\n')
            destination.mkdir()
            (base / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main",
                 str(selected), str(other), str(destination)],
                cwd=ROOT, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_options_sidecar_symlink_escape_is_not_materialized(self):
        main = '''class Main {
 static function main():Void {
  var plan = CodenameOptionsXmlDependencies.filesFor(Sys.args()[0]);
  if (plan.files.length != 0) throw "outside options symlink was planned";
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            selected, outside = base / "selected", base / "outside.xml"
            outside.write_text("external options", newline='\n')
            folder = selected / "data/config/options"
            folder.mkdir(parents=True)
            try:
                (folder / "external.xml").symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symlink fixture unavailable: {error}")
            (base / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main", str(selected)],
                cwd=ROOT, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


if __name__ == "__main__":
    unittest.main()
