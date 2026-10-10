"""Real class/static scopes and captured Psych Alphabet owner integration."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from source_alphabet_fixture_support import alphabet_fixture_files
from test_source_attachment_integration import integration_files
from test_nv_multifield_routes import method
ROOT = Path(__file__).resolve().parents[2]

class SourceAlphabetIntegrationTest(unittest.TestCase):
 def test_actual_iris_class_scope_routes(self):
  files = integration_files()
  files.update(alphabet_fixture_files())
  ps=(ROOT/'source/PlayState.hx').read_text()
  methods='\n'.join(method(ps,n).replace('function ', 'public function ',1) for n in ['function configurePsychAlphabetScope(', 'function bindSourceAlphabetClasses('])
  files['AlphabetHost.hx']='class AlphabetHost {public function new() {} public var views:Map<String,PsychAlphabetOwner>=new Map();public function sourceAlphabetOwner(paths:Dynamic):PsychAlphabetOwner return views.get(paths.view == null ? paths.root : paths.view);'+methods+'}'
  files['PsychOwnerPaths.hx']='class PsychOwnerPaths {public static function ownerRoot(paths:Dynamic):String return paths.root;}'
  files['Main.hx']=r'''
import PsychSourceAlphabet.PsychSourceAlphabetAlignment;
import DonorAlphabet.DonorAlphaCharacter;
class Main {
 static function ok(b:Bool,s:String) {if(!b)throw s;}
 static function owner():PsychAlphabetOwner return {atlas:function(n) return new flixel.graphics.frames.FlxAtlasFrames(),getPath:function(n)return n,exists:function(n)return true,text:function(n)return '{"characters":"a?","metadata":[]}',antialiasing:function()return true};
 static function main() {
  var h=new AlphabetHost();h.views.set("a",owner());h.views.set("b",owner());PsychAlphabetRegistry.enterSession("a");
  var a=new NightmareVisionScriptInterp();var a2=new NightmareVisionScriptInterp();var b=new NightmareVisionScriptInterp();
  h.bindSourceAlphabetClasses(a,{root:"a"});h.bindSourceAlphabetClasses(a2,{root:"a"});h.bindSourceAlphabetClasses(b,{root:"b"});
  var p=new NightmareVisionScriptParser();
  a.execute(p.parseString("import Reflect; import Type; import objects.Alphabet; import objects.Alphabet.AlphaCharacter; import objects.Alphabet.Alignment; import objects.AttachedText; saved=AlphaCharacter.allLetters; saved.set('z',null); loader=Reflect.field(AlphaCharacter,'loadAlphabetData'); glyph=new AlphaCharacter(); label=new Alphabet(5,6,'',false); attached=new AttachedText('',3,4); resolved=Type.resolveClass('objects.AlphaCharacter'); created=Type.createInstance(resolved,[]); enumType=Type.resolveEnum('objects.Alignment'); enumName=Type.getEnumName(enumType); className=Type.getClassName(Type.getClass(created));"));
  ok(Std.isOfType(a.variables.get("label"),PsychSourceAlphabet)&&Std.isOfType(a.variables.get("created"),PsychSourceAlphaCharacter),"real constructors/classes");
  ok(a.variables.get("enumType")==PsychSourceAlphabetAlignment&&a.variables.get("enumName")=="objects.Alignment"&&a.variables.get("className")=="objects.AlphaCharacter","canonical source names retaining actual enum/class");
  a2.execute(p.parseString("same=Reflect.getProperty(AlphaCharacter,'allLetters'); loader=AlphaCharacter.loadAlphabetData;"));
  b.execute(p.parseString("other=AlphaCharacter.allLetters; loader=AlphaCharacter.loadAlphabetData;"));
  ok(a.variables.get("saved")==a2.variables.get("same")&&a.variables.get("saved")!=b.variables.get("other"),"owner metadata identity");
  ok(Reflect.compareMethods(a.variables.get("loader"),a2.variables.get("loader"))&&!Reflect.compareMethods(a.variables.get("loader"),b.variables.get("loader")),"stable owner bound load identity");
  a.execute(p.parseString("Reflect.setProperty(AlphaCharacter,'allLetters',null); nullRead=AlphaCharacter.allLetters;"));
  h.bindSourceAlphabetClasses(a2,{root:"a"});a2.execute(p.parseString("stillNull=Reflect.field(AlphaCharacter,'allLetters');"));
  ok(a.variables.get("nullRead")==null&&a2.variables.get("stillNull")==null,"authored null survives factory rebind");
  a.execute(p.parseString("Reflect.callMethod(AlphaCharacter,loader,[]); restored=AlphaCharacter.allLetters; bareMissing=false; try { ignored=allLetters; } catch(error:Dynamic) {bareMissing=true;} runtimeReflect=Type.resolveClass('Reflect'); reflected=runtimeReflect.field(AlphaCharacter,'allLetters');"));
  ok(a.variables.get("restored")!=null&&a.variables.get("reflected")==a.variables.get("restored")&&a.variables.get("bareMissing")==true,"static load and resolved reflection without bare pollution");
  a.execute(p.parseString("extracted=Reflect.field; creator=Type.createInstance; extra=creator(resolved,[]); reflectedByExtract=extracted(AlphaCharacter,'allLetters'); copied=Reflect.copy(AlphaCharacter); deleted=Reflect.deleteField(AlphaCharacter,'loadAlphabetData'); methodCalls=0; replacement=function(request:String='alphabet'){methodCalls++;}; Reflect.setField(AlphaCharacter,'loadAlphabetData',replacement); AlphaCharacter.loadAlphabetData('alphabet');"));
  ok(Std.isOfType(a.variables.get("extra"),PsychSourceAlphaCharacter)&&a.variables.get("reflectedByExtract")==a.variables.get("restored"),"extracted callable routes");
  ok(Reflect.field(a.variables.get("copied"),"allLetters")==a.variables.get("restored")&&a.variables.get("deleted")==false,"native classfields copy/delete behavior");
  ok(a.variables.get("methodCalls")==0,"native regular staticmethod rejects write without throw");
  a2.execute(p.parseString("sameReplacement=AlphaCharacter.loadAlphabetData;"));ok(Reflect.compareMethods(a2.variables.get("sameReplacement"),a.variables.get("loader")),"regular method retained sameowner");
  b.execute(p.parseString("otherLoader=AlphaCharacter.loadAlphabetData;"));ok(!Reflect.compareMethods(b.variables.get("otherLoader"),a.variables.get("loader")),"regular method retained otherowner isolation");
  var donorA=new AlphabetIO();var donorB=new AlphabetIO();donorB.data='{"allowed":"a?","characters":{"a":{"normal":[22,0]}}}';Paths.io=donorA;var donorCached=DonorAlphaCharacter.loadAlphabetData;Paths.io=donorB;donorCached();ok(DonorAlphaCharacter.allLetters.get("a").offsets[0]==22,"actual donor cached loader follows latest global Paths IO");
  var left=owner();left.text=function(n)return '{"allowed":"a?","characters":{"a":{"normal":[11,0]}}}';var right=owner();right.text=function(n)return '{"allowed":"a?","characters":{"a":{"normal":[22,0]}}}';h.views.set("left",left);h.views.set("right",right);
  h.bindSourceAlphabetClasses(a,{root:"a",view:"left"});a.execute(p.parseString("cached=AlphaCharacter.loadAlphabetData;"));h.bindSourceAlphabetClasses(a2,{root:"a",view:"right"});a2.execute(p.parseString("cached=AlphaCharacter.loadAlphabetData;"));
  a.execute(p.parseString("readOnlyMap=AlphaCharacter.allLetters; readOnlyMethod=AlphaCharacter.loadAlphabetData; Reflect.setField(AlphaCharacter,'allLetters',readOnlyMap); cached('alphabet'); called=AlphaCharacter.allLetters.get('a').offsets[0]; constructedUnderSharedView=new AlphaCharacter(); constructedLabel=new Alphabet(0,0,'',true); cached('alphabet'); calledAgain=AlphaCharacter.allLetters.get('a').offsets[0];"));ok(a.variables.get("called")==22&&a.variables.get("calledAgain")==22,"earlier static reads/writes/method retrieval and constructors leave latest shared owner IO unchanged");
  a2.execute(p.parseString("Reflect.callMethod(null,cached,['alphabet']); called=AlphaCharacter.allLetters.get('a').offsets[0];"));ok(a2.variables.get("called")==22,"reflected static callable follows current shared owner IO view");
  var ctx=PsychAlphabetRegistry.get("a",h.views.get("a"));var oldMap=ctx.allLetters;
  a.release();a2.execute(p.parseString("survivor=AlphaCharacter.allLetters;"));ok(a2.variables.get("survivor")==oldMap,"one interpreter release preserves peer/context");
  PsychAlphabetRegistry.enterSession("a");ok(PsychAlphabetRegistry.get("a",h.views.get("a")).allLetters==oldMap,"same primary retry preserves map");
  PsychAlphabetRegistry.enterSession(null);ok(PsychAlphabetRegistry.get("a",h.views.get("a")).allLetters!=oldMap,"primary session exit resets registry");
  a2.release();b.release();
 }
}
'''
  self.run_haxe(files,cpp=True)
 def test_actual_lua_overlay_shares_class_context(self):
  from test_psych_reflection_bindings import HOST
  files=integration_files();files.update(alphabet_fixture_files())
  ps=(ROOT/'source/PlayState.hx').read_text()
  methods='\n'.join(method(ps,n).replace('function ', 'public function ',1) for n in ['function configurePsychAlphabetScope(', 'function psychLuaNativeClassScope(', 'function bindSourceAlphabetClasses('])
  host=HOST.replace("name == 'Item' ? Main.Item : null", "Type.resolveClass(Std.string(name))")
  host=host.replace(' public function new() {}', ' public function new() {} public var psychStageLibrary:String;public var psychNativeClassScopes:Array<SourceNativeClassScope>=[];public var views:Map<String,PsychAlphabetOwner>=new Map(); public function selectedPsychSkinRoot():String return "a";public function sourceAlphabetOwner(paths:Dynamic):PsychAlphabetOwner return views.get(paths.root);'+methods)
  files['PlayState.hx']=host
  files['EngineCompat.hx']='class EngineCompat {public static function propertyPath(p:Dynamic):String return Std.string(p);}'
  files['PsychOwnerPaths.hx']='class PsychOwnerPaths {public static function ownerRoot(paths:Dynamic):String return paths.root;public static function create(root:String,?library:String):Dynamic return {root:root,__sourceOwnerRoot:function()return root};}'
  files['PsychAchievementsIntegration.hx']='class PsychAchievementsIntegration {public static var hscriptCalls:Array<Array<Dynamic>>=[];public static var scopeCalls:Array<Array<Dynamic>>=[];public static function installHscript(host:Dynamic,interp:hscript.Interp,origin:String):Void hscriptCalls.push([host,interp,origin]);public static function installScope(host:Dynamic,scope:Dynamic,paths:Dynamic):Void scopeCalls.push([host,scope,paths]);}'
  files['Main.hx']=r'''
class Main {
 static function ok(b:Bool,s:String) {if(!b)throw s;}
 static function call(i:hscript.Interp,n:String,a:Array<Dynamic>):Dynamic return Reflect.callMethod(null,i.variables.get(n),a);
 static function main() {
  var h=new PlayState();h.views.set("a",{atlas:function(n)return new flixel.graphics.frames.FlxAtlasFrames(),getPath:function(n)return n,exists:function(n)return true,text:function(n)return '{"characters":"a?","metadata":[]}',antialiasing:function()return true});PsychAlphabetRegistry.enterSession("a");
  var lua=new hscript.Interp();lua.variables.set("Paths",PsychOwnerPaths.create("a"));lua.variables.set("getProperty",function(p:Dynamic)return null);lua.variables.set("setProperty",function(p:Dynamic,v:Dynamic){});lua.variables.set("getPropertyFromClass",function(c:Dynamic,p:Dynamic)return 88);lua.variables.set("setPropertyFromClass",function(c:Dynamic,p:Dynamic,v:Dynamic){});
  new PsychReflectionBindings(h,lua).install();
  var map=call(lua,"getPropertyFromClass",["objects.AlphaCharacter","allLetters"]);
  ok(PsychAchievementsIntegration.scopeCalls.length==1
   && PsychAchievementsIntegration.scopeCalls[0][0]==h
   && PsychAchievementsIntegration.scopeCalls[0][1]==h.psychNativeClassScopes[0]
   && PsychAchievementsIntegration.scopeCalls[0][2]==lua.variables.get("Paths"),
   "Lua native class scope receives the captured host, scope, and owner paths");
  var iris=new NightmareVisionScriptInterp();h.bindSourceAlphabetClasses(iris,PsychOwnerPaths.create("a"));iris.execute(new NightmareVisionScriptParser().parseString("map=AlphaCharacter.allLetters;"));ok(map==iris.variables.get("map"),"Lua/Iris same owner metadata");
  call(lua,"setPropertyFromClass",["objects.AlphaCharacter","allLetters",null]);ok(call(lua,"getPropertyFromClass",["objects.AlphaCharacter","allLetters"])==null,"Lua preserves explicitnull");
  call(lua,"callMethodFromClass",["objects.AlphaCharacter","loadAlphabetData",[]]);ok(call(lua,"getPropertyFromClass",["objects.AlphaCharacter","allLetters"])!=null,"Lua scopedsource loader");
  ok(call(lua,"createInstance",["glyph","objects.AlphaCharacter",[]])==true,"Lua actualconstructor factory");ok(Std.isOfType(h.psychScriptVariables.get("glyph"),PsychSourceAlphaCharacter),"Lua actualglyphtype");
  call(lua,"setPropertyFromClass",["objects.AlphaCharacter","allLetters.z",null,true]);var m:Map<String,Dynamic>=cast call(lua,"getPropertyFromClass",["objects.AlphaCharacter","allLetters"]);ok(m.exists("z"),"Lua map traversal existingsemantics");
  for(scope in h.psychNativeClassScopes)scope.release();iris.execute(new NightmareVisionScriptParser().parseString("survivor=AlphaCharacter.allLetters;"));ok(iris.variables.get("survivor")==m,"Lua scope cleanup independentIris");iris.release();
 }
}
'''
  self.run_haxe(files)
 def test_embedded_preset_uses_captured_paths_and_module_names(self):
  from test_psych_hscript_countdown_preset import MAIN_TEMPLATE
  files=integration_files();files.update(alphabet_fixture_files())
  ps=(ROOT/'source/PlayState.hx').read_text()
  methods='\n'.join(method(ps,n).replace('function ', 'public function ',1) for n in ['function configurePsychAlphabetScope(', 'function bindSourceAlphabetClasses('])
  template=MAIN_TEMPLATE[:MAIN_TEMPLATE.index('class Main {')]
  # The shared HUD preset delegates its Alphabet branch to the actual extracted
  # installer here. Real HUD identity is covered by embedded_hud_aliases.
  template=template.replace(' public function new() {}',' public var psychStageLibrary:String;public var views:Map<String,PsychAlphabetOwner>=new Map();public function compatPsychOwnerForScript(origin:String):String return "a";public function sourceAlphabetOwner(paths:Dynamic):PsychAlphabetOwner return views.get(paths.root); public function bindSourceBarClass(i:NightmareVisionScriptInterp,n:Bool,p:Dynamic):Void bindSourceAlphabetClasses(i,p); public function new() {}'+methods,1)
  template=template.replace('__INSTALL_METHOD__',method((ROOT/'source/PsychHscriptSourceBindings.hx').read_text(),'public function install():'))
  files['PsychOwnerPaths.hx']='class PsychOwnerPaths {public static function ownerRoot(paths:Dynamic):String return paths.root;public static function create(root:String,?library:String):Dynamic return {root:root,__sourceOwnerRoot:function()return root};}'
  files['PsychBaseStageCountdown.hx']='enum PsychBaseStageCountdown {THREE;TWO;ONE;GO;START;}'
  files['PsychAchievementsIntegration.hx']='class PsychAchievementsIntegration {public static var hscriptCalls:Array<Array<Dynamic>>=[];public static function installHscript(host:Dynamic,interp:hscript.Interp,origin:String):Void hscriptCalls.push([host,interp,origin]);}'
  files['Main.hx']=template+r'''
class Main {static function main() {
 var h=new FakeHost();h.views.set("a",{atlas:function(n)return new flixel.graphics.frames.FlxAtlasFrames(),getPath:function(n)return n,exists:function(n)return true,text:function(n)return '{"characters":"a?","metadata":[]}',antialiasing:function()return true});PsychAlphabetRegistry.enterSession("a");
 var embedded=new SourceIrisBridge(h);embedded.variables.set("Paths",PsychOwnerPaths.create("a"));new PsychHscriptSourceBindings(h,embedded,"a/script.lua#runHaxeCode",null).install();
 if(PsychAchievementsIntegration.hscriptCalls.length!=1||PsychAchievementsIntegration.hscriptCalls[0][0]!=h||PsychAchievementsIntegration.hscriptCalls[0][1]!=embedded||PsychAchievementsIntegration.hscriptCalls[0][2]!="a/script.lua#runHaxeCode")throw "embedded preset did not forward its captured integration context";
 embedded.evaluate("import objects.Alphabet.AlphaCharacter; import Reflect; import Type; glyph=Type.createInstance(Type.resolveClass('objects.AlphaCharacter'),[]); map=Reflect.field(AlphaCharacter,'allLetters');","embedded");
 if(!Std.isOfType(embedded.variables.get("glyph"),PsychSourceAlphaCharacter)||embedded.variables.get("map")==null)throw "embedded actualsource scope";
 var rejected=false;try embedded.bindLibrary("AlphaCharacter","objects.AlphaCharacter") catch(error:Dynamic) rejected=true;if(!rejected)throw "runtime type alias must not invent Haxe module import";
 embedded.release();
}}
'''
  self.run_haxe(files)
 def test_captured_owner_resource_view_and_stock_resolution(self):
  files=alphabet_fixture_files()
  ps=(ROOT/'source/PlayState.hx').read_text()
  body=method(ps,'function sourceAlphabetOwner(').replace('function ','public function ',1)
  atlas_import='import DynamicSprite.DynamicAtlasFrames;' if 'import DynamicSprite.DynamicAtlasFrames;' in ps else ''
  files['ResourceHost.hx']=atlas_import+'class ResourceHost {public var psychClientPrefs:Dynamic={data:{antialiasing:true}};public function new(){}'+body+'}'
  files['DynamicSprite.hx']='class DynamicSprite {} class DynamicAtlasFrames {public static var pair:Array<String>=[];public static function fromSparrow(image:String,xml:String):flixel.graphics.frames.FlxAtlasFrames {pair=[image,xml];return new flixel.graphics.frames.FlxAtlasFrames();}}'
  files['FNFAssets.hx']='class FNFAssets {public static function exists(p:String):Bool return p!=null;public static function getText(p:String):String return p;}'
  files['OptionsHandler.hx']='class OptionsHandler {public static var options={antialiasing:false};}'
  files['Main.hx']=r'''
import DynamicSprite.DynamicAtlasFrames;
class Main {static function main() {
 var owned:Map<String,String>=new Map();var paths:Dynamic={__sourceOwnedPath:function(p:String)return owned.get(p),getPath:function(p:String)return "captured/"+p,getSparrowAtlas:function(p:String)return new flixel.graphics.frames.FlxAtlasFrames()};var h=new ResourceHost();var owner=h.sourceAlphabetOwner(paths);var prefs=h.psychClientPrefs.data;
 if(owner.getPath("images/alphabet.json")!="assets/images/source_compat/psych/alphabet.json"||owner.getPath("images/custom.json")!="captured/images/custom.json")throw "only exact default stock JSON fallback";
 owned.set("images/alphabet.json","a/images/alphabet.json");if(owner.getPath("images/alphabet.json")!="a/images/alphabet.json")throw "owner JSON precedence";
 owner.atlas("alphabet");if(DynamicAtlasFrames.pair[0]!="assets/images/source_compat/psych/alphabet.png"||DynamicAtlasFrames.pair[1]!="assets/images/source_compat/psych/alphabet.xml")throw "stock core atlas";
 owned.set("images/alphabet.png","a/images/alphabet.png");owner.atlas("alphabet");if(DynamicAtlasFrames.pair[0]!="a/images/alphabet.png")throw "independent owner PNG precedence";
 owned.set("images/alphabet.xml","a/images/alphabet.xml");owner.atlas("alphabet");if(DynamicAtlasFrames.pair[1]!="a/images/alphabet.xml")throw "owner XML precedence";
 prefs.antialiasing=false;h.psychClientPrefs={data:{antialiasing:true}};if(owner.antialiasing())throw "captured prefs object live value without host capture";
 if(owner.text("a/file")!="a/file")throw "selected IO path";
}}
'''
  self.run_haxe(files)
 def run_haxe(self,files,cpp=False):
  from psych_standard_fixture_support import STANDARD_SERVICES
  files['PsychStandardServices.hx'] = STANDARD_SERVICES
  files['PsychPropertyBindings.hx']='class PsychPropertyBindings {public static function install(h:Dynamic,i:Dynamic,c:Dynamic,p:Dynamic):Void {}}'
  # Alphabet fixtures isolate native argument parsing, covered by the source oracle.
  files['PsychInstanceArguments.hx']='class PsychInstanceArguments {public static function parse(v:Dynamic,r:Bool,c:Dynamic,?p:Dynamic):Dynamic return v;}'
  if 'PlayState.hx' in files and 'var nightmareVisionLegacyFieldCameras' not in files['PlayState.hx']: files['PlayState.hx']=files['PlayState.hx'].replace('class PlayState {','class PlayState {public var nightmareVisionLegacyFieldCameras:Bool=false;')
  files['PsychAlphabetOwnerAccess.hx'] = (ROOT/'source/PsychAlphabetOwnerAccess.hx').read_text(encoding='utf-8')
  # Native state registration is tested by the connected state-registry probe.
  files['PsychStateClassBindings.hx'] = 'class PsychStateClassBindings {public static function registry(h:Dynamic):Dynamic return h.psychScriptVariables;public static function installScope(s:Dynamic):Void {} public static function install(i:Dynamic):Void {}}'
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   for name,content in files.items():
    path=Path(tmp)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
   env=os.environ.copy();env['HAXEPATH']=str(ROOT/'.tools/haxe');env['NEKOPATH']=str(ROOT/'.tools/neko');env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['PATH']=os.pathsep.join((env['HAXEPATH'],env['NEKOPATH'],env.get('PATH','')))
   cmd=[*HAXE_COMMAND,'-D','flixel','-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',tmp,'-main','Main']
   for target in ([['--interp'],['-cpp',str(Path(tmp)/'cpp'),'-D','no-compilation']] if cpp else [['--interp']]):
    r=subprocess.run(cmd+target,cwd=ROOT,env=env,capture_output=True,text=True,timeout=40)
    self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-3500:])
    if target[0]=='-cpp':
     # Actual native class reflection supports the variable, not the regular
     # function. Eval differs; the scoped API follows this Windows target.
     for name in ['PsychSourceAlphaCharacter','DonorAlphaCharacter']:
      native=(Path(tmp)/('cpp/src/'+name+'.cpp')).read_text()
      setter=native[native.index('bool '+name+'_obj::__SetStatic'):]
      setter=setter[:setter.index('#ifdef HXCPP_SCRIPTABLE')]
      self.assertIn('"allLetters"',setter)
      self.assertNotIn('"loadAlphabetData"',setter)
if __name__=='__main__':unittest.main()
