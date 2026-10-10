"""Direct native/source stage construction shares pinned registration order."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT, FLIXEL_ARGS, haxe_env
from test_psych_stage_scene_order import extract_method


class PsychStageDirectConstructionTest(unittest.TestCase):
    def test_direct_constructor_and_external_source_scope_registration(self):
        donor = ROOT.parent / 'fnf_sources/FNF-PsychEngine/source/backend/BaseStage.hx'
        if not donor.is_file():
            self.skipTest('pinned Psych source not mounted')
        constructor = extract_method(donor.read_text(encoding='utf-8'), 'public function new()')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            base = Path(folder)
            oracle = base/'oracle'
            actual = base/'actual'
            for work in (oracle, actual):
                work.mkdir()
                (work/'Probe.hx').write_text("""class Probe {
 public static var current:Dynamic;
 public static var log:Array<String>=[];
 public static var context:Dynamic;
}
""", encoding='utf-8')
            (oracle/'OracleBase.hx').write_text("""import flixel.FlxBasic;
class FlxG {public static var log={error:function(message:String):Void {}};}
class OracleBase extends FlxBasic {
 public var game(get,never):Dynamic;function get_game():Dynamic return Probe.current;
 public function create():Void {}
"""+constructor+'}', encoding='utf-8')
            probe = """class ProbeStage extends BASE {
 public function new() { SUPER; Probe.log.push('after:'+game.stages.indexOf(this)); }
 override public function create():Void {
  Probe.log.push('create:'+game.stages.indexOf(this)+':'+active+':'+exists);
 }
}
"""
            (oracle/'ProbeStage.hx').write_text(probe.replace('BASE','OracleBase').replace('SUPER','super()'),encoding='utf-8')
            (actual/'ProbeStage.hx').write_text(probe.replace('BASE','PsychBaseStageCompat').replace('SUPER','super(null,Probe.context,true)'),encoding='utf-8')
            main = """class Main {
 static function main() {
  Probe.current={stages:[],members:[]}; SETUP
  var stage=new ProbeStage();
  Sys.println(Probe.log.join('|'));
  EXTRA
 }
}
"""
            (oracle/'Main.hx').write_text(main.replace('SETUP','').replace('EXTRA',''),encoding='utf-8')
            setup = """Probe.context=new SourceStageContext(function() return Probe.current,function() return Probe.current,function(value) return true,function(name) return null);"""
            extra = """var first=Probe.current;
  var direct=PsychStageConstruction.createNative(Probe.context);
  if(first.stages.length!=2 || first.stages[1]!=direct || direct.game!=first) throw 'direct registration';
  var actor=new flixel.FlxBasic();first.boyfriend=actor;first.members.push(actor);
  first.add=function(value:Dynamic):Dynamic {first.members.push(value);return value;};
  first.insert=function(index:Int,value:Dynamic):Dynamic {first.members.insert(index,value);return value;};
  var prop=new flixel.FlxBasic();direct.add(prop);
  if(first.members[0]!=actor || first.members[1]!=prop) throw 'direct stage reused selected background placement';
  Probe.current={stages:[],members:[]};
  var next=PsychStageConstruction.createNative(Probe.context);
  if(Probe.current.stages.length!=1 || direct.game!=Probe.current || first.stages[1]!=direct) throw 'live roots/retained registration';
  var bindings:Map<String,Dynamic>=['backend.BaseStage'=>PsychBaseStageCompat,'Probe'=>Probe];
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.ExtraStage'],bindings,new Map());
  if(loaded.diagnostics.length!=0) throw loaded.diagnostics;
  var construction=new PsychStageConstruction(first,Probe.context);construction.bind(loaded.scope);
  var authored=loaded.scope.createInstance('demo.ExtraStage');
  if(Probe.current.stages.length!=3 || Probe.current.stages[1]!=authored || construction.stages[0]!=authored) throw 'non-selected source scope registration';
  if(construction.stages.length!=2 || !Std.isOfType(Probe.current.stages[2],PsychBaseStageCompat)) throw 'native constructor inside source class bypassed factory';
  if(Probe.log[2]!='source:1') throw 'non-selected source scope create ordering';
  PsychStageObject.call(authored,'destroy',[]);loaded.scope.release();
  stage.destroy();direct.destroy();next.destroy();"""
            (actual/'Main.hx').write_text(main.replace('SETUP',setup).replace('EXTRA',extra),encoding='utf-8')
            owner = actual/'owner/source/demo'
            owner.mkdir(parents=True)
            (owner/'ExtraStage.hx').write_text("""package demo; import backend.BaseStage; import Probe;
class ExtraStage extends BaseStage {override public function create():Void {Probe.log.push('source:'+game.stages.indexOf(this));new BaseStage();}}
""",encoding='utf-8')
            outputs=[]
            for work in (oracle,actual):
                command=[*HAXE_COMMAND,*FLIXEL_ARGS]
                if work==actual:
                    command+=['-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src')]
                command+=['-cp',str(work),'--run','Main',str(actual/'owner')]
                result=subprocess.run(command,cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                outputs.append(result.stdout)
            self.assertEqual(outputs[1],outputs[0])


if __name__=='__main__':
    unittest.main()
