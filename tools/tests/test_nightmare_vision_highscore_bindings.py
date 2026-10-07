"""Run the real source Highscore adapter through owner-local Iris scopes."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"


class NightmareVisionHighscoreBindingsTest(unittest.TestCase):
    def test_imported_static_maps_reflection_persistence_and_owner_release(self):
        fixture = r'''
import haxe.ds.StringMap;

class OwnerSave {
 public var fields:Map<String,Dynamic> = new Map();
 public var writes:Array<String> = [];
 public var reads:Array<String> = [];
 public var flushes:Int = 0;
 public function new() {}
 public function getField(name:String):Dynamic {
  reads.push(name);
  var value = fields.get(name);
  return value == null ? null : haxe.Json.parse(haxe.Json.stringify(value));
 }
 public function setField(name:String, value:Dynamic):Dynamic {
  writes.push(name);
  fields.set(name, haxe.Json.parse(haxe.Json.stringify(value)));
  return value;
 }
 public function flush():Void flushes++;
}
class Guard { public var active:Bool = true; public function new() {} }
class Captured { public var getter:Dynamic; public function new() {} }

class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var parser = new NightmareVisionScriptParser();
  var saveA = new OwnerSave();
  var saveB = new OwnerSave();
  var scoresA = new NightmareVisionHighscore(saveA,
   function(song:String):String return StringTools.replace(song, '/', '_'),
   function(diff:Int):String return ['Easy', 'Normal', 'Hard'][diff]);
  var scoresB = new NightmareVisionHighscore(saveB,
   function(song:String):String return StringTools.replace(song, '/', '_'),
   function(diff:Int):String return ['Easy', 'Normal', 'Hard'][diff]);
  var guardA = new Guard();
  var guardB = new Guard();
  var capturedA = new Captured();
  var interpA = new NightmareVisionScriptInterp(capturedA);
  var interpB = new NightmareVisionScriptInterp();
  var requireA:Void->Void = function():Void if (!guardA.active) throw 'owner A released';
  var requireB:Void->Void = function():Void if (!guardB.active) throw 'owner B released';
  NightmareVisionHighscoreBindings.install(interpA, scoresA, requireA);
  NightmareVisionHighscoreBindings.install(interpB, scoresB, requireB);
  var scopeA = interpA.sourceClassScope();
  var sameNativeType:Bool = interpA.importBindings.get('funkin.data.Highscore')
   == interpB.importBindings.get('funkin.data.Highscore');
  var apiSource = 'import Type; import Reflect; import funkin.data.Highscore as ScoreApi;\n'
   + 'resolvedClass=Type.resolveClass("funkin.data.Highscore");\n'
   + 'resolvedName=Type.getClassName(resolvedClass);\n'
   + 'resolvedScore=ScoreApi.getScore("Round Trip",2);\n'
   + 'ScoreApi.saveScore("Round Trip",321,2,0.8125);\n'
   + 'ScoreApi.songScores.set("Direct-Hard",44); liveBeforeReplace=ScoreApi.songScores.get("Direct-Hard");\n'
   + 'replacement.set("Assigned-Hard",8);\n'
   + 'Reflect.setProperty(ScoreApi,"songScores",replacement);\n'
   + 'ScoreApi.saveScore("Assigned",19,2,0.5);\n'
   + 'privateSetter=Reflect.field(ScoreApi,"setScore");\n'
   + 'Reflect.callMethod(ScoreApi,privateSetter,["Reflected-Normal",27]);\n'
   + 'getter=ScoreApi.getScore;';
  var replacement = new StringMap<Int>();
  replacement.set('Round Trip-Hard', 321);
  interpA.variables.set('replacement', replacement);
  interpA.execute(parser.parseString(apiSource, 'highscore-owner-A'));
  check(interpA.variables.get('resolvedClass') == NightmareVisionHighscore
   && interpA.variables.get('resolvedName') == 'funkin.data.Highscore',
   'the Iris import and Type reflection facade must resolve the owner-bound native class');
  check(interpA.variables.get('resolvedScore') == 0 && saveA.fields.exists('songScores'),
   'static method lookup must delegate to the selected owner score service');
  check(scoresA.songScores.get('Round Trip-Hard') == 321
   && scoresA.songRating.get('Round Trip-Hard') == 0.8125,
   'imported static methods must persist scores and fractional ratings through the owner save: '
    + scoresA.songScores.get('Round Trip-Hard') + '/' + scoresA.songRating.get('Round Trip-Hard')
    + ' writes=' + saveA.writes.join(','));
  check(interpA.variables.get('liveBeforeReplace') == 44,
   'the imported public map must remain a live mutable owner map');
  check(scoresA.songScores.get('Assigned-Hard') == 19 && !scoresA.songScores.exists('Direct-Hard'),
   'Reflect.setProperty on the imported static map must replace the owner map through its binding');
  check(scoresA.songScores.get('Reflected-Normal') == 27
   && interpA.variables.get('privateSetter') != null,
   'private source setters must be callable through the interpreter reflection facade');
  check(Reflect.isFunction(capturedA.getter), 'the bound method must be capturable by the script parent');

  // The same real native Highscore class is scoped to a distinct score service
  // for each imported owner. Neither the static map nor writes may bleed over.
  interpB.execute(parser.parseString('import funkin.data.Highscore as ScoreApi; '
   + 'ScoreApi.saveScore("Twin",222,0); twin=ScoreApi.getScore("Twin",0);', 'highscore-owner-B'));
  interpA.execute(parser.parseString('import funkin.data.Highscore as ScoreApi; '
   + 'ScoreApi.saveScore("Twin",111,0); twin=ScoreApi.getScore("Twin",0);', 'highscore-owner-A-second'));
  check(sameNativeType && scoresA.getScore('Twin', 0) == 111 && scoresB.getScore('Twin', 0) == 222,
   'two imported owners must retain one native class identity with independent score state');

  // Reconstruct the highscore service over serialized save fields and load it
  // via an Iris static call, including its live typed Maps.
  var restored = new NightmareVisionHighscore(saveA,
   function(song:String):String return StringTools.replace(song, '/', '_'),
   function(diff:Int):String return ['Easy', 'Normal', 'Hard'][diff]);
  var restoredInterp = new NightmareVisionScriptInterp();
  NightmareVisionHighscoreBindings.install(restoredInterp, restored, function():Void {});
  restoredInterp.execute(parser.parseString('import funkin.data.Highscore as ScoreApi; '
   + 'ScoreApi.load(); restoredScore=ScoreApi.getScore("Round Trip",2); '
   + 'restoredRating=ScoreApi.getRating("Round Trip",2);', 'highscore-roundtrip'));
  check(restoredInterp.variables.get('restoredScore') == 321
   && restoredInterp.variables.get('restoredRating') == 0.8125
   && Std.isOfType(restored.songScores, StringMap)
   && Std.isOfType(restored.songRating, StringMap),
   'Iris Highscore.load must restore JSON fields into live typed score and rating maps');

  // The active-owner guard protects future static access. Existing reflected
  // method handles still point at the real score instance, whose release
  // boundary rejects calls after owner teardown.
  guardA.active = false;
  var inactiveReadRejected = false;
  try interpA.execute(parser.parseString('inactiveMap=ScoreApi.songScores;', 'inactive-owner-read'))
  catch (_:Dynamic) inactiveReadRejected = true;
  check(inactiveReadRejected, 'static reads must enforce the captured owner active check');
  guardA.active = true;
  scoresA.release();
  var releasedMethodRejected = false;
  try Reflect.callMethod(scoresA, capturedA.getter, ['Round Trip', 2])
  catch (_:Dynamic) releasedMethodRejected = true;
  check(releasedMethodRejected, 'captured Highscore methods must reject use after the owner service is released');

  interpA.release();
  check(!scopeA.hasRuntimeClass('funkin.data.Highscore')
   && !scopeA.hasBinding(NightmareVisionHighscore, 'songScores')
   && !interpA.importBindings.exists('funkin.data.Highscore'),
   'releasing an interpreter must release its runtime class, static bindings, and import route');
  check(scoresB.getScore('Twin', 0) == 222 && guardB.active,
   'releasing one imported owner must leave another owner active');
  interpB.release();
  restoredInterp.release();
  scoresB.release();
  restored.release();
 }
}
'''
        runtime_stub = r'''
class HxcCompatRuntime {
 static var targets:Array<Dynamic> = [];
 static var values:Array<Int> = [];
 static function indexOf(target:Dynamic):Int return targets.indexOf(target);
 public static function clear():Void { targets.resize(0); values.resize(0); }
 public static function getZIndex(target:Dynamic):Dynamic {
  var index = indexOf(target);
  return index < 0 ? 0 : values[index];
 }
 public static function setZIndex(target:Dynamic, value:Dynamic, ?op:String='='):Dynamic {
  var current = getZIndex(target);
  var next = Std.int(Std.parseFloat(Std.string(value)));
  switch (op) {
   case '+=': next = current + next;
   case '-=': next = current - next;
   case '*=': next = current * next;
   case '/=': if (next != 0) next = Std.int(current / next);
  }
  var index = indexOf(target);
  if (index < 0) { targets.push(target); values.push(next); }
  else values[index] = next;
  return next;
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="nmv-highscore-bindings-", dir=ROOT / "tmp") as scratch:
            write_flixel_point_stub(Path(scratch))
            (Path(scratch) / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            (Path(scratch) / "HxcCompatRuntime.hx").write_text(runtime_stub, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", scratch,
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
