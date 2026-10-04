"""Resolve NMV healthicon aliases and direct strips from the selected owner."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class NightmareVisionHealthIconIdentityTest(unittest.TestCase):
    def test_owner_character_ids_resolve_authored_icon_ids_and_keep_source_scope(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/HealthIcon.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "static function ownerEngineForIcon(",
            "static function nightmareVisionHealthIcon(",
            "static function iconRequestForOwner(",
            "static function scopedCodenameIconPath(",
            "static function scopedCodenameIconFallbackPath(",
        ))
        fixture = r'''
class ImportEngine {
 public static inline var NIGHTMARE_VISION="Nightmare Vision";
 public static inline var V_SLICE="V-Slice";
}
class Character {
 public static function isNoGirlfriend(name:String):Bool
  return name=="no-gf" || name=="nogf" || name=="no_gf" || name=="NO GF";
}
class PlayState { public static var SONG:Dynamic={compatStorageFolder:"selected-chart"}; }
class Song {
 public static var engines:Map<String,String>=new Map();
 public static function storageFolder(chart:Dynamic):String return chart.compatStorageFolder;
 public static function characterOwnerEngineForSong(song:String):String
  return engines.exists(song)?engines.get(song):"";
 public static function characterRootForSong(song:String,?engine:String):String
  return song=="selected-chart"?"/owners/nmv":(song=="menu-row"?"/owners/menu":"");
 public static function currentCharacterRoot():String return "/owners/nmv";
}
class NightmareVisionCharacterData {
 public static var definitions:Map<String,Dynamic>=new Map();
 public static function load(root:String,name:String):Dynamic
  return definitions.get(root+"/"+name);
}
class FNFAssets {
 public static var files:Map<String,Bool>=new Map();
 public static function exists(path:String):Bool return files.exists(path);
}
class Main {
''' + methods + r'''
 static function iconRequestForCharacter(char:String,ownerRoot:String,gameplayIcon:Bool):Dynamic {
  if(gameplayIcon && Character.isNoGirlfriend(char))
   return {name:"face",ownerRoot:"",hidden:true};
  return {name:char,ownerRoot:ownerRoot,hidden:false};
 }
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  Song.engines.set("selected-chart",ImportEngine.NIGHTMARE_VISION);
  Song.engines.set("menu-row",ImportEngine.NIGHTMARE_VISION);
  NightmareVisionCharacterData.definitions.set("/owners/nmv/vedplayable",
   {healthicon:"guyy",healthbar_colour:-704660});
  NightmareVisionCharacterData.definitions.set("/owners/nmv/mack",
   {healthicon:"mack",healthbar_colour:-13190524});
  NightmareVisionCharacterData.definitions.set("/owners/nmv/missing-icon",{});
  NightmareVisionCharacterData.definitions.set("/owners/nmv/invalid-icon",{healthicon:7});
  NightmareVisionCharacterData.definitions.set("/owners/nmv/blank-icon",{healthicon:""});

  check(ownerEngineForIcon(null,true)==ImportEngine.NIGHTMARE_VISION,
   "gameplay icon engine lookup did not use selected chart storage");
  check(ownerEngineForIcon("menu-row",false)==ImportEngine.NIGHTMARE_VISION,
   "explicit menu owner did not retain its own engine identity");
  check(ownerEngineForIcon(null,false)=="",
   "an unowned menu icon borrowed the active gameplay engine");

  var ved=iconRequestForOwner("vedplayable","/owners/nmv",
   ImportEngine.NIGHTMARE_VISION,true);
  check(ved.name=="guyy" && ved.ownerRoot=="/owners/nmv" && !ved.hidden,
   "NMV chart character did not select its authored healthicon in the selected owner");
  FNFAssets.files.set("/owners/nmv/images/icons/icon-guyy.png",true);
  check(scopedCodenameIconFallbackPath(null,ved.name,ved.ownerRoot)
   =="/owners/nmv/images/icons/icon-guyy.png",
   "resolved NMV healthicon did not reach its selected-owner direct strip");

  var switched=iconRequestForOwner("guyy","/owners/nmv",
   ImportEngine.NIGHTMARE_VISION,true);
  check(switched.name=="guyy" && switched.ownerRoot=="/owners/nmv",
   "a later switchAnim using the resolved healthicon id changed identity or owner");
  var mack=iconRequestForOwner("mack","/owners/nmv",
   ImportEngine.NIGHTMARE_VISION,false);
  check(mack.name=="mack" && !mack.hidden,
   "the NMV source icon matching its character id stopped resolving");

  check(iconRequestForOwner("missing-icon","/owners/nmv",
   ImportEngine.NIGHTMARE_VISION,true).name=="face",
   "a missing NMV healthicon did not use CharacterData's template face");
  check(iconRequestForOwner("invalid-icon","/owners/nmv",
   ImportEngine.NIGHTMARE_VISION,true).name=="face",
   "a malformed NMV healthicon did not use the template face");
  check(iconRequestForOwner("blank-icon","/owners/nmv",
   ImportEngine.NIGHTMARE_VISION,true).name=="",
   "an authored blank NMV healthicon was not preserved");

  check(iconRequestForOwner("vedplayable","/owners/other","Psych",true).name=="vedplayable",
   "a non-NMV owner borrowed an NMV character alias");
  check(iconRequestForOwner("vedplayable","/owners/other",
   ImportEngine.NIGHTMARE_VISION,true).name=="vedplayable",
   "an NMV healthicon definition leaked across owner roots");
  var sentinel=iconRequestForOwner("no-gf","/owners/nmv",
   ImportEngine.NIGHTMARE_VISION,true);
  check(sentinel.hidden && sentinel.name=="face" && sentinel.ownerRoot=="",
   "the shared NMV alias resolver overrode the hidden gameplay sentinel");
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="nmv-health-icon-", dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(scratch), "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("iconRequestForOwner(curCharacter, iconOwnerRoot, iconOwnerEngine, isNormal)", source)
        self.assertIn("iconOwnerEngine = ownerEngineForIcon(ownerSong, isnormal)", source)


if __name__ == "__main__":
    unittest.main()
