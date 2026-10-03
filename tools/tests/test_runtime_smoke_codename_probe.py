"""Bounded smoke-only Codename snapshots and required song-end gate."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class RuntimeSmokeCodenameProbeTest(unittest.TestCase):
    def test_probe_is_opt_in_owner_scoped_and_requires_song_end_when_requested(self):
        harness = (ROOT / 'source/RuntimeSmokeHarness.hx').read_text()
        play_state = (ROOT / 'source/PlayState.hx').read_text()

        def method(source, name):
            start = source.index('function ' + name + '(')
            brace = source.index('{', start)
            depth = 0
            for index in range(brace, len(source)):
                depth += (source[index] == '{') - (source[index] == '}')
                if depth == 0:
                    return source[start:index + 1]
            raise AssertionError(name)

        self.assertIn("case '--smoke-require-song-end':", harness)
        self.assertIn("case '--smoke-codename-visuals':", harness)
        self.assertIn('missingRequiredSongEnd(config().requireSongEnd, naturalSongEndObserved)', harness)
        self.assertIn('RuntimeSmokeHarness.markNaturalSongEnd', play_state)
        self.assertIn('RuntimeSmokeHarness.markCodenameVisualSnapshot', play_state)
        self.assertIn("var eventCallback = callback == 'onEvent';", harness)

        required = '\n'.join('static ' + method(harness, name) for name in (
            'markCodenameVisualSnapshot', 'markNaturalSongEnd',
            'missingRequiredSongEnd', 'safeSmokeRelative', 'boundedSmokeText', 'safeToken'))
        fixture = r'''using StringTools;
class Main {
 static var finished:Bool = false;
 static var naturalSongEndObserved:Bool = false;
 static var naturalSongEndAt:Float = 0;
 static var codenameEventVisualMarkers:Int = 0;
 static var codenameCallbackVisualMarkers:Int = 0;
 static var codenameVisualSignatures:Map<String,String> = new Map();
 static var marks:Array<Dynamic> = [];
 static function config():Dynamic return {codenameVisuals:true, requireSongEnd:true};
 static function enabled():Bool return true;
 static function codenameVisualsEnabled():Bool return enabled() && config().codenameVisuals && !finished;
 static function emit(name:String,payload:Dynamic):Void marks.push({name:name,payload:payload});
''' + required + r'''
 static function main():Void {
  if (!missingRequiredSongEnd(true,false) || missingRequiredSongEnd(true,true)
   || missingRequiredSongEnd(false,false)) throw "required natural-end gate";
  var objects:Array<Dynamic> = [];
  for (i in 0...20) objects.push({index:i,kind:"video",videoLoaded:true,
   videoPlaying:true,videoTimeMs:50.5,mrl:"/private/donor/confetti.mp4",unbounded:{secret:true}});
  markCodenameVisualSnapshot("assets/imported_mods/owner-a", "data/events/confetti.pack",
   "onEvent", "ConfettiHUD", 7241.5, objects,
   {gameZoom:1.25,hudZoom:1.0,otherZoom:1.0,privatePath:"/secret"});
  if (marks.length != 1 || marks[0].name != "codename_visual_snapshot")
   throw "visual snapshot marker missing";
  var payload:Dynamic = marks[0].payload;
  if (payload.owner != "assets/imported_mods/owner-a"
   || payload.script != "data/events/confetti.pack" || payload.eventName != "ConfettiHUD"
   || payload.eventTimeMs != 7241.5 || payload.objects.length != 16
   || payload.objects[0].videoPlaying != true || Reflect.hasField(payload.objects[0],"mrl")
   || Reflect.hasField(payload.objects[0],"unbounded") || Reflect.hasField(payload.camera,"privatePath"))
   throw "visual snapshot leaked or exceeded its bounded schema";
  var prior = marks.length;
  markCodenameVisualSnapshot("/private/donor", "/private/donor/script.hx",
   "onEvent", "Private", 10, [], {});
  payload = marks[prior].payload;
  if (payload.owner != "" || payload.script != "")
   throw "absolute donor path escaped smoke scoping";
  for (i in 0...800)
   markCodenameVisualSnapshot("assets/imported_mods/owner-a", "data/events/e.pack",
    "onEvent", "event-"+i, i, [], {});
  if (codenameEventVisualMarkers != 768 || marks.length != 768)
   throw "event marker budget was not enforced";
  markNaturalSongEnd("fixture-song", 203168, 203168, 9, 10, 9);
  if (!naturalSongEndObserved || marks[marks.length-1].name != "song_end")
   throw "natural song-end marker missing";
  if (marks[marks.length-1].payload.dueEvents != 9
   || marks[marks.length-1].payload.totalEvents != 10)
   throw "post-audio authored events were not reported separately";
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            directory = Path(work)
            (directory / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(directory),
                 '--run', 'Main'], cwd=ROOT, text=True, capture_output=True,
                timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
