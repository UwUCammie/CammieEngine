"""V-Slice helper classes (haptics, touch, preferences, reflection, sequences, stepped fades) as base-game classes."""
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / '.haxelib/hscript/2,5,0'
HELPERS = ('HapticUtil', 'TouchUtil', 'Preferences', 'ReflectUtil', 'Sequence', 'RetroCameraFade')

STUBS = {
    'flixel/util/FlxTimer.hx': '''package flixel.util;
class FlxTimer {
 public static var all:Array<FlxTimer> = [];
 public var active = false; public var finished = false; public var time = 0.0;
 public var loops = 1; public var loopsLeft = 0; public var destroyed = false;
 var callback:FlxTimer->Void;
 public function new() {}
 public function start(time:Float = 1, ?callback:FlxTimer->Void, loops:Int = 1):FlxTimer {
  this.time = time; this.callback = callback; this.loops = loops; loopsLeft = loops;
  active = true; finished = false; if (all.indexOf(this) < 0) all.push(this); return this;
 }
 public function reset(newTime:Float = -1):FlxTimer { if (newTime < 0) newTime = time; return start(newTime, callback, loops); }
 public function cancel():Void { active = false; finished = true; }
 public function destroy():Void { destroyed = true; callback = null; }
 public function fire():Void {
  if (!active || finished || callback == null) return;
  if (loops > 0) { loopsLeft--; if (loopsLeft == 0) finished = true; }
  callback(this);
 }
}''',
    'flixel/FlxCamera.hx': 'package flixel;\nclass FlxCamera { public var filters:Array<Dynamic> = null; public function new() {} }',
    'flixel/FlxObject.hx': '''package flixel;
class FlxObject {
 public var cameras:Array<FlxCamera> = [new FlxCamera()];
 public var hitPoint:Bool = false;
 public function new() {}
 public function overlapsPoint(point:flixel.math.FlxPoint, inScreenSpace:Bool = false, ?camera:FlxCamera):Bool return hitPoint && camera == cameras[0];
}''',
    'flixel/math/FlxPoint.hx': 'package flixel.math;\nclass FlxPoint { public var released = 0; public function new() {} public function putWeak():Void released++; }',
    'openfl/filters/ColorMatrixFilter.hx': 'package openfl.filters;\nclass ColorMatrixFilter { public var matrix:Array<Float>; public function new(?matrix:Array<Float>) this.matrix = matrix; }',
    'OptionsHandler.hx': '''class OptionsHandler {
 public static var options(get, never):Dynamic;
 public static var current:Dynamic = {};
 static function get_options():Dynamic return current;
}''',
}

