"""Compare historical actor events with pinned source over shared animation services."""
from pathlib import Path
import re,subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
EVENTS=['Hey!','Set GF Speed','Play Animation','Alt Idle Animation']
HOST=r'''using StringTools;
class PlayState {
 public var boyfriend:Character=new Character('bf');public var dad:Character=new Character('dad');public var gf:Character=new Character('gf');
 public var sourceScoreOwner=true;public var sourceScoreNightmare=true;public var nightmareVisionLegacyFieldCameras=true;
 public var nightmareVisionScripts:Dynamic={};public var gfGroup:Dynamic={};public var gfSpeed(default,set):Int=1;
 public function new(){}
 __METHODS__
 __REFERENCE__
 public function snapshot():String return [Std.string(gfSpeed),Character.snapshot(boyfriend),Character.snapshot(dad),Character.snapshot(gf)].join('|');
}
'''
CHAR=r'''class ActorFrame {public var name:String='idle';public function new(){}}
class ActorAnimation {public var curAnim:ActorFrame=new ActorFrame();public function new(){}}
class Character {
 public var curCharacter:String;public var specialAnim=false;public var heyTimer:Float=0;
 public var idleSuffix='';public var danceEveryNumBeats=2;public var danceEvery=2;public var stunned=false;public var codenameLiveDefinition:Dynamic=null;
 public var animation=new ActorAnimation();public var events:Array<String>=[];
 public function new(n:String)curCharacter=n;
 public function playAnim(n:String,f:Bool){events.push('play:'+n+':'+f+':'+specialAnim+':'+heyTimer);animation.curAnim.name=n;}
 public function recalculateDanceIdle(){events.push('recalculate:'+idleSuffix);}
 public static function snapshot(c:Character):String return c==null?'null':[c.curCharacter,Std.string(c.specialAnim),Std.string(c.heyTimer),c.idleSuffix,Std.string(c.danceEveryNumBeats),c.events.join(',')].join(':');
}'''
MAIN=r'''@:access(PlayState) class Main {
 static function run(actual:Bool,n:String,a:String,b:String,mode:Int):String {
  var s=new PlayState();if(mode==1)s.gf=null;if(mode==2)s.dad.curCharacter='gf-car';if(mode==3)s.boyfriend=null;if(mode==4){s.sourceScoreOwner=false;s.sourceScoreNightmare=false;}
  var error=false;try{if(actual)NightmareVisionLegacyActorEvents.apply(s,n,a,b);else s.reference(n,a,b);}catch(_:Dynamic)error=true;
  return s.snapshot()+'#'+error;
 }
 static function main() {
  var values:Array<String>=[null,'','bad','0','1','2','3','1.5','-1','bf','GF',' girlfriend ','hey','  -alt  '];var count=0;
  for(n in __EVENTS__)for(a in values)for(b in values)for(mode in 0...5) {
   var expected=run(false,n,a,b,mode);var actual=run(true,n,a,b,mode);
   if(expected!=actual)throw n+':'+a+':'+b+':'+mode+'\n'+expected+'\n'+actual;count++;
  }
  var s=new PlayState();s.gfSpeed=2;s.gfSpeed=2;
  if(s.gf.danceEveryNumBeats!=2||s.girlfriendDanceDue(2)||!s.girlfriendDanceDue(4))throw 'historical stored cadence';
  s.gf.stunned=true;if(s.girlfriendDanceDue(4))throw 'stunned cadence';s.gf.stunned=false;
  s.gf.animation.curAnim.name='singLEFT';if(s.girlfriendDanceDue(4))throw 'sing cadence';s.gf.animation.curAnim=null;if(s.girlfriendDanceDue(4))throw 'absent animation';
  var cadence=0;
  for(speed in [-2,0,1,2,3])for(base in [0,1,2,3])for(beat in -1...7)for(mode in 0...4) {
   var actor=new PlayState();actor.gfSpeed=speed;actor.gf.danceEveryNumBeats=base;
   if(mode==1)actor.gf.stunned=true;if(mode==2)actor.gf.animation.curAnim.name='singLEFT';if(mode==3)actor.gf=null;
   if(actor.sourceGfDue(beat)!=actor.girlfriendDanceDue(beat))throw 'cadence '+speed+':'+base+':'+beat+':'+mode;cadence++;
  }
  trace(count+' pinned actor event cases and '+cadence+' cadence cases verified');
 }
}'''
class HistoricalActorEventsTest(unittest.TestCase):
 def test_pinned_arguments_actor_effects_and_cadence(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  src=subprocess.check_output(['git','show','7f96eb3b5a60352413229bf134bd348b79ad5fe6:source/meta/states/PlayState.hx'],cwd=donor,text=True)
  raw=extract_method(src,'function triggerEventNote(')
  cases=re.split(r'(?=^\t\t\tcase )',raw,flags=re.M)
  selected=[c for c in cases if (m:=re.match(r"\t\t\tcase '([^']+)':",c)) and m[1] in EVENTS]
  reference='public function reference(eventName:String,value1:String,value2:String){switch(eventName){'+''.join(selected)+'}}'
  beat=extract_method(src,'function beatHit(')
  gate=re.search(r'if \((gf != null.*?)\)\s*\{',beat,re.S)
  self.assertIsNotNone(gate)
  reference+='public function sourceGfDue(beat:Int):Bool return '+gate[1].replace('curBeat','beat')+';'
  play=(ROOT/'source/PlayState.hx').read_text()
  methods='\n'.join(extract_method(play,'function '+n+'(') for n in ['set_gfSpeed','sourceHeyEvent','sourceAnimationEventActor','playSourceEventAnimation','applySourceAltIdleAnimation','girlfriendDanceDue','characterDanceDue'])
  files={'PlayState.hx':HOST.replace('__METHODS__',methods).replace('__REFERENCE__',reference),'Character.hx':CHAR,'Main.hx':MAIN.replace('__EVENTS__',str(EVENTS))}
  for name in ['NightmareVisionLegacyActorEvents','PsychHeyEventCompat']:files[name+'.hx']=(ROOT/('source/'+name+'.hx')).read_text()
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder)
   for name,content in files.items():(work/name).write_text(content)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  self.assertIn('girlfriendDanceDue(tmr.loopsLeft)',play)
if __name__=='__main__':unittest.main()
