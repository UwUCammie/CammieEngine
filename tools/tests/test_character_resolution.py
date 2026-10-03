"""Missing imported characters must not bypass fallback on the victory screen."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
import os

ROOT = Path(__file__).resolve().parents[2]


def method(source, marker):
    start = source.index(marker)
    return source[start:source.index('\n\t}', start) + 3]


class CharacterResolutionTest(unittest.TestCase):
    def test_interpreter_uses_same_fallback_as_gameplay(self):
        source = (ROOT / 'source/Character.hx').read_text()
        no_gf = method(source, '\tpublic static function isNoGirlfriend(')
        exists = method(source, '\tpublic static function characterExists(')
        interp = method(source, '\tpublic static function getAnimInterp(')
        typedef_start = source.index('typedef CharacterProgramCacheEntry = {')
        typedef_end = source.index('\nclass Character extends', typedef_start)
        cache_start = source.index('\tstatic var characterProgramCache:')
        cache_end = source.index('\n\tpublic var animOffsets', cache_start)
        cache = source[cache_start:cache_end]
        fixture = '''import sys.FileSystem;
import hscript.Interp;
import hscript.Expr;
using StringTools;
enum Extension {Hscript;}
class CoolUtil {public static function parseJson(s:String):Dynamic {
 if(s==null) throw "parseJson: null input";
 return haxe.Json.parse(s);
}}
class FNFAssets {
 public static var entries:Dynamic={dad:{like:"dad"},valid:{like:"valid"},alias:{like:"valid"},broken:{like:"missing"}};
 public static function getJson(p:String):String {
  if(p=="assets/images/custom_chars/custom_chars")return haxe.Json.stringify(entries);
  return null;
 }
 public static function exists(p:String,?ext:Extension):Bool return p=="assets/images/custom_chars/dad" || p=="assets/images/custom_chars/valid";
 public static function getHscript(p:String):String return 'isPixel = false;';
 public static function getText(p:String):String return 'isPixel = false;';
}
class PluginManager {public static function createSimpleInterp()return new Interp();}
class EngineCompat {public static function rewriteLegacyAssetPaths(source:String):String return source;}
class PlayState {
 public static var universalVar:Map<String,Dynamic>=[];
 public static var instance:PlayState = null;
 public function hasPendingHxcCharacterVisual(name:String):Bool return false;
}
class Song {
 public static function resolveCharacterVisualForCurrentSong(name:String):Dynamic
  return resolveCharacterVisual(name);
 public static function resolveCharacterVisual(name:String):Dynamic {
  if(name=="dad") return {complete:true,selectedRegistryName:"dad",implementationName:"dad",assetName:"dad",assetRootPath:"assets/images/custom_chars/dad",implementationPath:"assets/images/custom_chars/dad.hscript"};
  if(name=="valid") return {complete:true,selectedRegistryName:"valid",implementationName:"valid",assetName:"valid",assetRootPath:"assets/images/custom_chars/valid",implementationPath:"assets/images/custom_chars/valid.hscript"};
  if(name=="alias") return {complete:true,selectedRegistryName:"alias",implementationName:"valid",assetName:"valid",assetRootPath:"assets/images/custom_chars/valid",implementationPath:"assets/images/custom_chars/valid.hscript"};
  if(name=="miku") return {complete:true,selectedRegistryName:"mikuv2",implementationName:"miku",assetName:"mikuv2",assetRootPath:"assets/images/custom_chars/mikuv2",implementationPath:"assets/images/custom_chars/miku.hscript"};
  return {complete:false,requested:name,diagnosticCode:"character-asset-missing",diagnostic:"missing"};
 }
}
''' + source[typedef_start:typedef_end] + '''
class Character {
 static var Level_NotAHoe=0;static var Level_Boogie=0;static var Level_Sadness=0;static var Level_Sing=0;
 public static function reportResolution(resolution:Dynamic):Void {}
''' + cache + '\n' + no_gf + '\n' + exists + '\n' + interp + '''
 static function main() {
  for (name in ["playableex", "missing", "broken", "valid", "alias", "miku"]) {
   var i=getAnimInterp(name);
   var expected=name;
   if(i.variables.get("charName")!=expected) throw 'Wrong character: '+name;
   var asset=name=="alias" ? "valid" : (name=="miku" ? "mikuv2" : (name!="valid" && name!="dad" ? "dad" : expected));
   if(i.variables.get("hscriptPath")!='assets/images/custom_chars/'+asset+'/') throw "Wrong asset path";
  }
  if(characterExists("broken"))throw "Missing implementation must not count as playable";
  if(!characterExists("alias"))throw "Shared-folder alias must be playable";
 }
}
class FlxColor {public static var CYAN=0;}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            p = Path(folder)
            for name in ['dad', 'valid', 'broken']:
                (p / 'assets/images/custom_chars' / name).mkdir(parents=True)
            (p / 'Character.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                     '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                                     '-main', 'Character', '--interp'], cwd=folder,
                                    env={**os.environ, 'TMPDIR': str(ROOT / 'tmp')},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_victory_uses_loaded_player_interpreter(self):
        source = (ROOT / 'source/VictoryLoopState.hx').read_text()
        self.assertNotIn('Character.getAnimInterp(p1)', source)
        self.assertIn('bf.usesPixelAssets()', source)


if __name__ == '__main__':
    unittest.main()
