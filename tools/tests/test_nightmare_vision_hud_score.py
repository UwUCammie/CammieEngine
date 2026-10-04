"""Executable contract for Nightmare Vision's borrowed PsychHUD score text."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class NightmareVisionHUDScoreTest(unittest.TestCase):
    def test_score_format_markup_bop_gates_and_tween_cleanup(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
import flixel.tweens.FlxTween;
import NightmareVisionHUDAdapter;

class FakeScale {
 public var x:Float = 1;
 public var y:Float = 1;
 public function new() {}
}
class FakeScoreFormat {
 public var color:Int;
 public function new(color:Int) this.color = color;
}
class FakeDisplay {
 public var x:Float = 0;
 public var y:Float = 0;
 public var width:Float = 100;
 public var height:Float = 12;
 public var min:Float = 0;
 public var max:Float = 1;
 public var percent:Float = 0;
 public var alpha:Float = 1;
 public var visible:Bool = true;
 public var text:String = '';
 public var scale:FakeScale = new FakeScale();
 public var formats:Array<Dynamic> = [];
 public function new() {}
 public function removeFormat(format:Dynamic):Void {
  for (entry in formats.copy()) if (entry.format == format) formats.remove(entry);
 }
 public function addFormat(format:Dynamic, start:Int, end:Int):Void {
  formats.push({format:format, range:{start:start, end:end}});
 }
}
class FakeParent {
 public var totalPlayed:Int = 0;
 public var ratingFC:String = '';
 public var instakillOnMiss:Bool = false;
 public var cpuControlled:Bool = false;
 public var nightmareVisionPrefs:Dynamic = {view:{scoreZoom:true}};
 public function new() {}
}
class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ': expected ' + expected + ', got ' + actual);

 static function main():Void {
  var state = new FakeParent();
  var healthBG = new FakeDisplay();
  var healthFill = new FakeDisplay();
  var iconP1 = new FakeDisplay();
  var iconP2 = new FakeDisplay();
  var score = new FakeDisplay();
  var songFill = new FakeDisplay();
  var songBG = new FakeDisplay();
  var timeText = new FakeDisplay();
  var scoreFormat:FakeScoreFormat = null;
  var markupTargets:Array<Dynamic> = [];
  var adapter = new NightmareVisionHUDAdapter({
   parent:state, healthFill:healthFill, healthBackground:healthBG,
   iconP1:iconP1, iconP2:iconP2, scoreText:score,
   songFill:songFill, songBackground:songBG, timeText:timeText,
   timeBarType:'Disabled',
   tweenScoreScale:function(target:Dynamic, duration:Float):Dynamic {
    return FlxTween.tween(target, {x:1.0, y:1.0}, duration);
   },
   applyScoreMarkup:function(target:Dynamic, color:Int, start:Int, end:Int):Void {
    var label:FakeDisplay = cast target;
    if (scoreFormat != null) label.removeFormat(scoreFormat);
    if (scoreFormat == null || scoreFormat.color != color)
     scoreFormat = new FakeScoreFormat(color);
    label.addFormat(scoreFormat, start, end);
    markupTargets.push(target);
   }
  });

  adapter.onUpdateScore(1234, 0, 0, false);
  eq(score.text, 'Score: 1,234 • Misses: 0 • Accuracy: N/A\n',
   'empty-score label follows donor format');
  eq(score.scale.x, 1.075, 'score bop starts before text refresh');
  eq(FlxTween.calls.length, 1, 'nonmiss player update starts source tween');
  eq(FlxTween.calls[0].duration, 0.2, 'score scale tween duration');
  eq(FlxTween.calls[0].target, score.scale, 'score scale is the tween target');
  eq(FlxTween.calls[0].values.x, 1, 'score tween returns x scale to one');
  eq(FlxTween.calls[0].values.y, 1, 'score tween returns y scale to one');

  state.totalPlayed = 8;
  state.ratingFC = 'SFC';
  adapter.onUpdateScore(1234567, 98.76, 5, false);
  eq(FlxTween.calls.length, 2, 'subsequent hit creates a replacement score tween');
  eq(FlxTween.calls[0].tween.cancelled, true, 'previous score tween is cancelled before replacement');
  eq(score.text, 'Score: 1,234,567 • Misses: 5 • Accuracy: 98.76% [SFC]\n',
   'score label uses grouped score, accuracy and rating FC');
  var range:Dynamic = score.formats[0].range;
  eq(range.start, score.text.indexOf('SFC'), 'markup starts at the rating FC');
  eq(range.end, score.text.length - 2, 'markup ends before the trailing newline');
  eq(score.formats[0].format.color, 0xFFFFEE56, 'SFC uses donor rank color');
  eq(markupTargets[0], score, 'markup callback receives the borrowed score label');

  var tweenCount = FlxTween.calls.length;
  adapter.onUpdateScore(-2500, 75.5, 9, true);
  eq(score.text, 'Score: -2,500 • Misses: 9 • Accuracy: 75.5% [SFC]\n',
   'miss text keeps signed grouped score and current accuracy');
  eq(FlxTween.calls.length, tweenCount, 'miss does not bop score text');

  state.instakillOnMiss = true;
  state.cpuControlled = true;
  adapter.onUpdateScore(10000, 99, 1, false);
  eq(score.text, 'Score: 10,000 • Accuracy: 99% [SFC]\n',
   'instakill layout omits the misses segment');
  eq(FlxTween.calls.length, tweenCount, 'CPU update does not bop score text');
  eq(score.formats.length, 1, 'score refresh replaces the existing markup range');

  state.cpuControlled = false;
  Reflect.setProperty(state.nightmareVisionPrefs.view, 'scoreZoom', false);
  adapter.onUpdateScore(10001, 99, 1, false);
  eq(FlxTween.calls.length, tweenCount, 'owner scoreZoom preference disables bop');

  // Re-enable zoom, leave a live tween, and ensure adapter teardown cancels it.
  Reflect.setProperty(state.nightmareVisionPrefs.view, 'scoreZoom', true);
  adapter.onUpdateScore(10002, 99, 1, false);
  var finalTween:Dynamic = FlxTween.calls[FlxTween.calls.length - 1].tween;
  adapter.release();
  eq(finalTween.cancelled, true, 'release cancels the outstanding score tween');
  eq(adapter.parent, null, 'release drops the borrowed owner reference');

  var missingTweenAdapter = new NightmareVisionHUDAdapter({
   parent:state, healthFill:healthFill, healthBackground:healthBG,
   iconP1:iconP1, iconP2:iconP2, scoreText:score,
   songFill:songFill, songBackground:songBG, timeText:timeText,
   timeBarType:'Disabled'
  });
  var missingTweenDiagnostic = false;
  try {
   missingTweenAdapter.onUpdateScore(1, 0, 0, false);
  } catch (error:Dynamic) {
   missingTweenDiagnostic = Std.string(error).indexOf('typed PlayState score-scale tween callback') >= 0;
  }
  check(missingTweenDiagnostic, 'missing typed score tween reports an explicit diagnostic');
  missingTweenAdapter.release();
 }
}
'''

        with tempfile.TemporaryDirectory(prefix="nv-score-hud-", dir=ROOT / "tmp") as scratch:
            scratch = FixturePath(scratch)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            tweens = scratch / "flixel" / "tweens"
            tweens.mkdir(parents=True)
            (tweens / "FlxTween.hx").write_text(r'''package flixel.tweens;
class FlxTween {
 public static var calls:Array<Dynamic> = [];
 public static function tween(target:Dynamic, values:Dynamic, duration:Float):Dynamic {
  var handle = new FakeScoreTween();
  calls.push({target:target, values:values, duration:duration, tween:handle});
  return handle;
 }
}
''', encoding="utf-8", newline="\n")
            (tweens / "FakeScoreTween.hx").write_text(r'''package flixel.tweens;
class FakeScoreTween {
 public var cancelled:Bool = false;
 public function new() {}
 public function cancel():Void cancelled = true;
}
''', encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
