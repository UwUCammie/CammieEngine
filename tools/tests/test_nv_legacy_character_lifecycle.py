"""Compare historical character frame ordering with its pinned implementation."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_hit_order import extract_method

ROOT = Path(__file__).resolve().parents[2]
REV = '7f96eb3b5a60352413229bf134bd348b79ad5fe6'


class HistoricalCharacterLifecycleTest(unittest.TestCase):
    def test_actual_frame_and_dance_branches_against_pinned_source(self):
        donor = ROOT.parent / 'fnf_sources/NightmareVision'
        if not donor.is_dir():
            self.skipTest('pinned historical source unavailable')
        source = subprocess.check_output(['git', 'show', REV + ':source/gameObjects/Character.hx'], cwd=donor, text=True)
        reference_update = extract_method(source, 'override function update(elapsed:Float)')
        reference_update = reference_update.replace('trace("special done");', '')
        reference_dance = extract_method(source, 'public function dance()').replace(
            'public function dance()', 'override public function dance(forced:Bool = false)')
        host = (ROOT / 'source/Character.hx').read_text()
        host_update = extract_method(host, 'override function update(elapsed:Float)')
        host_update = extract_method(host_update, 'if (nightmareVisionLegacyActor)')
        host_dance = extract_method(host, 'public function dance(forced:Bool = false)')
        guard = host_dance[host_dance.index('if (skipDance ||'):host_dance.index('return;') + len('return;')]
        host_dance = guard + extract_method(host_dance, 'if (nightmareVisionLegacyActor)')
        fixture = r'''
using StringTools;
class Anim {
 public var name:String;public var finished:Bool=false;
 public function new(name:String,finished:Bool=false){this.name=name;this.finished=finished;}
}
class Controller {
 public var curAnim:Anim;public var names:Map<String,Bool>=[];
 public function new(){}
 public function getByName(n:String):Dynamic return names.exists(n)?{}:null;
}
class Ghost {
 var owner:Character;public function new(owner:Character)this.owner=owner;
 public function update(e:Float):Void owner.log.push('ghost:'+e);
}
class Conductor {public static var stepCrotchet:Float=125;public static var stepCrochet:Float=125;}
class Character {
 public var debugMode=false;public var isPlayer=false;public var specialAnim=false;
 public var animTimer=0.;public var heyTimer=0.;public var holdTimer=0.;public var singDuration=4.;
 public var forceDance=true;public var holding=true;public var voicelining=false;public var skipDance=false;
 public var danceIdle=false;public var danced=false;public var idleSuffix='';
 public var nightmareVisionLegacyActor=true;public var animation=new Controller();
 public var doubleGhosts:Array<Ghost>=[];public var log:Array<String>=[];public var finishOnUpdate=false;
 public function new(){doubleGhosts=[new Ghost(this)];}
 public function dance(forced:Bool=false):Void{}
 public function playAnim(n:String,force:Bool=false,rev:Bool=false,frame:Int=0):Void {
  log.push('play:'+n+':'+force+':'+heyTimer+':'+animTimer+':'+holdTimer);
  specialAnim=false;
  if(animation.getByName(n)!=null) animation.curAnim=new Anim(n);
 }
 public function callInterp(n:String,args:Array<Dynamic>):Void{}
 public function update(e:Float):Void {
  log.push('super');if(finishOnUpdate && animation.curAnim!=null)animation.curAnim.finished=true;
 }
 public function snapshot():String return haxe.Json.stringify([animTimer,heyTimer,holdTimer,specialAnim,danced,
  animation.curAnim==null?null:animation.curAnim.name,animation.curAnim==null?null:animation.curAnim.finished,log]);
}
class Reference extends Character {
 __REF_UPDATE__
 __REF_DANCE__
}
class Actual extends Character {
 override public function update(elapsed:Float):Void {__HOST_UPDATE__}
 override public function dance(forced:Bool=false):Void {__HOST_DANCE__}
}
class Main {
 static function main(){
  var names=['hey','cheer','singLEFT','singLEFT-return','holdLEFTStart','idle','custom'];
  for(name in names)for(mask in 0...1024)for(elapsed in [0.01,0.1,0.5]){
   var a=new Actual(),b=new Reference();
   for(c in ([a,b]:Array<Character>)){
    c.debugMode=mask&1!=0;c.isPlayer=mask&2!=0;c.specialAnim=mask&4!=0;
    c.animTimer=mask&8!=0?0.05:0;c.heyTimer=mask&16!=0?0.05:0;
    c.holdTimer=mask&32!=0?0.53:0;c.singDuration=mask%3+2;
    c.animation.curAnim=mask%17==0?null:new Anim(name,mask&64!=0);
    c.finishOnUpdate=mask&128!=0;c.danceIdle=mask&256!=0;c.idleSuffix=mask&512!=0?'-alt':'';
    c.skipDance=mask%13==0;c.voicelining=mask%7==0;
    for(n in names)c.animation.names.set(n,true);
    for(n in ['danceLeft','danceRight','singdLEFT'])c.animation.names.set(n,true);
    if(mask%3==0)c.animation.names.set(name+'-loop',true);
    if(mask%5==0)c.animation.names.set('holdLEFT',true);
    if(mask%11==0)c.animation.names.set('idle-alt',true);
   }
   for(frame in 0...3){
    a.update(elapsed);b.update(elapsed);
    if(a.snapshot()!=b.snapshot())throw name+'/'+mask+'/'+elapsed+'/'+frame+': '+a.snapshot()+' != '+b.snapshot();
   }
  }
 }
}
'''
        for name, value in {'REF_UPDATE': reference_update, 'REF_DANCE': reference_dance,
                            'HOST_UPDATE': host_update, 'HOST_DANCE': host_dance}.items():
            fixture = fixture.replace('__' + name + '__', value)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = FixturePath(folder)
            (work / 'Main.hx').write_text(fixture.replace('Character', 'FixtureActor').replace('NightmareVisionLegacyFixtureActorLifecycle', 'NightmareVisionLegacyCharacterLifecycle'))
            (work / 'Character.hx').write_text('typedef Character = Main.FixtureActor;')
            (work / 'NightmareVisionLegacyCharacterLifecycle.hx').write_text(
                (ROOT / 'source/NightmareVisionLegacyCharacterLifecycle.hx').read_text())
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
                                    cwd=ROOT, text=True, capture_output=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
