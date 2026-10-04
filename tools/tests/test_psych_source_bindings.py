"""Execute the Psych source frame adapters against small host doubles."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, ROOT


def extract(source: str, name: str) -> str:
    match = re.search(r"\bfunction\s+" + re.escape(name) + r"\s*\(", source)
    if match is None:
        raise AssertionError(name)
    brace = source.index("{", match.end())
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():index + 1]
    raise AssertionError(f"unclosed {name}")


class PsychSourceBindingTest(unittest.TestCase):
    def test_owner_frames_and_symbol_indices(self):
        haxe = ROOT / "source/PsychSourceBindings.hx"
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        methods = "\n".join(extract(haxe.read_text(), name) for name in (
            "psychObject", "loadFrames", "loadMultipleFrames", "addAnimationBySymbolIndices",
        ))
        fixture = r'''class FlxAtlasFrames {
 public var parent:String;
 public var names:Array<String> = [];
 public function new(parent:String) this.parent=parent;
 public function addAtlas(other:FlxAtlasFrames, overwriteHash:Bool=false):FlxAtlasFrames {
  for(name in other.names) if(overwriteHash || !names.contains(name)) names.push(name);
  return this;
 }
}
class FlxSprite { public var frames:FlxAtlasFrames; public var anim:Dynamic; public function new() {} }
class FixtureAnimateController {
 public var curSymbol:Dynamic=null;
 public var call:Array<Dynamic>=null;
 public function new() {}
 public function addBySymbolIndices(name:String,symbol:String,indices:Array<Int>,framerate:Float,loop:Bool,x:Float,y:Float):Void
  call=[name,symbol,indices,framerate,loop,x,y];
}
class FixtureHost {
 public var objects:Map<String,Dynamic>=[];
 public var calls:Array<Array<Dynamic>>=[];
 public var played:Array<Dynamic>=null;
 public function new() {}
 public function compatFindObject(name:Dynamic):Dynamic return objects.get(Std.string(name));
 public function compatGetProperty(_name:Dynamic):Dynamic return null;
 public function compatPsychOwnerFallbackAllowed(_owner:String,reference:String):Bool
  return reference != null && !StringTools.startsWith(reference,'assets/imported_mods/other/');
 public function compatPsychAssetKey(value:String,extension:String):String
  return StringTools.endsWith(value.toLowerCase(),extension) ? value.substr(0,value.length-extension.length) : value;
 public function compatPsychPathCall(_owner:String,method:String,args:Array<Dynamic>):Dynamic {
  calls.push([method,args[0]]);
  if(args[0]=='missing') return null;
  var frames=new FlxAtlasFrames(Std.string(args[0]));
  frames.names=[Std.string(args[0])];
  return frames;
 }
 public function compatPlayAnim(tag:String,name:String,forced:Bool):Bool {played=[tag,name,forced];return true;}
}
class PsychSourceBindingsFixture {
 var host:FixtureHost;
 var ownerRoot:String='assets/imported_mods/selected';
 public function new(host:FixtureHost) this.host=host;
 __METHODS__
 static function main() {
  var host=new FixtureHost();
  var sprite=new FlxSprite(); host.objects.set('sprite',sprite);
  var bridge=new PsychSourceBindingsFixture(host);
  bridge.loadFrames('sprite','ui/menu','Sparrow Atlas');
  if(sprite.frames==null || sprite.frames.parent!='ui/menu') throw 'spriteType did not select the Psych Sparrow atlas';
  if(host.calls.length!=1 || host.calls[0][0]!='getSparrowAtlas') throw 'Sparrow alias mapped to the wrong Paths loader';
  bridge.loadFrames('sprite','assets/imported_mods/other/ui/menu','auto');
  if(host.calls.length!=1) throw 'cross-owner frame reference reached the path facade';
  bridge.loadMultipleFrames('sprite',['base','extra']);
  if(sprite.frames==null || sprite.frames.names.join(',')!='base,extra') throw 'multi-atlas merge lost Psych frame order';
  var animate=new FlxSprite(); var controller=new FixtureAnimateController(); animate.anim=controller; host.objects.set('anim',animate);
  if(!bridge.addAnimationBySymbolIndices('anim','idle','Idle',[2,4],24,false,3,5)) throw 'valid symbol indices were rejected';
  if(controller.call[2].join(',')!='2,4' || controller.call[5]!=3 || controller.call[6]!=5) throw 'symbol arguments changed';
  if(host.played==null || host.played[1]!='idle') throw 'first symbol animation did not start';
  controller.curSymbol='Idle';
  if(!bridge.addAnimationBySymbolIndices('anim','loop','Idle','1, 6, -2',30,true,1,2)) throw 'comma-separated symbol indices were rejected';
  if(controller.call[2].join(',')!='1,6,-2' || host.played[1]!='idle') throw 'indices parsing or active-symbol guard changed';
  Sys.println('OK');
 }
}'''.replace("__METHODS__", methods)
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "PsychSourceBindingsFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "PsychSourceBindingsFixture"],
                cwd=folder, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_score_aliases_write_through_and_hits_select_the_active_ledger(self):
        source = (ROOT / "source/PsychSourceBindings.hx").read_text(encoding="utf-8")
        methods = "\n".join(extract(source, name) for name in (
            "addScore", "setScore", "addMisses", "setMisses", "addHits", "setHits",
            "scorePropertyAlias", "readScorePropertyAlias", "writeScorePropertyAlias",
        ))
        fixture = r'''class PlayState {
 public static var misses:Int=0;
 public static var sicks:Int=1;
 public static var goods:Int=2;
 public static var bads:Int=3;
 public static var shits:Int=4;
}
class EngineCompat {
 public static function propertyPath(path:Dynamic):String return path == null ? '' : Std.string(path);
}
class FixtureHost {
 public var songScore:Int=0;
 public var songHits:Int=0;
 public var psychHitsAdjustment:Int=0;
 public var ledger:Bool=false;
 public var changes:Int=0;
 public function new() {}
 public function sourceScoreLedgerActive():Bool return ledger;
 public function psychScoreChanged():Void changes++;
 public function compatGetProperty(_path:Dynamic):Dynamic return null;
 public function compatSetProperty(_path:Dynamic,_value:Dynamic):Dynamic return null;
}
class PsychSourceBindingsFixture {
 var host:FixtureHost;
 public function new(host:FixtureHost) this.host=host;
__METHODS__
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  PlayState.misses=0;
  var host=new FixtureHost();
  var bindings=new PsychSourceBindingsFixture(host);
  bindings.addScore(5); bindings.setScore(31);
  bindings.addMisses(2); bindings.setMisses(4);
  check(host.songScore==31 && PlayState.misses==4,
   'score and miss aliases should write through to their host counters');

  bindings.addHits(3);
  check(host.songHits==0 && host.psychHitsAdjustment==3,
   'native fallback should preserve Psych hits adjustment');
  bindings.setHits(20);
  check(host.songHits==0 && host.psychHitsAdjustment==10,
   'native setHits should offset the existing rating categories');

  host.ledger=true;
  bindings.addHits(2); bindings.setHits(17);
  check(host.songHits==17 && host.psychHitsAdjustment==10,
   'source ledger add/set hits should write songHits without altering fallback state');

  check(bindings.scorePropertyAlias('score')=='score'
    && bindings.scorePropertyAlias('songScore')=='score'
    && bindings.scorePropertyAlias('game.score')=='',
   'score aliases should match only root paths');
  check(bindings.readScorePropertyAlias('score')==31
    && bindings.readScorePropertyAlias('misses')==4
    && bindings.readScorePropertyAlias('hits')==17,
   'property reads should use the same score, miss, and active-hit ledger');
  bindings.writeScorePropertyAlias('score',52);
  bindings.writeScorePropertyAlias('misses',6);
  bindings.writeScorePropertyAlias('hits',8);
  check(host.songScore==52 && PlayState.misses==6 && host.songHits==8,
   'property writes should update their corresponding live source counters');
  host.ledger=false;
  bindings.writeScorePropertyAlias('hits',12);
  check(bindings.readScorePropertyAlias('hits')==12 && host.songHits==8,
   'native property writes should keep using the Psych presentation adjustment');
  check(host.changes==12, 'each writable alias should announce one score change');
 }
}'''.replace("__METHODS__", methods)

        # These installed functions are the writable Psych-facing aliases.
        for name in ("addScore", "setScore", "addMisses", "setMisses", "addHits", "setHits"):
            self.assertIn(f"variables.set('{name}', function(value:Int = 0):Void {name}(value));", source)
        self.assertIn("host.sourceScoreLedgerActive()", source)
        self.assertIn("variables.set('getProperty'", source)
        self.assertIn("variables.set('setProperty'", source)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "PsychSourceBindingsFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "PsychSourceBindingsFixture"],
                cwd=folder, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
