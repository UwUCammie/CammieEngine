"""Source-version event admission and animation carry, independent of cache internals."""
from pathlib import Path
import re,subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
LEGACY='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
HOST=r'''using StringTools;
class PlayState {
 public var nightmareVisionLegacyFieldCameras:Bool;
 public var boyfriend:Character=new Character('bf');public var dad:Character=new Character('dad');public var gf:Character=new Character('gf');
 public var target:Character=new Character('replacement');public var redirected:Character=new Character('redirected');
 public var mode:Int;public var calls:Array<String>=[];
 public function new(legacy:Bool,mode:Int){nightmareVisionLegacyFieldCameras=legacy;this.mode=mode;}
 function actor(type:Int):Character return type==2?gf:type==1?dad:boyfriend;
 function assign(type:Int,c:Character){if(type==2)gf=c;else if(type==1)dad=c;else boyfriend=c;}
 function publishNightmareVisionCharacter(name:String,type:Int):Character {
  calls.push('publish:'+name+':'+type);
  if(mode==11)throw 'publication failure';
  if(type>=0&&type<=2){assign(type,target);if(mode==10)assign(type,redirected);}
  return target;
 }
 function changeCharacter(name:String,type:Int):Void {publishNightmareVisionCharacter(name,type);}
 __METHOD__
 __REFERENCE__
 public function snapshot():String return [calls.join(','),Character.snapshot(boyfriend),Character.snapshot(dad),Character.snapshot(gf),Character.snapshot(target),Character.snapshot(redirected)].join('|');
}
'''
CHAR=r'''class Frame {
 public var name:String;public var curFrame:Int;
 public function new(n:String,f:Int=0){name=n;curFrame=f;}
}
class Controller {
 public var curAnim:Frame=new Frame('singLEFT',3);public var allowed:Array<String>=['idle','singLEFT'];
 public function new(){}
 public function getByName(n:String):Frame return allowed.indexOf(n)<0?null:new Frame(n);
}
class Character {
 public var curCharacter:String;public var animation:Controller=new Controller();public var played:Array<String>=[];
 public var animCurFrame(get,set):Int;
 function get_animCurFrame():Int return animation.curAnim.curFrame;
 function set_animCurFrame(v:Int):Int return animation.curAnim.curFrame=v;
 public function isAnimNull():Bool return animation==null||animation.curAnim==null;
 public function getAnimName():String return animation.curAnim.name;
 public function new(n:String)curCharacter=n;
 public function playAnim(n:String,force:Bool){played.push(n+':'+force);if(animation.getByName(n)!=null)animation.curAnim=new Frame(n);}
 public static function snapshot(c:Character):String return c==null?'null':c.curCharacter+':'+(c.isAnimNull()?'null':c.animation.curAnim.name+':'+c.animation.curAnim.curFrame)+':'+c.played.join(',');
}
'''
MAIN=r'''@:access(PlayState) class Main {
 static function run(actual:Bool,legacy:Bool,role:String,name:String,mode:Int):String {
  var s=new PlayState(legacy,mode);
  if(mode==1)for(c in [s.boyfriend,s.dad,s.gf])c.animation.curAnim=null;
  if(mode==2)for(c in [s.boyfriend,s.dad,s.gf])c.animation=null;
  if(mode==3){s.target.animation.allowed=['idle'];s.target.animation.curAnim=new Character.Frame('idle',1);}
  if(mode==4)s.target.animation.curAnim=null;
  if(mode==5)s.target.animation=null;
  if(mode==6)s.gf=null;if(mode==7)s.dad=null;if(mode==8)s.boyfriend=null;
  if(mode==9)for(c in [s.boyfriend,s.dad,s.gf])c.curCharacter=null;
  s.redirected.animation.curAnim=new Character.Frame('idle',1);
  var error=false;try{if(actual)s.changeNightmareVisionCharacterEvent(role,name);else s.reference(role,name);}catch(_:Dynamic)error=true;
  return s.snapshot()+'#'+error;
 }
 static function main(){
  var roles:Array<String>=[null,'','bad','0','1','2','3','-1','1.5','bf','dad','opponent','gf','girlfriend','GF',' dad '];
  var names:Array<String>=[null,'','bf','bf-alt','dad','dad-alt','gf-alt','unrelated'];var count=0;
  for(role in roles)for(name in names)for(mode in 0...12){
   // The modern adapter keeps existing tolerance for absent/invalid actors.
   if(!__LEGACY__&&(mode>=6&&mode<=9||name==null))continue;
   var expected=run(false,__LEGACY__,role,name,mode);var actual=run(true,__LEGACY__,role,name,mode);
   if(expected!=actual)throw 'carry '+role+':'+name+':'+mode+'\n'+expected+'\n'+actual;count++;
  }
  trace(count+' source carry comparisons');
 }
}'''
class CharacterEventCarryTest(unittest.TestCase):
 def test_pinned_historical_and_modern_event_choreography(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('source checkout unavailable')
  versions=[(True,LEGACY,'source/meta/states/PlayState.hx'),(False,'733165c42ca71eb0961a70e4173b2d81ba4a29ea','source/funkin/states/PlayState.hx')]
  method=extract_method((ROOT/'source/PlayState.hx').read_text(),'function changeNightmareVisionCharacterEvent(')
  for legacy,revision,path in versions:
   with self.subTest(legacy=legacy):
    src=subprocess.check_output(['git','show',revision+':'+path],cwd=donor,text=True)
    raw=extract_method(src,'function triggerEventNote(')
    case=next(c for c in re.split(r'(?=^\t\t\tcase )',raw,flags=re.M) if c.startswith("\t\t\tcase 'Change Character':"))
    ref='function reference(value1:String,value2:String){switch("Change Character"){'+case+'}}'
    files={'PlayState.hx':HOST.replace('__METHOD__',method).replace('__REFERENCE__',ref),'Character.hx':CHAR,'Main.hx':MAIN.replace('__LEGACY__',str(legacy).lower()),'PsychCharacterChangeEvent.hx':(ROOT/'source/PsychCharacterChangeEvent.hx').read_text()}
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
     work=FixturePath(folder)
     for name,content in files.items():(work/name).write_text(content)
     result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
     self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_preload_null_admission_and_distinct_numeric_aliases(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder)
   (work/'Main.hx').write_text('''class Main {static function main(){
    var names:Array<String>=['0','1','2','3','-1','dad','DAD','gf','GF','girlfriend','opponent','bf',' bad ',' 1 '];
    var expected=[1,2,2,3,-1,1,1,2,2,2,1,0,0,1];
    for(i in 0...names.length)for(strict in [false,true])if(NightmareVisionCharacterEvent.preloadRole(names[i],strict)!=expected[i])throw names[i];
    var failed=false;try NightmareVisionCharacterEvent.preloadRole(null,true) catch(_:Dynamic)failed=true;
    if(!failed||NightmareVisionCharacterEvent.preloadRole(null)!=0)throw 'null admission';
   }}''')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
