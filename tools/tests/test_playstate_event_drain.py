"""Pin chart-event delivery at audio completion and across callback re-entry."""
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PlayStateEventDrainTest(unittest.TestCase):
    def test_completion_flushes_bounded_tail_without_replaying_rows(self):
        source = (ROOT / 'source/PlayState.hx').read_text()

        def method(name):
            start = source.index('\tfunction ' + name + '(')
            brace = source.index('{', start)
            depth = 0
            for index in range(brace, len(source)):
                depth += (source[index] == '{') - (source[index] == '}')
                if depth == 0:
                    return source[start:index + 1]
            raise AssertionError(name)

        helpers = '\n'.join(method(name) for name in (
            'dispatchDueSongEvents', 'dueSongEventCount', 'handleSongAudioComplete'))
        self.assertIn(
            'FlxG.sound.music.onComplete = function() handleSongAudioComplete();',
            source,
            'native audio completion must use the tail-draining callback')
        update_start = source.index('override public function update(')
        self.assertIn('dispatchDueSongEvents();', source[update_start:])

        fixture = r'''class Conductor { public static var songPosition:Float = 0; }
class RuntimeSmokeHarness {
 public static var lastDue:Int = -1;
 public static function enabled():Bool return false;
 public static function markStep(_label:String):Void {}
 public static function markNaturalSongEnd(song:String,length:Float,position:Float,
  dispatched:Int,total:Int,due:Int):Void {lastDue=due;}
}
class Main {
 var songEvents:Array<Dynamic> = [];
 var songEventIndex:Int = 0;
 var songLength:Float = 0;
 var demoMode:Bool = false;
 var demoSongFinished:Bool = false;
 var codenameInstFacade:Dynamic = null;
 var SONG:Dynamic = {song:"fixture"};
 var log:Array<String> = [];
 var reenterOn:String = "";
 public function new() {}
''' + helpers + r'''
 function fireSongEvent(event:Dynamic):Void {
  log.push(event.name);
  if (event.name == reenterOn) {
   reenterOn = "";
   handleSongAudioComplete();
  }
 }
 function endSong():Void log.push("end");
 function run():Void {
  songEvents = [
   {time:0.0, name:"zero"}, {time:5.0, name:"five"},
   {time:10.0, name:"boundary"}, {time:11.0, name:"future"}
  ];
  Conductor.songPosition = 10;
  dispatchDueSongEvents();
  if (log.join(",") != "zero,five,boundary" || songEventIndex != 3)
   throw "regular due-event pump changed order or inclusive boundary";
  dispatchDueSongEvents();
  if (log.join(",") != "zero,five,boundary")
   throw "regular update replayed a dispatched event";

  log.resize(0); songEventIndex = 0; songLength = 200;
  Conductor.songPosition = 190;
  songEvents = [
   {time:100.0, name:"early"}, {time:150.0, name:"near-tail"},
   {time:200.0, name:"at-song-end"}, {time:201.0, name:"past-song-end"}
  ];
  dispatchDueSongEvents();
  handleSongAudioComplete();
  if (log.join(",") != "early,near-tail,at-song-end,end" || songEventIndex != 3)
   throw "audio completion did not flush exactly through songLength before endSong";
  if (RuntimeSmokeHarness.lastDue != 3)
   throw "due event count included the authored event after audio completion";
  dispatchDueSongEvents(songLength);
  if (log.join(",") != "early,near-tail,at-song-end,end")
   throw "completion flush replayed a prior event";

  log.resize(0); songEventIndex = 0; songLength = 200;
  Conductor.songPosition = 190;
  codenameInstFacade = {onComplete: function() log.push("source-complete"),
   complete: function() log.push("source-complete")};
  handleSongAudioComplete();
  if (log.join(",") != "early,near-tail,at-song-end,source-complete" || songEventIndex != 3)
   throw "authored completion did not run after the bounded tail";
  codenameInstFacade = null;

  log.resize(0); songEventIndex = 0; songLength = 200;
  Conductor.songPosition = 100;
  songEvents = [{time:100.0, name:"reentrant"}, {time:200.0, name:"tail"}];
  reenterOn = "reentrant";
  dispatchDueSongEvents();
  if (log.join(",") != "reentrant,tail,end" || songEventIndex != 2)
   throw "callback re-entry duplicated or reordered the tail";

  log.resize(0); songEventIndex = 0; songLength = 200; demoMode = true;
  Conductor.songPosition = 0;
  songEvents = [{time:200.0, name:"demo-tail"}];
  handleSongAudioComplete();
  if (!demoSongFinished || songEventIndex != 0 || log.length != 0)
   throw "demo completion no longer leaves final-frame dispatch to update";
  Conductor.songPosition = 200;
  dispatchDueSongEvents();
  if (log.join(",") != "demo-tail") throw "demo final-frame event was lost";
 }
 static function main():Void new Main().run();
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            directory = Path(work)
            (directory / 'Main.hx').write_text(fixture)
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', str(directory),
                 '--run', 'Main'], cwd=ROOT, text=True, capture_output=True,
                timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
