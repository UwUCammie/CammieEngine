"""Psych stage songName follows Paths.formatToSongPath, not chart title case."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from test_psych_stage_scene_order import extract_method


ROOT = Path(__file__).resolve().parents[2]


class PsychStageSongNameTest(unittest.TestCase):
    def test_source_song_path_format_is_shared_with_stage_view(self):
        stage = (ROOT / "source/PsychBaseStageCompat.hx").read_text()
        paths = (ROOT / "source/PsychOwnerPaths.hx").read_text()
        self.assertIn("PsychSongNameCompat.format(Std.string(value))", stage)
        self.assertIn("return PsychSongNameCompat.format(path);", paths)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(
                """class Main {
 static function main():Void {
  var view=new StageView();
  view.sourceName={text:'HUD label'};
  if(view.songName!='2hot') throw 'HUD object became source stage song name';
  view.sourceName='source:authored';
  if(view.songName!='source:authored') throw 'live source string was reformatted or ignored';
  if(PsychSongNameCompat.format('2Hot')!='2hot') throw 'stage title case';
  if(PsychSongNameCompat.format('Dad Battle!')!='dad-battle') throw 'stage punctuation';
  if(PsychSongNameCompat.format('  Pico, Erect  ')!='--pico-erect--')
   throw 'source path convention';
 }
}
""" + """class StageView {
 public var sourceName:Dynamic;
 public var songName(get,never):String;
 public function new() {}
 function staticField(name:String):Dynamic return name=='SONG' ? {song:'2Hot'} : null;
 function readField(name:String):Dynamic return name=='songName' ? sourceName : null;
""" + extract_method(stage,"function get_songName():String {") + "\n}\n", encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"),
                 "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
