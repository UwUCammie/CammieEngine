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
 def test_uncapped_convex_scale_and_decimal_format(self):
  self.run_haxe(r'''function chart(interval:Float):Dynamic {return {notes:[{mustHitSection:true,sectionNotes:[for(i in 0...400)[i*interval,i%4,0]]}]};}
   var easy=ChartDifficultyAnalysis.analyze(chart(250),[]);var hard=ChartDifficultyAnalysis.analyze(chart(160),[]);var extreme=ChartDifficultyAnalysis.analyze(chart(10),[]);
   function pressure(d:ChartDifficultyAnalysis.ChartDensity):Float return d.nps*0.65+d.sustainedNps*0.25+Math.sqrt(d.peakNps)*0.4;
   check(hard.difficulty-easy.difficulty>pressure(hard)-pressure(easy),"convex scale did not stretch harder charts");
   check(extreme.difficulty>20 && ChartDifficultyAnalysis.read(extreme)!=null,"extreme chart capped");
   check(extreme.difficulty!=Math.floor(extreme.difficulty),"rating rounded to integer");
   check(ChartDifficultyAnalysis.color(extreme)==0xFF05020C,"uncapped palette unsafe");
   check(ChartDifficultyAnalysis.twoDecimals(21474836.48)=="21474836.48","decimal formatting overflowed Int");
   check(ChartDifficultyAnalysis.twoDecimals(1.999)=="2.00","decimal carry");
   check(ChartDifficultyAnalysis.twoDecimals(Math.POSITIVE_INFINITY)=="?","nonfinite formatting");''')
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
   check(ChartDifficultyAnalysis.read(invalid)!=null,"uncapped rating rejected");invalid.difficulty=1.2;
   check(ChartDifficultyAnalysis.read(invalid)!=null,"fractional rating rejected");
   var before=analyze(a);var chart:Dynamic={speed:99,notes:[{mustHitSection:true,sectionNotes:a}]};
   check(ChartDifficultyAnalysis.analyze(chart,[]).difficulty==before.difficulty,"scroll speed affects rating");
   check(ChartDifficultyAnalysis.describe(before).indexOf('Difficulty Rating '+ChartDifficultyAnalysis.twoDecimals(before.difficulty))==0,"rating text absent");''')
 def test_note_scripts_are_classified_by_code_shape_only(self):
  self.run_haxe(r"""var freeze='function setupNote(note) {\n note.canMiss = true; // optional\n}\nfunction goodNoteHit(note) {\n getFieldFromID(0).inControl = false;\n}';
   var h=ChartMechanicScan.noteHazard(freeze,false);
   check(h!=null && h.avoid && h.inputLock && !h.lethal && !h.damage,"haxe input lock trap");
   h=ChartMechanicScan.noteHazard("function onCreate()\n setPropertyFromGroup('unspawnNotes', i, 'ignoreNote', true) -- skip\nend\nfunction goodNoteHit(id)\n setProperty('boyfriend.stunned', true)\n setProperty('health', getProperty('health') - 0.3)\nend",true);
   check(h!=null && h.avoid && h.inputLock && h.damage && !h.lethal,"lua stun and drain");
   h=ChartMechanicScan.noteHazard("function noteMiss(note) { game.health = 0; }",false);
   check(h!=null && h.lethal && !h.avoid && !h.inputLock,"lethal miss");
   h=ChartMechanicScan.noteHazard("function setupNote(note) { note.hitCausesMiss = true; }",false);
   check(h!=null && h.avoid && h.damage,"miss on hit is harmful");
   check(ChartMechanicScan.noteHazard("function setupNote(note) {\n // note.canMiss = true; inControl = false;\n /* health = 0; */\n note.missHealth = 0;\n healthBar.alpha = 0;\n health = 0.5;\n}",false)==null,"comments or lookalikes classified");
   check(ChartMechanicScan.noteHazard("x = x--1 -- not lua here\nnote.canMiss = true;",false)!=null,"haxe decrement treated as a lua comment");
   check(ChartMechanicScan.noteHazard("-- note.ignoreNote = true",true)==null && ChartMechanicScan.noteHazard(null,false)==null,"lua comment or null classified");
   check(ChartMechanicScan.safeOwner('assets/imported_mods/pack-1')=='assets/imported_mods/pack-1',"owner rejected");
   for(bad in ['assets/imported_mods/../x','assets/data/x','assets/imported_mods/a/b','C:/x','assets/imported_mods/'])check(ChartMechanicScan.safeOwner(bad)==null,"unsafe owner "+bad);
   check(ChartMechanicScan.safeOwner(5)==null && !ChartMechanicScan.safeName('a/b') && !ChartMechanicScan.safeName('..') && ChartMechanicScan.safeName('try-harder'),"names");
   check(ChartMechanicScan.isScript('Ice Note.hx') && ChartMechanicScan.isScript('a.LUA') && !ChartMechanicScan.isScript('hard.json') && ChartMechanicScan.isLua('a.lua') && !ChartMechanicScan.isLua('a.hx'),"script names");""")
 def test_modchart_estimate_needs_playfield_code(self):
  self.run_haxe(r"""function one(text:String,lua:Bool=false):Float return ChartMechanicScan.modchart([{text:text,lua:lua}]);
   check(ChartMechanicScan.modchart([])==0 && ChartMechanicScan.modchart(null)==0,"empty");
   check(one("function onCreatePost() { boyfriend.playAnim('flip'); add(new FlxSprite().makeGraphic(1,1)); animation.addByPrefix('idle','reverse'); }")==0,"ordinary words counted as modifiers");
   var light=one("modManager.queueEase(16, 20, 'drunk', 1, 'cubeOut');");
   var heavy=one("for (i in 0...4) modManager.queueSet(8, 'reverse' + i, 1);\nmodManager.queueEaseP(4, 8, 'opponentSwap', 50);\nmodManager.queueSet(1, \"stealth\", 1, 1);\nmodManager.queueEase(1, 2, 'transform0X', 5);\nmodManager.queueEase(1, 2, 'transformY-a', 5);\nmodManager.queueSet(2, 'drunk', 1);\nmodManager.queueSetP(3, 'noteSpawnTime', 2000);");
   check(light>0 && heavy>light*3 && heavy<=4,"variety not rewarded");
   check(one("// modManager.queueSet(1, 'reverse', 1);")==0,"commented modchart counted");
   var many=one([for(i in 0...400)"modManager.queueSet("+i+", 'drunk', 1);"].join("\n"));
   check(many<light*2.01,"repetition outweighed variety");
   var lua=one("function onBeatHit()\n noteTweenX('a', 4, 100, 0.5, 'quadOut')\n setPropertyFromGroup('playerStrums', 0, 'y', 50)\nend",true);
   check(lua>0 && one("function onUpdate() { playerStrums.members[0].x += 3; camHUD.angle = 5; if (playerStrums.members[0].x == 4) {} }")>0,"direct strum movement missed");
   check(one("if (playerStrums.members[0].x == 4) trace('same');")==0,"comparison counted as movement");
   check(ChartMechanicScan.modchart([],'{"events":[[0,[["Change Scroll Speed","2","1"]]]]}')>0,"speed events missed");
   check(ChartMechanicScan.modchartLabel(0.5)=='light' && ChartMechanicScan.modchartLabel(2)=='moderate' && ChartMechanicScan.modchartLabel(3.5)=='heavy',"labels");""")
 def test_script_context_raises_but_never_lowers_a_rating(self):
  self.run_haxe(r"""var rows:Array<Dynamic>=[];for(i in 0...120){rows.push([i*250,i%4,0]);if(i%4==0)rows.push([i*250,(i+2)%4,0,'Ice Note']);}
   var chart:Dynamic={notes:[{mustHitSection:true,sectionNotes:rows}]};
   var plain=ChartDifficultyAnalysis.analyze(chart,[]);
   var hazards:Map<String,ChartMechanicScan.NoteScriptHazard>=['ice note'=>{avoid:true,inputLock:true,damage:false,lethal:false}];
   var trapped=ChartDifficultyAnalysis.analyze(chart,[],false,{noteHazards:hazards,modchart:0});
   check(plain.mechanicNotes==0 && plain.modchart==0 && plain.unknownKinds==30,"no context changed analysis");
   check(trapped.mechanicNotes==30 && trapped.dangerNotes==30 && trapped.playerNotes==120 && trapped.unknownKinds==0,"trap counts");
   check(trapped.difficulty>plain.difficulty && trapped.chordNotes==plain.chordNotes,"trap lowered or flattened the rating");
   check(ChartDifficultyAnalysis.describe(trapped).indexOf('Input-lock notes: 30')>=0 && ChartDifficultyAnalysis.describe(plain).indexOf('Input-lock')<0,"mechanic line");
   var optional:Map<String,ChartMechanicScan.NoteScriptHazard>=['ice note'=>{avoid:true,inputLock:false,damage:false,lethal:false}];
   var skipped=ChartDifficultyAnalysis.analyze(chart,[],false,{noteHazards:optional});
   check(skipped.playerNotes==120 && skipped.dangerNotes==0 && skipped.chordNotes==0,"harmless optional note still counted");
   var required:Map<String,ChartMechanicScan.NoteScriptHazard>=['ice note'=>{avoid:false,inputLock:false,damage:false,lethal:true}];
   var risky=ChartDifficultyAnalysis.analyze(chart,[],false,{noteHazards:required});
   check(risky.playerNotes==150 && risky.missRiskNotes==30 && risky.difficulty>plain.difficulty,"required lethal note ignored");
   var moving=ChartDifficultyAnalysis.analyze(chart,[],false,{modchart:2});var extreme=ChartDifficultyAnalysis.analyze(chart,[],false,{modchart:400});
   check(moving.difficulty>plain.difficulty && extreme.difficulty<=plain.difficulty*1.3001 && extreme.difficulty>moving.difficulty,"modchart unbounded or ignored");
   check(ChartDifficultyAnalysis.describe(moving).indexOf('Modchart: moderate (2.00)')>=0,"modchart line");
   check(ChartDifficultyAnalysis.analyze(chart,[],false,{modchart:-5}).difficulty==plain.difficulty,"negative modchart lowered rating");
   check(ChartDifficultyAnalysis.read(haxe.Json.parse(haxe.Json.stringify(trapped)))!=null,"roundtrip with mechanics");
   var old:Dynamic=haxe.Json.parse(haxe.Json.stringify(plain));Reflect.deleteField(old,'modchart');check(ChartDifficultyAnalysis.read(old)==null,"analysis without mechanics accepted");
   var declared:Array<Dynamic>=[[0,0,0],[500,1,0,'Hurt Note']];
   var hurt=ChartDifficultyAnalysis.analyze({notes:[{mustHitSection:true,sectionNotes:declared}]},[],false,{noteHazards:hazards});
   check(hurt.dangerNotes==1 && hurt.playerNotes==1 && hurt.mechanicNotes==0,"declared danger notes changed");""")
if __name__=='__main__':unittest.main()
