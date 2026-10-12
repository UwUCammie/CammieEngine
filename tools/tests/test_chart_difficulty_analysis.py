"""Real Haxe analysis: ownership, density, hazards, timing and versioned data."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]
class ChartDifficultyTest(unittest.TestCase):
 def run_haxe(self, body):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
   Path(temp,'Main.hx').write_text("class Main {static function check(ok:Bool,s:String){if(!ok)throw s;} static function main(){"+body+"}}")
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_sides_chords_sustains_and_dangers(self):
  self.run_haxe(r'''var rows:Array<Dynamic>=[[0,0,5000],[0,1,0],[1000,2,0,"Hurt Note"],[2000,4,0],[3000,3,0,"Can't Hit"]];
   var song:Dynamic={song:{notes:[{mustHitSection:true,sectionNotes:rows}]}};
   var before=haxe.Json.stringify(song);var d=ChartDifficultyAnalysis.analyze(song,[]);
   check(d.playerNotes==2 && d.dangerNotes==1 && d.seconds==5,"counts/duration");
   check(d.nps==0.4 && d.peakNps==1,"chord sustained density");
   check(haxe.Json.stringify(song)==before,"mutated chart");
   song.song.format='psych_v1';song.song.notes[0].mustHitSection=false;
   check(ChartDifficultyAnalysis.analyze(song,[]).playerNotes==2,"absolute sides");
   song.song.notes[0].sectionNotes=[[0,8,0],[1000,0,0],[2000,4,0]];song.song.format='nmv2';
   d=ChartDifficultyAnalysis.analyze(song,[],true);check(d.playerNotes==1,"autoplay extra fields counted");''')
 def test_fast_hazards_thresholds_and_unknowns(self):
  self.run_haxe(r'''var rows:Array<Dynamic>=[for(i in 0...48) [i*80,0,0]];
   rows.push([1900,1,0,'Hurt Note']);rows.push([2000,2,0,'Custom']);
   var d=ChartDifficultyAnalysis.analyze({notes:[{mustHitSection:true,sectionNotes:rows}]},[]);
   check(d.dangersInFastSections==1 && d.unknownKinds==1,"fast hazard/unknown");
   check(ChartDifficultyAnalysis.shadow(d),"extreme density lacks shadow");
   check(ChartDifficultyAnalysis.read(haxe.Json.parse(haxe.Json.stringify(d)))!=null,"roundtrip");
   d.version=-1;check(ChartDifficultyAnalysis.read(d)==null,"stale accepted");
   var easy=ChartDifficultyAnalysis.analyze({notes:[]},[]);
   check(easy.playerNotes==0 && easy.nps==0 && !ChartDifficultyAnalysis.shadow(easy),"empty invalid");
   check(ChartDifficultyAnalysis.color(easy)==0xFF55E68A,"easy not green");''')
 def test_metadata_and_malformed_notes(self):
  self.run_haxe(r'''var rows:Array<Dynamic>=[[0,0,0,'Spike'],[1000,1,0],[-1,0,0],[5,-1,0],[2,0.5,0],null];
   var d=ChartDifficultyAnalysis.analyze({notes:[{mustHitSection:true,sectionNotes:rows}]},[{sourceNoteType:'Spike',damageAmount:-1}]);
   check(d.playerNotes==1 && d.dangerNotes==1,"custom semantics/malformed input");
   check(ChartDifficultyAnalysis.analyze({notes:'wrong'},[])==null,"invalid chart accepted");
   check(PlayPerformance.label(null).indexOf('--')>=0,"old score invented");
   check(PlayPerformance.read({misses:-1,maxCombo:2,totalPlayerNotes:3})==null,"invalid stats");
   check(PlayPerformance.label({misses:2,maxCombo:90,totalPlayerNotes:100}).indexOf('90 / 100')>=0,"stats missing");''')
 def test_density_sort_and_favorites(self):
  self.run_haxe(r'''var d=ChartDifficultyAnalysis.analyze({notes:[{mustHitSection:true,sectionNotes:[[0,0,0],[2000,0,0]]}]},[]);
   var a=LibraryChartMetric.read('x',[],'npsHigh','normal',0,[0],function(_,_) return null,d);
   check(a!=null && a.value==d.difficulty,"metric missing");
   check(LibraryChartMetric.read('x',[],'npsHigh','hard',1,[0],function(_,_) return null,d)==null,"wrong difficulty");
   var data=new UserLibraryData();data.setSorting('flat','default','npsHigh');
   check(UserLibraryData.decode(data.encode()).sorting().charts=='npsHigh',"sort persistence");''')
if __name__=='__main__':unittest.main()
