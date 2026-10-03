"""Executed contract for the NMV PsychHUD bridge over live PlayState HUD objects."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class NightmareVisionHUDAdapterTest(unittest.TestCase):
    def test_live_bindings_timer_group_ownership_and_unsupported_paths(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
class FakePoint {
 public var x:Float = 1;
 public var y:Float = 1;
 public function new() {}
 public function set(x:Float = 0, y:Float = 0):FakePoint { this.x=x; this.y=y; return this; }
}
class FakeBar {
 public var x:Float; public var y:Float; public var width:Float; public var height:Float;
 public var barWidth:Float; public var barHeight:Float;
 public var alpha:Float = 1; public var visible:Bool = true;
 public var percent:Float = 0;
 public var min:Float; public var max:Float;
 public var fillDirection:String;
 public var emptyColor:Int = 11; public var fillColor:Int = 22;
 public var cameras:Array<Dynamic> = [];
 public var scrollFactor:FakePoint = new FakePoint();
 public var scale:FakePoint = new FakePoint();
 public var updates:Int = 0;
 public function new(x:Float, y:Float, width:Float, height:Float, min:Float, max:Float, direction:String) {
  this.x=x; this.y=y; this.width=width; this.height=height;
  this.barWidth=width; this.barHeight=height; this.min=min; this.max=max; this.fillDirection=direction;
 }
 public function createColoredEmptyBar(color:Int):FakeBar { emptyColor=color; return this; }
 public function createColoredFilledBar(color:Int):FakeBar { fillColor=color; return this; }
 public function setRange(min:Float, max:Float):Void { this.min=min; this.max=max; }
 public function updateBar():Void updates++;
}
class FakeObject {
 public var x:Float = 0; public var y:Float = 0;
 public var alpha:Float = 1; public var visible:Bool = true;
 public var flipX:Bool = false; public var text:String = '';
 public var scale:FakePoint = new FakePoint();
 public var cameras:Array<Dynamic> = [];
 public var bumps:Int = 0;
 public function new() {}
 public function bump():Void bumps++;
}
class FakePlayState {
 public var health:Float = 1.8;
 public var songPositionBar:Float = 0.25;
 public var curStep:Int = 21; public var curBeat:Int = 5; public var curSection:Int = 2;
 public var display:Array<Dynamic> = [];
 public var members(get,never):Array<Dynamic>;
 function get_members():Array<Dynamic> return display;
 public function new() {}
 public function add(object:Dynamic):Dynamic { display.push(object); return object; }
 public function remove(object:Dynamic, splice:Bool = false):Dynamic { display.remove(object); return object; }
 public function insert(position:Int, object:Dynamic):Dynamic { display.insert(position, object); return object; }
}

class FakeRatings {
 public var ratingPrefix:String = 'source/ratings/';
 public var ratingSuffix:String = '';
 public var comboPrefix:String = 'source/combo/';
 public var comboTween:Bool = true;
 public var comboOffsets:Array<Int> = [0,0,0,0];
 public var ratingGraphic:FakeObject = new FakeObject();
 public var ratingNumGroup:FakeObject = new FakeObject();
 public var showRating:Bool = true; public var showRatingNum:Bool = true; public var showCombo:Bool = true;
 public var calls:Array<Dynamic> = []; public var cached:Int = 0; public var released:Bool = false;
 public function new() {}
 public function popUpScore(rating:Dynamic,combo:Int,note:Dynamic):Void calls=[rating,combo,note];
 public function cachePopUpScore():Void cached++;
 public function release():Void released=true;
}
class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ': expected ' + expected + ', got ' + actual);

 static function main():Void {
  var state = new FakePlayState();
  var healthBG = new FakeObject(); healthBG.x=100; healthBG.y=400;
  var healthFill = new FakeBar(104,404,392,12,0,2,'RIGHT_TO_LEFT');
  healthFill.percent=50;
  var songBG = new FakeObject(); songBG.x=20; songBG.y=30;
  var songFill = new FakeBar(24,34,192,12,0,1,'LEFT_TO_RIGHT');
  var iconP1 = new FakeObject(); iconP1.x=110; iconP1.y=310;
  var iconP2 = new FakeObject(); iconP2.x=510; iconP2.y=310;
  var score = new FakeObject(); score.x=0; score.y=450;
  var timeText = new FakeObject(); timeText.x=20; timeText.y=30; timeText.text='Native title';
  var errors:Array<String> = [];
  var tweenTargets:Array<Dynamic> = [];
  var tweenDurations:Array<Float> = [];
  var characterRefreshes:Int = 0;
  var adapter = new NightmareVisionHUDAdapter({
   parent:state, healthFill:healthFill, healthBackground:healthBG,
   iconP1:iconP1, iconP2:iconP2, scoreText:score,
   songFill:songFill, songBackground:songBG, timeText:timeText,
   healthValue:function():Float return state.health,
   songProgress:function():Float return state.songPositionBar,
   ratingPrefix:'UI/ratings/', songTitle:'source-song', timeBarType:'Time Left', showTime:true,
   setHealthDirection:function(leftToRight:Bool):Void
    healthFill.fillDirection=leftToRight ? 'LEFT_TO_RIGHT' : 'RIGHT_TO_LEFT',
   setSongDirection:function(leftToRight:Bool):Void
    songFill.fillDirection=leftToRight ? 'LEFT_TO_RIGHT' : 'RIGHT_TO_LEFT',
   refreshCharacterPresentation:function():Void characterRefreshes++,
   tweenAlpha:function(target:Dynamic, duration:Float):Void {
    tweenTargets.push(target); tweenDurations.push(duration);
    Reflect.setProperty(target, 'alpha', 1);
   },
   reportUnsupported:function(message:String):Void errors.push(message),
   addDisplay:function(object:Dynamic):Dynamic return state.add(object),
   removeDisplay:function(object:Dynamic, splice:Bool):Dynamic return state.remove(object, splice),
   insertDisplay:function(position:Int, object:Dynamic):Dynamic return state.insert(position, object)
  });

  // The facade is non-rendering: it exposes only the actual display objects,
  // with no second group/add call during construction.
  eq(adapter.name, 'PSYCH', 'source HUD name');
  eq(adapter.parent, state, 'source parent identity');
  eq(adapter.healthBar.bg, healthBG, 'health background identity');
  eq(adapter.healthBar.fill, healthFill, 'health fill identity');
  eq(adapter.timeBar.bg, songBG, 'time background identity');
  eq(adapter.timeBar.fill, songFill, 'time fill identity');
  check(adapter.timeBar != adapter.timeTxt && adapter.timeTxt == timeText,
   'timeBar must be the native progress fill while timeTxt is the native label');
  eq(adapter.iconP1, iconP1, 'player icon identity');
  eq(adapter.iconP2, iconP2, 'opponent icon identity');
  eq(adapter.scoreTxt, score, 'score label identity');
  eq(adapter.members.length, 8, 'native HUD member count');
  eq(adapter.members[0], healthBG, 'member list holds native display objects');
  eq(state.display.length, 0, 'adapter constructor must not add a duplicate display owner');
  eq(adapter.curStep, 21, 'current step passthrough');
  eq(adapter.curBeat, 5, 'current beat passthrough');
  eq(adapter.curSection, 2, 'current section passthrough');
  eq(songFill.alpha, 0, 'source initial time bar fade');
  eq(songBG.alpha, 0, 'time background follows source group alpha');
  eq(timeText.alpha, 0, 'source initial time text fade');

  // Psych Bar controls operate on the already-owned native FlxBar and graphic.
  adapter.healthBar.setColors(0xFF112233, 0xFF445566);
  eq(healthFill.emptyColor, 0xFF112233, 'left color maps to native empty/background color');
  eq(healthFill.fillColor, 0xFF445566, 'right color maps to native filled color');
  adapter.healthBar.setColors(0xFFABCDEF, null);
  eq(healthFill.emptyColor, 0xFFABCDEF, 'one-sided setColors updates only the requested side');
  eq(healthFill.fillColor, 0xFF445566, 'one-sided setColors preserves the other side');
  adapter.timeBar.setColors(0xFF010203, 0xFF040506);
  eq(songFill.fillColor, 0xFF010203, 'LTR time bar maps physical left to filled');
  eq(songFill.emptyColor, 0xFF040506, 'LTR time bar maps physical right to empty');
  adapter.healthBar.setBGOffset(6, -2);
  eq(healthBG.x, 106, 'BG offset x'); eq(healthBG.y, 398, 'BG offset y');
  eq(healthFill.x, 104, 'BG offset leaves live fill x in place');
  eq(healthFill.y, 404, 'BG offset leaves live fill y in place');
  adapter.healthBar.setBGOffset(3, 4);
  eq(healthBG.x, 109, 'repeated BG offset x accumulates');
  eq(healthBG.y, 402, 'repeated BG offset y accumulates');
  adapter.healthBar.leftToRight = true;
  eq(healthFill.fillDirection, 'LEFT_TO_RIGHT', 'leftToRight updates native fill direction');
  eq(healthFill.fillColor, 0xFFABCDEF, 'physical left color maps to filled color when facing right');
  eq(healthFill.emptyColor, 0xFF445566, 'physical right color maps to empty color when facing right');
  adapter.healthBar.leftToRight = false;
  eq(healthFill.fillDirection, 'RIGHT_TO_LEFT', 'reverse direction restoration');
  eq(healthFill.emptyColor, 0xFFABCDEF, 'physical left color remaps to empty on reverse');
  eq(healthFill.fillColor, 0xFF445566, 'physical right color remaps to filled on reverse');
  adapter.onHealthChange();
  eq(healthFill.percent, 90, 'fractional live health is not truncated');
  eq(healthFill.updates, 1, 'health refresh updates the native bar');
  eq(adapter.healthBar.valueFunction(), 1.8, 'source valueFunction preserves fractions');
  eq(adapter.healthBar.bounds.min, 0, 'source health range minimum');
  eq(adapter.healthBar.bounds.max, 2, 'source health range maximum');
  adapter.healthBar.setBounds(0, 4);
  eq(healthFill.max, 4, 'source setBounds updates native FlxBar range');
  adapter.healthBar.percent = 61.5;
  eq(healthFill.percent, 61.5, 'percent writes through to live fill');

  // Group alpha/visibility/position and bar scale propagate without detaching
  // or cloning the native HUD pieces.
  adapter.alpha = 0.4;
  eq(healthBG.alpha, 0.4, 'group alpha health background');
  eq(healthFill.alpha, 0.4, 'group alpha health fill');
  eq(iconP1.alpha, 0.4, 'group alpha player icon');
  eq(timeText.alpha, 0.4, 'group alpha time label');
  adapter.visible = false;
  eq(healthBG.visible, false, 'group visibility health background');
  eq(timeText.visible, false, 'group visibility time label');
  adapter.visible = true;
  adapter.x = 10; adapter.y = 5;
  eq(healthFill.x, 114, 'group x moves fill');
  eq(healthBG.x, 119, 'group x preserves cumulative BG offset');
  eq(healthBG.y, 407, 'group y preserves cumulative BG offset');
  eq(songFill.y, 39, 'group y moves progress fill');
  eq(iconP1.x, 120, 'group x moves direct native child');
  eq(timeText.y, 35, 'group y moves direct text child');
  adapter.healthBar.scale.set(2, 3);
  eq(healthFill.scale.x, 2, 'Bar scale updates fill');
  eq(healthBG.scale.x, 2, 'Bar scale updates background');
  eq(healthBG.scale.y, 3, 'Bar scale y updates background');

  // Timer uses note-offset-adjusted audio time, pauses on source lifecycle
  // states, keeps Song Name text authored, and never rebinds to the label.
  adapter.updateTimer(52345, 100000, 245, 'Time Elapsed', false, false, false);
  eq(state.songPositionBar, 0.521, 'live progress uses note-offset-adjusted clock');
  eq(songFill.percent, 52.1, 'timeBar percent is the actual native fill');
  eq(timeText.text, '0:52', 'elapsed time label');
  adapter.updateTimer(80000, 100000, 0, 'Time Left', false, true, false);
  eq(state.songPositionBar, 0.521, 'paused source timer does not overwrite progress');
  eq(timeText.text, '0:52', 'paused source timer leaves label untouched');
  timeText.text = 'script-authored title';
  adapter.updateTimer(80000, 100000, 0, 'Song Name', false, false, false, 'native song');
  eq(timeText.text, 'script-authored title', 'Song Name mode leaves the live label authored');
  adapter.updateTimer(80000, 100000, 0, 'Disabled', false, false, false);
  eq(timeText.visible, true, 'per-frame timer does not reset authored visibility');
  eq(timeText.text, 'script-authored title', 'disabled timer leaves label untouched');

  // Source lifecycle and direct icon operations act on host-owned objects.
  adapter.onSongStart();
  eq(tweenTargets.length, 2, 'source start requests both time tweens');
  eq(tweenTargets[0], adapter.timeBar, 'fill tween target is live bar view');
  eq(tweenTargets[1], timeText, 'text tween target is native label');
  eq(tweenDurations[0], 0.5, 'source fade duration');
  eq(songFill.alpha, 1, 'fill alpha tween reaches native bar');
  eq(songBG.alpha, 1, 'group alpha tween reaches native background');
  eq(timeText.alpha, 1, 'text alpha tween reaches native label');
  adapter.beatHit();
  eq(iconP1.bumps, 1, 'beat callback bops player icon');
  eq(iconP2.bumps, 1, 'beat callback bops opponent icon');
  adapter.onCharacterChange();
  eq(characterRefreshes, 1, 'character change delegates to shared live-icon/color refresh');
  adapter.flipBar();
  eq(healthFill.fillDirection, 'LEFT_TO_RIGHT', 'flipBar changes fill direction');
  eq(iconP1.flipX, true, 'flipBar mirrors player icon');
  eq(iconP2.flipX, true, 'flipBar mirrors opponent icon');
  adapter.flipBar();
  eq(iconP1.flipX, false, 'second flip restores player icon');
  eq(iconP2.flipX, false, 'second flip restores opponent icon');

  var extra = new FakeObject();
  adapter.add(extra);
  eq(state.display[0], extra, 'add routes into real state display list');
  check(adapter.members.indexOf(extra) >= 0, 'added object appears in facade member view');
  adapter.insert(0, score);
  eq(state.display[0], score, 'insert routes through owner callback');
  adapter.remove(extra, true);
  check(state.display.indexOf(extra) < 0 && adapter.members.indexOf(extra) < 0,
   'remove updates real owner and facade view');

  eq(adapter.remove(null), null, 'null removal stays outside the native display container');

  // Source refreshZ must reorder the actual draw list, including opaque
  // shadows added after foreground text. Unrelated stage slots stay fixed.
  var background:Dynamic = {z:990};
  var foreground:Dynamic = {z:997};
  var shadow:Dynamic = {z:995};
  var outside:Dynamic = {z:-100};
  state.display = [outside, foreground, null, shadow, background];
  adapter.members.resize(0);
  for (object in [foreground,shadow,background]) adapter.members.push(object);
  adapter.sort(function(order:Int, a:Dynamic, b:Dynamic):Int
   return a.z < b.z ? order : (a.z > b.z ? -order : 0), -1);
  eq(state.display[0], outside, 'HUD sort preserves unrelated stage slot');
  eq(state.display[2], null, 'HUD sort preserves vacant stage slot');
  eq(state.display[1], background, 'background is behind HUD text in live draw list');
  eq(state.display[3], shadow, 'shadow renders before foreground');
  eq(state.display[4], foreground, 'white text renders over its black shadow');
  eq(adapter.members[2], foreground, 'logical HUD order matches rendering');
  adapter.sort(function(order:Int, a:Dynamic, b:Dynamic):Int
   return a.z < b.z ? order : (a.z > b.z ? -order : 0), 1);
  eq(state.display[1], foreground, 'descending source sort is honored');
  // Restore the existing test's borrowed membership and display targets.
  adapter.members.resize(0);
  var restored:Array<Dynamic> = [healthBG,healthFill,iconP1,iconP2,score,songBG,songFill,timeText];
  for (object in restored) adapter.members.push(object);
  state.display = [score];

  eq(adapter.remove(new FakeObject()), null, 'nonmember removal follows source null result');
  state.add(songBG); state.add(songFill);
  eq(adapter.remove(adapter.timeBar), adapter.timeBar, 'source bar removal returns the view');
  check(state.display.indexOf(songBG) < 0 && state.display.indexOf(songFill) < 0,
   'bar removal removes both physical pieces without adding the view to FlxBasic');
  eq(adapter.remove(adapter.timeBar), null, 'repeated bar removal is safe');

  var prefixErrors = errors.length;
  adapter.ratingPrefix = 'custom/ratings/';
  eq(adapter.ratingPrefix, 'custom/ratings/', 'ratingPrefix is mutable');
  check(errors.length == prefixErrors + 1
   && errors[errors.length - 1].indexOf('ratingPrefix is stored') >= 0,
   'unconnected rating renderer emits a direct diagnostic');
  var unsupported = false;
  try adapter.popUpScore(null, 1, null) catch (error:Dynamic) {
   unsupported = Std.string(error).indexOf('PsychHUD.popUpScore') >= 0;
  }
  check(unsupported, 'unsupported popup is an error, not a silent no-op');

  var presentation = new FakeRatings();
  var popupAdapter = new NightmareVisionHUDAdapter({
   parent:state, healthFill:healthFill, healthBackground:healthBG,
   iconP1:iconP1, iconP2:iconP2, scoreText:score,
   songFill:songFill, songBackground:songBG, timeText:timeText,
   ratingPresentation:presentation,
   removeDisplay:function(object:Dynamic, splice:Bool):Dynamic return state.remove(object, splice)
  });
  eq(popupAdapter.ratingGraphic, presentation.ratingGraphic, 'popup exposes real sprite identity');
  eq(popupAdapter.ratingNumGroup, presentation.ratingNumGroup, 'popup exposes actual digit group');
  popupAdapter.showRating=false; popupAdapter.showRatingNum=false; popupAdapter.showCombo=false;
  check(!presentation.showRating && !presentation.showRatingNum && !presentation.showCombo,
   'popup flags forward to the live renderer');
  popupAdapter.ratingPrefix='authored/';
  eq(presentation.ratingPrefix, 'authored/', 'owner prefix reaches live renderer');
  popupAdapter.ratingSuffix='-pixel';
  popupAdapter.comboPrefix='digits/';
  popupAdapter.comboTween=false;
  var offsets=[1,2,3,4];
  popupAdapter.comboOffsets=offsets;
  check(presentation.ratingSuffix=='-pixel' && popupAdapter.ratingSuffix=='-pixel'
   && presentation.comboPrefix=='digits/' && popupAdapter.comboPrefix=='digits/'
   && !presentation.comboTween && !popupAdapter.comboTween
   && presentation.comboOffsets==offsets && popupAdapter.comboOffsets==offsets,
   'all source popup API properties forward to the actual renderer');
  var rating={name:'sick',image:'sick'}, note=new FakeObject();
  popupAdapter.popUpScore(rating, 234, note);
  eq(presentation.calls[0], rating, 'source rating identity preserved');
  eq(presentation.calls[1], 234, 'source combo preserved');
  eq(presentation.calls[2], note, 'source note identity preserved');
  popupAdapter.cachePopUpScore(); eq(presentation.cached, 1, 'source cache dispatch');
  popupAdapter.visible=false;
  check(!presentation.ratingGraphic.visible && !presentation.ratingNumGroup.visible,
   'HUD hiding reaches actual popup roots');
  popupAdapter.release(); check(presentation.released, 'popup tween cleanup reaches presentation');

  adapter.release();
  eq(adapter.parent, null, 'release clears parent reference');
  eq(adapter.members.length, 0, 'release clears display references');
  eq(adapter.healthBar, null, 'release clears bar wrappers');
  eq(healthFill.alpha, 0.4, 'release does not destroy or reset host-owned objects');
  var released = false;
  try adapter.onSongStart() catch (_:Dynamic) released = true;
  check(released, 'released adapter cannot be reused');
 }
}
'''

        with tempfile.TemporaryDirectory(prefix="nmv-hud-", dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", scratch,
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