MAIN = r'''import flixel.FlxCamera;
import flixel.FlxObject;
import flixel.math.FlxPoint;
import flixel.util.FlxTimer;
import openfl.filters.ColorMatrixFilter;
class StoryMenuState { public function new() {} }
class VictoryLoopState { public function new() {} }
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function lastOffset(camera:FlxCamera):Float {
  var filter:ColorMatrixFilter = cast camera.filters[0];
  return filter.matrix[4];
 }
 static function main() {
  // Haptics: never available, every call is a quiet no-op.
  check(HapticUtil.hapticsAvailable == false, 'desktop haptics must report unavailable');
  HapticUtil.vibrate(); HapticUtil.vibrate(0.1, 0.2, 0.5, 1); HapticUtil.vibrateByPreset(); HapticUtil.increasingVibrate(0.1, 1);
  check(HapticUtil.defaultVibrationPreset.amplitude == 0.5, 'default preset keeps V-Slice values');

  // Touch: no touch, so every touch query is false; the point test is geometry only.
  check(!TouchUtil.pressed && !TouchUtil.justPressed && !TouchUtil.justReleased && !TouchUtil.released && !TouchUtil.justMoved,
   'desktop touch queries must be false');
  check(TouchUtil.touch == null, 'there is no first touch');
  var object = new FlxObject();
  check(!TouchUtil.overlaps(object) && !TouchUtil.overlapsComplex(object) && !TouchUtil.pressAction(object) && !TouchUtil.pressAction(),
   'touch overlap queries must be false');
  var point = new FlxPoint();
  check(!TouchUtil.overlapsComplexPoint(object, point) && point.released == 1, 'a miss still releases the weak point');
  object.hitPoint = true;
  check(TouchUtil.overlapsComplexPoint(object, point) && point.released == 2, 'the point test uses the object camera');
  check(!TouchUtil.overlapsComplexPoint(null, point), 'null objects never overlap');

  // Preferences follow engine options, fall back to V-Slice defaults, ignore writes.
  OptionsHandler.current = {naughtyness: false, downscroll: true, flashingLights: false, autoPause: false,
   lyricsEnabled: false, zoomCamera: false, offset: 12.7, fpsCap: 144};
  check(Preferences.naughtyness == false && Preferences.downscroll == true && Preferences.flashingLights == false,
   'preferences must read the engine options');
  check(Preferences.autoPause == false && Preferences.subtitles == false && Preferences.zoomCamera == false,
   'autoPause, subtitles and zoomCamera read the engine options');
  check(Preferences.globalOffset == 12 && Preferences.framerate == 144, 'numeric options are converted');
  OptionsHandler.current = {};
  check(Preferences.naughtyness == true && Preferences.downscroll == false && Preferences.flashingLights == true
   && Preferences.subtitles == true, 'missing options use V-Slice defaults');
  // V-Slice's default is no strumline background, which is also what the engine draws.
  check(Preferences.hapticsMode == 0 && Preferences.controlsScheme == 'Arrows' && Preferences.strumlineBackgroundOpacity == 0,
   'options the engine lacks answer with fixed defaults');
  Preferences.flashingLights = false;
  check(Preferences.flashingLights == true, 'script writes must not change the player options');

  // ReflectUtil: engine screens answer with the V-Slice names scripts compare against.
  check(ReflectUtil.getClassNameOf(new StoryMenuState()) == 'funkin.ui.story.StoryMenuState', 'story menu alias');
  check(ReflectUtil.getClassNameOf(new VictoryLoopState()) == 'funkin.play.ResultState', 'results screen alias');
  check(ReflectUtil.getClassNameOf(null) == 'Unknown', 'V-Slice reports Unknown for null');
  check(ReflectUtil.getClassNameOf(new FlxPoint()) == 'flixel.math.FlxPoint', 'other classes keep their own name');
  check(ReflectUtil.compatClassName('some.pkg.PauseSubState') == 'funkin.play.PauseSubState', 'the alias ignores the package');
  var anon:Dynamic = {a: 1};
  ReflectUtil.setAnonymousField(anon, 'b', 2);
  check(ReflectUtil.getAnonymousField(anon, 'b') == 2 && ReflectUtil.hasAnonymousField(anon, 'a')
   && ReflectUtil.getAnonymousFieldsOf(anon).length == 2, 'anonymous field helpers');
  check(ReflectUtil.getAnonymousField(null, 'a') == null, 'null objects read as null');

  // Sequence: sorted, absolute times, one timer, relative delays.
  var log:Array<String> = [];
  var sequence = new Sequence([{time: 2.0, callback: function() log.push('b')}, {time: -0.5, callback: function() log.push('a')}]);
  var timer = FlxTimer.all[FlxTimer.all.length - 1];
  check(timer.time == 0.5 && sequence.running, 'the first event waits its own time, a negative time counts as positive');
  timer.fire();
  check(log.join(',') == 'a' && timer.time == 1.5 && sequence.running, 'the next delay is the gap between events');
  timer.fire();
  check(log.join(',') == 'a,b' && sequence.completed && !sequence.running && timer.destroyed, 'finished sequences destroy themselves');
  var paused = new Sequence([{time: 1.0, callback: function() log.push('c')}], 2, false);
  var pausedTimer = FlxTimer.all[FlxTimer.all.length - 1];
  check(!paused.running && pausedTimer.time == 2 && !pausedTimer.active, 'start=false leaves the sequence paused, mult scales time');
  paused.running = true;
  check(pausedTimer.active && paused.running, 'running=true resumes');
  var stopping:Sequence = null;
  stopping = new Sequence([{time: 1.0, callback: function() stopping.stop()}, {time: 2.0, callback: function() log.push('never')}]);
  FlxTimer.all[FlxTimer.all.length - 1].fire();
  check(stopping.completed && log.indexOf('never') < 0, 'stop() inside a callback skips the rest');
  var failing = new Sequence([{time: 1.0, callback: function() throw 'script error'}, {time: 2.0, callback: function() log.push('after')}]);
  var failingTimer = FlxTimer.all[FlxTimer.all.length - 1];
  failingTimer.fire();
  failingTimer.fire();
  check(log[log.length - 1] == 'after' && failing.completed, 'a failing event does not stop the game or the sequence');
  var empty = new Sequence([]);
  check(empty.completed && !empty.running && empty.currentEvent == null, 'an empty sequence is already complete');

  // RetroCameraFade: hard steps through one colour offset filter, V-Slice loop counts.
  var camera = new FlxCamera();
  RetroCameraFade.fadeToBlack(camera, 4, 1);
  var fade = FlxTimer.all[FlxTimer.all.length - 1];
  check(fade.time == 0.25 && fade.loops == 4 && camera.filters == null, 'fadeToBlack waits a step before darkening');
  fade.fire();
  check(lastOffset(camera) == 0, 'the first step is unchanged');
  fade.fire();
  check(lastOffset(camera) == -0.25 * 255, 'each step darkens by one share');
  RetroCameraFade.fadeBlack(camera, 2, 1);
  var back = FlxTimer.all[FlxTimer.all.length - 1];
  check(lastOffset(camera) == -255 && back.loops == 3, 'fadeBlack starts black and has the extra tick');
  back.fire(); back.fire(); back.fire();
  check(lastOffset(camera) == 0, 'fadeBlack ends at normal colours');
  RetroCameraFade.fadeWhite(camera, 2, 1);
  var white = FlxTimer.all[FlxTimer.all.length - 1];
  white.fire(); white.fire(); white.fire();
  check(lastOffset(camera) == 255 && white.loops == 3, 'fadeWhite ends at white');
  check(RetroCameraFade.stepMatrix(0.5, 1)[9] == 127.5 && RetroCameraFade.stepMatrix(1, -1)[19] == 0, 'matrix offsets');
 }
}
'''

