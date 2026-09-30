"""Focused coverage for the Round 23 HXC lifecycle and facade adapters."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def hx_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


class HxcRound23LifecycleTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            command = [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(folder),
                       "-main", "Main", "--interp"]
            return subprocess.run(command, cwd=ROOT, capture_output=True,
                                  text=True, timeout=180)

    def test_lifecycle_aliases_and_bounded_facades_generate(self):
        donor = r'''
class Round23Song extends Song {
    function onNoteGhostMiss(event) { trace(event.dir); }
    function onCountdownEnd(event) { trace(event.countdownStep); }
    function onPauseSubstateOpen(event) { trace(event.targetState); }
    function onPauseSubstateClose(event) { trace(event.targetState); }
    function onCreate(event) {
        var beat = Conductor.instance.currentBeat;
        var step = Conductor.instance.stepLengthMs;
        var crochet = Conductor.instance.beatLengthMs;
        var position = Conductor.instance.songPosition;
        var offset = Conductor.instance.combinedOffset;
        var cutout = FullScreenScaleMode.gameCutoutSize.x;
        var story = PlayStatePlaylist.isStoryMode;
        Countdown.skipCountdown();
        Countdown.stopCountdown();
        VideoCutscene.play(Paths.videos("round23"), CutsceneType.ENDING);
    }
}
'''
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/songs/round23.hxc");
    var generated = result.generatedHscript;
    for (name in ["noteGhostMiss", "countdownEnd", "subStateOpenEnd", "subStateCloseBegin"])
      if (generated.indexOf("function " + name) < 0) fail("missing generated lifecycle " + name + "\\n" + generated);
    for (name in ["HxcCompatRuntime.conductorStepLengthMs", "HxcCompatRuntime.conductorBeatLengthMs",
      "HxcCompatRuntime.conductorSongPosition", "HxcCompatRuntime.conductorCombinedOffset",
      "HxcCompatRuntime.fullScreenScaleMode.gameCutoutSize",
      "HxcCompatRuntime.playStatePlaylistIsStoryMode", "HxcCompatRuntime.skipCountdown(PlayState.instance)",
      "HxcCompatRuntime.stopCountdown(PlayState.instance)",
      "HxcCompatRuntime.playVideoCutscene(PlayState.instance, Paths.videos(\\\"round23\\\"), true)"])
      if (generated.indexOf(name) < 0) fail("missing generated alias " + name + "\\n" + generated);
    for (finding in result.diagnostics)
      if (finding.code == "unsupported-hxc-api") fail("supported alias diagnosed: " + finding.message);
    var names = EngineCompat.callbackNames("countdownEnd");
    if (names.indexOf("onCountdownEnd") < 0) fail("countdown callback alias");
    names = EngineCompat.callbackNames("noteGhostMiss");
    if (names.indexOf("onNoteGhostMiss") < 0) fail("ghost callback alias");
    names = EngineCompat.callbackNames("subStateOpenEnd");
    if (names.indexOf("onPauseSubstateOpen") < 0) fail("pause-open callback alias");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_conductor_update_uses_bounded_native_route(self):
        donor = r'''
class Round23Unsupported extends Song {
    function onCreate(event) { Conductor.instance.update(0); }
}
'''
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/songs/round23-unsupported.hxc");
    for (finding in result.diagnostics)
      if (finding.code == "unsupported-hxc-api" && finding.message.indexOf("Conductor.instance.update") >= 0)
        fail("bounded conductor update remained unsupported: " + finding.message);
    if (result.generatedHscript.indexOf("HxcCompatRuntime.conductorUpdate(0)") < 0)
      fail("bounded conductor update was not lowered: " + result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_facades_use_only_owner_methods(self):
        main = r'''class FakeOwner {
  public function new() {}
  public var skipped:Bool = false;
  public var stopped:Bool = false;
  public var videoEnded:Bool = false;
  public function hxcSkipCountdown():Bool { skipped = true; return true; }
  public function hxcStopCountdown():Bool { stopped = true; return true; }
  public function hxcPlayImportedVideo(path:Dynamic, ending:Bool):Bool { videoEnded = ending; return true; }
}
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var owner = new FakeOwner();
    if (!HxcCompatRuntime.skipCountdown(owner) || !owner.skipped) fail("skip facade");
    if (!HxcCompatRuntime.stopCountdown(owner) || !owner.stopped) fail("stop facade");
    if (!HxcCompatRuntime.playVideoCutscene(owner, "assets/videos/round23.mp4", true)
      || !owner.videoEnded) fail("video facade");
    var scale:Dynamic = HxcCompatRuntime.fullScreenScaleMode;
    if (scale.gameCutoutSize.x != 0 || scale.wideScale.x != 1) fail("fullscreen geometry facade");
    scale.enabled = false;
    scale.removeCutouts();
    if (scale.enabled) fail("fullscreen geometry mutation");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_owns_dispatch_and_scoped_video_surface(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("callHxcNoteHScript('noteGhostMiss'", play_state)
        self.assertIn("callAllHScript('countdownEnd'", play_state)
        self.assertIn("public function hxcSkipCountdown", play_state)
        self.assertIn("public function hxcStopCountdown", play_state)
        self.assertIn("public function hxcPlayImportedVideo", play_state)
        self.assertIn("Reflect.setField(proxy, 'videos'", play_state)
        self.assertIn("Reflect.setField(proxy, 'getPath'", play_state)


if __name__ == "__main__":
    unittest.main()
