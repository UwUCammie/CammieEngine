"""hxCodec FlxVideo and vlc MP4Handler, the video players older Psych mods use, on the engine playback."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

STUBS = {
    'flixel/FlxG.hx': '''package flixel;
class Signal {
 public var listeners:Array<Void->Void> = [];
 public function new() {}
 public function add(listener:Void->Void):Void listeners.push(listener);
 public function dispatch():Void for (listener in listeners.copy()) listener();
}
class Signals { public var preStateSwitch = new Signal(); public function new() {} }
class FlxG {
 public static var signals = new Signals();
 public static function addChildBelowMouse(child:Dynamic):Dynamic return child;
 public static function removeChild(child:Dynamic):Dynamic return child;
}''',
    'flixel/util/FlxTimer.hx': '''package flixel.util;
class FlxTimer {
 public static var all:Array<FlxTimer> = [];
 var callback:FlxTimer->Void;
 public var active = false;
 public function new() {}
 public function start(time:Float = 1, ?callback:FlxTimer->Void, loops:Int = 1):FlxTimer {
  this.callback = callback; active = true; all.push(this); return this;
 }
 public function cancel():Void active = false;
 public function fire():Void if (active) { active = false; callback(this); }
}''',
}

MAIN = r'''import flixel.FlxG;
import flixel.util.FlxTimer;
class Event {
 public var listeners:Array<Dynamic> = [];
 public function new() {}
 public function add(listener:Dynamic, once:Bool = false, priority:Int = 0):Void listeners.push(listener);
 public function dispatch():Void for (listener in listeners.copy()) listener();
}
class FakeDecoder {
 public var log:Array<String> = [];
 public var onEndReached = new Event();
 public var onFormatSetup = new Event();
 public var onOpening = new Event();
 public var alpha:Float = 1;
 public var visible:Bool = true;
 public var volumeAdjust:Float = 1;
 public var bitmapData:Dynamic = 'frame';
 public var isPlaying = false;
 public var accept = true;
 public function new() {}
 public function load(location:String, ?options:Array<String>):Bool {
  log.push('load:' + location + (options == null ? '' : ':' + options.join(' ')));
  return accept;
 }
 public function play():Bool { log.push('play'); isPlaying = true; return true; }
 public function stop():Void log.push('stop');
 public function pause():Void log.push('pause');
 public function resume():Void log.push('resume');
 public function dispose():Void log.push('dispose');
}
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main() {
  var decoders:Array<FakeDecoder> = [];
  LegacyVideoHandler.backendFactory = function() { var d = new FakeDecoder(); decoders.push(d); return d; };

  // hxCodec 3: play(path, loop) starts on the frame after load, signals pass through.
  var video = new LegacyVideoHandler();
  var decoder = decoders[0];
  var ended = 0;
  video.onEndReached.add(function() ended++, true);
  check(video.play('videos/clip.mp4', true) == 0, 'an accepted video returns 0 like hxCodec');
  check(decoder.log.join(',') == 'load:videos/clip.mp4::input-repeat=65535', 'loop asks the decoder to repeat: ' + decoder.log);
  FlxTimer.all[FlxTimer.all.length - 1].fire();
  check(decoder.log[decoder.log.length - 1] == 'play', 'playback starts after load');
  video.alpha = 0;
  check(decoder.alpha == 0 && video.bitmapData == 'frame', 'alpha and bitmapData reach the decoder');
  video.volume = 50;
  check(decoder.volumeAdjust == 0.5, 'hxCodec 3 percent volume becomes a share');
  video.volume = 0.25;
  check(decoder.volumeAdjust == 0.25, 'a share is passed through');
  decoder.onEndReached.dispatch();
  check(ended == 1, 'the script end listener runs');
  video.dispose();
  video.dispose();
  check(decoder.log.filter(function(e) return e == 'dispose').length == 1, 'dispose runs once');
  check(video.play('videos/clip.mp4') == -1, 'a disposed player refuses to play');

  // hxCodec 2: playVideo with readyCallback and finishCallback.
  var handler = new LegacyVideoHandler();
  var second = decoders[1];
  var calls:Array<String> = [];
  handler.readyCallback = function() calls.push('ready');
  handler.finishCallback = function() calls.push('finish');
  handler.playVideo('videos/other.mp4');
  check(second.log.join(',') == 'load:videos/other.mp4', 'no loop option without repeat');
  handler.finishCallback = function() calls.push('finish:' + handler.disposed);
  second.onFormatSetup.dispatch();
  second.onEndReached.dispatch();
  check(calls.join(',') == 'ready,finish:true', 'MP4Handler callbacks follow the decoder events: ' + calls);
  // hxCodec 2 closed the player at the end, so the last frame never stays over the game.
  check(second.log[second.log.length - 1] == 'dispose', 'an ended MP4Handler video releases its decoder');
  var kept = new LegacyVideoHandler();
  var keptDecoder = decoders[decoders.length - 1];
  kept.play('videos/kept.mp4');
  keptDecoder.onEndReached.dispatch();
  check(!kept.disposed, 'an ended hxCodec 3 video stays open until the script disposes it');
  kept.dispose();

  // A refused file reports failure without starting a timer.
  var refused = new LegacyVideoHandler();
  decoders[decoders.length - 1].accept = false;
  var timers = FlxTimer.all.length;
  check(refused.play('missing.mp4') == -1 && FlxTimer.all.length == timers, 'a refused file does not start playback');

  // A state switch closes players the script never disposed.
  FlxG.signals.preStateSwitch.dispatch();
  var open = new LegacyVideoHandler();
  var openDecoder = decoders[decoders.length - 1];
  open.playVideo('videos/open.mp4', true);
  FlxG.signals.preStateSwitch.dispatch();
  check(open.disposed && refused.disposed, 'open players close on a state switch');
  check(openDecoder.log[openDecoder.log.length - 1] == 'dispose', 'the decoder is released on a state switch');
 }
}
'''


class LegacyVideoHandlerTest(unittest.TestCase):
    def test_hxcodec_and_mp4handler_apis_drive_the_engine_decoder(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            root = Path(folder)
            for relative, text in STUBS.items():
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text, newline='\n')
            (root / 'LegacyVideoHandler.hx').write_text(
                (ROOT / 'source/LegacyVideoHandler.hx').read_text(encoding='utf-8'), newline='\n')
            (root / 'Main.hx').write_text(MAIN, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '-main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_evaluators_resolve_every_legacy_path(self):
        bindings = (ROOT / 'source/PsychStateClassBindings.hx').read_text(encoding='utf-8')
        install = bindings[bindings.index('public static function install(interp:NightmareVisionScriptInterp)'):]
        self.assertIn('for (path in LegacyVideoHandler.SCRIPT_PATHS)', install)
        self.assertIn('interp.bindImport(path, LegacyVideoHandler);', install)
        handler = (ROOT / 'source/LegacyVideoHandler.hx').read_text(encoding='utf-8')
        for path in ('hxcodec.flixel.FlxVideo', 'vlc.MP4Handler', 'hxcodec.VideoHandler', "'MP4Handler'"):
            self.assertIn(path, handler)
        # addHaxeLibrary('MP4Handler', 'vlc') resolves the full path through the evaluator's import table.
        bridge = (ROOT / 'source/SourceIrisBridge.hx').read_text(encoding='utf-8')
        self.assertIn('value = evaluator.getOrImportClass(packagePath);', bridge)


if __name__ == '__main__':
    unittest.main()