SCRIPT_MAIN = r'''import hscript.Interp;
import hscript.Parser;
class Main {
 static function main() {
  var interp = new Interp();
  interp.variables.set('HapticUtil', HapticUtil);
  interp.variables.set('TouchUtil', TouchUtil);
  interp.variables.set('Preferences', Preferences);
  interp.variables.set('ReflectUtil', ReflectUtil);
  interp.variables.set('Sequence', Sequence);
  OptionsHandler.current = {naughtyness: false};
  var source = "out = [];"
   + "if (!HapticUtil.hapticsAvailable) out.push('nohaptics'); else HapticUtil.vibrate(0, 0.1);"
   + "if (!TouchUtil.justPressed && !TouchUtil.pressAction()) out.push('keyboard');"
   + "out.push(Preferences.naughtyness ? 'naughty' : 'clean');"
   + "out.push(ReflectUtil.getClassNameOf(null));"
   + "var seq = new Sequence([{time: 0.1, callback: function() out.push('event')}]);"
   + "out.join(',');";
  var result = interp.execute(new Parser().parseString(source));
  if (result != 'nohaptics,keyboard,clean,Unknown') throw 'script saw ' + result;
  flixel.util.FlxTimer.all[flixel.util.FlxTimer.all.length - 1].fire();
  var out:Array<String> = interp.variables.get('out');
  if (out[out.length - 1] != 'event') throw 'the sequence callback did not reach the script';
 }
}
'''

