"""Exercise source-tick keyboard and elapsed views through the NMV Iris interp."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'
IRIS = ROOT / '.haxelib/hscript-iris/1,1,3'


class CompatScriptInputSnapshotTest(unittest.TestCase):
    def test_edges_survive_host_frames_and_only_reach_last_catchup_tick(self):
        if not HAXE.is_file():
            self.skipTest('portable Haxe interpreter is unavailable')
        if not IRIS.is_dir():
            self.skipTest('pinned Iris interpreter is unavailable')

        fixture = r'''import crowplexus.hscript.Parser;
class NativeKeys {
 public var enabled:Bool=true;
 public var preventDefaultKeys:Array<Int>=[];
 public var pressed:Dynamic={ENTER:false,SPACE:false,SHIFT:false};
 public var released:Dynamic={ENTER:true,SPACE:true,SHIFT:true};
 public var justPressed:Dynamic={ENTER:false,SPACE:false,SHIFT:false};
 public var justReleased:Dynamic={ENTER:false,SPACE:false,SHIFT:false};
 public function new() {}
 public function getIsDown():Dynamic return [];
 public function reset():Void {}
 public function destroy():Void {}
}
class NativeFlxG {
 public var elapsed:Float=0.001;
 public var keyboard:NativeKeys=new NativeKeys();
 public var keysReads:Int=0;
 public var keys(get,never):NativeKeys;
 function get_keys():NativeKeys {keysReads++;return keyboard;}
 public var save:Dynamic={data:{}};
 public function new() {}
}
class SaveStorage {
 public var values:Map<String,Dynamic>=new Map();
 public function new() {}
 public function getField(name:String):Dynamic return values.get(name);
 public function setField(name:String,value:Dynamic):Dynamic {values.set(name,value);return value;}
 public function flush():Void {}
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw '[input-test] '+message;
 static function run(interp:NightmareVisionScriptInterp,parser:Parser,script:String):Void
  interp.execute(parser.parseString(script));
 static function main():Void for (hostHz in [480, 1440, 4800]) {
  var clock=new CompatScriptClock();
  var native=new NativeFlxG();
  var interp=new NightmareVisionScriptInterp();
  var save=interp.bindOwnerSave('assets/imported_mods/nmv-input-test',new SaveStorage());
  var codes:Map<String,Int>=['ENTER'=>13,'SPACE'=>32,'SHIFT'=>16];
  var view=new NightmareVisionFlxGView(native,save,clock,codes);
  interp.variables.set('FlxG',view);
  var secondInterp=new NightmareVisionScriptInterp();
  var secondSave=secondInterp.bindOwnerSave('assets/imported_mods/nmv-input-test-second',new SaveStorage());
  var secondView=new NightmareVisionFlxGView(native,secondSave,clock,codes);
  var parser=new Parser();
  interp.variables.set('pre',[]);
  interp.variables.set('post',[]);
  var pairedKeyboard:Dynamic=null;

  // A short key edge disappears from native justPressed before the first
  // source tick at high host rates; the owner view must retain it until then.
  var sourceFrameCount=0;
  var hostFrames=Std.int(hostHz/60);
  native.keysReads=0;
  for (frame in 0...hostFrames) {
   native.elapsed=1.0/hostHz;
   native.keyboard.justPressed.ENTER=(frame==2);
   native.keyboard.pressed.ENTER=(frame>=2);
   NightmareVisionFlxGView.captureSourceFrame(clock);
   var batch=clock.advance(native.elapsed);
   if (batch.tickCount>0) {
    batch.dispatchUpdate(function(index,dt) {
     NightmareVisionFlxGView.runSourceTick(clock,index,batch.tickCount,function() {
      var sharedManager=view.getField('keys');
      check(sharedManager==secondView.getField('keys'),
       'same-delegate owner views did not share the tick keyboard facade');
      pairedKeyboard=sharedManager;
      run(interp,parser,'pre.push([FlxG.keys.justPressed.ENTER,FlxG.keys.pressed.ENTER,FlxG.elapsed,FlxG.keys.anyJustPressed([13]),FlxG.keys.firstJustPressed(),FlxG.keys.checkStatus(13,2)]);');
     });
    });
    batch.dispatchUpdatePost(function(index,dt) {
     NightmareVisionFlxGView.runSourceTick(clock,index,batch.tickCount,function() {
      check(view.getField('keys')==secondView.getField('keys'),
       'pre/post phases did not reuse the per-tick keyboard facade');
      check(view.getField('keys')==pairedKeyboard,
       'onUpdatePost did not reuse the exact onUpdate keyboard snapshot');
      run(interp,parser,'post.push([FlxG.keys.justPressed.ENTER,FlxG.keys.pressed.ENTER,FlxG.elapsed,FlxG.keys.anyJustPressed([13]),FlxG.keys.firstJustPressed(),FlxG.keys.checkStatus(13,2)]);');
     });
    });
    NightmareVisionFlxGView.finishSourceBatch(clock,batch.tickCount);
   }
   sourceFrameCount+=batch.tickCount;
  }
  var pre:Array<Dynamic>=cast interp.variables.get('pre');
  var post:Array<Dynamic>=cast interp.variables.get('post');
  check(sourceFrameCount==1 && pre.length==1 && post.length==1,
   'render frames did not produce one paired source tick at '+hostHz+' Hz');
  check(native.keysReads==hostFrames,
   'keyboard manager was fetched more than once per host frame for multiple script views');
  check(pre[0][0]==true && post[0][0]==true && pre[0][1]==true && post[0][1]==true,
   'latched press or held state was missing from the source tick pair');
  check(pre[0][2]==clock.tickElapsed && post[0][2]==clock.tickElapsed,
   'FlxG.elapsed did not match the fixed source delta');
  check(pre[0][3]==true && post[0][3]==true && pre[0][4]==13 && post[0][4]==13
   && pre[0][5]==true && post[0][5]==true,
   'keyboard query methods did not use the latched edge snapshot: '+Std.string(pre[0])+' / '+Std.string(post[0]));
  check(view.getField('elapsed')==native.elapsed
   && Reflect.getProperty(view.getField('keys'),'justPressed').ENTER==false,
   'native FlxG values were changed outside a source callback');

  // During a three-tick catch-up, input edges go to the latest source tick
  // exactly once, while both callback phases observe the same edge snapshot.
  native.keyboard.justPressed.ENTER=true;
  native.keyboard.justReleased.SPACE=true;
  native.keyboard.pressed.ENTER=true;
  native.keyboard.released.SPACE=true;
  NightmareVisionFlxGView.captureSourceFrame(clock);
  native.keyboard.justPressed.ENTER=false;
  native.keyboard.justReleased.SPACE=false;
  var catchup=clock.advance(clock.tickElapsed*3);
  check(catchup.tickCount==3,'test catch-up did not produce three ticks');
  var catchupKeyboards:Array<Dynamic>=[];
  catchup.dispatchUpdate(function(index,dt) {
   NightmareVisionFlxGView.runSourceTick(clock,index,catchup.tickCount,function() {
    catchupKeyboards[index]=view.getField('keys');
    run(interp,parser,'pre.push([FlxG.keys.justPressed.ENTER,FlxG.keys.justReleased.SPACE,FlxG.elapsed,FlxG.keys.anyJustPressed([13]),FlxG.keys.firstJustPressed()]);');
   });
  });
  catchup.dispatchUpdatePost(function(index,dt) {
   NightmareVisionFlxGView.runSourceTick(clock,index,catchup.tickCount,function() {
    check(view.getField('keys')==catchupKeyboards[index],
     'catch-up post phase allocated a different keyboard snapshot');
    run(interp,parser,'post.push([FlxG.keys.justPressed.ENTER,FlxG.keys.justReleased.SPACE,FlxG.elapsed,FlxG.keys.anyJustPressed([13]),FlxG.keys.firstJustPressed()]);');
   });
  });
  NightmareVisionFlxGView.finishSourceBatch(clock,catchup.tickCount);
  check(pre.length==4 && post.length==4,
   'catch-up callbacks did not keep paired tick counts');
  for (i in 1...3) {
   check(pre[i][0]==false && pre[i][1]==false && post[i][0]==false && post[i][1]==false
    && pre[i][3]==false && post[i][3]==false && pre[i][4]==-1 && post[i][4]==-1,
    'buffered input edge repeated on an earlier catch-up tick');
  }
  check(pre[3][0]==true && pre[3][1]==true && post[3][0]==true && post[3][1]==true
   && pre[3][3]==true && post[3][3]==true && pre[3][4]==13 && post[3][4]==13,
   'latest catch-up tick did not share buffered press/release edges across callback phases');
  check(pre[3][2]==clock.tickElapsed && post[3][2]==clock.tickElapsed,
   'catch-up callbacks did not receive source elapsed');

  var after:Array<Dynamic>=[];
  interp.variables.set('after',after);
  var last=clock.advance(clock.tickElapsed);
  last.dispatchUpdate(function(index,dt) {
   NightmareVisionFlxGView.runSourceTick(clock,index,last.tickCount,function() {
    run(interp,parser,'after.push(FlxG.keys.justPressed.ENTER);');
   });
  });
  last.dispatchUpdatePost(function(index,dt) {});
  NightmareVisionFlxGView.finishSourceBatch(clock,last.tickCount);
  check(after.length==1 && after[0]==false,'consumed edges leaked into the following batch');
  save.release();
  secondSave.release();
  var keysReadsAtRelease=native.keysReads;
  NightmareVisionFlxGView.captureSourceFrame(clock);
  check(native.keysReads==keysReadsAtRelease,
   'released owner views retained the shared native keyboard binding');
  interp.release();
  secondInterp.release();
 }
}'''
        runtime_stub = '''class HxcCompatRuntime {
 public static function getZIndex(target:Dynamic):Dynamic return 0;
 public static function setZIndex(target:Dynamic,value:Dynamic,?op:String='='):Dynamic return value;
}'''
        with tempfile.TemporaryDirectory(prefix='compat-script-input-', dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            (work / 'HxcCompatRuntime.hx').write_text(runtime_stub, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(IRIS), '-cp', str(work),
                 '--run', 'Main'], cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
