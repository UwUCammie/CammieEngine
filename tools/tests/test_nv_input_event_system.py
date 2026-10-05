"""Execute NV's captured-action/event contract with real Flixel/OpenFL types."""
import os
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_source_camera_reflection import FLIXEL_ARGS

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''import flixel.FlxG;
import flixel.FlxGame;
import flixel.input.FlxInput;
import flixel.input.keyboard.FlxKey;
import flixel.input.keyboard.FlxKeyboard;
import nightmarevision.input.NightmareVisionInputEnums.Control;
import nightmarevision.input.NightmareVisionInputEnums.Device;
import nightmarevision.input.NightmareVisionInputEnums.KeyboardScheme;
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  @:privateAccess FlxG.game=Type.createEmptyInstance(FlxGame);
  @:privateAccess FlxG.game.inputFrame=1;
  @:privateAccess FlxG.keys=Type.createEmptyInstance(FlxKeyboard);
  var a=new FlxInput<FlxKey>(FlxKey.A), b=new FlxInput<FlxKey>(FlxKey.B);
  @:privateAccess FlxG.keys._keyListMap=new haxe.ds.IntMap();
  @:privateAccess FlxG.keys._keyListMap.set(FlxKey.A,a);
  @:privateAccess FlxG.keys._keyListMap.set(FlxKey.B,b);
  var controls=new NightmareVisionControls('probe', None);
  controls.bindKeys(NOTE_LEFT,[FlxKey.A]);
  controls.bindKeys(NOTE_DOWN,[FlxKey.A]);
  var system=new NightmareVisionInputSystem(controls,false);
  var received:Array<NightmareVisionInputEvent>=[];
  system.addEventListener(NightmareVisionInputEvent.INPUT_PRESSED,function(e) received.push(e));
  system.addEventListener(NightmareVisionInputEvent.INPUT_RELEASED,function(e) received.push(e));
  a.press();
  check(system.inputPressed(0) && system.inputJustPressed(0),'captured actions not checked');
  @:privateAccess system.onInputEvent(NightmareVisionInputEvent.INPUT_PRESSED,Keys,FlxKey.A,11.5);
  a.update(); a.update();
  @:privateAccess system.onInputEvent(NightmareVisionInputEvent.INPUT_PRESSED,Keys,FlxKey.A,12);
  a.release();
  @:privateAccess FlxG.game.inputFrame++;
  @:privateAccess system.onInputEvent(NightmareVisionInputEvent.INPUT_RELEASED,Keys,FlxKey.A,13.5);
  check(received.length==0,'queued event dispatched early');
  system.update();
  check(received.length==2,'repeat suppression or FIFO count changed');
  check(received[0].noteData==0 && received[1].noteData==0,'duplicate binding did not choose first lane');
  check(received[0].timer==11.5 && received[1].timer==13.5,'physical timestamps changed');
  check(received[0].cancelable && Type.enumEq(received[0].device,Keys),'event shape changed');
  system.update(); check(received.length==2,'event dispatched twice');
  controls.unbindKeys(NOTE_LEFT,[FlxKey.A]); controls.bindKeys(NOTE_LEFT,[FlxKey.B]);
  b.press(); a.press(); @:privateAccess FlxG.game.inputFrame++;
  check(system.inputPressed(0),'action objects should remain live after remapping');
  @:privateAccess system.onInputEvent(NightmareVisionInputEvent.INPUT_PRESSED,Keys,FlxKey.B,20);
  @:privateAccess system.onInputEvent(NightmareVisionInputEvent.INPUT_PRESSED,Keys,FlxKey.A,21);
  system.update();
  check(received.length==3 && received[2].inputID==FlxKey.A && received[2].noteData==0,'captured physical lookup refreshed after remapping');
  var dispatcher=new NightmareVisionInputSystem(controls,false);
  var order:Array<String>=[];
  dispatcher.addEventListener(NightmareVisionInputEvent.INPUT_PRESSED,function(e) {e.preventDefault();order.push('first');},false,10);
  dispatcher.addEventListener(NightmareVisionInputEvent.INPUT_PRESSED,function(e) {check(e.isDefaultPrevented(),'default prevention lost');order.push('second');});
  var event=new NightmareVisionInputEvent('inputDown',false,true,3,Gamepad(7),42,100.25);
  check(!dispatcher.dispatchEvent(event) && order.join(',')=='first,second','OpenFL cancellation/order changed');
  check(event.noteData==3 && event.inputID==42 && event.timer==100.25 && Type.enumEq(event.device,Gamepad(7)),'constructor fields changed');
  check(Reflect.field(event,'cancel')==null,'invented cancel API');
  var stopped=new NightmareVisionInputSystem(controls,false); var later=0;
  stopped.addEventListener('inputDown',function(e) e.stopImmediatePropagation(),false,10);
  stopped.addEventListener('inputDown',function(e) later++);
  stopped.dispatchEvent(new NightmareVisionInputEvent('inputDown',false,true,0,Keys,FlxKey.A,1));
  check(later==0,'immediate propagation cancellation ignored');
  system.destroy();dispatcher.destroy();stopped.destroy();
  check(controls.actions.get('note_left')!=null,'InputSystem destroyed shared controls');
  var previous=NightmareVisionInputSystem.ACTION_LIST;
  NightmareVisionInputSystem.ACTION_LIST=['missing'];
  var message=''; try new NightmareVisionInputSystem(controls,false) catch (e:Dynamic) message=Std.string(e);
  check(message=='Missing Control Bind.\n[If your bind is modded-in, Was it named correctly?]','missing-bind error changed');
  NightmareVisionInputSystem.ACTION_LIST=previous;
  trace('NV_INPUT_EVENTS_OK');
 }
}'''


class NightmareVisionInputEventSystemTest(unittest.TestCase):
    def run_contract(self, gameinput):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name in ('NightmareVisionControls',
                         'NightmareVisionInputEvent', 'NightmareVisionInputSystem'):
                (folder / (name + '.hx')).write_text(
                    (ROOT / 'source' / (name + '.hx')).read_text(encoding='utf-8'), newline='\n')
            enums = folder / 'nightmarevision/input/NightmareVisionInputEnums.hx'
            enums.parent.mkdir(parents=True, exist_ok=True)
            enums.write_text((ROOT / 'source/nightmarevision/input/NightmareVisionInputEnums.hx').read_text(), newline='\n')
            (folder / 'Main.hx').write_text(MAIN, newline='\n')
            args = list(FLIXEL_ARGS) + ['-D','FLX_KEYBOARD','-D','FLX_GAMEPAD','-D','FLX_MOUSE','-D','FLX_MOUSE_ADVANCED']
            if not gameinput:
                position = args.index('FLX_GAMEINPUT_API')
                del args[position-1:position+1]
                # Keep Flixel gamepad actions; only remove the Lime hardware event API.
            env = os.environ.copy()
            env['HAXELIB_PATH'] = str(ROOT / '.haxelib')
            env['PATH'] = os.pathsep.join((str(ROOT / '.tools/haxe'), str(ROOT / '.tools/neko'), env.get('PATH', '')))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(folder), *args,
                                     '-main', 'Main', '--interp', '-dce', 'full'],
                                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('NV_INPUT_EVENTS_OK', result.stdout + result.stderr)

    def test_captured_actions_fifo_and_openfl_events(self):
        self.run_contract(True)



if __name__ == '__main__':
    unittest.main()
