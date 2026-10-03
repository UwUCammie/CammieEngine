"""Freeplay search includes the separately rendered imported-source subtitle."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class FreeplaySourceSearchTest(unittest.TestCase):
    def test_title_display_and_resolved_source_subtitles_are_searchable(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/FreeplayState.hx").read_text()
        normalizer_start = source.index("\tpublic static function searchNorm(")
        matcher_start = source.index("\tfunction songMatches(i:Int):Bool {")
        normalizer = source[normalizer_start:matcher_start]
        matcher_end = source.index("\n\tfunction anyVisible()", matcher_start)
        matcher = source[matcher_start:matcher_end]
        fixture = '''
class SongMetadata {
 public var songName:String;
 public var display:String;
 public var sourceLabel:String;
 public var sourceResolved:Bool = false;
 public function new(name:String, title:String, source:String) {
  songName=name; display=title; sourceLabel=source;
 }
}
class FreeplayState {
 public var searchString:String='';
 public var songs:Array<SongMetadata>=[];
 public var legacySources:Map<String,String>=new Map();
 public function new() {}
 public function runMatch(index:Int):Bool return songMatches(index);
 function sourceDisplayFor(song:SongMetadata):Void {
  if (song.sourceResolved) return;
  song.sourceResolved=true;
  if (song.sourceLabel != '') return;
  var label=legacySources.get(song.songName);
  if (label != null) song.sourceLabel=label;
 }
''' + normalizer + matcher + '''
}
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  var state=new FreeplayState();
  state.songs=[
   new SongMetadata('legacy-id','Imported display title',''),
   new SongMetadata('explicit-id','Another display','Example Pack · Psych Engine'),
   new SongMetadata('base-song','A searchable base title','')
  ];
  state.legacySources.set('legacy-id','A Unique Package · Codename Engine');
  state.searchString='unique package';
  check(state.runMatch(0),'legacy provenance subtitle must be resolved and searchable');
  check(state.songs[0].sourceResolved,'subtitle resolution must use the row cache');
  state.searchString='psych engine';
  check(state.runMatch(1),'explicit sourceLabel must be searchable');
  state.searchString='searchable base';
  check(state.runMatch(2),'song display search must remain available');
  check(!state.songs[2].sourceResolved,'title hit should not resolve unrelated provenance');
  state.searchString='missing package';
  check(!state.runMatch(2),'unmatched base title and source must stay hidden');
  Sys.println('freeplay-source-search-ok');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("freeplay-source-search-ok", result.stdout)

    def test_source_resolves_lazy_subtitle_before_searching_its_label(self):
        source = (ROOT / "source/FreeplayState.hx").read_text()
        start = source.index("\tfunction songMatches(i:Int):Bool {")
        end = source.index("\n\tfunction anyVisible()", start)
        matcher = source[start:end]
        self.assertLess(matcher.index("sourceDisplayFor(song)"),
                        matcher.index("searchNorm(song.sourceLabel)"))
        self.assertIn("if (hay.indexOf(needle) != -1 || display.indexOf(needle) != -1)", matcher)


if __name__ == "__main__":
    unittest.main()
