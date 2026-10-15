"""V-Slice PlayState.subtitles: SRT lines follow their sound on the native lyric line."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


def hx_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


SRT = "﻿1\r\n00:00:01,000 --> 00:00:02,500\r\n<i>Hi</i> {b}cutie{/b}\r\n\r\n" \
      "2\r\n00:00:02,000 --> 00:00:03,000 X1:10\r\nsecond\r\nline\r\n\r\n" \
      "broken block without times\r\n\r\n3\r\n00:00:05,000 --> 00:00:06,000\r\nlast\r\n"


class VSliceSubtitlesTest(unittest.TestCase):
    def run_main(self, source: str, extra=None) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(source, newline='\n')
            for relative, text in (extra or {}).items():
                target = Path(folder) / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, newline='\n')
            return subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(folder),
                                   "-main", "Main", "--interp"],
                                  cwd=ROOT, capture_output=True, text=True, timeout=180)

    def test_track_parses_srt_and_reports_visible_lines(self):
        main = f'''class Main {{
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function main() {{
    var track = SubtitleTrack.parse({hx_string(SRT)});
    check(track.cues.length == 3, "three timed cues, the broken block is skipped");
    check(track.cues[0].start == 1000 && track.cues[0].end == 2500, "times in ms");
    check(track.cues[0].text == "Hi cutie", "tags removed: " + track.cues[0].text);
    check(track.cues[1].end == 3000, "position settings after the end time are ignored");
    check(track.textAt(500) == "" && track.visibleKey(500) == 0, "nothing before the first cue");
    check(track.textAt(1500) == "Hi cutie", "one cue");
    check(track.textAt(2200) == "second\\nline\\nHi cutie", "overlapping cues stack newest first");
    check(track.visibleKey(2200) != track.visibleKey(1500), "key changes with the visible set");
    check(track.visibleKey(1200) == track.visibleKey(1500), "key is stable inside one cue");
    check(track.textAt(4000) == "", "gap between cues");
    check(SubtitleTrack.parseTimeLine("00:01:02,345 -> 00:01:03,000")[0] == 62345, "short arrow");
    check(SubtitleTrack.parse(null).cues.length == 0, "no source no cues");
    Sys.println("track-ok");
  }}
}}'''
        result = self.run_main(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("track-ok", result.stdout)

    def test_runtime_follows_sound_and_stops_with_its_state(self):
        main = f'''class PlayState {{
  public static var instance:Dynamic;
}}
class Owner {{
  public var lines:Array<String> = [];
  public function new() {{}}
  public function hxcSetLyricText(values:Array<Dynamic>, ?second:Bool = false):Bool {{
    lines.push(Std.string(values[0]));
    return true;
  }}
}}
class Main {{
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function main() {{
    var owner = new Owner();
    PlayState.instance = owner;
    var sound:Dynamic = {{time: 0.0}};
    var subtitles = HxcCompatRuntime.subtitlesFor("assets/imported_mods/v-slice-fixture");
    check(!subtitles.assignSubtitles("subtitles/english/missing", sound), "a missing file assigns nothing");
    check(!HxcCompatRuntime.assignSubtitles("", "x", null, {hx_string(SRT)}), "no sound assigns nothing");
    check(HxcCompatRuntime.assignSubtitles("", "x", sound, {hx_string(SRT)}), "assigned");
    HxcCompatRuntime.updateSubtitles();
    check(owner.lines.length == 0, "no line before the first cue");
    sound.time = 1200.0;
    HxcCompatRuntime.updateSubtitles();
    HxcCompatRuntime.updateSubtitles();
    check(owner.lines.join("|") == "Hi cutie", "one call per change: " + owner.lines.join("|"));
    sound.time = 4000.0;
    HxcCompatRuntime.updateSubtitles();
    check(owner.lines[owner.lines.length - 1] == "", "cleared between cues");
    sound.time = 5500.0;
    HxcCompatRuntime.updateSubtitles();
    PlayState.instance = new Owner();
    HxcCompatRuntime.updateSubtitles();
    var count = owner.lines.length;
    sound.time = 1200.0;
    HxcCompatRuntime.updateSubtitles();
    check(owner.lines.length == count && owner.lines[count - 1] == "last", "a replaced state stops the track");
    Sys.println("runtime-ok");
  }}
}}'''
        result = self.run_main(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("runtime-ok", result.stdout)

    def test_track_stops_when_the_game_leaves_its_state(self):
        # PlayState.instance outlives the song; the running FlxG.state decides.
        flxg = '''package flixel;
class FlxG {
  public static var state:Dynamic;
  public static var signals:Dynamic;
}
'''
        main = f'''class PlayState {{
  public static var instance:Dynamic;
}}
class Owner {{
  public var lines:Array<String> = [];
  public function new() {{}}
  public function hxcSetLyricText(values:Array<Dynamic>, ?second:Bool = false):Bool {{
    lines.push(Std.string(values[0]));
    return true;
  }}
}}
class Signal {{
  public var listeners:Array<Dynamic> = [];
  public function new() {{}}
  public function add(listener:Dynamic):Void listeners.push(listener);
  public function remove(listener:Dynamic):Void
    listeners = [for (current in listeners) if (!Reflect.compareMethods(current, listener)) current];
}}
class Main {{
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function main() {{
    var owner = new Owner();
    var signal = new Signal();
    PlayState.instance = owner;
    flixel.FlxG.state = owner;
    flixel.FlxG.signals = {{preUpdate: signal}};
    var sound:Dynamic = {{time: 1200.0}};
    check(HxcCompatRuntime.assignSubtitles("", "x", sound, {hx_string(SRT)}), "assigned");
    check(signal.listeners.length == 1, "one frame listener while a track runs");
    HxcCompatRuntime.updateSubtitles();
    check(owner.lines.join("|") == "Hi cutie", "line shown while the song state runs");
    flixel.FlxG.state = new Owner();
    sound.time = 2200.0;
    HxcCompatRuntime.updateSubtitles();
    check(owner.lines.join("|") == "Hi cutie", "a left state is not written to: " + owner.lines.join("|"));
    check(signal.listeners.length == 0, "the frame listener is removed when the state is left");
    sound.time = 5500.0;
    HxcCompatRuntime.updateSubtitles();
    check(owner.lines.length == 1, "a stopped track stays stopped");
    Sys.println("leave-ok");
  }}
}}'''
        result = self.run_main(main, {"flixel/FlxG.hx": flxg})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("leave-ok", result.stdout)

    def test_playstate_subtitles_and_import_copy_are_wired(self):
        donor = r'''
class LineSong extends Song {
    var sfx;
    function onCountdownStart(event) {
        sfx = FunkinSound.load('sounds/line.ogg');
        if (Preferences.subtitles) PlayState.instance.subtitles.assignSubtitles('subtitles/english/line', sfx);
    }
}
'''
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/songs/line.hxc");
    var generated = result.generatedHscript;
    if (generated.indexOf("HxcCompatRuntime.subtitlesFor(hxcAssetRoot).assignSubtitles(") < 0)
      fail("subtitles not lowered: " + generated);
    Sys.println("lowering-ok");
  }}
}}'''
        result = self.run_main(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("lowering-ok", result.stdout)
        source = (ROOT / "source/ModuleFunctions.hx").read_text(encoding="utf-8")
        start = source.index("static function mergeVSliceRuntimeAssets(")
        body = source[start:source.index("static function mergeVSliceSongSidecars(", start)]
        self.assertIn("Path.join([runtimeNamespace, 'data', 'subtitles'])", body)


if __name__ == "__main__":
    unittest.main()
