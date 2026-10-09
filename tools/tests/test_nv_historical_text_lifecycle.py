"""Pinned source text construction, mounting and replacement transactions."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'

class HistoricalTextLifecycleTest(unittest.TestCase):
 def test_source_text_transactions(self):
  donor=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/NightmareVision'),'show',REV+':source/meta/data/scripts/FunkinLua.hx'],text=True)
  callbacks=[]
  for name in ['makeLuaText','addLuaText','removeLuaText']:
   callback=extract_method(donor[donor.index('Lua_helper.add_callback(lua, "'+name+'"'):],'function(')
   callbacks.append(callback.replace('function(', 'public static function '+name+'(',1))
  helpers='public static '+extract_method(donor,'function resetTextTag(')+'\npublic static '+extract_method(donor,'function getTextObject(')
  source_text=extract_method(donor,'class ModchartText extends FlxText')
  actual_text=(ROOT/'source/SourceModchartText.hx').read_text();actual_text=actual_text[actual_text.index('class SourceModchartText'):]
  # Native enum constants have identical string representations in this constructor double.
  def constants(text):return text.replace('FlxTextBorderStyle.OUTLINE','"outline"').replace(', CENTER,',', "center",').replace(', OUTLINE,',', "outline",')
  play=(ROOT/'source/PlayState.hx').read_text()
  methods='\n'.join(extract_method(play,'function '+name+'(') for name in ['compatMakeLuaText','compatAddLuaText','compatRemoveLuaText','compatFindText'])
  fixture=r'''using StringTools;
class FlxCamera {public function new(){}}
class FlxColor {public static var WHITE:Int=-1;public static var BLACK:Int=0xff000000;}
class Scroll {public var x:Float=1;public var y:Float=1;public function new(){}public function set(x:Float=0,y:Float=0){this.x=x;this.y=y;}}
class FlxText {
 public var id:Int;public var x:Float;public var y:Float;public var fieldWidth:Float;public var text:String;public var size:Int;
 public var font:String;public var color:Int;public var alignment:String;public var borderStyle:String;public var borderColor:Int;public var borderSize:Float=0;
 public var cameras:Array<FlxCamera>;public var scrollFactor=new Scroll();public var alive=true;public var destroyed=false;
 public function new(x:Float,y:Float,width:Float,text:String,size:Int){this.x=x;this.y=y;fieldWidth=width;this.text=text;this.size=size;id=PlayState.instance.created.length;PlayState.instance.created.push(this);}
 public function setFormat(font:String,size:Int,color:Int,alignment:String,borderStyle:String,borderColor:Int){this.font=font;this.size=size;this.color=color;this.alignment=alignment;this.borderStyle=borderStyle;this.borderColor=borderColor;}
 public function kill(){alive=false;PlayState.instance.record('kill',this);if(PlayState.instance.mode==1)PlayState.instance.active=PlayState.instance.other;}
 public function destroy(){destroyed=true;PlayState.instance.record('destroy',this);if(PlayState.instance.mode==4)PlayState.instance.replaceRegistry();}
}
class Scene {
 public var id:String;public var members:Array<FlxText>=[];public function new(id:String)this.id=id;
 public function add(o:FlxText){PlayState.instance.record('add:'+id,o);if(members.indexOf(o)<0)members.push(o);if(PlayState.instance.mode==2)PlayState.instance.replaceRegistry();}
 public function remove(o:FlxText,splice:Bool){PlayState.instance.record('remove:'+id+':'+splice,o);members.remove(o);if(PlayState.instance.mode==3)PlayState.instance.replaceRegistry();}
}
class Paths {public static function font(name:String):String return 'owner/fonts/'+name;}
__TEXT_CLASSES__
class FunkinLua {
 public static function getInstance():Dynamic return PlayState.instance.active;
 __SOURCE__
}
class PlayState extends Scene {
 public static var instance:PlayState;public var camHUD=new FlxCamera();public var other:Scene;public var active:Scene;public var mode:Int;
 public var created:Array<FlxText>=[];public var events:Array<String>=[];public var modchartTexts:Map<String,Dynamic>=[];
 public var nightmareVisionLegacyFieldCameras=true;public var nightmareVisionPaths=Paths;
 public var haxeSprites:Map<String,FlxText>=[];public var haxeSpriteAtlasNames:Map<String,Array<String>>=[];
 public var fieldText:FlxText;
 public function new(dead:Bool,mode:Int){super('play');instance=this;this.mode=mode;other=new Scene('dead');active=dead?other:this;}
 public function record(name:String,o:Dynamic){events.push(name+':'+o.id+':'+o.wasAdded+':'+o.alive+':'+o.destroyed);}
 public function replaceRegistry(){var next:Map<String,Dynamic>=[];if(created.length>0)next.set('ab',created[0]);modchartTexts=next;}
 function historicalPropertyInstance():Dynamic return active;
 function historicalReadProperty(o:Dynamic,k:String):Dynamic return Reflect.getProperty(o,k);
 function compatRemoveLuaSprite(tag:String,destroy:Bool=true):Void {}
 function compatAddLuaSprite(tag:String,front:Bool):Void {}
 function compatFindObject(name:Dynamic):Dynamic return haxeSprites.get(name);
 function compatForgetSpriteAtlas(o:Dynamic):Void {}
 __METHODS__
 function snapshot():String {
  var keys=[for(k in modchartTexts.keys())k];keys.sort(Reflect.compare);
  return [for(o in created){var text:Dynamic=o;var values:Array<Dynamic>=[o.id,text.wasAdded,o.alive,o.destroyed,o.x,o.y,o.fieldWidth,o.text,o.size,o.font,o.color,o.alignment,o.borderStyle,o.borderColor,o.borderSize,o.cameras[0]==camHUD,o.scrollFactor.x,o.scrollFactor.y];values.join(':');}].join('|')+';'+events.join('|')+';'+[for(k in keys)k+':'+modchartTexts.get(k).id].join(',')+';'+[for(o in members)o.id].join(',')+';'+[for(o in other.members)o.id].join(',');
 }
 function run(actual:Bool,tag:String,flag:Bool,keep:Bool):String {
  var snapshots=[];
  var make=function(){if(actual)compatMakeLuaText('a.b','first',125,12,23);else FunkinLua.makeLuaText('a.b','first',125,12,23);};
  var add=function(){if(actual)compatAddLuaText(tag);else FunkinLua.addLuaText(tag);};
  var remove=function(){if(actual)compatRemoveLuaText(tag,!keep);else FunkinLua.removeLuaText(tag,!keep);};
  make();(cast created[0]:Dynamic).wasAdded=flag;
  for(action in [add,add,remove,add,make,remove]){try{action();snapshots.push(snapshot());}catch(_:Dynamic)snapshots.push('error:'+snapshot());}
  // Text helpers use the dedicated registry, then a literal play-state field.
  fieldText=created[0];haxeSprites.set('spriteOnly',created[0]);
  for(key in ['ab','a.b','fieldText','spriteOnly','missing']){var text:FlxText=actual?compatFindText(key):FunkinLua.getTextObject(key);snapshots.push(text==null?'null':Std.string(text.id));}
  return snapshots.join('\n');
 }
 static function main(){var count=0;for(dead in [false,true])for(mode in 0...5)for(tag in ['ab','a.b','missing'])for(flag in [false,true])for(keep in [false,true]){
  var expected=new PlayState(dead,mode).run(false,tag,flag,keep);var observed=new PlayState(dead,mode).run(true,tag,flag,keep);if(expected!=observed)throw dead+':'+mode+':'+tag+':'+flag+':'+keep+'\n'+expected+'\n'+observed;count++;
 }Sys.println(count+' source text transactions');}
}'''.replace('__TEXT_CLASSES__',constants(source_text)+'\n'+constants(actual_text)).replace('__SOURCE__',helpers+'\n'+'\n'.join(callbacks)).replace('__METHODS__',methods)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);(work/'PlayState.hx').write_text(fixture)
   (work/'SourceScriptTextLifecycle.hx').write_text((ROOT/'source/SourceScriptTextLifecycle.hx').read_text())
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','PlayState','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
