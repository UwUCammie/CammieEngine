"""Execute the remaining Psych source callback and HScript helper semantics."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, ROOT


def extract(source: str, name: str) -> str:
    match = re.search(r"\bfunction\s+" + re.escape(name) + r"\s*\(", source)
    if match is None:
        raise AssertionError(name)
    brace = source.index("{", match.end())
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():index + 1]
    raise AssertionError(f"unclosed {name}")


class PsychRemainingSourceBindingTest(unittest.TestCase):
    def run_haxe(self, source: str, classname: str) -> str:
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / f"{classname}.hx").write_text(source, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder, "--run", classname],
                cwd=folder, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_tagged_property_helpers_and_direction_tween(self):
        source = (ROOT / "source/PsychSourceBindings.hx").read_text()
        methods = "\n".join(extract(source, name) for name in (
            "getPropertyLuaSprite", "setPropertyLuaSprite", "noteTweenDirection",
            "readTaggedProperty", "writeTaggedProperty", "formatTweenTag",
        ))
        self.assertNotIn("psychEaseName", source)
        self.assertNotIn("Reflect.field(FlxEase", source)
        fixture = r'''using StringTools;
class Note { public var direction:Float = 0; public function new() {} }
class FakeHost {
 public var psychScriptVariables:Map<String,Dynamic> = [];
 public var receptors:Array<Note>;
 public var wrapped:Array<Bool>=[];
 public var tweens:Array<Array<Dynamic>>=[];
 public function new() receptors=[new Note(),new Note()];
 // The direction tween is only argument preparation: the receptor lookup and
 // the tag bookkeeping belong to the host and have their own tests.
 public function receptorAt(index:Int,wrap:Bool=false):Dynamic { wrapped.push(wrap); return receptors[index % receptors.length]; }
 public function startTaggedTween(tag:String,target:Dynamic,props:Dynamic,duration:Float,?options:Dynamic,?completedArgs:Array<Dynamic>):Dynamic {
  tweens.push([tag,target,props,duration,options,completedArgs]); return null;
 }
}
class BindingFixture {
 var host:FakeHost;
 public function new(host:FakeHost) this.host=host;
 __METHODS__
 static function main() {
  var host=new FakeHost(); var binding=new BindingFixture(host);
  var tagged={position:{x:3.0}}; host.psychScriptVariables.set('sprite',tagged);
  if(binding.getPropertyLuaSprite('sprite','position.x')!=3) throw 'dotted read failed';
  if(!binding.setPropertyLuaSprite('sprite','position.x',8)) throw 'existing tag write returned false';
  if(binding.getPropertyLuaSprite('sprite','position.x')!=8) throw 'dotted write failed';
  if(binding.getPropertyLuaSprite('missing','position.x')!=null) throw 'missing tag read was not null';
  if(binding.setPropertyLuaSprite('missing','position.x',9)) throw 'missing tag write returned true';
  var tag=binding.noteTweenDirection(' turn.one ',1,135.5,0.4,'quadOut');
  if(tag!='tween_turnone') throw 'tween registry tag was not Psych-formatted';
  var call=host.tweens[0];
  if(call[1]!=host.receptors[1] || call[2].direction!=135.5 || call[3]!=0.4 || call[4].ease!='quadOut') throw 'direction tween arguments changed';
  if(call[0]!=' turn.one ') throw 'the tween must be stored under the tag the script gave, so cancelTween finds it';
  if(call[5].length!=1 || call[5][0]!=' turn.one ') throw 'completion callback did not preserve original tag';
  if(host.wrapped.join(',')!='true') throw 'direction tween must use the wrapping receptor lookup';
  if(binding.noteTweenDirection('wrap',3,10,0.1)!='tween_wrap' || host.tweens[1][1]!=host.receptors[1]) throw 'index past the end did not wrap';
  if(binding.noteTweenDirection(null,0,45,0.2)!=null || host.tweens[2][0]!=null || host.tweens[2][2].direction!=45) throw 'untagged tween behavior changed';
  if(host.tweens[2][4].ease!='linear') throw 'default ease changed';
  host.receptors[0]=null;
  var before=host.tweens.length;
  if(binding.noteTweenDirection('missing',0,30,1)!=null || host.tweens.length!=before) throw 'missing strum created a tween';
  Sys.println('OK');
 }
}'''.replace("__METHODS__", methods)
        self.run_haxe(fixture, "BindingFixture")

    def test_lua_setvar_resolves_only_explicit_instance_markers(self):
        source = (ROOT / "source/PsychSourceBindings.hx").read_text()
        methods = "\n".join(extract(source, name) for name in ("setVar", "storePsychVariable"))
        fixture = r'''class PsychInstanceArguments {public static function parse(v:Dynamic,r:Bool,c:Dynamic):Dynamic throw 'Unexpected modern parser in historical extension test';}
class PsychStateClassBindings {public static function registry(host:Dynamic):Dynamic return host.psychScriptVariables;}
class FakeHost { public var nightmareVisionLegacyFieldCameras:Bool=true;public function compatResolveClass(n:String):Dynamic return null;public var psychScriptVariables:Map<String,Dynamic>=[]; public function new() {} }
class BindingFixture {
 var host:FakeHost;
 var resolved:Array<Array<Dynamic>>=[];
 public function new(host:FakeHost) this.host=host;
 function resolveInstancePath(path:String,type:Null<String>):Dynamic { resolved.push([path,type]); return path=='sprite.position.x' && type=='FakeType' ? 42 : null; }
 __METHODS__
 static function main() {
  var host=new FakeHost(); var binding=new BindingFixture(host);
  var marker=SourceScriptReflection.INSTANCE_PREFIX+'sprite.position.x::FakeType';
  if(binding.setVar('resolved',marker)!=marker || host.psychScriptVariables.get('resolved')!=42) throw 'setVar did not resolve and return the source marker';
  var array:Array<Dynamic>=[marker,'ordinary string'];
  if(binding.setVar('array',array)!=array) throw 'setVar did not return the assigned input';
  var stored:Array<Dynamic>=cast host.psychScriptVariables.get('array');
  if(stored[0]!=42 || stored[1]!='ordinary string' || binding.resolved.length!=2) throw 'setVar recursively parsed values or parsed an ordinary string';
  Sys.println('OK');
 }
}'''.replace("__METHODS__", methods)
        self.run_haxe(fixture, "BindingFixture")

    def test_hscript_shared_vars_callback_bridge_and_build_targets(self):
        source = (ROOT / "source/PsychHscriptSourceBindings.hx").read_text()
        methods = "\n".join(extract(source, name) for name in (
            "invokeBridge", "registerLocal", "registerGlobal", "platformBuildTarget",
        ))
        fixture = r'''class FakeBridge {
 public var calls:Array<Array<Dynamic>>=[];
 public function new() {}
 public function parentFacade(origin:String,owner:Dynamic):Dynamic { calls.push(['parent',origin,owner]); return 'parent-facade'; }
 public function selfFacade(origin:String,owner:Dynamic,parent:Dynamic):Dynamic { calls.push(['self',origin,owner,parent]); return 'self-facade'; }
 public function registerLocal(origin:String,name:String,func:Dynamic,parent:Dynamic):Dynamic { calls.push(['local',origin,name,func,parent]); return 'local-ok'; }
 public function registerGlobal(origin:String,name:String,func:Dynamic):Dynamic { calls.push(['global',origin,name,func]); return 'global-ok'; }
}
class BindingFixture {
 public function new() {}
 __METHODS__
 static function main() {
  var binding=new BindingFixture();
  var vars:Map<String,Dynamic>=[];
  if(SourceScriptVariables.set(function() return vars,'x',17)!=17 || SourceScriptVariables.get(function() return vars,'x',true)!=17) throw 'shared set/get mismatch';
  if(!SourceScriptVariables.remove(function() return vars,'x') || SourceScriptVariables.remove(function() return vars,'x')) throw 'remove existence result mismatch';
  var bridge=new FakeBridge(); var owner={id:'interp'}; var cb=function() return 2;
  var parent=binding.invokeBridge(bridge,'parentFacade',['owner/song.lua',owner]);
  var self=binding.invokeBridge(bridge,'selfFacade',['owner/song.lua',owner,parent]);
  if(parent!='parent-facade' || self!='self-facade' || bridge.calls[0][2]!=owner || bridge.calls[1][3]!=parent) throw 'owner facade bridge contract changed';
  binding.registerLocal(bridge,'owner/song.lua','sample',cb,parent);
  binding.registerGlobal(bridge,'owner/song.lua','globalSample',cb);
  if(bridge.calls.length!=4 || bridge.calls[2][1]!='owner/song.lua' || bridge.calls[2][4]!=parent || bridge.calls[3][0]!='global') throw 'callback bridge scope or arguments changed';
  var targets=[['windows','windows'],['linux','linux'],['mac','mac'],['html5','browser'],['android','android'],['switch','switch'],['other','unknown']];
  for (target in targets) if(binding.platformBuildTarget(target[0])!=target[1]) throw 'build target mismatch: '+target[0];
  if(binding.platformBuildTarget('windows',true)!='windows_x86') throw 'x86 build target mismatch';
  var failed=false; try binding.invokeBridge(null,'parentFacade',[]) catch (_:Dynamic) failed=true;
  if(!failed) throw 'missing bridge silently accepted';
  Sys.println('OK');
 }
}'''.replace("__METHODS__", methods)
        self.run_haxe(fixture, "BindingFixture")


if __name__ == "__main__":
    unittest.main()
