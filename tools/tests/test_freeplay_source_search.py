"""Freeplay search includes the separately rendered imported-source subtitle."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from test_native_asset_resolution import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class FreeplaySourceSearchTest(unittest.TestCase):
    def test_title_display_and_resolved_source_subtitles_are_searchable(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/FreeplayState.hx").read_text()
        normalizer = extract_method(source, 'public static function searchNorm(')
        matcher = extract_method(source, 'function songMatches(')
        fixture = '''
class UserLibrary {
 public static var model = new UserLibraryData();
 public static function data():UserLibraryData return model;
}
class SongMetadata {
 public var songName:String;
 public var display:String;
 public var sourceLabel:String;
 public var sourceResolved:Bool = false;
 public var ownerRoot:String = "";
 public function new(name:String, title:String, source:String) {
  songName=name; display=title; sourceLabel=source;
 }
}
class FreeplayState {
 public var searchString:String='';
 public var soundTest=false;
 public var favoritesOnly=false;
 public var libraryViewId="";
 public var categoryFilters:Array<String>=[];
 function libraryOwner(i:Int):String return songs[i].sourceLabel;
 function libraryChartKey(i:Int):String return songs[i].songName;
 function libraryHidden(i:Int):Bool return false;
 public var songs:Array<SongMetadata>=[];
 public var legacySources:Map<String,String>=new Map();
 public var identityReads=0;
 function resolveSongIdentity(song:SongMetadata):Void {identityReads++;}
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
  UserLibrary.model.setFavorite('explicit-id',true);
  state.favoritesOnly=true;state.searchString='';
  check(state.runMatch(1) && !state.runMatch(0) && !state.runMatch(2),'favorites subset');
  state.searchString='psych';check(state.runMatch(1),'favorites compose with source search');
  state.searchString='unique';check(!state.runMatch(0) && !state.runMatch(1),'search cannot bypass favorites');
  check(!state.runMatch(-1) && !state.runMatch(3),'invalid selection');
  state.favoritesOnly=false;check(state.runMatch(0),'clearing filter restores registry rows');
  var category=UserLibrary.model.createCategory('Imported');
  UserLibrary.model.setMembership(category,state.songs[1].sourceLabel,true);
  state.categoryFilters=[category];state.searchString='';
  check(state.runMatch(1) && !state.runMatch(0) && !state.runMatch(2),'category filter');
  state.favoritesOnly=true;state.searchString='psych';check(state.runMatch(1),'three filters compose');
  state.searchString='unique';check(!state.runMatch(0) && !state.runMatch(1),'search cannot bypass category');
  state.favoritesOnly=false;state.categoryFilters=[];check(state.runMatch(0),'clearing categories restores rows');
  check(state.identityReads==0,'ordinary title/source search read package identities');
  state.songs[0].ownerRoot='assets/imported_mods/first';state.songs[1].ownerRoot='assets/imported_mods/second';
  state.searchString=LibraryPackageLabel.badge(state.songs[1].ownerRoot);
  check(!state.runMatch(0) && state.runMatch(1),'package badge search mixed owners');
  state.favoritesOnly=true;check(!state.runMatch(0) && state.runMatch(1),'badge query bypassed favorite selection');
  state.categoryFilters=[category];check(state.runMatch(1),'badge query lost category membership');
  Sys.println('freeplay-source-search-ok');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "Main.hx").write_text(fixture, newline='\n')
            Path(folder, "UserLibraryData.hx").write_text((ROOT/"source/UserLibraryData.hx").read_text())
            Path(folder, "LibraryHistoryData.hx").write_text((ROOT/"source/LibraryHistoryData.hx").read_text())
            Path(folder, "LibraryPackageLabel.hx").write_text((ROOT/"source/LibraryPackageLabel.hx").read_text())
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
