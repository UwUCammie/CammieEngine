"""Source-compared super/create ordering and owner-scoped nested stage lifetime."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT, FLIXEL_ARGS, haxe_env
from test_psych_stage_scene_order import extract_method

STAGES = {
    "Middle": """package demo; import backend.BaseStage;
class Middle extends BaseStage {
 public function new() { ProbeHost.events.push('middle:before'); super(); ProbeHost.events.push('middle:after'); }
 override public function create():Void { ProbeHost.events.push('inherited:' + game.stages.indexOf(this)); }
}
""",
    "Leaf": """package demo; import backend.BaseStage;
class Leaf extends BaseStage {
 public function new() { ProbeHost.events.push('leaf:before'); super(); ProbeHost.events.push('leaf:after'); }
 override public function create():Void { ProbeHost.events.push('leaf:create:' + game.stages.indexOf(this)); }
 override public function destroy():Void { ProbeHost.events.push('leaf:destroy'); super.destroy(); }
}
""",
    "Child": """package demo; import demo.Middle; import demo.Leaf;
class Child extends Middle {
 public var value:String = 'initial';
 public function new() { ProbeHost.events.push('child:before'); value = 'before'; active = false; defaultCamZoom = 1.25; super(); value = 'after'; ProbeHost.events.push('child:after'); }
 override public function create():Void {
  ProbeHost.events.push('child:create:' + value + ':' + game.stages.indexOf(this) + ':' + active + ':' + defaultCamZoom);
  new Leaf();
 }
 override public function stepHit():Void { new Leaf(); }
 override public function destroy():Void { ProbeHost.events.push('child:destroy'); super.destroy(); }
}
""",
    "Inherited": """package demo; import demo.Middle;
class Inherited extends Middle { public function new() super(); }
""",
    "Broken": """package demo; import backend.BaseStage; import demo.Leaf;
class Broken extends BaseStage {
 override public function create():Void { new Leaf(); throw 'authored failure'; }
}
""",
}
HOST = """class ProbeHost {
 public static var events:Array<String> = [];
 public static var current:Dynamic;
 public var stages:Array<Dynamic> = [];
 public var members:Array<Dynamic> = [];
 public var defaultCamZoom:Float=.5;
 public function new() {}
}
"""

class PsychStageConstructionTest(unittest.TestCase):
    def run_haxe(self, base, main, *args, native=False):
        command = [*HAXE_COMMAND]
        if not native:
            command += ['-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),
                        '-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),*FLIXEL_ARGS]
        command += ['-cp',str(base),'--run',main,*map(str,args)]
        result = subprocess.run(command,cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return result.stdout.strip()

    def test_source_constructor_order_nested_registration_and_failure_cleanup(self):
        donor=ROOT.parent/'fnf_sources/FNF-PsychEngine/source/backend/BaseStage.hx'
        if not donor.is_file(): self.skipTest('pinned Psych source not mounted')
        constructor=extract_method(donor.read_text(encoding='utf-8'),'public function new()')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            base=Path(directory); oracle=base/'oracle'; actual=base/'actual'; owner=actual/'owner'
            for folder in [oracle,actual]:
                folder.mkdir(parents=True)
                (folder/'ProbeHost.hx').write_text(HOST,encoding='utf-8')
            for name,source in STAGES.items():
                for folder in [oracle/'demo',owner/'source/demo']:
                    folder.mkdir(parents=True,exist_ok=True)
                    (folder/(name+'.hx')).write_text(source,encoding='utf-8')
            (oracle/'flixel').mkdir();(oracle/'backend').mkdir()
            (oracle/'flixel/FlxBasic.hx').write_text("""package flixel; class FlxBasic {
 public var active:Bool=true; public var exists:Bool=true;
 public function new() {} public function destroy():Void {exists=false;}
}""",encoding='utf-8')
            (oracle/'FlxG.hx').write_text("class FlxG { public static var log={error:function(message:String) {throw message;}}; }",encoding='utf-8')
            (oracle/'backend/BaseStage.hx').write_text("""package backend; import flixel.FlxBasic; import FlxG;
class BaseStage extends FlxBasic {
 public var game(get,never):Dynamic; function get_game():Dynamic return ProbeHost.current;
 public var defaultCamZoom(get,set):Float;
 function get_defaultCamZoom():Float return game.defaultCamZoom;
 function set_defaultCamZoom(value:Float):Float return game.defaultCamZoom=value;
 public function create():Void {} public function stepHit():Void {}
"""+constructor+'}',encoding='utf-8')
            (oracle/'Oracle.hx').write_text("""class Oracle {
 static function main() {
  ProbeHost.current=new ProbeHost(); new demo.Child();new demo.Inherited();
  Sys.println(ProbeHost.events.join('|'));
 }
}""",encoding='utf-8')
            expected=self.run_haxe(oracle,'Oracle',native=True)
            (actual/'Main.hx').write_text("""class Main {
 static function main() {
  var host=new ProbeHost(); ProbeHost.current=host;
  var bindings:Map<String,Dynamic>=['ProbeHost'=>ProbeHost];
  var runtime=new PsychCompiledStageRuntime(Sys.args()[0],'demo.Child',host,bindings);
  if(!runtime.create()) throw runtime.diagnostics;
  var inherited=new PsychCompiledStageRuntime(Sys.args()[0],'demo.Inherited',host,bindings);
  if(!inherited.create()) throw inherited.diagnostics;
  Sys.println(ProbeHost.events.join('|'));
  if(host.stages.length!=3 || host.stages[0]!=runtime.sourceObject || host.stages[2]!=inherited.sourceObject) throw 'registered wrong source identity';
  runtime.beginPostCreate();runtime.dispatch('stepHit',[]);
  if(host.stages.length!=4) throw 'callback-created nested stage not registered';
  var count=ProbeHost.events.length;
  var root=runtime.sourceObject;
  runtime.destroy(true,false);
  PsychStageObject.call(host.stages[1],'destroy',[]);
  PsychStageObject.call(host.stages[3],'destroy',[]);
  runtime.destroy();
  if(ProbeHost.events.slice(count).join('|')!='child:destroy|leaf:destroy|leaf:destroy') throw 'scope released before sibling cleanup or duplicate destroy';
  if(PsychStageObject.read(root,'exists')!=false) throw 'native stage lifetime survived release';
  inherited.destroy();
  var isolatedHost=new ProbeHost();
  var broken=new PsychCompiledStageRuntime(Sys.args()[0],'demo.Broken',isolatedHost,bindings);
  if(broken.create()) throw 'authored constructor failure accepted';
  if(isolatedHost.stages.length!=0) throw 'failed constructor retained registered stages';
  if(host.stages.length!=4) throw 'failed owner changed another owner registry';
  var inactiveHost=new ProbeHost();
  var inactive=new PsychCompiledStageRuntime(Sys.args()[0],'demo.Child',inactiveHost,bindings);
  if(!inactive.create()) throw inactive.diagnostics;
  PsychStageObject.write(inactive.sourceObject,'active',false);
  var cleanupStart=ProbeHost.events.length;
  PsychStageObject.call(inactiveHost.stages[1],'destroy',[]);
  inactive.releaseAfterHostTraversal();
  if(ProbeHost.events.slice(cleanupStart).join('|')!='leaf:destroy') throw 'host finalizer repeated sibling callbacks or destroyed inactive root';

 }
}""",encoding='utf-8')
            self.assertEqual(self.run_haxe(actual,'Main',owner),expected)

if __name__=='__main__': unittest.main()
