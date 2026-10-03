"""Exercise Codename OBJ material and diffuse-texture import dependencies."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


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


def hx_string(value: str) -> str:
    return json.dumps(str(value))


class CodenameObjAssetDependencyTest(unittest.TestCase):
    def test_material_and_diffuse_maps_copy_from_only_the_selected_owner(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        copy_method = extract_method(module, "static function copyImportFileNonOverwriting(")
        ensure_method = extract_method(module, "static function ensureDirectory(")
        main_source = '''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
typedef ImportAssetMergeResult = {var copied:Int; var skipped:Int; var failed:Int; var errors:Array<String>;};
class Main {
''' + ensure_method + '\n' + copy_method + '''
  static function fail(message:String):Void throw message;
  static function main():Void {
    var sourceA = Sys.args()[0];
    var sourceB = Sys.args()[1];
    var destinationA = Sys.args()[2];
    var destinationB = Sys.args()[3];
    var dependencies = CodenameObjAssetDependencies.filesFor(sourceA, "models/plane.obj");
    if (dependencies.length != 3) fail("expected one MTL and two map_Kd textures, got " + dependencies.length
      + ": " + [for (dependency in dependencies) dependency.relative].join(","));
    var expected = [
      "models/materials/testStage.mtl",
      "models/materials/textures/gradient mask.png",
      "models/materials/textures/detail.png"
    ];
    for (relative in expected) {
      var found = false;
      for (dependency in dependencies) {
        if (dependency.relative == relative) {
          found = true;
          if (!CodenameScriptDiscovery.withinRoot(sourceA, dependency.source))
            fail("dependency escaped the selected source owner: " + dependency.source);
          if (dependency.source.indexOf(sourceB + "/") == 0)
            fail("dependency borrowed the other owner: " + dependency.source);
        }
      }
      if (!found) fail("selected-owner dependency missing: " + relative);
    }

    var result:ImportAssetMergeResult = {copied:0, skipped:0, failed:0, errors:[]};
    for (dependency in dependencies)
      copyImportFileNonOverwriting(dependency.source, Path.join([destinationA, dependency.relative]), result);
    if (result.failed != 0 || result.copied != 3 || result.skipped != 0)
      fail("copy result " + result.copied + "/" + result.skipped + "/" + result.failed);
    for (relative in expected) {
      var source = Path.join([sourceA, relative]);
      var copied = Path.join([destinationA, relative]);
      if (!FileSystem.exists(copied) || File.getContent(source) != File.getContent(copied))
        fail("dependency did not materialize byte-for-byte: " + relative);
      if (FileSystem.exists(Path.join([destinationB, relative])))
        fail("dependency leaked into another import owner: " + relative);
    }

    var otherOwner = CodenameObjAssetDependencies.filesFor(sourceB, "models/plane.obj");
    if (otherOwner.length != 2 || otherOwner[0].source.indexOf(sourceB + "/") != 0
      || otherOwner[0].source.indexOf(sourceA + "/") == 0)
      fail("second import did not resolve its own MTL dependency");
  }
}'''

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            source_a = base / "source-a"
            source_b = base / "source-b"
            destination_a = base / "owner-a"
            destination_b = base / "owner-b"
            files_a = {
                "models/plane.obj": "# fixture\nmtllib materials/testStage.mtl\n",
                "models/materials/testStage.mtl": (
                    "newmtl floor\n"
                    "map_Kd -s 1 1 1 textures/gradient mask.png\n"
                    "map_Kd -o 0 0 0 textures/detail.png\n"
                    "map_Ks textures/not-supported-by-runtime.png\n"
                ),
                "models/materials/textures/gradient mask.png": "owner A gradient",
                "models/materials/textures/detail.png": "owner A detail",
            }
            files_b = {
                "models/plane.obj": "# fixture\nmtllib materials/testStage.mtl\n",
                "models/materials/testStage.mtl": "newmtl other\nmap_Kd textures/other.png\n",
                "models/materials/textures/other.png": "owner B texture",
            }
            for root, files in ((source_a, files_a), (source_b, files_b)):
                for relative, content in files.items():
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, newline='\n')
            destination_a.mkdir()
            destination_b.mkdir()

            main = base / "Main.hx"
            main.write_text(main_source, newline='\n')
            result = subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp", str(ROOT / "source"),
                    "-cp", str(base),
                    "--run", "Main",
                    source_a.as_posix(), source_b.as_posix(), destination_a.as_posix(), destination_b.as_posix(),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_obj_material_and_texture_paths_cannot_escape_the_source_owner(self):
        main = '''class Main {
  static function main():Void {
    var dependencies = CodenameObjAssetDependencies.filesFor(Sys.args()[0], "models/plane.obj");
    if (dependencies.length != 0) throw "escaped material sidecar was planned";
  }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            source = base / "source"
            source.mkdir()
            outside = base / "outside.mtl"
            outside.write_text("newmtl outside\nmap_Kd texture.png\n", newline='\n')
            outside_texture = base / "texture.png"
            outside_texture.write_text("outside texture", newline='\n')
            models = source / "models"
            models.mkdir()
            (models / "plane.obj").write_text("mtllib escape.mtl\n", newline='\n')
            try:
                (models / "escape.mtl").symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symlink fixture unavailable: {error}")
            (base / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                 "--run", "Main", str(source)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_codename_runtime_importer_plans_obj_sidecars_before_owner_copy(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("CodenameObjAssetDependencies.filesFor(sourceRoot, objRelative)", source)
        self.assertIn("'Paths\\\\s*\\\\.\\\\s*obj", source)
        self.assertIn("copyImportFileNonOverwriting(entry.source, destination, result);", source)


if __name__ == "__main__":
    unittest.main()