MODULE_MAIN = r'''class Main {
 static function main() {
  var bodies = [
   'if (!HapticUtil.hapticsAvailable) return; HapticUtil.vibrate(0, 0.01, 1);',
   'if (TouchUtil.pressAction() || TouchUtil.justPressed) trace(1);',
   'if (Preferences.flashingLights) trace(Preferences.naughtyness);',
   "if (ReflectUtil.getClassNameOf(FlxG.state) == 'funkin.ui.freeplay.FreeplayState') trace(2);",
   'var s = new Sequence([{time: 1, callback: function() trace(3)}]);',
   'RetroCameraFade.fadeBlack(FlxG.camera, 5, 1);',
   'FlxTransitionableState.skipNextTransIn = true;',
   'var t = new AtlasText(0, 0, "HI", "bold");',
   // Warm-ups lower to the engine precache every interpreter has.
   "FunkinMemory.permanentCacheSound(Paths.sound('menu/confirm')); FunkinMemory.cacheTexture(Paths.image('menu/bg'));"
  ];
  for (body in bodies) {
   var source = "class Helpers extends Module { function new() { super('helpers'); } "
    + "override function onUpdate(event) { " + body + " } }";
   var result = HxcCompat.analyze(source, 'scripts/modules/Helpers.hxc');
   if (result.kind != 'module' || !result.moduleSafe)
    throw body + ' made the module unsafe: ' + result.moduleSafetyReasons.join(',');
  }
  var unknown = HxcCompat.analyze("class Helpers extends Module { function new() { super('helpers'); } "
   + "override function onUpdate(event) { NotAHelperUtil.vibrate(); } }", 'scripts/modules/Helpers.hxc');
  if (unknown.moduleSafe) throw 'an unknown helper root was accepted';
  // A known helper with a member it does not implement would throw on its first call.
  var missing = HxcCompat.analyze("class Helpers extends Module { function new() { super('helpers'); } "
   + "override function onUpdate(event) { Preferences.flush(); } }", 'scripts/modules/Helpers.hxc');
  if (missing.moduleSafe) throw 'a helper member with no base-game equivalent was accepted';
  var song = HxcCompat.analyze("class HelperSong extends Song { function new() { super('helper-song'); } "
   + "function onBeatHit(event) { HapticUtil.rumble(); } }", 'scripts/songs/helper-song.hxc');
  var seen = 0;
  for (callback in (cast song.callbackAdapters:Array<Dynamic>))
   if (callback.sourceName == 'onBeatHit') {
    seen++;
    if (callback.safe) throw 'song scripts must report the missing helper member too';
   }
  if (seen != 1) throw 'the song callback was not analysed';
 }
}
'''


def run_haxe(main, stubs=None, extra=()):
    with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
        root = Path(folder)
        for relative, text in (stubs or {}).items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text, newline='\n')
        (root / 'Main.hx').write_text(main, newline='\n')
        # Later class paths win, so the fixture folder goes last.
        return subprocess.run([*HAXE_COMMAND, *extra, '-cp', folder, '-main', 'Main', '--interp'],
                              cwd=ROOT, capture_output=True, text=True, timeout=300)


def helper_sources():
    return {name + '.hx': (ROOT / 'source' / (name + '.hx')).read_text(encoding='utf-8') for name in HELPERS}


