"""Selected stages and real Iris scripts share owner identity without sharing phase."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_compiled_stage_runtime import ROOT, FLIXEL_ARGS, haxe_env

MODULES = {
    'Counter': """package demo; class Counter {
 public static var count:Int=0;
 public var value:Int=7;
 public function new() {}
 public function next():Int return ++count;
}""",
    'Stage': """package demo; import backend.BaseStage; import backend.ClientPrefs; import demo.Counter; import flixel.FlxObject;
class Stage extends BaseStage {
 public static var created:Int=0;
 public static var destroyed:Int=0;
 public var pref:Int=0;
 override public function create():Void {
  created++; Counter.count+=10; pref=ClientPrefs.token;
  var prop=new FlxObject(); prop.ID=created; add(prop);
  var helper=new BaseStage(); var extra=new FlxObject(); extra.ID=created+100; helper.add(extra);
 }
 override public function stepHit():Void {new Stage(); throw 'callback probe';}
 override public function destroy():Void {destroyed++; super.destroy();}
}""",
    'Broken': """package demo; import demo.Stage; import backend.BaseStage; import flixel.FlxObject;
class Broken extends BaseStage {
 override public function create():Void {new Stage();add(new FlxObject());throw 'constructor probe';}
}""",
    'Bad': 'package demo; class Wrong {}',
}

class PsychStageSharedSessionTest(unittest.TestCase):
    def test_identity_phase_failure_and_ordered_lifetime(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            base=Path(directory);owner=base/'owner';modules=owner/'source/demo';modules.mkdir(parents=True)
            for name,source in MODULES.items():
                (modules/(name+'.hx')).write_text(source,encoding='utf-8')
            (base/'HxcCompatRuntime.hx').write_text('class HxcCompatRuntime {public static function getZIndex(o:Dynamic):Dynamic return 0; public static function setZIndex(o:Dynamic,v:Dynamic,?op:String="="):Dynamic return v; public static function getProperty(o:Dynamic,n:String):Dynamic return Reflect.getProperty(o,n); public static function setProperty(o:Dynamic,n:String,v:Dynamic):Dynamic {Reflect.setProperty(o,n,v);return v;}}')
            (base/'ProbeHost.hx').write_text("""class ProbeHost {
 public var stages:Array<Dynamic>=[];
 public var members:Array<Dynamic>=[];
 public var gf:flixel.FlxObject=new flixel.FlxObject();
 public var dad:flixel.FlxObject=new flixel.FlxObject();
 public var boyfriend:flixel.FlxObject=new flixel.FlxObject();
 public function new() {members=[gf,dad,boyfriend];}
 public function add(o:Dynamic):Dynamic {members.push(o);return o;}
 public function insert(i:Int,o:Dynamic):Dynamic {members.insert(i,o);return o;}
 public function remove(o:Dynamic,splice:Bool):Dynamic {members.remove(o);return o;}
}""",encoding='utf-8')
            (base/'Main.hx').write_text("""class Main {
 static function check(ok:Bool,why:String):Void {if(!ok) throw why;}
 static function main():Void {
  var root=Sys.args()[0],host=new ProbeHost();
  var context=new SourceStageContext(function() return host,function() return host,function(_) return true,function(_) return null);
  var prefs:Dynamic={token:37};
  var bindings:Map<String,Dynamic>=['backend.BaseStage'=>PsychBaseStageCompat,'backend.ClientPrefs'=>prefs,'flixel.FlxObject'=>flixel.FlxObject];
  var session=new PsychSourceClassSession(root,host,bindings,context);
  var iris=new SourceIrisBridge({});iris.evaluator.bindSourceClasses(session);iris.variables.set('Type',Type);
  iris.evaluate('import demo.Counter; import demo.Stage; item=new Counter(); Counter.count=5;', 'before-stage');
  var counter=iris.variables.get('Counter'),type=iris.variables.get('Stage'),item=iris.variables.get('item');
  var selected=new PsychCompiledStageRuntime(root,'demo.Stage',host,null,null,context,session);
  check(selected.create(), 'selected create: '+selected.diagnostics);
  iris.variables.set('selected',selected.sourceObject);
  iris.evaluate('same=Type.getClass(selected)==Stage; count=Counter.count; pref=selected.pref;', 'selected');
  check(iris.variables.get('same')==true && iris.variables.get('count')==15 && iris.variables.get('pref')==37,'identity/statics/owner prefs');
  check(host.members.indexOf(host.gf)==2 && host.members[0].ID==1 && host.members[1].ID==101,'selected source and native helper background placement');
  iris.evaluate('ordinary=new Stage();', 'ordinary');
  var ordinary=iris.variables.get('ordinary');
  check(host.members.indexOf(host.gf)==2 && host.members[host.members.length-1].ID==102,'ordinary phase restored after create');
  check(!selected.dispatch('stepHit') && selected.diagnostics.join('|').indexOf('callback probe')>=0,'authored callback failure');
  iris.evaluate('afterFailure=new Stage();', 'after-callback-failure');
  check(host.members[host.members.length-1].ID==104,'ordinary phase restored after callback error');
  var count=host.stages.length,members=host.members.copy();
  var bad=new PsychCompiledStageRuntime(root,'demo.Bad',host,null,null,context,session);
  check(!bad.create() && host.stages.length==count && session.loader.scope.isActive(),'failed import must preserve owner');
  var wrong=new PsychCompiledStageRuntime(root+'/foreign','demo.Stage',host,null,null,context,session);
  check(!wrong.create() && wrong.diagnostics.join('|').indexOf('owners differ')>=0,'reject foreign owner');
  var broken=new PsychCompiledStageRuntime(root,'demo.Broken',host,null,null,context,session);
  check(!broken.create() && broken.diagnostics.join('|').indexOf('constructor probe')>=0,'constructor error');
  check(host.stages.length==count && host.members.length==members.length,'failed creation rollback');
  for(i in 0...members.length) check(host.members[i]==members[i],'failed creation changed existing member');
  check(session.read(item,'value')==7 && session.read(ordinary,'exists')==true,'failed selected stage released ordinary objects');
  var destroys=session.read(type,'destroyed');
  selected.destroy(true,false);
  for(stage in host.stages) if(stage!=iris.variables.get('selected')) PsychStageObject.call(stage,'destroy',[]);
  selected.releaseAfterHostTraversal();selected.destroy();
  check(session.read(type,'destroyed')==destroys+4,'ordered cleanup must visit each source stage exactly once');
  iris.evaluate('afterDestroy=item.next(); fresh=new Stage();', 'after-selected-destroy');
  check(iris.variables.get('Stage')==type && iris.variables.get('Counter')==counter && session.loader.scope.isActive(),'selected release invalidated shared classes');
  check(host.members[host.members.length-1].ID==106,'selected failure/destroy leaked construction policy');
  session.call(iris.variables.get('fresh'),'destroy',[]);iris.release();session.release();
  var rejected=false;try session.read(item,'value') catch(e:Dynamic) rejected=true;
  check(rejected,'owner teardown did not reject retained objects');
  Sys.println('Shared selected stage session passed');
 }
}""",encoding='utf-8')
            args=list(FLIXEL_ARGS);idx=args.index('flixel');args[idx-1:idx+1]=['-cp',str(ROOT/'.haxelib/flixel/6,1,2')]
            result=subprocess.run([*HAXE_COMMAND,*args,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(ROOT/'.haxelib/hscript-ex/git/src'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(base),'--run','Main',str(owner)],cwd=ROOT,env=haxe_env(),capture_output=True,text=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('Shared selected stage session passed',result.stdout)

if __name__=='__main__':unittest.main()
