"""Case-folded native asset lookup used by Windows-authored donor packs."""

from pathlib import Path
import os
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
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class NativeAssetResolutionTest(unittest.TestCase):
    def test_resolver_is_safe_deterministic_and_import_aware(self):
        source = (ROOT / "source/FNFAssets.hx").read_text()
        resolver = extract_method(source, "public static function resolveCaseInsensitivePath(")
        disk_resolver = extract_method(source, "static function resolveDiskPath(")
        in_scope = extract_method(source, "public static function isInScope(")
        self.assertIn("FNFAssets.resolveCaseInsensitivePath(candidate)",
                      (ROOT / "source/CoolUtil.hx").read_text())
        self.assertNotIn(".contains(Path.normalize(Main.cwd))", source)

        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;

class Assets {{
  public static var existsCalls:Int = 0;
  public static function exists(path:String):Bool {{
    existsCalls++;
    return path == "assets/images/custom_chars/custom_chars.jsonc";
  }}
}}
class Main {{
  public static var cwd:String;
}}
class FNFAssets {{
  static var caseResolvedPaths:Map<String, String> = new Map<String, String>();
{disk_resolver}
{resolver}
{in_scope}
  static function main() {{
    Main.cwd = Sys.getCwd();
    FileSystem.createDirectory("assets");
    FileSystem.createDirectory("assets/music");
    FileSystem.createDirectory("assets/images");
    FileSystem.createDirectory("assets/images/custom_chars");
    sys.io.File.saveContent("assets/music/Chaos_Inst.ogg", "audio");
    sys.io.File.saveContent("assets/images/custom_chars/custom_chars.jsonc", "disk registry");
    var resolved = resolveCaseInsensitivePath("assets/music/chaos_inst.ogg");
    if (resolved == null || Path.withoutDirectory(resolved) != "Chaos_Inst.ogg")
      throw "mixed-case donor audio did not resolve: " + resolved;
    if (Assets.existsCalls != 0)
      throw "a dynamic case-fold hit probed the OpenFL asset index";
    var embeddedShadow = resolveCaseInsensitivePath("assets/images/custom_chars/custom_chars.jsonc");
    if (embeddedShadow == null || Path.withoutDirectory(embeddedShadow) != "custom_chars.jsonc")
      throw "disk registry was not preferred over embedded manifest";
    if (Assets.existsCalls != 0)
      throw "an exact disk hit probed the OpenFL asset index";
    sys.io.File.saveContent("assets/music/Icon.ogg", "one");
    sys.io.File.saveContent("assets/music/iCON.ogg", "two");
    if (resolveCaseInsensitivePath("assets/music/ICON.ogg") != null)
      throw "ambiguous folded asset was guessed";
    if (resolveCaseInsensitivePath("../outside/Chaos_Inst.ogg") != null)
      throw "out-of-root asset escaped scope";
    var sibling = Path.normalize(Sys.getCwd() + "-evil/asset.ogg");
    if (resolveCaseInsensitivePath(sibling) != null)
      throw "path-prefix sibling escaped scope";
    FileSystem.deleteFile("assets/music/Chaos_Inst.ogg");
    if (resolveCaseInsensitivePath("assets/music/chaos_inst.ogg") != null)
      throw "stale positive case-fold cache survived deletion";
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "FNFAssets.hx"
            path.write_text(fixture)
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "FNFAssets", "--interp"],
                # Keep the fixture's relative asset tree isolated.  Running
                # from the repository root makes the standalone probe write
                # its synthetic registry into the live game assets; later
                # importer tests then (correctly) see that bogus registry and
                # lose the native character fallback.
                cwd=folder,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_text_read_keeps_disk_scope_and_packaged_asset_rules(self):
        source = (ROOT / "source/FNFAssets.hx").read_text()
        disk_resolver = extract_method(source, "static function resolveDiskPath(")
        in_scope = extract_method(source, "public static function isInScope(")
        get_text = extract_method(source, "public static function getText(")
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
class Assets {{
  public static var existsCalls:Int = 0;
  public static function exists(path:String):Bool {{
    existsCalls++;
    return path == "../embedded.txt";
  }}
  public static function getPath(_path:String):String return "embedded.txt";
  public static function getText(_path:String):String return "packaged asset";
}}
class ImportOverlayResolver {{
  public static function applyText(_path:String, content:String):String return content;
}}
class Main {{ public static var cwd:String; }}
class FNFAssets {{
  static var caseResolvedPaths:Map<String, String> = new Map<String, String>();
{disk_resolver}
{in_scope}
{get_text}
  static function main() {{
    Main.cwd = Sys.getCwd();
    File.saveContent("dynamic.txt", "runtime file");
    if (getText("dynamic.txt") != "runtime file")
      throw "runtime disk read failed";
    if (Assets.existsCalls != 0)
      throw "exact runtime read queried the OpenFL manifest";
    if (getText("../embedded.txt") != "packaged asset")
      throw "out-of-root packaged asset was rejected";
    var rejected = false;
    try getText("../outside.txt") catch (error:Dynamic)
      rejected = Std.string(error).indexOf("out of scope") >= 0;
    if (!rejected) throw "out-of-root non-asset read was not rejected";
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "FNFAssets.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "FNFAssets", "--interp"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exists_resolves_each_miss_once_and_rechecks_after_import(self):
        source = (ROOT / "source/FNFAssets.hx").read_text()
        exists = extract_method(source, "static public function exists(")
        fixture = f'''import sys.FileSystem;
import sys.io.File;
enum Extensions {{ None; Json; Hscript; }}
class Assets {{
  public static var embedded:Bool = false;
  public static function exists(_path:String):Bool return embedded;
}}
class CoolUtil {{
  public static var JSON_EXT:Array<String> = ["json"];
  public static var HSCRIPT_EXT:Array<String> = ["hscript"];
}}
class FNFAssets {{
  static var resolution:Null<String> = null;
  static var resolverCalls:Int = 0;
  static function resolveDiskPath(_id:String):Null<String> {{
    resolverCalls++;
    return resolution;
  }}
  static function isInScope(_id:String):Bool return true;
  static function existsAmbig(_ids:Array<String>, _extensions:Array<String>):String return "";
{exists}
  static function main() {{
    if (exists("assets/images/custom_ui/ui_packs/normal/multiNotePresets.json"))
      throw "missing note preset resolved as present";
    if (resolverCalls != 1) throw "missing path was resolved " + resolverCalls + " times";

    File.saveContent("late-import.json", "{{}}");
    resolution = "late-import.json";
    resolverCalls = 0;
    if (!exists("late-import.json")) throw "newly imported file was not discovered";
    if (resolverCalls != 1) throw "successful path used repeated resolver walks";

    resolution = null;
    Assets.embedded = true;
    resolverCalls = 0;
    if (!exists("embedded.json")) throw "embedded fallback was lost";
    if (resolverCalls != 1) throw "embedded fallback repeated the native resolver";
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "FNFAssets.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-main", "FNFAssets", "--interp"],
                cwd=folder,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
