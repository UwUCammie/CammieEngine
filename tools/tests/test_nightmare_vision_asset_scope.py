"""Pin package/core scope selection for retained Nightmare Vision asset roots."""

from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


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
                return source[start : index + 1]
    raise AssertionError(marker)


FIXTURE = r'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

class ImportDirectoryListing {
  public static function normalize(entries:Array<String>):Array<String> return entries;
}
class ImportPackageFamilyCatalog {
  public static function isAuthenticatedNightmareVisionContainer(root:String):Bool {
    var project = Path.join([root, "Project.xml"]);
    if (!FileSystem.exists(project) || FileSystem.isDirectory(project)) return false;
    var xml = File.getContent(project).toLowerCase();
    return xml.indexOf("com.nmvteam.nightmareengine") >= 0;
  }
}
class ImportIO {
  public static function current():Null<ImportIO> return null;
  public function namespace(_root:String, _engine:String):String return null;
  public function setNamespace(_root:String, _engine:String, _namespace:String):Void {}
}
class SourceMappedMediaPolicy {
  public static inline var PACKAGE_SCOPE:String = "package";
  public static inline var CORE_SCOPE:String = "core";
}
class ImportEngine {
  public static inline var NIGHTMARE_VISION:String = "Nightmare Vision";
}

class NightmareVisionAssetScopeFixture {
  static function ensure(path:String):Void {
    if (path == null || path == "" || FileSystem.exists(path)) return;
    var parent = Path.directory(path);
    if (parent != null && parent != "" && parent != path && !FileSystem.exists(parent)) ensure(parent);
    FileSystem.createDirectory(path);
  }
  static function write(path:String, text:String):Void {
    ensure(Path.directory(path));
    File.saveContent(path, text);
  }

  __METHODS__

  static function main():Void {
    var base = Sys.args()[0];
    var game = Path.join([base, "game"]);
    write(Path.join([game, "Project.xml"]), '<project><app packageName="com.nmvteam.nightmareengine" /></project>');
    ensure(Path.join([game, "assets"]));

    var directPackage = Path.join([game, "content", "direct"]);
    var directAssets = Path.join([directPackage, "assets"]);
    write(Path.join([directPackage, "meta.json"]), '{"name":"direct"}');
    ensure(directAssets);
    if (authenticatedNightmareVisionScope(directPackage, directAssets) != SourceMappedMediaPolicy.PACKAGE_SCOPE)
      throw "direct package root was not classified as package";

    var markedPackage = Path.join([game, "content", "marked"]);
    var markedAssets = Path.join([markedPackage, "assets"]);
    write(Path.join([markedPackage, "meta.json"]), '{"name":"marked"}');
    write(Path.join([markedAssets, "Project.xml"]), '<project><app packageName="com.nmvteam.nightmareengine" /></project>');
    if (authenticatedNightmareVisionScope(markedAssets, markedAssets) != SourceMappedMediaPolicy.PACKAGE_SCOPE)
      throw "package assets root with an app marker shadowed the outer core and was classified as core";

    var plainPackage = Path.join([game, "content", "plain"]);
    var plainAssets = Path.join([plainPackage, "assets"]);
    write(Path.join([plainPackage, "meta.json"]), '{"name":"plain"}');
    write(Path.join([plainAssets, "Project.xml"]), '<project><assets path="images" /></project>');
    if (authenticatedNightmareVisionScope(plainAssets, plainAssets) != SourceMappedMediaPolicy.PACKAGE_SCOPE)
      throw "package assets root without an app marker was not classified as package";

    if (authenticatedNightmareVisionScope(game, Path.join([game, "assets"])) != SourceMappedMediaPolicy.CORE_SCOPE)
      throw "authenticated outer game assets root was not classified as core";
  }
}
'''


class NightmareVisionAssetScopeTest(unittest.TestCase):
    def test_canonical_package_proof_precedes_inner_project_marker(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function normalizedImportFileName",
                "static function findImportFile",
                "static function isImportFile",
                "static function canonicalNightmareVisionPackageRoot",
                "static function retainNightmareVisionPackageNamespace",
                "static function authenticatedNightmareVisionScope",
            )
        )
        fixture = FIXTURE.replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            (scratch / "NightmareVisionAssetScopeFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(scratch), "--run", "NightmareVisionAssetScopeFixture", str(scratch / "input")],
                cwd=scratch,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
