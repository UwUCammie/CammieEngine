"""Execute the NMV owner-scoped FlxG.save bridge with real Iris scripts."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
IRIS = ROOT / '.haxelib/hscript-iris/1,1,3'


class NightmareVisionOwnerSaveTest(unittest.TestCase):
    def test_owner_save_roundtrip_views_and_cleanup(self):
        fixture = r'''import crowplexus.hscript.Parser;
import haxe.ds.StringMap;
class MemoryStorage {
 public var records:Map<String,Dynamic>;
 public var flushes:Int=0;
 public var failWrites:Bool=false;
 public function new(records:Map<String,Dynamic>) this.records=records;
 public function getField(name:String):Dynamic return records.get(name);
 public function setField(name:String,value:Dynamic):Dynamic {
  if(failWrites) throw "temporary save backend failure";
  records.set(name,haxe.Json.parse(haxe.Json.stringify(value))); return value;
 }
 public function flush():Void flushes++;
}
class NativeFlxG {
 public var width:Int=1280;
 public var timeScale:Float=1;
 public var resetCount:Int=0;
 public var save:Dynamic={data:{options:{antialiasing:false},personalSetting:'keep'}};
 public function new() {}
 public function resetState():Void resetCount++;
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function run(interp:NightmareVisionScriptInterp,parser:Parser,source:String):Void
  interp.execute(parser.parseString(source));
 static function saveView(interp:NightmareVisionScriptInterp,native:NativeFlxG,
  root:String,storage:MemoryStorage):NightmareVisionSaveFacade {
 var save=interp.bindOwnerSave(root,storage);
  interp.variables.set('Reflect',Reflect);
  interp.variables.set('StringMap',haxe.ds.StringMap);
  interp.variables.set('FlxG',new NightmareVisionFlxGView(native,save));
  return save;
 }
 static function main():Void {
  var parser=new Parser();
  var native=new NativeFlxG();
  var savedA:Map<String,Dynamic>=new Map();
  savedA.set('nightmareVisionClientPrefs',{version:1,values:{streamedMusic:true}});
  var storageA=new MemoryStorage(savedA);
  var first=new NightmareVisionScriptInterp();
  var firstSave=saveView(first,native,'assets/imported_mods/nightmare-vision-a',storageA);
  run(first,parser,
   'FlxG.save.data.loading=false; '
   +'FlxG.save.data.completedSongs=[]; FlxG.save.data.completedSongs.push("try-harder"); '
   +'FlxG.save.data.completedMenuShit=new StringMap(); '
   +'FlxG.save.data.completedMenuShit.set("funky",false); '
   +'FlxG.save.data.completedMenuShit.set("main",true); '
   +'FlxG.save.data.trophyData=["bronce","gold"]; '
   +'FlxG.save.data.trophyCompletion=new StringMap(); '
   +'FlxG.save.data.trophyCompletion.set("bf",false); '
   +'FlxG.save.data.charClicks=12; '
   +'observedWidth=FlxG.width; FlxG.timeScale=2; FlxG.resetState(); '
   +'if(Reflect.field(FlxG,"nativeFlxG")!=null) throw "native FlxG delegate leaked"; '
   +'if(FlxG.save.release!=null) throw "host save release leaked into script API"; '
   +'var hiddenSession=Reflect.field(FlxG.save.data,"session"); '
   +'if(hiddenSession!=null && Reflect.field(hiddenSession,"storage")!=null) '
   +'throw "owner storage backend leaked"; '
   +'if(FlxG.save.data.personalSetting!=null) throw "native save leaked"; '
   +'FlxG.save.data.personalSetting="owner-only"; FlxG.save.flush();');
  check(first.variables.get('observedWidth')==1280 && native.timeScale==2
   && native.resetCount==1,'FlxG non-save fields/methods did not forward');
  check(Reflect.field(Reflect.field(native.save,'data'),'personalSetting')=='keep'
   && Reflect.field(Reflect.field(native.save,'data'),'options').antialiasing==false,
   'owner save view exposed or modified native personal settings');
  var firstView:NightmareVisionFlxGView=cast first.variables.get('FlxG');
  check(Reflect.field(firstView,'nativeFlxG')==null,
   'native FlxG delegate remained a reflected instance field');
  var hiddenSession=Reflect.field(firstView.save.data,'session');
  check(hiddenSession!=null && Reflect.field(hiddenSession,'storage')==null,
   'owner save session exposed its persistence backend');
  check(savedA.get('completedSongs')!=null && savedA.get('completedMenuShit')!=null
   && storageA.flushes>0,'owner data was not flushed to its selected storage');
  check(Reflect.field(savedA.get('nightmareVisionClientPrefs'),'version')==1
   && Reflect.field(Reflect.field(savedA.get('nightmareVisionClientPrefs'),'values'),'streamedMusic')==true,
   'plugin save flush clobbered the independent ClientPrefs record');

  var rejectedSaveReplacement=false;
  try run(first,parser,'FlxG.save={data:{personalSetting:"overwrite"}};')
  catch (_:Dynamic) rejectedSaveReplacement=true;
  check(rejectedSaveReplacement,'script replaced the protected owner save view');

  var second=new NightmareVisionScriptInterp();
  var storageA2=new MemoryStorage(savedA);
  var secondSave=saveView(second,new NativeFlxG(),'assets/imported_mods/nightmare-vision-a',storageA2);
  run(second,parser,
   'if(FlxG.save.data.completedSongs.length!=1 '
   +'|| FlxG.save.data.completedSongs[0]!="try-harder") throw "array reload"; '
   +'if(FlxG.save.data.completedMenuShit.get("main")!=true '
   +'|| FlxG.save.data.completedMenuShit.get("funky")!=false) throw "StringMap reload"; '
   +'if(FlxG.save.data.trophyCompletion.get("bf")!=false '
   +'|| FlxG.save.data.trophyData[1]!="gold" || FlxG.save.data.charClicks!=12) '
   +'throw "nested saved values"; '
   +'FlxG.save.data.completedMenuShit.set("story",true); '
   +'FlxG.save.data.completedSongs.push("dusk");');
  check(Std.isOfType(secondSave.data.getField('completedMenuShit'),StringMap),
   'StringMap was not reconstructed with its original type');
  storageA2.setField('nightmareVisionClientPrefs',
   {version:1,values:{streamedMusic:false}});
  run(first,parser,
   'if(FlxG.save.data.completedMenuShit.get("story")!=true '
   +'|| FlxG.save.data.completedSongs.length!=2) throw "same-owner session not shared";');
  secondSave.flush();
  check(Reflect.field(Reflect.field(savedA.get('nightmareVisionClientPrefs'),'values'),'streamedMusic')==false,
   'plugin save flush clobbered a concurrent ClientPrefs update');
  first.release();
  check(!first.variables.exists('FlxG') && first.ownerSave==null,
   'interpreter release retained its save view');
  var releasedViewRejected=false;
  try firstView.getField('width') catch (_:Dynamic) releasedViewRejected=true;
  check(releasedViewRejected,'save release retained its native FlxG delegate');

  var storageB=new MemoryStorage(new Map());
  var other=new NightmareVisionScriptInterp();
  var otherSave=saveView(other,new NativeFlxG(),'assets/imported_mods/nightmare-vision-b',storageB);
  run(other,parser,
   'if(FlxG.save.data.completedSongs!=null '
   +'|| FlxG.save.data.completedMenuShit!=null) throw "cross-owner save leak"; '
   +'FlxG.save.data.completedSongs=["other-owner"]; FlxG.save.flush();');
  check(storageB.records.get('completedSongs')!=null
   && storageB.records.get('completedSongs')!=savedA.get('completedSongs'),
   'different owners shared persisted mutable values');
  otherSave.release(); other.release();
  second.release();

  var reloaded=new NightmareVisionScriptInterp();
  var finalSave=saveView(reloaded,new NativeFlxG(),'assets/imported_mods/nightmare-vision-a',
   new MemoryStorage(savedA));
  run(reloaded,parser,
   'if(FlxG.save.data.completedSongs.length!=2 '
   +'|| FlxG.save.data.completedSongs[1]!="dusk" '
   +'|| FlxG.save.data.completedMenuShit.get("story")!=true) '
   +'throw "flush/reload lost in-place mutations";');
  finalSave.release(); reloaded.release();

  var failingStorage=new MemoryStorage(new Map());
  failingStorage.failWrites=true;
  var failing=new NightmareVisionScriptInterp();
  saveView(failing,new NativeFlxG(),'assets/imported_mods/nightmare-vision-retry',failingStorage);
  run(failing,parser,'FlxG.save.data.pending=1;');
  var releaseReportedSaveFailure=false;
  try failing.release() catch (_:Dynamic) releaseReportedSaveFailure=true;
  check(releaseReportedSaveFailure && !failing.variables.exists('FlxG') && failing.ownerSave==null,
   'save failure prevented interpreter cleanup');
  failingStorage.failWrites=false;
  var retry=new NightmareVisionScriptInterp();
  var retrySave=saveView(retry,new NativeFlxG(),'assets/imported_mods/nightmare-vision-retry',failingStorage);
  retrySave.flush();
  check(failingStorage.records.get('pending')==1,'failed save session could not be retried');
  retrySave.release(); retry.release();
 }
}'''
        runtime_stub = '''class HxcCompatRuntime {
 public static function getZIndex(target:Dynamic):Dynamic return 0;
 public static function setZIndex(target:Dynamic,value:Dynamic,?op:String='='):Dynamic return value;
}'''
        with tempfile.TemporaryDirectory(prefix='nmv-save-', dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            (work / 'HxcCompatRuntime.hx').write_text(runtime_stub, newline='\n')
            for defines in ([], ['-D', 'hscriptPos']):
                with self.subTest(defines=defines):
                    result = subprocess.run(
                        [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                         '-cp', str(IRIS), '-cp', str(work)] + defines + ['--run', 'Main'],
                        cwd=ROOT, capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
