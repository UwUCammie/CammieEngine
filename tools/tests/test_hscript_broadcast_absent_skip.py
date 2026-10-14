"""Broadcasts pass over scopes without the hook and keep every delivered result."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, marker):
    start = source.index(marker)
    depth = 0
    seen = False
    for index in range(source.index('{', start), len(source)):
        if source[index] == '{':
            depth += 1
            seen = True
        elif source[index] == '}':
            depth -= 1
            if seen and depth == 0:
                return source[start:index + 1]
    raise AssertionError('unterminated ' + marker)


class HscriptBroadcastAbsentSkipTest(unittest.TestCase):
    def run_fixture(self, name, fixture, extra=None):
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / (name + '.hx')).write_text(fixture, newline='\n')
            for file_name, text in (extra or {}).items():
                (Path(folder) / file_name).write_text(text, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                                     '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', folder,
                                     '-main', name, '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('OK', result.stdout + result.stderr)

    def test_absent_hooks_skip_without_changing_results_or_order(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        start = source.index('\tfunction callHscript(')
        helpers_end = source.index('\n\t/** Psych spawn broadcasts', start)
        hxc_start = source.index('\n\t/** Dispatch a note lifecycle hook only to HXC interpreters', helpers_end)
        hxc_end = source.index('\n\t/** A NoteKind interpreter', hxc_start)
        methods = (source[start:helpers_end] + source[hxc_start:hxc_end]).replace(
            'OptionsHandler.options.flashingLights', 'true')
        fixture = '''class FakeInterp {public var variables:Map<String,Dynamic>=[];public function new(){}}
typedef Interp = FakeInterp;
class SourceIrisBridge extends FakeInterp {
 public function callFunction(name:String,args:Array<Dynamic>):Dynamic
  return Reflect.callMethod(null, variables.get(name), args);
}
class BroadcastSkip {
 var notes:{members:Array<Dynamic>}=null;
 var hscriptStates:Map<String,FakeInterp>=[];
 var hxcPayloadStates:Map<String,Bool>=[];
 var defaultPsychGlobalScopes:Array<String>=[];
 var hxcNoteKindScopes:Map<String,String>=[];
 var psychFlashEventScopes:Map<String,Bool>=[];
 var hxcCharacterScopeNames:Map<String,String>=[];
 var hxcDispatchOrder=new ScriptDispatchOrder();
 var hxcScriptEventScopes:Map<String,Bool>=[];
 var lastHxcCallPayload:Dynamic=null;
 var countdownStartErrors:Int=0;
 var refreshFails=false;
 public function new(){}
 static function psychFlashCallbackSuppressed(flashingLights:Bool,isFlashEventScript:Bool,eventName:String):Bool return false;
 function refreshPsychScoreGlobals(_interp:FakeInterp):Void if(refreshFails) throw 'refresh failure';
 function hxcCharacterScopeIsActive(_scope:String):Bool return true;
 function hxcCharacterScopeOwnsNote(_scope:String,_args:Array<Dynamic>):Bool return true;
 function hxcNoteKindScopeOwnsNote(_scope:String,_args:Array<Dynamic>):Bool return true;
''' + methods + '''
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function scope(t:BroadcastSkip,key:String,?psych:Bool=false):FakeInterp {
  var interp=new FakeInterp();
  if(psych) interp.variables.set('__psychScoreGlobals',true);
  t.hscriptStates.set(key,interp);
  return interp;
 }
 static function main(){
  var messages:Array<String>=[];
  haxe.Log.trace=function(v:Dynamic,?p:haxe.PosInfos){messages.push(Std.string(v));};
  var t=new BroadcastSkip();
  var calls:Array<String>=[];
  var quiet=scope(t,'quiet',true);
  var listener=scope(t,'listener',true);
  listener.variables.set('onUpdate',function(elapsed:Float){calls.push('listener:'+elapsed);});

  // A scope without the hook keeps its old result and is never visited, and
  // that stale value cannot stop the scopes after it.
  quiet.variables.set('__compatLastResult',ScriptCallbackResult.STOP_ALL);
  t.callAllHScript('update',[0.5]);
  check(calls.join(',')=='listener:0.5','donor spelling was not delivered: '+calls.join(','));
  check(quiet.variables.get('__compatLastResult')==ScriptCallbackResult.STOP_ALL,
   'a scope without the hook was still visited');

  // A closed scope that defines the hook keeps a stale stop value; it must not
  // stop the broadcast either.
  calls=[];
  quiet.variables.set('onUpdate',function(elapsed:Float){calls.push('closed');});
  quiet.variables.set('__compatClosed',true);
  t.callAllHScript('update',[1]);
  check(calls.join(',')=='listener:1','closed scope ran or stopped the listener: '+calls.join(','));
  quiet.variables.remove('__compatClosed');
  quiet.variables.remove('onUpdate');

  // A delivered stop still stops later psych HScript scopes.
  var stopper=scope(t,'stopper',true);
  stopper.variables.set('gate',function():Dynamic {calls.push('stopper');return ScriptCallbackResult.STOP_HSCRIPT;});
  listener.variables.set('gate',function():Dynamic {calls.push('listener');return null;});
  calls=[];
  t.callAllHScript('gate',[]);
  check(calls.join(',')=='stopper'||calls.join(',')=='listener,stopper',
   'a delivered stop did not stop later scopes: '+calls.join(','));
  stopper.variables.remove('gate');
  listener.variables.remove('gate');

  // An empty press reaches a scope that defines only noteMissPress.
  var press=scope(t,'press');
  press.variables.set('__psychPlainHscript',true);
  var lanes:Array<Dynamic>=[];
  press.variables.set('onNoteMissPress',function(lane:Int){lanes.push(lane);});
  t.callAllHScript('noteMiss',[null,true,2]);
  check(lanes.join(',')=='2','empty press callback was skipped: '+lanes.join(','));
  check(t.hscriptCallbackListened('noteMiss')&&t.hscriptCallbackListened('onUpdate'),
   'listened check missed a defined hook');
  check(!t.hscriptCallbackListened('noteIncoming'),'listened check reported an absent hook');

  // Nested broadcasts get their own key list and the outer one keeps going.
  var nested:Array<String>=[];
  var outerA=scope(t,'outer-a');var outerB=scope(t,'outer-b');
  outerA.variables.set('outer',function(){nested.push('a');t.callAllHScript('inner',[]);});
  outerB.variables.set('outer',function(){nested.push('b');t.callAllHScript('inner',[]);});
  outerB.variables.set('inner',function(){nested.push('inner');});
  t.callAllHScript('outer',[]);
  nested.sort(Reflect.compare);
  check(nested.join(',')=='a,b,inner,inner','nested broadcast lost scopes: '+nested.join(','));
  check(t.hscriptKeyDepth==0,'key list depth was not released');

  // An error outside a callback still propagates and releases the key list.
  t.refreshFails=true;
  var failed=false;
  try t.callAllHScript('outer',[]) catch(_:Dynamic) failed=true;
  t.refreshFails=false;
  check(failed&&t.hscriptKeyDepth==0,'failed broadcast kept its key list');

  // HXC note hooks: only HXC scopes that define the hook.
  var hxc=scope(t,'hxc');t.hxcPayloadStates.set('hxc',true);
  var hxcIdle=scope(t,'hxc-idle');t.hxcPayloadStates.set('hxc-idle',true);
  hxcIdle.variables.set('__compatLastResult','idle');
  var hits:Array<String>=[];
  hxc.variables.set('noteHit',function(event:Dynamic){hits.push('hxc');});
  outerA.variables.set('noteHit',function(event:Dynamic){hits.push('plain');});
  t.callHxcNoteHScript('noteHit',[null]);
  check(hits.join(',')=='hxc'&&hxcIdle.variables.get('__compatLastResult')=='idle',
   'HXC note dispatch changed: '+hits.join(','));

  // Explicit requests still report a missing hook.
  messages=[];
  check(!t.callHscript('neverDefined',[],'listener'),'missing explicit hook reported success');
  check(messages.length==1&&messages[0].indexOf('listener.neverDefined')>=0,'missing explicit hook was quiet');
  messages=[];
  check(!t.callHscript('neverDefined',[],'listener',true)&&messages.length==0,'optional hook was not quiet');
  Sys.println('OK');
 }
}
'''
        self.run_fixture('BroadcastSkip', fixture)

    def test_frame_timing_sync_matches_the_separate_passes(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        names = ['function setHaxeVar(', 'function setAllHaxeVar(', 'function syncLegacyKadeGlobals(',
                 'function syncPsychTimingGlobals(', 'function syncFrameTimingGlobals(']
        methods = '\n'.join(method(source, name) for name in names)
        update = source[source.index('\toverride public function update('):]
        self.assertIn('syncFrameTimingGlobals();', update[:update.index('syncVocalTrackState();')])
        fixture = '''class FakeInterp {public var variables:Map<String,Dynamic>=[];public function new(){}}
class SourceIrisBridge extends FakeInterp {}
class Conductor {
 public static var songPosition:Float=1234.5;public static var bpm:Float=137.25;
 public static var crochet:Float=437.1;public static var stepCrochet:Float=109.3;
}
class TimingSync {
 var hscriptStates:Map<String,FakeInterp>=[];
 var timingMode=1;
 public function new(){}
 function sourceNoteTimingMode():Int return timingMode;
''' + methods + '''
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function snapshot(t:TimingSync):String {
  var out:Array<String>=[];
  var keys=[for(key in t.hscriptStates.keys()) key];keys.sort(Reflect.compare);
  for(key in keys){
   var vars=t.hscriptStates.get(key).variables;
   var names=[for(name in vars.keys()) name];names.sort(Reflect.compare);
   for(name in names) out.push(key+'.'+name+'='+Std.string(vars.get(name)));
  }
  return out.join(';');
 }
 static function main(){
  var separate=new TimingSync();var combined=new TimingSync();
  for(t in [separate,combined]){
   t.hscriptStates.set('lua',new FakeInterp());t.hscriptStates.set('iris',new SourceIrisBridge());
   t.hscriptStates.get('lua').variables.set('bpm',1);t.hscriptStates.get('iris').variables.set('songPos','overwritten');
  }
  separate.syncLegacyKadeGlobals();separate.syncPsychTimingGlobals();
  combined.syncFrameTimingGlobals();
  check(snapshot(separate)==snapshot(combined),'combined pass differs: '+snapshot(separate)+' / '+snapshot(combined));

  // setAllHaxeVar keeps the health/icon rule for source Iris scopes only.
  var t=new TimingSync();
  t.hscriptStates.set('lua',new FakeInterp());t.hscriptStates.set('iris',new SourceIrisBridge());
  t.hscriptStates.get('iris').variables.set('health',9);
  t.setAllHaxeVar('health',1.5);
  check(t.hscriptStates.get('lua').variables.get('health')==1.5&&!t.hscriptStates.get('iris').variables.exists('health'),
   'source health rule changed');
  t.timingMode=0;t.setAllHaxeVar('iconP1','icon');
  check(t.hscriptStates.get('iris').variables.get('iconP1')=='icon','native timing lost icon global');
  t.timingMode=1;t.setAllHaxeVar('score',10);
  check(t.hscriptStates.get('iris').variables.get('score')==10&&t.hscriptStates.get('lua').variables.get('score')==10,
   'plain global was not written everywhere');
  Sys.println('OK');
 }
}
'''
        self.run_fixture('TimingSync', fixture)

    def test_untouched_incoming_payload_writes_back_nothing_new(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        spawn = source[source.index("if (hscriptCallbackListened('noteIncoming')) {"):]
        spawn = spawn[:spawn.index('dunceNote.destroy();')]
        self.assertIn('HxcCompatRuntime.observeIncoming(dunceNote);', spawn)
        self.assertIn('incomingEvent != null &&', spawn)
        self.assertIn('|| !dunceNote.alive', spawn)
        runtime = '''class HxcCompatRuntime {
 public static var observed=0;
 public static function observeIncoming(_note:Dynamic):Void observed++;
 public static function markSongEventNativeHandled(_event:Dynamic):Void {}
 public static function beginActiveSong(?_state:Dynamic):Void {}
}
'''
        fixture = '''class Offset {public var x:Float=3.5;public var y:Float=-2;public function new(){}}
class FakeNote {
 public var noteData:Int=2;public var strumTime:Float=500;public var isSustainNote:Bool=true;
 public var mustPress:Bool=true;public var lowPriority:Bool=false;public var active:Bool=true;
 public var visible:Bool=false;public var alpha:Float=0.6;public var x:Float=10.25;public var y:Float=-40;
 public var angle:Float=12;public var frames:Dynamic=null;public var offset=new Offset();
 public var flipY:Bool=true;public var ID:Int=4;public var sourceKind:String='kind';
 public var writes=0;
 public function new(){}
 public function kill():Void writes++;
 public function destroy():Void writes++;
}
class IncomingPayload {
 static function main(){
  var note=new FakeNote();
  var before=([note.lowPriority,note.active,note.visible,note.alpha,note.x,note.y,note.angle,
   note.offset.x,note.offset.y,note.flipY]:Array<Dynamic>).join(',');
  var payload=EngineCompat.hxcNoteIncomingPayload(note);
  EngineCompat.hxcApplyNoteCallbackPayload(payload);
  var after=([note.lowPriority,note.active,note.visible,note.alpha,note.x,note.y,note.angle,
   note.offset.x,note.offset.y,note.flipY]:Array<Dynamic>).join(',');
  if(before!=after||note.writes!=0||EngineCompat.hxcPayloadCanceled(payload))
   throw 'an untouched payload changed the note: '+before+' / '+after;
  if(HxcCompatRuntime.observed!=1) throw 'payload no longer performs the tally observation';
  Sys.println('OK');
 }
}
'''
        self.run_fixture('IncomingPayload', fixture, {'HxcCompatRuntime.hx': runtime})


if __name__ == '__main__':
    unittest.main()
