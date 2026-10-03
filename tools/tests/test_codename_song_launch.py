"""Codename menu chart loading stays in the selected imported owner."""
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


class CodenameSongLaunchTest(unittest.TestCase):
    def test_static_loader_preserves_difficulty_and_selected_owner(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/PlayState.hx").read_text()
        loader = extract_method(source, "@:keep public static function __loadSong(")
        fixture = r'''
using StringTools;
class Song {
 public static var chart:String=""; public static var folder:String=""; public static var fail=false;
 public static function loadFromJson(input:String, storage:String):Dynamic {
  chart=input; folder=storage;
  if(fail) throw "missing requested difficulty";
  return {song:input, compatStorageFolder:storage};
 }
}
class DifficultyManager {
 public static function getDifficultyNames():Array<String> return ["easy","Normal","hard"];
 public static function getDiffEnding(index:Int):String return index==1 ? "" : "-"+["easy","Normal","hard"][index];
}
class CodenameScriptDiscovery {public static function safeName(value:String):Bool
 return value!="" && value.indexOf("/")<0 && value!="..";}
class CodenameModRuntime {public static var owner="assets/imported_mods/codename-fnas-1234567890";
 public static function activeRoot():String return owner;}
class CodenameSongLaunch {public static var selectedOwner="";
 public static function resolveStorageFolder(song:String, owner:String):String {
  selectedOwner=owner; return "better-clone--codename-fnas-1234567890";
 }}
class RuntimeSmokeHarness {public static function enabled():Bool return false;
 public static function fail(_:String,_:String):Void throw "unexpected smoke failure";}
class LoadingState {public static var menu=false;
 public static function loadAndSwitchState(_:Dynamic):Void menu=true;}
class MainMenuState {public function new() {}}
class Main {
 static var SONG:Dynamic=null;
 static var storyDifficulty=0;
 static var storyDifficultyText="";
''' + loader + r'''
''' + extract_method(source, "static function guardMissingSongBeforeCreate(") + r'''
 static function main():Void {
  __loadSong("Better-Clone", "nOrMaL");
  if(SONG==null || Song.chart!="better-clone" || Song.folder!="better-clone--codename-fnas-1234567890")
   throw "selected chart or owner folder was not loaded";
  if(CodenameSongLaunch.selectedOwner!=CodenameModRuntime.owner || storyDifficulty!=1
    || storyDifficultyText!="nOrMaL") throw "owner or source difficulty casing was lost";
  if(guardMissingSongBeforeCreate()) throw "valid chart was rejected";
  var caught=false;
  try __loadSong("Better-Clone", "Unknown") catch(_:Dynamic) caught=true;
  if(!caught || SONG!=null) throw "unknown difficulty left a stale chart";
  Song.fail=true; caught=false;
  try __loadSong("Better-Clone", "Normal") catch(_:Dynamic) caught=true;
  if(!caught || SONG!=null) throw "failed chart load left stale chart state";
  if(!guardMissingSongBeforeCreate() || !LoadingState.menu)
   throw "null chart did not recover to the native menu";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, newline='\n')
            completed = subprocess.run([*HAXE_COMMAND, "-cp", scratch, "--run", "Main"],
                                       cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        create = source[source.index("override public function create() {", source.index("var uiSmelly:TUI;")):]
        self.assertLess(create.index("guardMissingSongBeforeCreate()"), create.index("Sys.println('[dims]"))

    def test_storage_resolver_prefers_exact_owner_and_rejects_foreign_claim(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        owner = "assets/imported_mods/codename-fnas-1234567890"
        foreign = "assets/imported_mods/codename-other-abcdef0123"
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            data_root = Path(scratch) / "assets" / "data"
            canonical = data_root / "better-clone"
            qualified = data_root / "better-clone--codename-fnas-1234567890"
            canonical.mkdir(parents=True)
            qualified.mkdir(parents=True)
            (canonical / "compatScripts.json").write_text(json.dumps({
                "version": 1, "selectedRoot": foreign,
                "roots": [{"engine": "Codename Engine", "path": foreign}],
            }), newline='\n')
            (qualified / "importProvenance.json").write_text(json.dumps({
                "version": 1, "sourceFolder": "better-clone", "sourceEngine": "Codename Engine",
                "sourceOwner": owner, "destinationFolder": qualified.name,
            }), newline='\n')
            (Path(scratch) / "Main.hx").write_text(r'''
class Main {static function main():Void {
 var folder=CodenameSongLaunch.resolveStorageFolder("Better-Clone", "''' + owner + r'''", "''' + data_root.as_posix() + r'''");
 if(folder!="better-clone--codename-fnas-1234567890") throw "did not select qualified owner folder: "+folder;
 var rejected=false;
 try CodenameSongLaunch.resolveStorageFolder("Better-Clone", "assets/imported_mods/codename-unrelated-9999999999", "''' + data_root.as_posix() + r'''")
 catch(_:Dynamic) rejected=true;
 if(!rejected) throw "foreign owner's canonical folder was accepted";
}}
''', newline='\n')
            completed = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", scratch,
                                        "--run", "Main"], cwd=ROOT, capture_output=True,
                                       text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
