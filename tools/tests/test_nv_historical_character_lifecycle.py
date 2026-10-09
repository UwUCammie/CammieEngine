"""Historical state-owned preload/replacement against pinned source, including reentry."""
from pathlib import Path
import re,subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
CHAR=r"""class Point {public var x:Float;public var y:Float;public function new(x=0.,y=0.){this.x=x;this.y=y;}public function set(x:Float,y:Float){this.x=x;this.y=y;}}
class Character {
 public var curCharacter:String;public var healthIcon:String;public var id:Int;public var alpha:Float=1;public var visible=true;
 public var x:Float=0;public var y:Float=0;public var positionArray:Array<Float>=[3,5];public var scrollFactor=new Point(1,1);public var danceEveryNumBeats=1;
 public function new(n:String,id:Int){curCharacter=n;healthIcon=n;this.id=id;}
 public function setPosition(x:Float,y:Float){this.x=x;this.y=y;}
 public static function snap(c:Character):Dynamic return c==null?null:[c.id,c.curCharacter,c.alpha,c.visible,c.x,c.y,c.scrollFactor.x,c.danceEveryNumBeats];
}"""
HOST=r"""using StringTools;
class Field {public var owner:Character;public function new(c:Character)owner=c;}
class Group {public var label:String;public var members:Array<Character>=[];var s:PlayState;public function new(s:PlayState,n:String){this.s=s;label=n;}public function add(c:Character){members.push(c);c.x+=10;c.y+=20;s.events.push('add:'+label+':'+c.id);if(s.mode==14)s.cache(s.role).set(s.requested,s.third);if(s.mode==15)s.assign(s.role,s.third);}}
class Icon {var s:PlayState;var type:Int;public function new(s:PlayState,t:Int){this.s=s;type=t;}public function changeIcon(n:String){s.events.push('icon:'+type+':'+n);if(s.mode==5)s.assign(type,s.third);}}
class Registry {var s:PlayState;public function new(s:PlayState)this.s=s;public function setOnScripts(n:String,v:Dynamic){var id:Dynamic=Std.isOfType(v,Character)?(cast v:Character).id:Std.isOfType(v,Group)?(cast v:Group).label:v;s.events.push('set:'+n+':'+id);if(s.mode==6&&n=='boyfriend')s.boyfriend=s.third;}}
class PlayState {
 public var boyfriend=new Character('bf',0);public var dad=new Character('dad',1);public var gf=new Character('gf',2);public var third=new Character('third',3);
 public var focusedChar:Character;public var boyfriendMap:Map<String,Character>=[];public var dadMap:Map<String,Character>=[];public var gfMap:Map<String,Character>=[];
 public var boyfriendGroup:Group;public var dadGroup:Group;public var gfGroup:Group;public var bfGhost='ghost';public var nightmareVisionHiddenGFPlaceholder:Character=null;
 public var playFields:{members:Array<Field>};public var iconP1:Icon;public var iconP2:Icon;public var registry:Registry;
 public var mode:Int;public var nested=false;public var actual:Bool;public var events:Array<String>=[];public var all:Array<Character>;public var role:Int;public var requested:String;
 public function new(actual:Bool,mode:Int,role:Int,name:String){this.actual=actual;this.mode=mode;this.role=role;requested=name;
  boyfriendGroup=new Group(this,'bfGroup');dadGroup=new Group(this,'dadGroup');gfGroup=new Group(this,'gfGroup');iconP1=new Icon(this,0);iconP2=new Icon(this,1);registry=new Registry(this);
  all=[boyfriend,dad,gf,third];playFields={members:[new Field(boyfriend),new Field(dad),new Field(gf),new Field(actor(role))]};focusedChar=actor(role);
  actor(role).alpha=.4;
  if(mode==1){var cached=new Character(name,4);all.push(cached);cache(role).set(name,cached);}
  if(mode==7)playFields.members.insert(1,null);if(mode==8)focusedChar=third;if(mode==9)gf=null;
  if(mode==10)actor(role).curCharacter=name;
 }
 public function actor(t:Int):Character return t==2?gf:t==1?dad:boyfriend;
 public function assign(t:Int,c:Character){if(t==2)gf=c;else if(t==1)dad=c;else boyfriend=c;}
 public function cache(t:Int):Map<String,Character> return t==2?gfMap:t==1?dadMap:boyfriendMap;
 public function nightmareVisionCharacterGroup(t:Int):Group return t==2?gfGroup:t==1?dadGroup:boyfriendGroup;
 public function constructNightmareVisionRole(n:String,t:Int):Character {events.push('construct:'+t+':'+n);if(mode==11)throw 'construct';if(mode==2){if(t==2)gfMap=[];else if(t==1)dadMap=[];else boyfriendMap=[];}
  var c=new Character(mode==13?'resolved':n,all.length);all.push(c);return c;}
 public function startHistoricalCharacterPos(c:Character,check:Bool=false):Void {events.push('position:'+c.id+':'+check);if(check&&c.curCharacter.startsWith('gf')){c.setPosition(100,200);c.scrollFactor.set(.95,.95);c.danceEveryNumBeats=2;}c.x+=c.positionArray[0];c.y+=c.positionArray[1];}
 public function loadNightmareVisionCharacter(c:Character):Void {events.push('load:'+c.id+':'+c.alpha);if(mode==12)throw 'load';if(mode==3){assign(role,third);playFields.members.push(new Field(third));}if(mode==4)cache(role).set(requested,third);if(mode==16)addNightmareVisionCharacterToList(requested,role);if(mode==17&&!nested){nested=true;if(actual)NightmareVisionLegacyCharacterChanges.change(this,requested,role);else referenceChange(requested,role);}}
 public function startCharacterPos(c:Character,check:Bool=false):Void startHistoricalCharacterPos(c,check);
 public function startCharacterLua(n:String,c:Character):Void loadNightmareVisionCharacter(c);
 public function legacyScriptRegistry():Registry return registry;
 public function setHistoricalCharacterLua(n:String,v:Dynamic):Void events.push('lua:'+n+':'+v);
 public function setOnLuas(n:String,v:Dynamic):Void setHistoricalCharacterLua(n,v);
 public function setOnScripts(n:String,v:Dynamic):Void registry.setOnScripts(n,v);
 public function changeHistoricalCharacterIcon(p:Bool,n:String):Void (p?iconP1:iconP2).changeIcon(n);
 public function reloadHistoricalHealthBarColors():Void events.push('bar');
 public function reloadHealthBarColors():Void reloadHistoricalHealthBarColors();
 public function addNightmareVisionCharacterToList(n:String,t:Int):Void {if(actual)NightmareVisionLegacyCharacterChanges.preload(this,n,t);else referencePreload(n,t);}
 public function addCharacterToList(n:String,t:Int):Void addNightmareVisionCharacterToList(n,t);
 __REFERENCE__
 public function snapshot():String {var maps=[];for(m in [boyfriendMap,dadMap,gfMap]){var keys=[for(k in m.keys())k];keys.sort(Reflect.compare);maps.push([for(k in keys)k+':'+m.get(k).id]);}
  return haxe.Json.stringify({events:events,roles:[Character.snap(boyfriend),Character.snap(dad),Character.snap(gf)],focus:Character.snap(focusedChar),all:[for(c in all)Character.snap(c)],fields:[for(f in playFields.members)f==null?null:f.owner.id],maps:maps,groups:[for(g in [boyfriendGroup,dadGroup,gfGroup])[for(c in g.members)c.id]]});}
}
"""
MAIN=r"""class Main {
 static function run(actual:Bool,mode:Int,role:Int,name:String,preload:Bool):String {var s=new PlayState(actual,mode,role,name);var failed=false;
  try {if(preload)s.addNightmareVisionCharacterToList(name,role);else if(actual)NightmareVisionLegacyCharacterChanges.change(s,name,role);else s.referenceChange(name,role);}catch(_:Dynamic)failed=true;
  return s.snapshot()+'#'+failed;}
 static function main(){var count=0;for(preload in [false,true])for(mode in 0...18)for(role in [-1,0,1,2,3])for(name in ['bf','bf-alt','dad','gf','gf-alt','replacement']){
  var want=run(false,mode,role,name,preload);var got=run(true,mode,role,name,preload);if(want!=got)throw 'case '+preload+':'+mode+':'+role+':'+name+'\n'+want+'\n'+got;count++;
 }trace(count+' source preload/replacement cases');}
}"""
class HistoricalCharacterLifecycleTest(unittest.TestCase):
 def test_pinned_cache_publication_reentry_and_failure_order(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned donor unavailable')
  src=subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
  preload=extract_method(src,'function addCharacterToList(').replace('function addCharacterToList(', 'public function referencePreload(')
  preload=preload.replace('new Boyfriend(0, 0, newCharacter)','constructNightmareVisionRole(newCharacter,0)').replace('new Character(0, 0, newCharacter)','constructNightmareVisionRole(newCharacter,type)').replace(':Boyfriend',':Character')
  change=extract_method(src,'function changeCharacter(').replace('function changeCharacter(', 'public function referenceChange(')
  files={'Character.hx':CHAR,'PlayState.hx':HOST.replace('__REFERENCE__',preload+'\n'+change),'Main.hx':MAIN,'NightmareVisionLegacyCharacterChanges.hx':(ROOT/'source/NightmareVisionLegacyCharacterChanges.hx').read_text()}
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder)
   for name,content in files.items():(work/name).write_text(content)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_live_bar_callback_stop_replacement_and_color_order(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned donor unavailable')
  src=subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
  reference=extract_method(src,'function reloadHealthBarColors(').replace('function reloadHealthBarColors(', 'public function reference(')
  actual=extract_method((ROOT/'source/PlayState.hx').read_text(),'function reloadHistoricalHealthBarColors(')
  host=r'''class Globals {public static var Function_Stop=1;}
class NightmareVisionScriptGroup {public static var STOP_FUNC=1;}
class FlxColor {public static function fromRGB(r:Int,g:Int,b:Int):Int return r*65536+g*256+b;}
class Bar {public var id:Int;public var log:Array<String>=[];public function new(id:Int)this.id=id;
 public function createFilledBar(l:Int,r:Int):Void setColors(l,r);
 public function setColors(l:Int,r:Int):Void log.push('colors:'+l+':'+r);
 public function updateBar():Void log.push('update');}
typedef NightmareVisionBar=Bar;
class PlayState {
 public var sourceHUDBarMode:Int;public var mode:Int;public var healthBar=new Bar(0);public var bars:Array<Bar>;public var log:Array<String>=[];
 public var dad={healthColorArray:[1,2,3]};public var boyfriend={healthColorArray:[4,5,6]};
 public function new(mode:Int,source:Int){this.mode=mode;sourceHUDBarMode=source;bars=[healthBar];}
 public function legacyScriptRegistry():PlayState return this;
 public function callOnHScripts(n:String,a:Array<Dynamic>):Int {var b:Bar=cast a[0];log.push(n+':'+b.id);
  if(mode==2||mode==4){healthBar=new Bar(1);bars.push(healthBar);}if(mode==3)dad.healthColorArray=[9,8,7];if(mode==5)throw 'hook';return mode==1||mode==4?1:0;}
 public function sourceHUDBarAlias(n:String):Dynamic return healthBar;
 __METHODS__
 public function run(actual:Bool):String {var failed=false;try{if(actual)reloadHistoricalHealthBarColors();else reference();}catch(_:Dynamic)failed=true;return haxe.Json.stringify({log:log,bars:[for(b in bars){id:b.id,log:b.log}],failed:failed});}
}
class Main {static function main(){for(mode in 0...6)for(source in [0,2]){var a=new PlayState(mode,source);var b=new PlayState(mode,source);if(a.run(true)!=b.run(false))throw 'bar '+mode+':'+source;}trace('12 source bar callback cases');}}
'''.replace('__METHODS__',actual+'\n'+reference)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);(work/'Main.hx').write_text(host)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_public_character_calls_use_real_interpreter_and_owner(self):
  from tools.haxe_flixel_math_stubs import write_flixel_point_stub
  host=r"""class Owner {
 public var log:Array<String>=[];public function new(){}
 public function bind(i:NightmareVisionScriptInterp){i.variables.set('game',this);i.variables.set('PlayState',Owner);i.variables.set('Reflect',i.sourceClassScope().reflectFacade());i.variables.set('actor',new Character());
  NightmareVisionLegacyCharacterBindings.install(i,this,Owner,function(n,t)log.push('load:'+n+':'+t),function(n,t)log.push('change:'+n+':'+t),function(c,check=false)log.push('position:'+check),function()log.push('bar'));}
}
class Main {static function main(){var one=new Owner();var two=new Owner();var a=new NightmareVisionScriptInterp(one);var b=new NightmareVisionScriptInterp(two);one.bind(a);two.bind(b);
 a.execute(new NightmareVisionScriptParser().parseString('addCharacterToList("a",0);game.changeCharacter("b",1);PlayState.changeCharacter("c",2);Reflect.callMethod(game,Reflect.field(game,"changeCharacter"),["d",0]);startCharacterPos(actor);game.startCharacterPos(actor,true);PlayState.reloadHealthBarColors();'));
 b.execute(new NightmareVisionScriptParser().parseString('changeCharacter("other",2);'));
 if(one.log.join(',')!='load:a:0,change:b:1,change:c:2,change:d:0,position:false,position:true,bar'||two.log.join(',')!='change:other:2')throw one.log.join(',')+' / '+two.log.join(',');a.release();b.release();
}}
"""
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);write_flixel_point_stub(work);(work/'Main.hx').write_text(host);(work/'Character.hx').write_text('class Character {public function new(){}}')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
