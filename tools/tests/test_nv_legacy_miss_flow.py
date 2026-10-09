"""Compare missed-note orchestration with the pinned historical NV handler."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_hit_order import extract_method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class LegacyMissFlowTest(unittest.TestCase):
 def test_pinned_miss_order_duplicates_accounting_and_singer(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir(): self.skipTest('pinned historical source unavailable')
  src=subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
  ref=extract_method(src,'function noteMiss(').replace('function noteMiss(', 'public function sourceMiss(').replace('songMisses','PlayState.misses').replace('.gfNote','.forceGfSing')
  press=extract_method(src,'function noteMissPress(').replace('function noteMissPress(', 'public function sourcePress(').replace('songMisses','PlayState.misses').replace('ClientPrefs.ghostTapping','nightmareVisionPrefs.view.ghostTapping')
  press=press.replace("FlxG.sound.play(Paths.soundRandom('missnote', 1, 3), FlxG.random.float(0.1, 0.2));", 'playHistoricalNightmareMissSound();')
  retire=extract_method((ROOT/'source/PlayState.hx').read_text(),'function retireNightmareVisionLegacyDuplicate(').replace('function retire','public function retire')
  host=r'''
class PlayState {
 public var events:Array<String>=[];public var notes:Group;public var vocals:Voice;
 public var modchartObjects:Map<String,Dynamic>=[];public var health=1.;public var healthLoss=2.;public var combo=8;
 public var instakillOnMiss=false;public var practiceMode=false;public var endingSong=true;
 public static var misses=2;public var songScore=70;public var totalPlayed=3;
 public var boyfriend:Character;public var gf:Character;public var nightmareVisionPrefs:Dynamic={view:{ghostTapping:false}};
 public var singAnimations=['LEFT','DOWN','UP','RIGHT','EXTRA'];
 public function new(){notes=new Group(events);vocals=new Voice(events);boyfriend=new Character('bf',events);gf=new Character('gf',events);}
 public function playHistoricalNightmareMissSound(){events.push('sound');}
 public function broadcastHistoricalNightmareScripts(n:String,a:Array<Dynamic>):Dynamic {events.push(n+':'+a[0]);return 2;}
 public function callOnScripts(n:String,a:Array<Dynamic>):Dynamic return broadcastHistoricalNightmareScripts(n,a);
 public function updateScoreBar(){events.push('bar:'+combo+':'+songScore);}
 public function setSourceVocalVolume(role:String,v:Float){vocals.volume=v;}
 public function doDeathCheck(v:Bool){events.push('death:'+health+':'+misses);return false;}
 public function refreshSourceAccuracy(){}
 public function RecalculateRating(){events.push('rating:'+misses+':'+songScore+':'+totalPlayed+':'+combo+':'+health);}
 public function callOnLuas(n:String,a:Array<Dynamic>):Dynamic {events.push('lua:'+n+':'+haxe.Json.stringify(a));return 2;}
 public function callOnHScripts(n:String,a:Array<Dynamic>):Dynamic {events.push('hscript:'+n+':'+cast(a[0],Note).ID);return 2;}
 public function callScript(s:Dynamic,n:String,a:Array<Dynamic>){}
 public function dispatchHistoricalNightmareNoteHit(n:Note,c:String){callOnLuas(c,[notes.members.indexOf(n),n.noteData,n.noteType,n.isSustainNote,n.ID]);callOnHScripts(c,[n]);}
 public function publishHistoricalNightmareMiss(n:Note){}
 public function nightmareVisionRemoveFieldNoteMembership(n:Note){n.member=false;}
 __RETIRE__
}
class Voice {public var volume(default,set):Float=1;var log:Array<String>;public function new(l){log=l;}function set_volume(v:Float){log.push('voice:'+v);return volume=v;}}
class Group {
 public var members:Array<Note>=[];var log:Array<String>;public function new(l){log=l;}
 public function forEachAlive(f:Note->Void){for(n in members)if(n!=null&&n.exists&&n.alive)f(n);}
 public function remove(n:Note,splice:Bool){log.push('remove:'+n.ID);if(splice)members.splice(members.indexOf(n),1);else members[members.indexOf(n)]=null;return n;}
}
'''.replace('__RETIRE__',retire)
  note=r'''
class Note {
 public var ID:Int;public var exists=true;public var alive=true;public var member=true;
 public var noteData=2;public var strumTime=100.;public var isSustainNote=false;public var mustPress=false;
 public var playField:NightmareVisionPlayFieldView;public var missHealth=0.08;public var forceGfSing=false;
 public var noteType='';public var noMissAnimation=false;public var canMiss=true;public var blockHit=false;
 public var noteScript:Dynamic=null;var log:Array<String>;
 public function new(id:Int,l:Array<String>){ID=id;log=l;playField=new NightmareVisionPlayFieldView();}
 public function kill(){log.push('kill:'+ID);alive=false;exists=false;}
 public function destroy(){log.push('destroy:'+ID);}
}
'''
  char='class Character {public var animOffsets:Map<String,Array<Dynamic>>=[];public var hasMissAnimations=true;public var animTimer=0.;public var voicelining=false;public var stunned=true;var name:String;var log:Array<String>;public function new(n,l){name=n;log=l;}public function playAnim(a:String,f:Bool=false){log.push(name+":"+a+":"+f);}}'
  main=r'''
class Main {
 static function setup(s:PlayState,mask:Int,negative:Bool):Note {
  s.practiceMode=mask&1!=0;s.instakillOnMiss=mask&2!=0;
  var n=new Note(1,s.events);n.forceGfSing=mask&4!=0;n.noMissAnimation=mask&8!=0;
  for(c in [s.boyfriend,s.gf]){c.animTimer=mask&16!=0?1:0;c.voicelining=mask&32!=0;c.hasMissAnimations=mask&64==0;}
  n.playField.playerControls=mask&128!=0;n.noteType=mask&256!=0?'Alt Animation':'custom';n.canMiss=mask&512!=0;n.blockHit=mask&1024!=0;n.isSustainNote=mask&2048!=0;
  if(negative)n.noteData=-2;
  s.notes.members.push(n);
  for(i in 2...10){var d=new Note(i,s.events);d.noteData=n.noteData;d.isSustainNote=n.isSustainNote;
   d.strumTime=100.5;if(i==4)d.strumTime=101;if(i==5)d.alive=false;if(i==6)d.exists=false;if(i==7)d.noteData=4;if(i==8)d.isSustainNote=!n.isSustainNote;
   s.notes.members.push(d);s.modchartObjects.set('note'+i,d);
  }
  if(mask&4!=0&&mask&16!=0)s.gf=null;
  return n;
 }
 static function main(){for(mask in 0...4096)for(negative in [false,true]){
  var a=new PlayState(),b=new Reference();var an=setup(a,mask,negative),bn=setup(b,mask,negative);
  PlayState.misses=2;NightmareVisionLegacyMissFlow.miss(a,an);var gotMisses=PlayState.misses;PlayState.misses=2;b.sourceMiss(bn);
  if(a.events.join('|')!=b.events.join('|'))throw 'order '+mask+': '+a.events+' != '+b.events;
  if(a.health!=b.health||a.combo!=b.combo||a.songScore!=b.songScore||gotMisses!=PlayState.misses||a.totalPlayed!=b.totalPlayed)throw 'accounting';
  if(!an.alive||!an.exists)throw 'missed note retired early';
  for(i in 2...10)if(a.modchartObjects.exists('note'+i)!=b.modchartObjects.exists('note'+i))throw 'stale duplicate alias';
  if(a.notes.members.length!=b.notes.members.length)throw 'duplicate count';
 }
 for(mask in 0...2048)for(anim in [false,true])for(direction in [-2,2]){
  var a=new PlayState(),b=new Reference();
  for(s in [a,b]){
   s.nightmareVisionPrefs.view.ghostTapping=mask&1!=0;s.boyfriend.stunned=mask&2!=0;
   s.practiceMode=mask&4!=0;s.endingSong=mask&8!=0;s.instakillOnMiss=mask&16!=0;
   s.combo=mask&32!=0?5:6;s.boyfriend.hasMissAnimations=mask&64!=0;
   s.boyfriend.animTimer=mask&128!=0?1:0;s.boyfriend.voicelining=mask&256!=0;
   if(mask&512!=0)s.gf=null;else if(mask&1024!=0)s.gf.animOffsets.set('sad',[]);
  }
  PlayState.misses=2;NightmareVisionLegacyMissFlow.press(a,direction,anim);var gotMisses=PlayState.misses;
  PlayState.misses=2;b.sourcePress(direction,anim);
  if(a.events.join('|')!=b.events.join('|'))throw 'press order '+mask+': '+a.events+' != '+b.events;
  if(a.health!=b.health||a.combo!=b.combo||a.songScore!=b.songScore||gotMisses!=PlayState.misses||a.totalPlayed!=b.totalPlayed)throw 'press accounting';
 }
 }
}
'''
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder)
   files={'Main':main,'PlayState':host,'Reference':'class Reference extends PlayState {public function new(){super();}'+ref+press+'}','Note':note,'Character':char,'NightmareVisionPlayFieldView':'class NightmareVisionPlayFieldView {public var playerControls=true;public function new(){}}'}
   for name in ['NightmareVisionLegacyMissFlow','SourceMissDuplicates','SourceScoreLedger','SourceHealthDelta']:files[name]=(ROOT/'source'/f'{name}.hx').read_text()
   for name,text in files.items():(work/f'{name}.hx').write_text(text,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
