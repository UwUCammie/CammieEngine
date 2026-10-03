"""Compiled donor classes can partially apply functions through Haxe bind syntax."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HScriptFunctionBindTest(unittest.TestCase):
    def test_interpreted_function_bind_preserves_argument_order_and_callback(self):
        source = (ROOT / ".haxelib/hscript-ex/git/src/hscript/InterpEx.hx").read_text()
        self.assertIn("dp-owner-function-bind-fcall", source)
        self.assertIn("dp-owner-assign-once", source)
        self.assertIn("dp-owner-callable-field", (ROOT / ".haxelib/hscript-ex/git/src/hscript/ScriptClass.hx").read_text())
        self.assertIn("dp-owner-function-bind-fcall", (ROOT / "tools/patch_hscript_ex_owner_scope.py").read_text())
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(r'''import hscript.InterpEx;
import hscript.ParserEx;
import hscript.ScriptClassScope;
class Main {
 static function main():Void {
  var interp=new InterpEx();
  var program=new ParserEx().parseString(
   'function record(a,b) { return a+":"+b; } '
   +'var later=record.bind("intro"); later("next");');
  var result=interp.execute(program);
  if(result!='intro:next')
   throw 'Function.bind did not preserve the bound argument and callback';
  var scope=new ScriptClassScope();
  scope.registerModule(new ParserEx().parseModule(
   'class Probe { function target(?name:String=null) { return name; } '
   +'function register() { return target.bind("video"); } }','fixture'));
  var proxy=scope.createInstance('Probe',[]);
  var callback=proxy.callFunction('register');
  if(Reflect.callMethod(null,callback,[])!='video')
   throw 'Bound source-class method lost its argument outside the interpreter';
  scope.registerModule(new ParserEx().parseModule(
   'class TimerProbe { var timedEvents:Array<Dynamic>=[]; '
   +'function new() { timedEvents.push({time:0,func:function() return 3}); } '
   +'function update() { return timedEvents[0].func(); } }','timer-fixture'));
  var timer=scope.createInstance('TimerProbe',[]);
  var timerResult:Dynamic=timer.callFunction('update');
  if(timerResult!=3)
   throw 'Stored source-class timer closure did not run';
  scope.registerModule(new ParserEx().parseModule(
   'class NullGuardProbe { var onStart:Void->Void=null; '
   +'function fire() { if(onStart != null) onStart(); return 1; } }','null-guard-fixture'));
  var guarded=scope.createInstance('NullGuardProbe',[]);
  var guardResult:Dynamic=guarded.callFunction('fire');
  if(guardResult!=1) throw 'Null optional callback guard was ignored';
  scope.registerModule(new ParserEx().parseModule(
   'class AssignmentProbe { var created:Int=0; var value:Dynamic=null; '
   +'function make() { created++; return {id:created}; } '
   +'function run() { value=make(); return created; } }','assignment-fixture'));
  var assigned=scope.createInstance('AssignmentProbe',[]);
  var created:Dynamic=assigned.callFunction('run');
  if(created!=1) throw 'Script field assignment evaluated constructor twice: '+created;
  scope.registerModule(new ParserEx().parseModule(
   'class CallbackHolder { var finishCallback:Void->Void=null; '
   +'function install(cb:Void->Void) { finishCallback=cb; } }','callback-fixture'));
  var holder=scope.createInstance('CallbackHolder',[]);
  var callbackCount=0;
  holder.callFunction('install',[function() callbackCount++]);
  var external=new InterpEx();
  external.variables.set('holder',holder);
  external.execute(new ParserEx().parseString('holder.finishCallback();'));
  if(callbackCount!=1) throw 'Function-valued source-class field was not called';
 }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
