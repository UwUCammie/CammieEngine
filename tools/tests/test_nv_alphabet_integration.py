"""Connected NV Alphabet class identity, static metadata and owner lifecycle."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from nv_alphabet_fixture_support import nv_alphabet_fixture_files
from nv_sprite_macro_fixture_support import nv_sprite_macro_fixture_files
from test_source_attachment_integration import integration_files
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]

class NVAlphabetIntegrationTest(unittest.TestCase):
 def test_actual_iris_static_routes_and_owner_lease(self):
  files=integration_files();files.update(nv_alphabet_fixture_files())
  macro_files=nv_sprite_macro_fixture_files()
  for dependency in ['flixel/FlxSprite.hx','flixel/util/FlxColor.hx']:files[dependency]=macro_files[dependency]
  files['NightmareVisionPaths.hx']='class NightmareVisionPaths {public final root:String;public final view:String;public var calls:Array<String>=[];public function new(r:String,v:String){root=r;view=v;}public function getAtlasFrames(name:String):flixel.graphics.frames.FlxAtlasFrames return getSparrowAtlas(name);public function getSparrowAtlas(name:String):flixel.graphics.frames.FlxAtlasFrames {calls.push(view+":"+name);return new flixel.graphics.frames.FlxAtlasFrames();}}'
  files['Main.hx']=r'''
class Main {
 static function ok(b:Bool,s:String):Void if(!b)throw s;
 static function main() {
  NightmareVisionAlphabetRegistry.enterSession("a");
  var a=new NightmareVisionScriptInterp();var peer=new NightmareVisionScriptInterp();var b=new NightmareVisionScriptInterp();
  var pa=new NightmareVisionPaths("a","first");var pp=new NightmareVisionPaths("a","latest");var pb=new NightmareVisionPaths("b","other");
  NightmareVisionAlphabetBindings.install(a,pa);NightmareVisionAlphabetBindings.install(peer,pp);NightmareVisionAlphabetBindings.install(b,pb);
  var p=new NightmareVisionScriptParser();
  a.execute(p.parseString("import funkin.objects.Alphabet; import funkin.objects.Alphabet.AlphaCharacter; import Reflect; import Type; original=AlphaCharacter.alphabet; originalNumbers=AlphaCharacter.numbers; originalSymbols=AlphaCharacter.symbols; AlphaCharacter.alphabet='abc'; Reflect.setProperty(AlphaCharacter,'numbers','79'); setter=Reflect.setField; setter(AlphaCharacter,'symbols','!?'); label=new Alphabet(12,24,'ab',false,.5); glyph=new AlphaCharacter(4,5,.5); type=Type.resolveClass('funkin.objects.AlphaCharacter'); creator=Type.createInstance; reflectedGlyph=creator(type,[8,9,.75]); name=Type.getClassName(Type.getClass(reflectedGlyph)); classAgain=Type.resolveClass(name); fields=Type.getClassFields(AlphaCharacter); copy=Reflect.copy(AlphaCharacter); resolvedReflect=Type.resolveClass('Reflect'); field=resolvedReflect.field; observed=field(AlphaCharacter,'alphabet');"));
  ok(Std.isOfType(a.variables.get("label"),NightmareVisionAlphabet)&&Std.isOfType(a.variables.get("glyph"),NightmareVisionAlphaCharacter)&&Std.isOfType(a.variables.get("reflectedGlyph"),NightmareVisionAlphaCharacter),"actual class/factory identities");
  a.variables.set("ordinaryString","source copy");a.variables.set("ordinaryArray",[1,{value:2}]);a.variables.set("ordinaryObject",{value:3,child:{value:4}});
  a.execute(p.parseString("copyString=Reflect.copy(ordinaryString); copyArray=Reflect.copy(ordinaryArray); copyObject=Reflect.copy(ordinaryObject); copyNull=Reflect.copy(null);"));
  ok(a.variables.get("copyString")==Reflect.copy(a.variables.get("ordinaryString"))&&a.variables.get("copyNull")==null,"ordinary string/null copy delegates platform source behavior");
  var copiedArray:Array<Dynamic>=cast a.variables.get("copyArray");var originalArray:Array<Dynamic>=cast a.variables.get("ordinaryArray");ok(copiedArray!=originalArray&&copiedArray.length==2&&copiedArray[1]==originalArray[1],"ordinary array shallow clone retains native type");
  var copiedObject=a.variables.get("copyObject");var originalObject=a.variables.get("ordinaryObject");ok(copiedObject!=originalObject&&copiedObject.value==3&&copiedObject.child==originalObject.child,"ordinary anonymous object native shallow copy");
  ok(a.variables.get("name")=="funkin.objects.AlphaCharacter"&&a.variables.get("classAgain")==NightmareVisionAlphaCharacter,"canonical runtime class roundtrip");
  var fields:Array<String>=cast a.variables.get("fields");for(name in ["alphabet","numbers","symbols"])ok(fields.indexOf(name)>=0,"actual static schema "+name);
  ok(Reflect.field(a.variables.get("copy"),"alphabet")=="abc"&&a.variables.get("observed")=="abc","copy and resolved/extracted reflection scoped");
  ok(pa.calls.length==0&&pp.calls.length==4&&pb.calls.length==0,"scope setup sole atlas view boundary; construction uses latest sameowner IO");
  peer.execute(p.parseString("same=AlphaCharacter.alphabet; nums=AlphaCharacter.numbers; syms=AlphaCharacter.symbols;"));b.execute(p.parseString("other=AlphaCharacter.alphabet;"));
  ok(peer.variables.get("same")=="abc"&&peer.variables.get("nums")=="79"&&peer.variables.get("syms")=="!?"&&b.variables.get("other")=="abcdefghijklmnopqrstuvwxyz","sameowner mutations and distinctowner isolation");
  a.execute(p.parseString("Reflect.setField(AlphaCharacter,'alphabet',null); Reflect.setProperty(AlphaCharacter,'numbers',null); AlphaCharacter.symbols=null; empty=new Alphabet(0,0,''); nullAlphabet=AlphaCharacter.alphabet; nullNumbers=AlphaCharacter.numbers; nullSymbols=AlphaCharacter.symbols;"));
  NightmareVisionAlphabetBindings.install(peer,pp);peer.execute(p.parseString("kept=AlphaCharacter.alphabet; keptNumbers=AlphaCharacter.numbers; keptSymbols=AlphaCharacter.symbols;"));
  ok(a.variables.get("nullAlphabet")==null&&a.variables.get("nullNumbers")==null&&a.variables.get("nullSymbols")==null&&peer.variables.get("kept")==null&&peer.variables.get("keptNumbers")==null&&peer.variables.get("keptSymbols")==null,"all three authored nulls preserved by binding and empty construction");
  a.execute(p.parseString("AlphaCharacter.alphabet=original; AlphaCharacter.numbers=originalNumbers; AlphaCharacter.symbols=originalSymbols; bare=false;try {unused=alphabet;} catch(error:Dynamic){bare=true;}"));ok(a.variables.get("bare")==true,"no bare static name pollution");
  ok(a.importBindings.get("funkin.objects.Alphabet")==NightmareVisionAlphabet&&a.importBindings.get("funkin.objects.Alphabet.AlphaCharacter")==NightmareVisionAlphaCharacter&&!a.importBindings.exists("funkin.objects.AlphaCharacter"),"source module import distinct from runtime name");
  a.execute(p.parseString("AlphaCharacter.alphabet='retained sameowner';"));NightmareVisionAlphabetRegistry.enterSession("a");var retry=new NightmareVisionScriptInterp();NightmareVisionAlphabetBindings.install(retry,pp);retry.execute(p.parseString("retained=AlphaCharacter.alphabet;"));ok(retry.variables.get("retained")=="retained sameowner","sameowner retry retains static charset");
  a.release();peer.execute(p.parseString("survivor=AlphaCharacter.alphabet;"));ok(peer.variables.get("survivor")=="retained sameowner","one interpreter release independent shared metadata");
  NightmareVisionAlphabetRegistry.enterSession("");var released=false;try peer.execute(p.parseString("stale=new AlphaCharacter(0,0,1);")) catch(error:Dynamic)released=Std.string(error).indexOf("released")>=0;ok(released,"owner exit releases old atlas IO");
  var fresh=new NightmareVisionScriptInterp();NightmareVisionAlphabetBindings.install(fresh,pp);fresh.execute(p.parseString("fresh=AlphaCharacter.alphabet;"));ok(fresh.variables.get("fresh")=="abcdefghijklmnopqrstuvwxyz","owner exit resets next realm defaults");
  NightmareVisionAlphabetRegistry.enterSession("c");var afterSwitch=new NightmareVisionScriptInterp();NightmareVisionAlphabetBindings.install(afterSwitch,pb);afterSwitch.execute(p.parseString("fresh=AlphaCharacter.numbers;"));ok(afterSwitch.variables.get("fresh")=="1234567890","primary switch resets dependency contexts");
  peer.release();b.release();retry.release();fresh.release();afterSwitch.release();
 }
}
'''
  self.run_haxe(files)
 def test_common_preset_and_primary_lease_routes(self):
  ps=(ROOT/'source/PlayState.hx').read_text()
  common=method(ps,'static function seedNightmareVisionCommon(')
  self.assertIn('NightmareVisionAlphabetBindings.install(interp, paths);',common)
  self.assertLess(common.index('NightmareVisionAlphabetBindings.install'),common.index('NightmareVisionSourceBindings.bindOwner'))
  initialization=method(ps,'function initializeNightmareVisionScripts(')
  self.assertLess(initialization.index('NightmareVisionPluginHost.releaseOtherOwner(root)'),initialization.index('NightmareVisionAlphabetRegistry.enterSession(root)'))
  self.assertLess(initialization.index('NightmareVisionAlphabetRegistry.enterSession(root)'),initialization.index("if (root == '') return"))
  self.assertIn('sourceSession.mountPlugins()',initialization)
  mount=method((ROOT/'source/NightmareVisionStateSession.hx').read_text(),'public function mountPlugins(')
  self.assertIn('PlayState.seedNightmareVisionCommon(interp, paths, prefs, runtime, mods, difficulty',mount)
  self.assertIn('seedNightmareVisionCommon(interp, nightmareVisionPaths',method(ps,'function seedNightmareVision('))
 def test_old_plugin_teardown_precedes_context_release(self):
  files=integration_files();files.update(nv_alphabet_fixture_files())
  macro_files=nv_sprite_macro_fixture_files()
  for dependency in ['flixel/FlxSprite.hx','flixel/util/FlxColor.hx']:files[dependency]=macro_files[dependency]
  files['NightmareVisionPaths.hx']='class NightmareVisionPaths {public final root:String;public var calls=0;public function new(r:String)root=r;public function getAtlasFrames(name:String):flixel.graphics.frames.FlxAtlasFrames return getSparrowAtlas(name);public function getSparrowAtlas(name:String):flixel.graphics.frames.FlxAtlasFrames {calls++;return new flixel.graphics.frames.FlxAtlasFrames();}}'
  init=method((ROOT/'source/PlayState.hx').read_text(),'function initializeNightmareVisionScripts(')
  start=init.index('var root = nightmareVisionSelectedRoot();');end=init.index('if (nightmareVisionActiveMods',start)
  files['LeaseHost.hx']='class LeaseHost {public var selected:String;public function new(s:String)selected=s;function nightmareVisionSelectedRoot():String return selected;public function initializeLease():Void{'+init[start:end]+'}}'
  files['NightmareVisionPluginHost.hx']='class NightmareVisionPluginHost {public static var onDestroy:Void->Void;public static function releaseOtherOwner(root:String):Void {if(onDestroy!=null)onDestroy();}}'
  files['Main.hx']=r'''
class Main {static function main() {
 NightmareVisionAlphabetRegistry.enterSession("old");var paths=new NightmareVisionPaths("old");var interp=new NightmareVisionScriptInterp();NightmareVisionAlphabetBindings.install(interp,paths);var p=new NightmareVisionScriptParser();var called=false;
 NightmareVisionPluginHost.onDestroy=function(){interp.execute(p.parseString("teardownGlyph=new AlphaCharacter(0,0,1);"));called=true;};new LeaseHost("new").initializeLease();if(!called||paths.calls!=1)throw "actual lease prefix must allow old plugin atlas IO before release";
 var released=false;try interp.execute(p.parseString("afterRelease=new AlphaCharacter(0,0,1);")) catch(error:Dynamic)released=Std.string(error).indexOf("released")>=0;if(!released)throw "old owner IO must release after plugin callback";interp.release();
}}
'''
  self.run_haxe(files)
 def run_haxe(self,files):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   for name,content in files.items():
    path=Path(tmp)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding="utf-8")
   env=os.environ.copy();env['HAXEPATH']=str(ROOT/'.tools/haxe');env['NEKOPATH']=str(ROOT/'.tools/neko');env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['PATH']=os.pathsep.join((env['HAXEPATH'],env['NEKOPATH'],env.get('PATH','')))
   cmd=[*HAXE_COMMAND,'-D','flixel','-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',tmp,'-main','Main']
   for target in [['--interp'],['-cpp',str(Path(tmp)/'cpp'),'-D','no-compilation']]:
    r=subprocess.run(cmd+target,cwd=ROOT,env=env,capture_output=True,text=True,timeout=40)
    self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-3500:])
    if target[0]=='-cpp':
     native=(Path(tmp)/'cpp/src/NightmareVisionAlphaCharacter.cpp').read_text();setter=native[native.index('bool NightmareVisionAlphaCharacter_obj::__SetStatic'):];setter=setter[:setter.index('#ifdef HXCPP_SCRIPTABLE')]
     for name in ['alphabet','numbers','symbols']:self.assertIn('"'+name+'"',setter)
if __name__=='__main__':unittest.main()
