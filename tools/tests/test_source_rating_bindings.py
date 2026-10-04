"""Exercise owner-local NMV and Psych Rating imports through Iris."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class SourceRatingBindingsTest(unittest.TestCase):
    def test_nightmare_imports_live_owner_and_release(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
class Host {
 public var ratingsData:Array<SourceRating>;
 public var changes:Map<String, Int> = [];
 public function new(ratings:Array<SourceRating>) ratingsData = ratings;
 public function changeSourceRatingCounter(name:String, amount:Int):Void {
  changes.set(name, (changes.exists(name) ? changes.get(name) : 0) + amount);
 }
}

class OtherRating {
 public var name:String;
 public function new(name:String) this.name = name;
}

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;

 static function main():Void {
  var first = new SourceRating('first', 10);
  var last = new SourceRating('last', 20);
  var hostA = new Host([first, last]);
  var hostB = new Host([new SourceRating('other', 80), new SourceRating('fallback', 90)]);
  var current:Host = hostA;
  var active = true;
  var prefsA:Dynamic = {data:{customWindow:17}};
  var prefsB:Dynamic = {data:{customWindow:39}};
  var interpA = new NightmareVisionScriptInterp();
  var apiA = SourceRatingBindings.installNightmare(interpA, null, prefsA,
   function() return active, function():Dynamic return current);
  var parser = new NightmareVisionScriptParser();

  interpA.execute(parser.parseString(
   'import funkin.game.Rating as NVRating; import funkin.game.Rating; '
   + 'observed=Rating.judgeTime(5); observedNote=Rating.judgeNote(null,5); '
   + 'made=new Rating("custom"); aliasMade=new NVRating("alias"); '
   + 'qualifiedMade=new funkin.game.Rating("qualified");'));
  check(interpA.variables.get('observed') == first
   && interpA.variables.get('observedNote') == first,
   'imported judge methods did not use the live owner ratings list');
  var made:SourceRating = cast interpA.variables.get('made');
  var aliasMade:SourceRating = cast interpA.variables.get('aliasMade');
  var qualifiedMade:SourceRating = cast interpA.variables.get('qualifiedMade');
  check(made != null && made.hitWindow == 17 && aliasMade != null && qualifiedMade != null,
   'bare, aliased, or qualified construction did not use the owner facade');

  var replacement = new SourceRating('replacement', 50);
  hostA.ratingsData = [replacement, new SourceRating('fallback', 100)];
  interpA.execute(parser.parseString('afterReplace=Rating.judgeTime(5);'));
  check(interpA.variables.get('afterReplace') == replacement,
   'judging captured the original list instead of reading the current owner list');

  // A script-local class with the same spelling takes precedence over the
  // seeded imported API and must use its own constructor.
  interpA.variables.set('OtherRating', OtherRating);
  interpA.execute(parser.parseString(
   'function shadowConstructor() { var Rating=OtherRating; return new Rating("local"); } '
   + 'shadowed=shadowConstructor();'));
  var shadowed:Dynamic = interpA.variables.get('shadowed');
  check(Std.isOfType(shadowed, OtherRating) && shadowed.name == 'local',
   'the Rating factory intercepted a script-local class binding');

  var madeB = apiA.newRating('custom');
  current = hostB;
  madeB.increase(2);
  check(!hostA.changes.exists('customs') && hostB.changes.get('customs') == 2,
   'a persistent facade counter callback did not resolve the current matching host');

  var interpB = new NightmareVisionScriptInterp();
  var apiB = SourceRatingBindings.installNightmare(interpB, null, prefsB, null,
   function():Dynamic return hostB);
  var madeFromB = apiB.newRating('custom');
  check(madeFromB.hitWindow == 39, 'a second owner reused the first owner preferences');
  madeFromB.increase(3);
  check(hostB.changes.get('customs') == 5,
   'the second owner constructor did not write through its own counter callback');

  active = false;
  check(apiA.judgeTime(1) == null,
   'an inactive scene continued exposing its ratings list');
  active = true;
  hostB.ratingsData = null;
  check(apiA.judgeTime(1) == null,
   'a missing ratings list returned a fabricated descriptor');
  hostB.ratingsData = [];
  check(apiA.judgeTime(1) == null,
   'an empty ratings list returned a fabricated descriptor');

  var retained = apiA.newRating('retained');
  var oldCount = hostB.changes.get('retaineds');
  interpA.release();
  retained.increase(4);
  check(apiA.judgeTime(1) == null
   && hostB.changes.get('retaineds') == oldCount,
   'released facade or an externally retained descriptor reached the old host');
  interpB.release();
 }
}'''

        runtime_stub = '''class HxcCompatRuntime {
 public static function getZIndex(_target:Dynamic):Dynamic return 0;
 public static function setZIndex(_target:Dynamic, value:Dynamic, ?_op:String='='):Dynamic return value;
        }'''
        with tempfile.TemporaryDirectory(prefix="source-rating-", dir=ROOT / "tmp") as scratch:
            write_flixel_point_stub(Path(scratch))
            (Path(scratch) / "Main.hx").write_text(fixture, newline="\n")
            (Path(scratch) / "HxcCompatRuntime.hx").write_text(runtime_stub, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", scratch,
                 "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_backend_rating_import_uses_seeded_compat_class(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
class Host { public function new() {} }
class PsychRatingImportProbe {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var bridge = new SourceIrisBridge(new Host());
  bridge.variables.set('Rating', PsychRatingCompat);
  bridge.evaluate('import backend.Rating; imported = new Rating("good"); '
   + 'defaults=Rating.loadDefault(); qualified=new backend.Rating("qualified");', 'rating-import.hx');
  var rating:Dynamic = bridge.variables.get('imported');
  check(Std.isOfType(rating, PsychRatingCompat) && rating.name == 'good'
   && rating.ratingMod == 1,
   'backend.Rating did not construct the seeded Psych compatibility descriptor');
  var defaults:Array<SourceRating> = cast bridge.variables.get('defaults');
  check(defaults != null && defaults.length == 4 && defaults[0].name == 'sick'
   && defaults[1].ratingMod == 0.67,
   'backend.Rating.loadDefault did not execute on the seeded compatibility class');
  var qualified:Dynamic = bridge.variables.get('qualified');
  check(Std.isOfType(qualified, PsychRatingCompat) && qualified.name == 'qualified',
   'qualified backend.Rating construction lost its seeded class identity');
  check(PsychHscriptCompat.importBindings().get('backend.Rating') == 'Rating'
   && bridge.evaluator.importBindings.get('backend.Rating') == PsychRatingCompat,
   'Psych Rating import did not retain the owner-seeded class identity');
  bridge.release();
 }
}'''
        runtime_stub = '''class HxcCompatRuntime {
 public static function getZIndex(_target:Dynamic):Dynamic return 0;
 public static function setZIndex(_target:Dynamic, value:Dynamic, ?_op:String='='):Dynamic return value;
}'''
        with tempfile.TemporaryDirectory(prefix="psych-rating-import-", dir=ROOT / "tmp") as scratch:
            write_flixel_point_stub(Path(scratch))
            (Path(scratch) / "PsychRatingImportProbe.hx").write_text(fixture, newline="\n")
            (Path(scratch) / "HxcCompatRuntime.hx").write_text(runtime_stub, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", scratch,
                 "--run", "PsychRatingImportProbe"],
                cwd=ROOT, capture_output=True, text=True, timeout=90,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