class VSliceBaseHelpersTest(unittest.TestCase):
    def test_helpers_match_vslice_behaviour_on_desktop(self):
        result = run_haxe(MAIN, {**STUBS, **helper_sources()})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scripts_reach_static_properties_and_constructors(self):
        result = run_haxe(SCRIPT_MAIN, {**STUBS, **helper_sources()}, ('-cp', str(HSCRIPT)))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_modules_using_helpers_pass_the_root_gate(self):
        result = run_haxe(MODULE_MAIN, None, ('-cp', str(ROOT / 'source'), '-cp', str(HSCRIPT)))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_interpreter_binds_the_helpers(self):
        plugins = (ROOT / 'source/PluginManager.hx').read_text(encoding='utf-8')
        for name in HELPERS + ('AtlasText',):
            self.assertIn('interp.variables.set("%s", %s);' % (name, name), plugins)
        self.assertIn('interp.variables.set("FunkinTiledSprite", DynamicSprite.DynamicTiledSprite);', plugins)
        self.assertIn('interp.variables.set("FunkinBackdrop", DynamicSprite.DynamicBackdrop);', plugins)
        # The FunkinMemory warm-up pair comes from one runtime helper.
        self.assertIn('HxcCompatRuntime.bindAssetWarmups(interp.variables);', plugins)
        playstate = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        self.assertIn('HxcCompatRuntime.bindAssetWarmups(interp.variables);', playstate)
        self.assertNotIn("interp.variables.set('hxcCacheSound'", playstate)
        self.assertNotIn('interp.variables.set("hxcCacheSound"', plugins)
        catalogue = (ROOT / 'source/ScriptNativeClasses.hx').read_text(encoding='utf-8')
        for name in ('FlxTransitionableState', 'FlxGradient', 'FlxGraphic', 'FlxBitmapFont'):
            self.assertRegex(catalogue, r"entry\('%s'," % name)

    def test_asset_warmups_bind_both_names_and_read_the_root_when_run(self):
        main = '''class Main {
 static function main() {
  var variables = new Map<String, Dynamic>();
  HxcCompatRuntime.bindAssetWarmups(variables);
  if (!variables.exists('hxcCacheTexture') || !variables.exists('hxcCacheSound')) throw 'warm-up names missing';
  if (variables.get('hxcCacheTexture')('menu/bg') != null) throw 'texture warm-up returned a value';
  // No root bound yet and a missing file: the warm-up must stay silent.
  if (variables.get('hxcCacheSound')('menu/absent') != null) throw 'sound warm-up returned a value';
  variables.set('hxcAssetRoot', 'assets/imported_mods/none');
  if (variables.get('hxcCacheSound')('menu/absent') != null) throw 'sound warm-up with a root returned a value';
  Sys.println('warmups-ok');
 }
}'''
        result = run_haxe(main, None, ('-cp', str(ROOT / 'source')))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('warmups-ok', result.stdout)

    def test_gate_member_lists_match_the_helper_classes(self):
        compat = (ROOT / 'source/HxcCompat.hx').read_text(encoding='utf-8')
        table = compat[compat.index('static final BASE_HELPER_STATIC_MEMBERS'):]
        table = table[:table.index('];')]
        for owner, members in re.findall(r"'([A-Za-z]+)' => \[([^\]]*)\]", table):
            source = (ROOT / 'source' / (owner + '.hx')).read_text(encoding='utf-8')
            # Only the helper class itself; its file may hold support classes.
            body = source[source.index('class ' + owner + ' '):]
            later = body.find('\nclass ', 1)
            body = body if later < 0 else body[:later]
            declared = set(re.findall(r'public static (?:var|function) ([A-Za-z_]+)', body))
            listed = set(re.findall(r"'([A-Za-z_]+)'", members))
            self.assertEqual(listed, declared, owner)

    def test_helpers_carry_no_regex_literals(self):
        # These run inside script callbacks every frame on native builds.
        for name in HELPERS + ('AtlasText',):
            text = (ROOT / 'source' / (name + '.hx')).read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'~/', text), name)
            self.assertNotIn('new EReg', text, name)


if __name__ == '__main__':
    unittest.main()
