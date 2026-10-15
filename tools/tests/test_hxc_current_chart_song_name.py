"""V-Slice currentChart.songName is the display name, not the chart id."""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


class HxcCurrentChartSongNameTest(unittest.TestCase):
    def test_song_name_reads_the_display_name(self):
        donor = r'''
class TitleSong extends Song {
    function onCreate(event) { trace(PlayState.instance.currentChart.songName); }
}
'''
        main = '''class PlayState {
  public static var instance:Dynamic;
  public static var SONG:Dynamic;
}
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var generated = HxcCompat.analyze(''' + json.dumps(donor) + ''', "scripts/songs/title.hxc").generatedHscript;
    if (generated.indexOf("trace(HxcCompatRuntime.currentChartSongName)") < 0) fail("not lowered: " + generated);
    PlayState.SONG = {song: "chart-id"};
    if (HxcCompatRuntime.currentChartSongName != "chart-id") fail("no view falls back to the chart id");
    PlayState.instance = {currentChart: {songName: "Display Name"}};
    if (HxcCompatRuntime.currentChartSongName != "Display Name") fail("display name not used");
    Sys.println("song-name-ok");
  }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                                     "-main", "Main", "--interp"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("song-name-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
