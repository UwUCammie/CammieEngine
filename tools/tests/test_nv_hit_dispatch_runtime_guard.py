"""Native and Psych hits must not enter NV field lookup or mark NV dispatch."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]


class NvHitDispatchRuntimeGuardTest(unittest.TestCase):
    def test_real_dispatch_rejects_unselected_runtime_and_missing_fields(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        dispatch = method(source, 'function dispatchNightmareVisionNoteHit(')
        fixture = r'''
class Note {
 public var sourcePlayfieldIndex:Int=0;
 public var nightmareVisionHitDispatched:Bool=false;
 public function new() {}
}
class NightmareVisionScriptGroup {
 public static inline var CONTINUE_FUNC:Int=0;
 public static inline var STOP_FUNC:Int=1;
}
class Scripts {
 public var calls:Array<String>=[];
 public var ids:Array<Int>=[];
 public function new() {}
 public function call(name:String,args:Array<Dynamic>,stop:Bool,exclude:Array<String>):Void {
  calls.push(name);ids.push(args[1]);
 }
}
class NightmareVisionNoteTypeRuntime {
 public var calls:Array<String>=[];
 public var stop:Bool=false;
 public function new() {}
 public static function noteTypeOf(note:Note):String return 'default';
 public function hit(note:Note,id:Int):Void calls.push('hit:'+id);
 public function goodNoteHit(note:Note,id:Int):Int {calls.push('good:'+id);return stop?1:0;}
 public function opponentNoteHit(note:Note,id:Int):Int {calls.push('opponent:'+id);return stop?1:0;}
 public function extraNoteHit(note:Note,id:Int):Int {calls.push('extra:'+id);return stop?1:0;}
}
class Main {
 var nightmareVisionScripts:Scripts=null;
 var nightmareVisionNoteTypes:NightmareVisionNoteTypeRuntime=null;
 var lookups:Int=0;
 var failLookup:Bool=false;
 var fields:Array<{playerControls:Bool}>=[{playerControls:true},{playerControls:false},{playerControls:false}];
 public function new() {}
 function getNightmareVisionField(id:Int):Null<{playerControls:Bool}> {
  lookups++;if(failLookup)throw 'non NV gameplay entered field lookup';
  return id>=0&&id<fields.length?fields[id]:null;
 }
 __DISPATCH__
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function main() {
  // Both native and Psych route successful hits here, with no selected NV runtime.
  for(nativeOrPsych in ['native','psych']) {
   var h=new Main();h.failLookup=true;h.nightmareVisionNoteTypes=new NightmareVisionNoteTypeRuntime();
   var note=new Note();h.dispatchNightmareVisionNoteHit(note);
   h.dispatchNightmareVisionNoteHit(note,0,'goodNoteHit');
   check(h.lookups==0&&!note.nightmareVisionHitDispatched&&h.nightmareVisionNoteTypes.calls.length==0,
    nativeOrPsych+' hit leaked into NV dispatch');
  }
  var h=new Main();h.nightmareVisionScripts=new Scripts();h.nightmareVisionNoteTypes=new NightmareVisionNoteTypeRuntime();
  for(id in [-1,3,9]) {
   var note=new Note();note.sourcePlayfieldIndex=id;
   h.dispatchNightmareVisionNoteHit(note);
   check(!note.nightmareVisionHitDispatched,'missing NV field marked dispatched');
  }
  check(h.nightmareVisionScripts.calls.length==0&&h.nightmareVisionNoteTypes.calls.length==0,'missing field called source hooks');
  for(id in 0...3) {
   var note=new Note();note.sourcePlayfieldIndex=id;h.dispatchNightmareVisionNoteHit(note);
   check(note.nightmareVisionHitDispatched,'valid NV note not marked');
   var before=h.nightmareVisionScripts.calls.length;h.dispatchNightmareVisionNoteHit(note);
   check(h.nightmareVisionScripts.calls.length==before,'NV callback dispatched twice');
  }
  check(h.nightmareVisionScripts.calls.join(',')=='goodNoteHit,opponentNoteHit,extraNoteHit','source callback family changed');
  check(h.nightmareVisionScripts.ids.join(',')=='0,1,2','source callback field ID changed');
  check(h.nightmareVisionNoteTypes.calls.join(',')=='hit:0,good:0,hit:1,opponent:1,hit:2,extra:2','note type callback ordering changed');
  h.nightmareVisionNoteTypes.stop=true;var stopped=new Note();h.dispatchNightmareVisionNoteHit(stopped);
  check(stopped.nightmareVisionHitDispatched&&h.nightmareVisionScripts.calls.length==3,'note type STOP must suppress global callback');
  h.nightmareVisionNoteTypes=null;h.failLookup=true;var captured=new Note();
  h.dispatchNightmareVisionNoteHit(captured,2,'goodNoteHit');
  check(captured.nightmareVisionHitDispatched&&h.nightmareVisionScripts.calls[3]=='goodNoteHit','captured pre-admitted callback must retain family without new field lookup');
 }
}
'''.replace('__DISPATCH__', dispatch)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', directory, '-main', 'Main', '--interp'],
                                    capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
