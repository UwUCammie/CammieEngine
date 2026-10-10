"""Compare shared text callbacks with both pinned source dialects."""
from pathlib import Path
import re, subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_event_preparation import extract_method
ROOT=Path(__file__).resolve().parents[2]
class SourceTextPropertiesTest(unittest.TestCase):
 def test_shared_callbacks_remain_discoverable(self):
  import audit_script_api_coverage as audit_api
  names={'setTextString','setTextSize','setTextWidth','setTextHeight','setTextAutoSize','setTextItalic','setTextFont','setTextColor','setTextAlignment','setTextBorder','getTextString','getTextSize','getTextFont','getTextWidth'}
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   root=Path(folder);(root/'source').mkdir()
   (root/'source/SourceScriptTextBindings.hx').write_text((ROOT/'source/SourceScriptTextBindings.hx').read_text())
   direct,_,_,_=audit_api._engine_inventory(root,names)
   self.assertTrue(all(direct.get(name) for name in names))

 def test_source_callbacks_and_style(self):
  def donor(repo,rev,file):return subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources'/repo),'show',rev+':'+file],text=True)
  old=donor('NightmareVision','7f96eb3b5a60352413229bf134bd348b79ad5fe6','source/meta/data/scripts/FunkinLua.hx')
  modern=donor('FNF-PsychEngine','5c67ced49e5a98535298a6daa3f8f4ec79ac8399','source/psychlua/TextFunctions.hx')
  cool=donor('FNF-PsychEngine','5c67ced49e5a98535298a6daa3f8f4ec79ac8399','source/backend/CoolUtil.hx')
  methods=['setTextString','setTextSize','setTextWidth','setTextItalic','setTextFont','setTextColor','setTextAlignment','setTextBorder','getTextString','getTextSize','getTextFont','getTextWidth']
  def callbacks(source,names):
   result=[]
   for name in names:
    callback=extract_method(source[source.index('Lua_helper.add_callback(lua, "'+name+'"'):],'function(')
    result.append(callback.replace('function(', 'public static function '+name+'(',1))
   return '\n'.join(result)
  def constants(text):
   for name in ['LEFT','RIGHT','CENTER','JUSTIFY','SHADOW','OUTLINE','OUTLINE_FAST','NONE']:
    text=re.sub(r'(?<![\w.])'+name+r'\b',"'"+name.lower()+"'",text)
   return text
  fields={'text':'"before"','size':'16','fieldWidth':'100.0','fieldHeight':'24.0','italic':'false','autoSize':'false','font':'"old.ttf"','color':'0','alignment':'"center"','borderStyle':'"outline"','borderSize':'2.0','borderColor':'0'}
  properties=[]
  for name,value in fields.items():
   properties.append(f'public var {name}(get,set):Dynamic;var _{name}:Dynamic={value};function get_{name}():Dynamic return _{name};function set_{name}(v:Dynamic):Dynamic {{Main.log.push("{name}:"+Main.repr(v));return _{name}=v;}}')
  color_source=(ROOT/'.haxelib/flixel/6,1,2/flixel/util/FlxColor.hx').read_text()
  parser='public static '+extract_method(color_source,'function fromString(')
  fixture=r'''using StringTools;
abstract FlxColor(Int) from Int to Int {
 public inline function new(v:Int=0)this=v;
 public static var WHITE:Int=-1;public static var RED:Int=0xffff0000;
 static var COLOR_REGEX = ~/^(0x|#)(([A-F0-9]{2}){3,4})$/i;
 static var colorLookup:Map<String,Int>=['WHITE'=>-1,'RED'=>0xffff0000,'BLUE'=>0xff0000ff,'TRANSPARENT'=>0];
 public var alphaFloat(never,set):Float;inline function set_alphaFloat(v:Float):Float {this=(this&0xffffff)|(Std.int(v*255)<<24);return v;}
 __COLOR_PARSER__
}
class FlxTextBorderStyle {public static var SHADOW='shadow';public static var OUTLINE='outline';public static var OUTLINE_FAST='outline_fast';public static var NONE='none';}
class FlxText {__FIELDS__ public function new(){}}
class Paths {public static function font(name:String):String {Main.log.push('font:'+name);return 'owner/fonts/'+name;}}
class FunkinLua {public static function luaTrace(message:String,a:Bool,b:Bool,c:Dynamic):Void {Main.warnings.push(message);}}
class LuaUtils {
 public static function getObjectDirectly(name:String):Dynamic return Main.target;
 public static function getPropertyLoop(parts:Array<String>):Dynamic return {child:Main.target};
 public static function getVarInArray(o:Dynamic,key:String):Dynamic return Reflect.getProperty(o,key);
}
class CoolUtil {__COOL__}
class Legacy {
 public static function getTextObject(tag:String):FlxText return Main.target;
 __LEGACY__
}
class Modern {__MODERN__}
__STYLE__
class Main {
 public static var target:FlxText;public static var log:Array<String>;public static var warnings:Array<String>;
 public static function repr(v:Dynamic):String return Std.string(Type.typeof(v))+':'+Std.string(v);
 static function run(actual:Bool,legacy:Bool,present:Bool,name:String,values:Array<Dynamic>):String {
  target=present?new FlxText():null;log=[];warnings=[];
  var vars:Map<String,Dynamic>=[];
  new SourceScriptTextBindings(legacy,function(tag)return target,Paths.font,legacy?SourceTextStyle.historicalColor:SourceTextStyle.psychColor,SourceTextStyle.border,function(message)warnings.push(message)).install(vars);
  var args:Array<Dynamic>=['tag'];args=args.concat(values);var result:String;
  try{var value=Reflect.callMethod(null,actual?vars.get(name):Reflect.field(legacy?cast Legacy:cast Modern,name),args);
   if(actual&&legacy&&StringTools.startsWith(name,'set')&&value!=null)throw 'historical return was not nil';
   result=legacy&&StringTools.startsWith(name,'set')?'void':repr(value);
  }catch(_:Dynamic)result='error';
  return result+';'+log.join('|')+';'+warnings.join('|');
 }
 static function main(){var cases:Array<Dynamic>=[
  {name:'setTextString',values:[[null],['hello'],['']]}, {name:'setTextSize',values:[[-1],[0],[24]]},
  {name:'setTextWidth',values:[[-1.0],[0.0],[120.5]]}, {name:'setTextHeight',values:[[-1.0],[120.5]]},
  {name:'setTextItalic',values:[[false],[true]]}, {name:'setTextAutoSize',values:[[false],[true]]},
  {name:'setTextFont',values:[[null],['vcr.ttf'],['fonts/custom.ttf']]},
  {name:'setTextAlignment',values:[[null],[''],[' LEFT '],['right'],['center'],['justify'],['invalid']]},
  {name:'getTextString',values:[[]]}, {name:'getTextSize',values:[[]]}, {name:'getTextFont',values:[[]]}, {name:'getTextWidth',values:[[]]}
 ];
 var colors:Array<Dynamic>=[null,'','FFFFFF','FF112233','#80112233','0x80112233','0X80112233',' red ','r\ned','0xff','bogus','#00FF00','FFFFFFFF','000000','transparent'];
 cases.push({name:'setTextColor',values:[for(c in colors)[c]]});
 for(legacy in [false,true]){
  var borderCases:Array<Dynamic>=[];for(c in colors)for(size in [-1,0,3])for(style in [null,'outline','shadow','OUTLINE_FAST','invalid'])borderCases.push(legacy?[size,c]:[size,c,style]);
  var all=cases.copy();all.push({name:'setTextBorder',values:borderCases});var count=0;
  for(present in [false,true])for(test in all){if(legacy&&(test.name=='setTextHeight'||test.name=='setTextAutoSize'))continue;var variants:Array<Dynamic>=test.values;
   for(values in variants){var expected=run(false,legacy,present,test.name,values);var observed=run(true,legacy,present,test.name,values);if(expected!=observed)throw legacy+':'+present+':'+test.name+':'+Std.string(values)+'\n'+expected+'\n'+observed;count++;}}
  Sys.println((legacy?'historical':'Psych')+': '+count+' callback cases');
 }
 }
}'''.replace('__FIELDS__','\n'.join(properties)).replace('__COLOR_PARSER__',parser).replace('__LEGACY__',constants(callbacks(old,methods))).replace('__MODERN__',constants(callbacks(modern,methods+['setTextHeight','setTextAutoSize']))).replace('__COOL__',constants('public static '+extract_method(cool,'function colorFromString(')+'\npublic static '+extract_method(cool,'function setTextBorderFromString(')))
  style=(ROOT/'source/SourceTextStyle.hx').read_text();fixture=fixture.replace('__STYLE__',style[style.index('class SourceTextStyle'):])
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=FixturePath(folder);(work/'Main.hx').write_text(fixture);(work/'SourceScriptTextBindings.hx').write_text((ROOT/'source/SourceScriptTextBindings.hx').read_text())
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
