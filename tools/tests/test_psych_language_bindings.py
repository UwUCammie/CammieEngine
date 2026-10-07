"""HScript, reflected-class and Lua bindings for Psych Language."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND, TEST_TMP
from tools.haxe_flixel_math_stubs import write_flixel_point_stub

ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"


class PsychLanguageBindingsTest(unittest.TestCase):
    def test_source_class_reflection_and_lua_callbacks_share_the_owner_runtime(self):
        fixture = r'''
import hscript.Interp;
import PsychLanguageRuntime.PsychLanguageHost;

class OwnerPrefs {
 public var data:Dynamic={language:'en-US'};
 public var defaultData:Dynamic={language:'en-US'};
 public function new() {}
}
class Hooks {
 public var active:Bool=true;
 public var alphabetPaths:Array<String>=[];
 public function new() {}
 public function host():PsychLanguageHost return {
  ownerActive:function():Bool return active,
  mergedLines:function(_language:String):Array<String> return [
   'English', 'hello: "Hello {1}"', 'images/alphabet: "images/test.png"'
  ],
  loadAlphabetData:function(path:String):Void alphabetPaths.push(path),
  report:function(_message:String):Void {}
 };
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function call(callback:Dynamic,args:Array<Dynamic>):Dynamic
  return Reflect.callMethod(null,callback,args);
 static function main():Void {
  var hooks=new Hooks();
  var runtime=new PsychLanguageRuntime('assets/imported_mods/language-bindings',
   new OwnerPrefs(),hooks.host());
  runtime.reloadPhrases();

  var interp=new NightmareVisionScriptInterp();
  PsychLanguageBindings.install(interp,runtime);
  var parser=new NightmareVisionScriptParser();
  interp.execute(parser.parseString(
   'import Type; import Reflect; import backend.Language as Lang; '
   +'resolved=Type.resolveClass("backend.Language"); '
   +'shortResolved=Type.resolveClass("Language"); '
   +'resolvedName=Type.getClassName(resolved); '
   +'listed=Reflect.fields(Lang); classListed=Type.getClassFields(Lang); '
   +'hasPhrases=Reflect.hasField(Lang,"phrases"); '
   +'direct=Lang.getPhrase("hello",null,["Hscript"]); '
   +'reflected=Reflect.callMethod(Lang,Reflect.field(Lang,"getPhrase"),["hello",null,["Reflected"]]); '
   +'file=Reflect.callMethod(Lang,Reflect.field(Lang,"getFileTranslation"),["IMAGES/ALPHABET"]); '
   +'defaultBefore=Lang.defaultLangName; Lang.defaultLangName="Français"; '
   +'defaultAfter=Lang.defaultLangName; mapValue=Lang.phrases.get("hello"); '
   +'capturedPhrase=Reflect.field(Lang,"getPhrase");',
   'psych-language-owner'));

  check(interp.variables.get('resolved')==PsychLanguageRuntime
   && interp.variables.get('shortResolved')==PsychLanguageRuntime
   && interp.variables.get('resolvedName')=='backend.Language',
   'short and qualified imports must resolve to the same real source class token');
  var fields:Array<String>=cast interp.variables.get('listed');
  var classFields:Array<String>=cast interp.variables.get('classListed');
  for (name in ['defaultLangName','phrases','reloadPhrases','getPhrase','getFileTranslation'])
   check(fields.indexOf(name)>=0 && classFields.indexOf(name)>=0,
    'Reflect and Type reflection must expose the donor Language member '+name);
  check(interp.variables.get('hasPhrases')==true
   && interp.variables.get('direct')=='Hello Hscript'
   && interp.variables.get('reflected')=='Hello Reflected'
   && interp.variables.get('file')=='images/test.png'
   && interp.variables.get('defaultBefore')=='English (US)'
   && interp.variables.get('defaultAfter')=='Français'
   && interp.variables.get('mapValue')=='Hello {1}',
   'direct and reflected class methods, mutable source fields and phrases must use the same runtime');
  var capturedPhrase:Dynamic=interp.variables.get('capturedPhrase');

  var luaInterp=new Interp();
  PsychLanguageBindings.installLua(luaInterp,runtime);
  check(call(luaInterp.variables.get('getTranslationPhrase'),['hello','Fallback',['Lua']])=='Hello Lua'
   && call(luaInterp.variables.get('getTranslationPhrase'),['missing','Fallback'])=='Fallback'
   && call(luaInterp.variables.get('getTranslationPhrase'),['missing'])=='missing'
   && call(luaInterp.variables.get('getFileTranslation'),[' images/alphabet '])=='images/test.png',
   'Lua globals must register the donor names and delegate their defaults to the same owner runtime');

  var scope=new SourceNativeClassScope();
  scope.installReflectionBindings();
  var priorFields:Dynamic=function(value:Dynamic):Array<String>
   return ['earlierReflection'].concat(Reflect.fields(value));
  scope.bindStaticField(Reflect,'fields',function() return priorFields);
  PsychLanguageBindings.installScope(scope,runtime);
  var token=scope.resolveClass('backend.Language');
  var shortToken=scope.resolveClass('Language');
  var scopedFields:Array<String>=cast call(scope.read(Reflect,'fields'),[token]);
  var scopedClassFields:Array<String>=cast call(scope.read(Type,'getClassFields'),[token]);
  var scopedMethod:Dynamic=scope.read(token,'getPhrase');
  check(token==PsychLanguageRuntime && shortToken==token
   && scopedFields.indexOf('earlierReflection')>=0
   && scopedFields.indexOf('getFileTranslation')>=0
   && scopedClassFields.indexOf('getPhrase')>=0
   && call(scopedMethod,['hello',null,['Scoped']])=='Hello Scoped',
   'the Lua native class scope must compose prior Reflect routes and use the shared service: '
   +Std.string(token==PsychLanguageRuntime)+','+Std.string(shortToken==token)+','
   +scopedFields.join('|')+','+scopedClassFields.join('|')+','
   +Std.string(call(scopedMethod,['hello',null,['Scoped']])));

  hooks.active=false;
  var guarded=false;
  try call(capturedPhrase,['hello']) catch(_ :Dynamic) guarded=true;
  var scopeGuarded=false;
  try call(scopedMethod,['hello']) catch(_ :Dynamic) scopeGuarded=true;
  check(guarded && scopeGuarded,
   'method closures obtained before owner release must still check the captured owner');

  runtime.release();
  var luaGuarded=false;
  try call(luaInterp.variables.get('getFileTranslation'),['x']) catch(_ :Dynamic) luaGuarded=true;
  check(luaGuarded,'retained translated-Lua callbacks must reject the released runtime');
  interp.release();luaInterp.variables.clear();scope.release();
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="psych-language-bindings-", dir=TEST_TMP) as scratch:
            scratch = Path(scratch)
            write_flixel_point_stub(scratch)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                 "-cp", str(IRIS), "-cp", str(scratch),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
