"""Authored rating names/scales survive conversion and host difficulty reordering."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND

ROOT=Path(__file__).resolve().parents[2]

class DifficultyRatingTest(unittest.TestCase):
    def test_real_vslice_conversion_and_strict_rating_resolution(self):
        fixture=r'''class Main {
 static function check(ok:Bool,message:String):Void {if(!ok) throw message;}
 static function main() {
  var metadata:Dynamic={version:"2.2.4",songName:"rating-fixture",artist:"fixture",timeChanges:[{t:0,bpm:120}],playData:{difficulties:["nightmare","normal"],ratings:{normal:0,nightmare:17},characters:{player:"bf",opponent:"dad",girlfriend:"gf"},stage:"stage"}};
  var chart:Dynamic={version:"2.0.0",scrollSpeed:{normal:1,nightmare:1},notes:{normal:[],nightmare:[]},events:[]};
  var before=haxe.Json.stringify(metadata);
  var converted=VSliceImporter.convert(metadata,chart,"fixture");
  check(converted.charts.length==2,"both source difficulties must convert");
  for (entry in converted.charts) {
   var ratings=FreeplayDifficultyRating.read(Reflect.field(entry.chart.song,"authoredDifficultyRatings"));
   check(FreeplayDifficultyRating.resolve(ratings,"NIGHTMARE").value==17,"named value lost");
   check(FreeplayDifficultyRating.resolve(ratings,"normal").value==0,"authored zero treated as absent");
   check(FreeplayDifficultyRating.resolve(ratings,"hard")==null,"invented rating for unsupported difficulty");
   check(FreeplayDifficultyRating.resolve(ratings,"normal").scale=="V-Slice","source scale lost");
   check(FreeplayDifficultyRating.label(ratings,"nightmare")=="Authored rating: 17.00 (V-Slice)","display changed source value");
  }
  var imported=FreeplayDifficultyRating.forImport({convertedCharts:converted.charts});
  check(FreeplayDifficultyRating.resolve(imported,"nightmare").value==17,"registry export lost converted rating table");
  var old=FreeplayDifficultyRating.forImport({difficultyRatings:[1,2,3]});
  check(old.length==0,"legacy array guessed a host difficulty order");
  check(haxe.Json.stringify(metadata)==before,"conversion mutated donor metadata");
  var bad=FreeplayDifficultyRating.named({hard:"12",normal:true,easy:-1,expert:Math.NaN,extreme:Math.POSITIVE_INFINITY},"V-Slice");
  check(bad.length==0,"coerced invalid rating");
  check(FreeplayDifficultyRating.read([1,2,3]).length==0,"assumed unnamed array order");
  var collision=FreeplayDifficultyRating.named(haxe.Json.parse('{"HARD":3,"hard":4}'),"V-Slice");
  check(FreeplayDifficultyRating.resolve(collision,"hard")==null,"ambiguous keys accepted");
  var source:Dynamic=[{difficulty:" CUSTOM ",value:2.5,scale:"source-stars"}];
  var entries=FreeplayDifficultyRating.read(source);source[0].value=99;
  check(FreeplayDifficultyRating.resolve(entries,"custom").value==2.5,"retained mutable source reference");
  check(FreeplayDifficultyRating.resolve(entries,"normal")==null,"custom rating became default difficulty");
  check(FreeplayDifficultyRating.label([],"normal")=="Authored rating: Unknown","missing value fabricated");
  Sys.println("rating-contract-ok");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'Main.hx').write_text(fixture)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',folder,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('rating-contract-ok',result.stdout)
