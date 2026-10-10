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
  var independent=Probe.current;
  independent.boyfriend=new flixel.FlxBasic();independent.members.push(independent.boyfriend);
  independent.add=function(value:Dynamic):Dynamic {independent.members.push(value);return value;};
  independent.insert=function(index:Int,value:Dynamic):Dynamic {independent.members.insert(index,value);return value;};
  var independentProp=new flixel.FlxBasic();authored.callFunction('add',[independentProp]);
  if(independent.members[0]!=independent.boyfriend || independent.members[1]!=independentProp) throw 'independent source scope reused selected background placement';
  independent.boyfriend.destroy();independentProp.destroy();
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


    def test_nested_helpers_match_source_scene_order_across_construction_phases(self):
        donor = ROOT.parent / 'fnf_sources/FNF-PsychEngine/source/backend/BaseStage.hx'
        if not donor.is_file():
            self.skipTest('pinned Psych source not mounted')
        source = donor.read_text(encoding='utf-8')
        constructor = extract_method(source, 'public function new()')
        add = 'public ' + next(line.strip() for line in source.splitlines() if line.strip().startswith('function add('))
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            base = Path(folder)
            outputs = []
            for native in (True, False):
                work = base/('oracle' if native else 'actual')
                work.mkdir()
                owner = work/'owner'
                modules = work if native else owner/'source'
                (modules/'demo').mkdir(parents=True)
                (work/'Probe.hx').write_text("""import flixel.FlxBasic;
class Probe {
 public static var current:Dynamic;
 public static var foreign:Dynamic;
 public static function prop(id:Int):FlxBasic {var p=new FlxBasic();p.ID=id;return p;}
 public static function swap():Dynamic {var old=current;current=foreign;return old;}
 public static function restore(value:Dynamic):Void {current=value;}
}
""",encoding='utf-8')
                (modules/'demo/Child.hx').write_text("""package demo;
import backend.BaseStage; import Probe;
class Child extends BaseStage {
 override public function create():Void {add(Probe.prop(3));}
}
""",encoding='utf-8')
                (modules/'demo/Parent.hx').write_text("""package demo;
import backend.BaseStage; import Probe; import demo.Child;
class Parent extends BaseStage {
 public var helper:BaseStage;
 override public function create():Void {
  add(Probe.prop(1)); helper=new BaseStage(); helper.add(Probe.prop(2)); new Child();
  var old=Probe.swap();helper.add(Probe.prop(4));new Child();Probe.restore(old);
  helper.add(Probe.prop(7));
 }
 override public function createPost():Void {
  helper.add(Probe.prop(5));new BaseStage().add(Probe.prop(6));new Child();
 }
}
""",encoding='utf-8')
                if native:
                    (work/'backend').mkdir()
                    (work/'backend/BaseStage.hx').write_text("""package backend;
import flixel.FlxBasic;import Probe;
class FlxG {public static var log={error:function(message:String):Void {}};public static var state(get,never):Dynamic;static function get_state():Dynamic return Probe.current;}
class BaseStage extends FlxBasic {
 public var game(get,never):Dynamic;function get_game():Dynamic return Probe.current;
 public function create():Void {} public function createPost():Void {}
"""+constructor+'\n'+add+'\n}',encoding='utf-8')
                main="""import flixel.FlxBasic;
class Main {
 static function scene():Dynamic {
  var s:Dynamic={stages:[],members:[],gf:Probe.prop(10),dad:Probe.prop(11),boyfriend:Probe.prop(12)};
  s.add=function(v:Dynamic):Dynamic {s.members.push(v);return v;};
  s.insert=function(i:Int,v:Dynamic):Dynamic {s.members.insert(i,v);return v;};return s;
 }
 static function actors(s:Dynamic):Void {s.add(s.gf);s.add(s.dad);s.add(s.boyfriend);s.add(Probe.prop(13));}
 static function dump(s:Dynamic):String {var ids=[];for(v in (cast s.members:Array<FlxBasic>)) ids.push(v.ID);return ids.join(',');}
 static function main():Void {
  var scene=scene();Probe.current=scene;scene.add(Probe.prop(0));
  Probe.foreign=Main.scene();actors(Probe.foreign);
  SETUP
  Sys.println(dump(scene)+'|'+dump(Probe.foreign));
  POST
  Sys.println(dump(scene)+'|'+dump(Probe.foreign));
  CLEANUP
 }
}
"""
                if native:
                    setup='var stage=new demo.Parent();actors(scene);'
                    post='stage.createPost();'
                    cleanup=''
                else:
                    setup="""actors(scene);
  var context=new SourceStageContext(function() return Probe.current,function() return Probe.current,function(v) return true,function(n) return null);
  var bindings:Map<String,Dynamic>=['backend.BaseStage'=>PsychBaseStageCompat,'Probe'=>Probe];
  var loaded=CodenameScriptClassLoader.load(Sys.args()[0],['demo.Parent'],bindings,new Map());
  if(loaded.diagnostics.length!=0) throw loaded.diagnostics;
  // The retained asset owner differs from the current construction scene.
  var construction=new PsychStageConstruction(Probe.foreign,context,true);
  construction.bind(loaded.scope);construction.bind(loaded.scope);
  var stage=loaded.scope.createInstance('demo.Parent');
  // Rebinding the same scope must not restart the phase or change its scene.
  Probe.current=Probe.foreign;construction.bind(loaded.scope);Probe.current=scene;
"""
                    post="""construction.beginPostCreate();
  stage.callFunction('createPost',[]);
"""
                    cleanup="""var rejected=false;
  var other=new hscript.ScriptClassScope();
  try construction.bind(other) catch(e:Dynamic) rejected=true;
  if(!rejected) throw 'construction owner changed';other.release();
  for(stage in construction.stages) PsychStageObject.call(stage,'destroy',[]);
  loaded.scope.release();
"""
                (work/'Main.hx').write_text(main.replace('SETUP',setup).replace('POST',post).replace('CLEANUP',cleanup),encoding='utf-8')
                command=[*HAXE_COMMAND,*FLIXEL_ARGS]
                if not native:
                    command+=['-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src')]
                command+=['-cp',str(work),'--run','Main',str(owner)]
                result=subprocess.run(command,cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                outputs.append(result.stdout)
            self.assertEqual(outputs[1],outputs[0])
            self.assertIn('0,1,2,3,7,10,11,12,13|10,11,12,13,4,3',outputs[0])
            self.assertIn('0,1,2,3,7,10,11,12,13,5,6,3|',outputs[0])


if __name__=='__main__':
    unittest.main()
