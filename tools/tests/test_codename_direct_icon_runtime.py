"""Keep a script-selected Codename icon inside the active import owner."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, name: str) -> str:
    start = source.index("\tstatic function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(name)


class CodenameDirectIconRuntimeTest(unittest.TestCase):
    def test_selected_owner_path_registry_fallback_and_invalid_ids(self):
        source = (ROOT / "source/HealthIcon.hx").read_text(encoding="utf-8")
        method = extract_method(source, "scopedCodenameIconPath")
        fallback_method = extract_method(source, "scopedCodenameIconFallbackPath")
        self.assertIn("scopedCodenameIconFallbackPath(customIconRoot", source)
        self.assertIn("FNFAssets.getBitmapData(directIcon)", source)
        self.assertIn("clampIconFrames([0, 1, 1, 0])", source)
        fixture = r'''class Song {
 public static var root:String="";
 public static function currentCharacterRoot():String return root;
}
class FNFAssets {
 public static var files:Map<String,Bool>=new Map();
 public static function exists(path:String):Bool return files.exists(path);
}
class Main {
''' + method + r'''
''' + fallback_method + r'''
 static function main():Void {
  Song.root="/owners/current";
  FNFAssets.files.set("/owners/current/images/icons/zephmoldy/icon.png",true);
  FNFAssets.files.set("/owners/current/images/icons/zeph/icon.png",true);
  FNFAssets.files.set("/owners/foreign/images/icons/zephmoldy/icon.png",true);
  FNFAssets.files.set("/owners/vslice/images/icons/icon-portrait-id.png",true);
  if(scopedCodenameIconPath("zephmoldy",null)
   != "/owners/current/images/icons/zephmoldy/icon.png")
   throw "current chart did not select its own direct icon";
  if(scopedCodenameIconPath("zephmoldy","/owners/foreign")
   != "/owners/foreign/images/icons/zephmoldy/icon.png")
   throw "explicit menu owner was ignored";
  if(scopedCodenameIconPath("portrait-id","/owners/vslice")
   != "/owners/vslice/images/icons/icon-portrait-id.png")
   throw "selected V-Slice owner icon-<id> path was ignored";
  // A selected-owner character may be registered but ship its Codename HUD
  // strip only under images/icons/<id>/icon.png.
  var registeredCharacterWithoutStrip="/owners/current/images/custom_chars/zeph/";
  if(scopedCodenameIconFallbackPath(registeredCharacterWithoutStrip,"zeph",null)
   != "/owners/current/images/icons/zeph/icon.png")
   throw "registered character blocked its selected-owner Codename icon";
  FNFAssets.files.set(registeredCharacterWithoutStrip+"icons.png",true);
  if(scopedCodenameIconFallbackPath(registeredCharacterWithoutStrip,"zeph",null)!=null)
   throw "direct icon replaced the registered character's custom icon strip";
  if(scopedCodenameIconFallbackPath(null,"zeph",null)
   != "/owners/current/images/icons/zeph/icon.png")
   throw "unregistered character lost its direct Codename icon";
  FNFAssets.files.remove(registeredCharacterWithoutStrip+"icons.png");
  Song.root="/owners/empty";
  if(scopedCodenameIconPath("zephmoldy",null)!=null)
   throw "direct icon leaked across owners";
  if(scopedCodenameIconFallbackPath(registeredCharacterWithoutStrip,"zeph",null)!=null)
   throw "registry fallback leaked a foreign-owner icon";
  for(invalid in ["../zephmoldy","sub/icon","icon.png",""])
   if(scopedCodenameIconPath(invalid,"/owners/current")!=null)
    throw "unsafe icon id was resolved: "+invalid;
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            path = Path(directory) / "Main.hx"
            path.write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", directory,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
