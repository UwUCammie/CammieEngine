"""Keep NMV teardown complete while preserving owner-save flush failures."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
IRIS = ROOT / '.haxelib/hscript-iris/1,1,3'


class NightmareVisionTeardownTest(unittest.TestCase):
    def test_module_and_group_release_every_scope_before_propagating_save_errors(self):
        fixture = r'''import crowplexus.hscript.Parser;
class MemoryStorage {
 public var values:Map<String,Dynamic>=new Map();
 public var failWrites:Bool;
 public function new(failWrites:Bool) this.failWrites=failWrites;
 public function getField(name:String):Dynamic return values.get(name);
 public function setField(name:String,value:Dynamic):Dynamic {
  if(failWrites) throw 'flush blocked';
  values.set(name,value); return value;
 }
 public function flush():Void {}
}
class Parent { public var id:Int=1; public function new() {} }
class Main {
 static function eq(actual:Dynamic,expected:Dynamic,message:String):Void
  if(actual!=expected) throw message+': expected '+expected+', got '+actual;
 static function module(name:String,storage:MemoryStorage,log:Array<String>,errors:Array<String>):NightmareVisionScriptModule {
  var interp=new NightmareVisionScriptInterp();
  interp.variables.set('record',function(text:String):Void log.push(text));
  var save=interp.bindOwnerSave('assets/imported_mods/'+name,storage);
  save.data.setField('pending',name);
  var parser=new Parser();
  interp.execute(parser.parseString('function onDestroy() record("destroy-'+name+'");'));
  return new NightmareVisionScriptModule(name,interp,function(script,phase,error):Void
   errors.push(script+'#'+phase+':'+Std.string(error)));
 }
 static function main():Void {
  var log:Array<String>=[];
  var errors:Array<String>=[];
  var parent=new Parent();
  var group=new NightmareVisionScriptGroup(parent,function(name,phase,error):Void
   errors.push(name+'#'+phase+':'+Std.string(error)));
  var bad=module('bad',new MemoryStorage(true),log,errors);
  var good=module('good',new MemoryStorage(false),log,errors);
  group.addScript(bad); group.addScript(good);
  group.sharedFields.set('retained',true);
  var clearFailed=false;
  try group.clear() catch (_:Dynamic) clearFailed=true;
  eq(clearFailed,true,'clear did not propagate the first save failure');
  eq(group.members.length,0,'clear left module references');
  eq(bad.released,true,'failed module not marked released');
  eq(bad.interp,null,'failed module retained interpreter');
  eq(good.released,true,'later module was not destroyed');
  eq(good.interp,null,'later module retained interpreter');
  eq(log.join(','),'destroy-bad,destroy-good','onDestroy did not reach every member');
  eq(errors.length,1,'save failure was not reported exactly once');
  eq(errors[0].indexOf('bad#destroy:')==0,true,'failure lacked module attribution');
  eq(group.sharedFields.get('retained'),true,'clear discarded reusable shared fields');
  eq(group.parent,parent,'clear discarded reusable parent');
  group.clear(); // A failed clear still leaves the group reusable and empty.

  var doomed=new NightmareVisionScriptGroup(new Parent(),function(name,phase,error):Void
   errors.push(name+'#'+phase+':'+Std.string(error)));
  doomed.sharedFields.set('discard',true);
  var finalBad=module('final-bad',new MemoryStorage(true),log,errors);
  doomed.addScript(finalBad);
  var destroyFailed=false;
  try doomed.destroy() catch (_:Dynamic) destroyFailed=true;
  eq(destroyFailed,true,'group destroy hid the save failure');
  eq(doomed.released,true,'group destroy left group active');
  eq(doomed.members.length,0,'group destroy retained modules');
  eq(doomed.sharedFields.exists('discard'),false,'group destroy retained shared values');
  eq(doomed.parent,null,'group destroy retained parent');
  eq(finalBad.released,true,'group destroy left failed module active');
  eq(finalBad.interp,null,'group destroy retained failed interpreter');
  doomed.destroy();

  // Standalone module destruction follows the same detach/report/rethrow rule.
  var standalone=module('standalone',new MemoryStorage(true),log,errors);
  var moduleFailed=false;
  try standalone.destroy() catch (_:Dynamic) moduleFailed=true;
  eq(moduleFailed,true,'module destroy hid the save failure');
  eq(standalone.released,true,'module destroy left module active');
  eq(standalone.interp,null,'module destroy retained interpreter');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            for defines in ([], ['-D', 'hscriptPos']):
                with self.subTest(defines=defines):
                    result = subprocess.run(
                        [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                         '-cp', str(IRIS), '-cp', str(work)] + defines + ['--run', 'Main'],
                        cwd=ROOT, capture_output=True, text=True, timeout=45)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
