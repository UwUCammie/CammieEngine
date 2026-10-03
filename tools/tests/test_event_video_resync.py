"""Execute the shared event-video clock correction against donor timing rules."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
    start = source.index(marker)
    begin = source.index("{", start)
    depth = 0
    for index in range(begin, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start:index + 1]
    raise AssertionError(marker)


class EventVideoResyncTest(unittest.TestCase):
    def test_event_video_cleanup_restores_hud_and_releases_video(self):
        play_source = (ROOT / "source/PlayState.hx").read_text()
        fixture = r'''
class FlxTween {public static var canceled=0;
 public static function cancelTweensOf(_:Dynamic,_:Array<String>):Void canceled++;
}
class FakeHUD {public var alpha:Float=0;public var visible=false;public function new(){}}
class FakeVideo {public var destroyed=false;public function new(){}
 public function destroy():Void destroyed=true;}
class Main {
 var compatEventVideo:FakeVideo=new FakeVideo();
 var compatEventVideoHudFaded=true;
 var compatEventVideoHudAlpha:Float=0.75;
 var compatEventVideoControlsDisabled=true;
 var compatEventVideoResync=true;
 var compatEventVideoEventTime:Float=1234;
 var compatEventVideoHudFadeDuration:Float=1;
 var camHUD:FakeHUD=new FakeHUD();
 public function new(){}
 function remove(_:Dynamic):Void {}
''' + method(play_source, "function stopCompatEventVideo(") + r'''
 static function main():Void {
  var state=new Main();
  var video=state.compatEventVideo;
  state.stopCompatEventVideo();
  if(!video.destroyed || state.compatEventVideo!=null || state.camHUD.alpha!=0.75
   || state.camHUD.visible || FlxTween.canceled!=1 || state.compatEventVideoResync
   || state.compatEventVideoControlsDisabled || state.compatEventVideoEventTime!=0)
   throw "event video cleanup left owner state behind";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", scratch,
                                     "--run", "Main"], cwd=ROOT, text=True,
                                    capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_video_resync_only_after_donor_threshold(self):
        video_source = (ROOT / "source/VideoCutscene.hx").read_text()
        play_source = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("compatEventVideo.resyncSongTime(", play_source)
        self.assertIn("Math.max(0, Conductor.songPosition - compatEventVideoEventTime)", play_source)
        self.assertIn("compatEventVideoEventTime = eventTime", play_source)
        fixture = r'''
class FakeVideo {
 public var isPlaying=true;
 public var time:Int=1000;
 public var pauses=0;
 public var resumes=0;
 public function new() {}
 public function pause():Void pauses++;
 public function resume():Void resumes++;
}
class Main {
 var disposed=false;
 var finished=false;
 var suspended=false;
 var video:FakeVideo=new FakeVideo();
 public function new() {}
''' + method(video_source, "public function resyncSongTime(") + r'''
 static function main():Void {
  var cutscene=new Main();
  if(cutscene.resyncSongTime(1500) || cutscene.video.time!=1000)
   throw "correction below donor threshold";
  if(!cutscene.resyncSongTime(1551) || cutscene.video.time!=1551
   || cutscene.video.pauses!=1 || cutscene.video.resumes!=1)
   throw "late clip was not resynced";
  cutscene.suspended=true;
  if(cutscene.resyncSongTime(3000)) throw "paused clip was resynced";
  cutscene.suspended=false;
  cutscene.video.isPlaying=false;
  if(cutscene.resyncSongTime(3000)) throw "stopped clip was resynced";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", scratch,
                                     "--run", "Main"], cwd=ROOT, text=True,
                                    capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
