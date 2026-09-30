"""Codename's static PlayState view stays live inside HScript."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenamePlayStateFacadeTest(unittest.TestCase):
    def test_live_chart_owner_receives_song_metadata_in_transition_scripts(self):
        bindings = (ROOT / 'source/CodenameModBindings.hx').read_text()
        self.assertIn('currentPlayState.codenameTransitionOwnerRoot() == root', bindings)
        self.assertIn('new CodenamePlayStateFacade(currentPlayState, currentPlayState.codenameSongView)', bindings)

    def test_story_state_and_completion_methods_are_live(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            base = Path(work)
            (base / 'PlayState.hx').write_text('''class PlayState {
 public static var isStoryMode:Bool=false;
 public static var storyDifficultyText:String='Hard';
 public static var resets:Int=0;
 public static var loaded:String='';
 public static function resetSongInfos():Void {resets++;isStoryMode=false;}
 public static function __loadSong(song:String,?difficulty:String):Void loaded=song+":"+difficulty;
 public function codenameCharterIdentity():Dynamic return {variation:null};
 public function new() {}
}''')
            (base / 'CodenameSongView.hx').write_text('''class CodenameSongView {
 public var name:String; public function new(name:String) this.name=name;
}''')
            (base / 'Main.hx').write_text('''class Main {
 static function main():Void {
  var song=new CodenameSongView("first");
  var host=new PlayState();
  var view=new CodenamePlayStateFacade(host,function() return song);
  var interp=new hscript.Interp();
  interp.variables.set("PlayState",view);
  var parser=new hscript.Parser();
  PlayState.isStoryMode=true;
  interp.execute(parser.parseString("if (!PlayState.isStoryMode || PlayState.instance == null || PlayState.SONG.name != 'first' || PlayState.difficulty != 'Hard' || PlayState.variation != null || PlayState.chartingMode) throw 'static view'; PlayState.__loadSong('second','normal');"));
  if(PlayState.loaded!='second:normal') throw "source song selection";
  song=new CodenameSongView("replacement");
  interp.execute(parser.parseString("if (PlayState.SONG.name != 'replacement') throw 'stale song'; PlayState.resetSongInfos();"));
  if(PlayState.isStoryMode || PlayState.resets!=1) throw "story completion reset";
 }
}''')
            result = subprocess.run([
                str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', work,
                '--run', 'Main'
            ], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
