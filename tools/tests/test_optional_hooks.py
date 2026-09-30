from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class OptionalHooksTest(unittest.TestCase):
    def test_optional_hooks_are_quiet_but_failures_remain_visible(self):
        source=(ROOT/'source/PlayState.hx').read_text()
        start=source.index('\tfunction callHscript(')
        # Keep this fixture scoped to the callback broadcaster. Native HXC
        # timeline helpers now live before setHaxeVar(), but are unrelated to
        # optional-hook dispatch and bring their manifest typedefs with them.
        end=source.index('\n\t/** A NoteKind interpreter', start)
        # The production callback now checks a settings flag only for its
        # discovered Flash scope. Keep this helper fixture independent of the
        # graphics-heavy OptionsHandler module; the preference behavior has a
        # separate focused adapter test.
        methods=source[start:end].replace('OptionsHandler.options.flashingLights', 'true')
        fixture='''class FakeInterp {public var variables:Map<String,Dynamic>;public function new(v:Map<String,Dynamic>){variables=v;}}
class HookTest {
 var notes:{members:Array<Dynamic>}=null;
 var hscriptStates:Map<String,FakeInterp>=[];
 var hxcPayloadStates:Map<String,Bool>=[];
 var defaultPsychGlobalScopes:Array<String>=[];
 var hxcNoteKindScopes:Map<String,String>=[];
 var psychFlashEventScopes:Map<String,Bool>=[];
 var hxcCharacterScopeNames:Map<String,String>=[];
 public function new(){}
 static function psychFlashCallbackSuppressed(flashingLights:Bool,isFlashEventScript:Bool,eventName:String):Bool
  return !flashingLights && isFlashEventScript && eventName != null && StringTools.trim(eventName).toLowerCase() == 'flash';
 function hxcCharacterScopeIsActive(_scope:String):Bool return true;
 function hxcCharacterScopeOwnsNote(_scope:String,_args:Array<Dynamic>):Bool return true;
 function hxcNoteKindScopeOwnsNote(_scope:String,_args:Array<Dynamic>):Bool return true;
''' + methods + '''
 static function main(){
  var messages:Array<String>=[];
  haxe.Log.trace=function(v:Dynamic,?p:haxe.PosInfos){messages.push(Std.string(v));};
  var t=new HookTest();var count=0;
  var empty:Map<String,Dynamic>=[];
  var stage:Map<String,Dynamic>=['countdownTick'=>function(tick:Int,timer:Dynamic){count+=tick;}];
  t.hscriptStates.set('stage',new FakeInterp(stage));t.hscriptStates.set('layout',new FakeInterp(empty));
  t.callAllHScript('countdownTick',[4,null]);t.callAllHScript('onCountdownTick',[4,null]);
  if(count!=4||messages.length!=0)throw 'Optional countdown hooks must work quietly';
  t.callHscript('noteHit',[],'missing');
  if(messages.length!=1||messages[0].indexOf('missing.noteHit')<0)throw 'Required callback needs context';
  stage.set('update',function(){throw 'real failure';});t.callAllHScript('update',[]);
  if(messages.length!=2||messages[1].indexOf('stage.update')<0||messages[1].indexOf('real failure')<0)throw 'Real error was hidden';
  stage.set('__compatDiagnosticCallback','outer');
  stage.set('probe',function(){
   if(stage.get('__compatDiagnosticCallback')!='probe')throw 'Missing callback context';
   t.callHscript('update',[],'stage');
   if(stage.get('__compatDiagnosticCallback')!='probe')throw 'Nested failure lost caller context';
  });
  if(!t.callHscript('probe',[],'stage') || stage.get('__compatDiagnosticCallback')!='outer')
   throw 'Callback diagnostic context was not restored';
  var hxc:Map<String,Dynamic>=[];
  t.hscriptStates.set('hxc',new FakeInterp(hxc));
  t.hxcPayloadStates.set('hxc',true);
  var shared=EngineCompat.hxcLifecyclePayload('pause');
  hxc.set('onPause',function(event:Dynamic):Dynamic {
   if(event!=shared)throw 'HXC did not receive shared gate payload';
   return 'Function_Stop'; // A Void donor callback can expose this incidentally.
  });
  stage.set('onPause',function():Dynamic return 'Function_Stop');
  var results:Array<Dynamic>=[];
  t.callAllHScript('onPause',[],false,results,[shared]);
  if(results.length!=1 || !EngineCompat.anyFunctionStop(results))
   throw 'Psych Function_Stop must be retained without HXC return';
  stage.remove('onPause');
  hxc.set('onPause',function(event:Dynamic):Dynamic return true);
  results=[];
  t.callAllHScript('onPause',[],false,results,[shared]);
  if(results.length!=0 || shared.eventCanceled)
   throw 'incidental HXC result canceled native pause';
  hxc.set('onPause',function(event:Dynamic):Dynamic { event.cancel(); return true; });
  t.callAllHScript('onPause',[],false,results,[shared]);
  if(!shared.eventCanceled)throw 'explicit HXC event.cancel was lost';
 }
}
'''
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder)/'HookTest.hx').write_text(fixture)
            p=subprocess.run([str(ROOT/'.tools/haxe/haxe'),'-cp',folder,'-cp',str(ROOT/'source'),
                '-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-main','HookTest','--interp'],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
