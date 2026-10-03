"""Execute authored prop references across stage swaps without stealing globals."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]

class CodenameStageBindingsTest(unittest.TestCase):
    def test_surviving_timer_only_scope_refreshes_immediately(self):
        source = (ROOT/'source/PlayState.hx').read_text()
        start = source.index('\tfunction refreshCodenameStageAliases():Void {')
        end = source.index('\n\tfunction loadCodenameStageCompat(', start)
        helper = source[start:end]
        fixture = '''class Main {
 var codenameScriptScopes:Array<Dynamic> = [];
 var curStage:Dynamic;
 public function new() {}
 function refreshCodenameCharacterScopes():Void {}
''' + helper + '''
 function run():Void {
  var interpreter = new hscript.Interp();
  var bindings = new CodenameStageBindings();
  codenameScriptScopes.push({interp:{variables:interpreter.variables,stageBindings:bindings,
   isStageActorAlias:function(name:String,value:Dynamic):Bool return false}});
  var first:Dynamic={alpha:0.25}; var next:Dynamic={alpha:0.75};
  curStage={elements:(['ground'=>first]:Map<String,Dynamic>)};
  refreshCodenameStageAliases();
  interpreter.execute(new hscript.Parser().parseString('function timerCallback() { return [ground, stage]; }'));
  // No update, beat or other lifecycle callback runs between the stage swap
  // and this retained asynchronous callback.
  curStage={elements:(['ground'=>next]:Map<String,Dynamic>)};
  refreshCodenameStageAliases();
  var callback:Dynamic=interpreter.variables.get('timerCallback');
  var result:Array<Dynamic>=callback();
  if(result[0]!=next || result[1]!=curStage) throw 'timer saw stale stage';
  curStage={elements:new Map<String,Dynamic>()};
  refreshCodenameStageAliases();
  if(interpreter.variables.exists('ground')) throw 'failed replacement retained prop';
 }
 static function main():Void new Main().run();
}'''
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as work:
            p=Path(work)
            (p/'Main.hx').write_text(fixture, newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(p),'--run','Main'],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_names_refresh_across_stages_and_preserve_script_assignments(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as work:
            p=Path(work)
            (p/'Main.hx').write_text('''class Main {
 static function main() {
  var interp = new hscript.Interp();
  var binding = new CodenameStageBindings();
  var a:Dynamic = {alpha:1.0}; var b:Dynamic = {alpha:1.0};
  var scene:Map<String,Dynamic> = ['ground'=>a, 'oldProp'=>a, 'camHUD'=>a, 'with-dash'=>a];
  var camera:Dynamic={alpha:1.0}; interp.variables.set('camHUD',camera);
  binding.refresh(interp.variables, scene);
  interp.execute(new hscript.Parser().parseString('ground.alpha = 0.25;'));
  if (a.alpha != 0.25 || interp.variables.get('camHUD') != camera
      || interp.variables.exists('with-dash')) throw 'authored prop binding';
  binding.refresh(interp.variables, ['ground'=>b]);
  if (interp.variables.get('ground') != b || interp.variables.exists('oldProp')) throw 'stage replacement';
  binding.refresh(interp.variables, ['ground'=>null]);
  if (interp.variables.exists('ground')) throw 'null prop retained stale object';
  binding.refresh(interp.variables, ['ground'=>b]);
  var custom:Dynamic={alpha:0.5}; interp.variables.set('ground',custom);
  binding.refresh(interp.variables, ['ground'=>a]);
  if (interp.variables.get('ground') != custom) throw 'script reassignment overwritten';
  binding.refresh(interp.variables, null);
  if (interp.variables.get('ground') != custom || interp.variables.get('camHUD') != camera) throw 'teardown';
 }
}''', newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(p),'--run','Main'],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
