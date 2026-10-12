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
   check(Math.abs(d.nps-2/6)<0.0001 && d.peakNps==1,"chord sustained density");
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
   check(d.sustainedNps > 8,"consistent rate lost");
   check(ChartDifficultyAnalysis.read(haxe.Json.parse(haxe.Json.stringify(d)))!=null,"roundtrip");
   d.version=-1;check(ChartDifficultyAnalysis.read(d)==null,"stale accepted");
   var easy=ChartDifficultyAnalysis.analyze({notes:[]},[]);
   check(easy.playerNotes==0 && easy.nps==0 && !ChartDifficultyAnalysis.shadow(easy),"empty invalid");
   check(ChartDifficultyAnalysis.color(easy)==0xFF4290FB,"easy not blue");''')
 def test_sparse_native_heads_and_brief_bursts(self):
  self.run_haxe(r'''var sparse=ChartDifficultyAnalysis.analyze({notes:[{mustHitSection:true,sectionNotes:[[0,0],[1000,1],[2000,2,0]]}]},[]);
   check(sparse.playerNotes==3 && sparse.nps==0.75,"native no-sustain heads were omitted");
   check(ChartDifficultyAnalysis.describe(sparse).indexOf('NPS 0.75 / peak 1.00')>=0,"NPS not fixed to two decimals");
   var burst:Array<Dynamic>=[for(i in 0...40)[10000+i*25,0,0]];burst.push([120000,4,0]);
   var d=ChartDifficultyAnalysis.analyze({notes:[{mustHitSection:true,sectionNotes:burst}]},[]);
   check(d.peakNps==20,"isolated peak missing");
   var fast:Array<Dynamic>=[for(i in 0...2400)[i*50,0,0]];
   d=ChartDifficultyAnalysis.analyze({notes:[{mustHitSection:true,sectionNotes:fast}]},[]);
   check(ChartDifficultyAnalysis.shadow(d),"sustained extreme chart lost shadow");
   d.difficulty=20*2/9;check(ChartDifficultyAnalysis.color(d)==0xFF4CFF86,"middle palette green missing");
   d.difficulty=20;check(ChartDifficultyAnalysis.color(d)==0xFF05020C,"top palette black missing");''')
 def test_real_native_erect_chart_counts_sparse_rows(self):
  self.run_haxe(r'''var song=haxe.Json.parse(sys.io.File.getContent('assets/data/bopeebo/bopeebo-erect.json'));
   var d=ChartDifficultyAnalysis.analyze(song,[]);var expected=0;
   for(s in (cast song.song.notes:Array<Dynamic>))for(n in (cast s.sectionNotes:Array<Dynamic>))
    if(n.length>=2 && n[1]>=0 && ChartNoteOwnership.mustPress(null,n[1],s.mustHitSection,4))expected++;
   check(d.playerNotes==expected && expected>100,"Erect omitted short native rows");''')
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
 def test_breaks_holds_chords_and_lethal_hazards(self):
  self.run_haxe(r'''function analyze(rows:Array<Dynamic>,defs:Array<Dynamic>=null):ChartDifficultyAnalysis.ChartDensity return ChartDifficultyAnalysis.analyze({notes:[{mustHitSection:true,sectionNotes:rows}]},defs==null?[]:defs);
   var a:Array<Dynamic>=[for(i in 0...80)[i*200,0,0]];
   var shifted:Array<Dynamic>=[for(row in a)[row[0]+60000,row[1],row[2]]];
   var d=analyze(a);var e=analyze(shifted);
   check(d.nps==e.nps && d.difficulty==e.difficulty && d.sustainedNps==e.sustainedNps,"initial break changed rating");
   var split:Array<Dynamic>=[for(row in a)[row[0]+(row[0]>=8000?60000:0),row[1],row[2]]];
   e=analyze(split);check(Math.abs(d.difficulty-e.difficulty)<=1 && Math.abs(d.nps-e.nps)<0.6,"long break diluted rating");
   var singles=analyze([[0,0,0],[60000,0,0],[120000,0,0]]);
   check(singles.nps==0.5 && singles.difficulty<=2,"isolated heads became extreme");
   var longHold=analyze([[0,0,60000]]);check(longHold.activeSeconds>=60 && longHold.nps<0.02,"hold excluded from activity");
   var chords:Array<Dynamic>=[];for(row in a){chords.push(row);chords.push([row[0],1,1000]);}
   var chord=analyze(chords);check(chord.chordNotes==160 && chord.chordStrain>0 && chord.difficulty>d.difficulty,"chords did not compound");
   var tapping:Array<Dynamic>=a.copy();tapping.insert(0,[0,1,16000]);var held=analyze(tapping);
   check(held.sustainTapNotes>60 && held.sustainTapStrain>0 && held.difficulty>d.difficulty,"hold plus taps ignored");
   var mine=analyze([[0,8,0],[1000,0,0]]);var nuke=analyze([[0,24,0],[1000,0,0]]);
   check(mine.lethalDangerNotes==0 && nuke.lethalDangerNotes==1 && nuke.difficulty>mine.difficulty,"native lethal bank lost");
   var hazards:Array<Dynamic>=[for(i in 0...20)[i*200,0,0,'Spike']];
   var mild=analyze(hazards,[{sourceNoteType:'Spike',damageAmount:-0.04}]);
   var lethal=analyze(hazards,[{sourceNoteType:'Spike',damageAmount:-2}]);
   check(lethal.lethalDangerNotes==20 && mild.lethalDangerNotes==0 && lethal.difficulty>mild.difficulty,"health depletion ignored");
   var healing=analyze([[0,0,0,'Heal']],[{sourceNoteType:'Heal',damageAmount:2}]);
   check(healing.dangerNotes==0,"positive health became lethal");
   var required=analyze([[0,0,0,'Risk'],[1000,1,0,'Risk']],[{sourceNoteType:'Risk',damageMultiplier:50}]);
   check(required.playerNotes==2 && required.dangerNotes==0 && required.missRiskNotes==2,"miss damage excluded required heads");
   var opponent=ChartDifficultyAnalysis.analyze({notes:[{mustHitSection:false,sectionNotes:[[0,0,0],[0,1,0],[0,24,0]]}]},[]);
   check(opponent.playerNotes==0 && opponent.dangerNotes==0 && opponent.chordNotes==0,"opponent pressure counted");
   var longRest:Array<Dynamic>=[for(row in split)[row[0]+(row[0]>=60000?60000:0),row[1],row[2]]];
   var longer=analyze(longRest);check(longer.nps==e.nps && longer.difficulty==e.difficulty,"rest length affects rating");
   var invalid:Dynamic=haxe.Json.parse(haxe.Json.stringify(required));invalid.difficulty=21;
   check(ChartDifficultyAnalysis.read(invalid)==null,"out of scale rating accepted");invalid.difficulty=1.2;
   check(ChartDifficultyAnalysis.read(invalid)==null,"fractional rating accepted");
   var before=analyze(a);var chart:Dynamic={speed:99,notes:[{mustHitSection:true,sectionNotes:a}]};
   check(ChartDifficultyAnalysis.analyze(chart,[]).difficulty==before.difficulty,"scroll speed affects rating");
   check(ChartDifficultyAnalysis.describe(before).indexOf('Difficulty Rating '+Std.int(before.difficulty)+'/20')==0,"rating text absent");''')
if __name__=='__main__':unittest.main()
