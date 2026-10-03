"""Synthetic semantic coverage for the HXC/native song-event owner boundary."""
from haxe_test_support import HAXE_COMMAND

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


class VSliceEventOwnershipTest(unittest.TestCase):
    @unittest.skipIf(not (DONOR / 'v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/events/Zoom Rabbit.hxc').is_file(), 'mounted event donor fixtures are unavailable')
    def test_authored_zoom_event_runs_through_generic_hxc_handler(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/events/Zoom Rabbit.hxc").read_text()
        sibling = (DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/events/Add Camera Zoom.hxc").read_text()
        main = f'''import hscript.Interp;
import hscript.Parser;
import haxe.Json;

class Camera {{
 public var zoom:Float;
 public function new(zoom:Float) this.zoom=zoom;
}}
class Game {{
 public var camHUD:Camera=new Camera(1);
 var baseZoom:Float=1.3;
 public var currentCameraZoom(get,set):Float;
 function get_currentCameraZoom():Float return baseZoom;
 function set_currentCameraZoom(value:Float):Float return baseZoom=value;
 public function new() {{}}
}}
class PlayState {{ public static var instance:Game=new Game(); }}
class FlxG {{ public static var camera:Camera=new Camera(1.3); }}
class FlxTween {{ public static function cancelTweensOf(_target:Dynamic):Void {{}} }}
class FlxEase {{ public static var sineInOut:Dynamic=null; }}
class Main {{
 static function check(ok:Bool,why:String):Void if(!ok) throw why;
 static function main():Void {{
  var result=HxcCompat.analyze({json.dumps(source)},'scripts/events/Zoom Rabbit.hxc');
  var sibling=HxcCompat.analyze({json.dumps(sibling)},'scripts/events/Add Camera Zoom.hxc');
  var generated=result.generatedHscript;
  check(generated.indexOf('function songEvent(event)')>=0,'source handler was replaced by native adapter');
  check(generated.indexOf('currentCameraZoom = newDef')>=0,'authored resting zoom update was dropped');
  check(sibling.identifier=='Zoom Rabbit' && sibling.generatedHscript.indexOf('function songEvent(event)')<0,
   'duplicate donor identifier gained a second executable handler');
  var interp=new Interp();
  interp.variables.set('PlayState',PlayState);
  interp.variables.set('FlxG',FlxG);
  interp.variables.set('FlxTween',FlxTween);
  interp.variables.set('FlxEase',FlxEase);
  interp.variables.set('HxcCompatRuntime',HxcCompatRuntime);
  interp.variables.set('Math',Math);
  interp.variables.set('SONG',{{song:'rabbit-hole'}});
  interp.execute(new Parser().parseString(generated));
  var callback:Dynamic=interp.variables.get('songEvent');
  var empty=EngineCompat.hxcSongEventPayload(['Zoom Rabbit',Json.stringify({{value1:'',value2:''}}),'','',950]);
  Reflect.callMethod(null,callback,[empty]);
  check(Math.abs(FlxG.camera.zoom-1.345)<0.000001,'empty schema values did not use authored defaults: '+FlxG.camera.zoom);
  var payload=EngineCompat.hxcSongEventPayload(['Zoom Rabbit',Json.stringify({{value1:'2',value2:'0.55'}}),'','',4000]);
  Reflect.callMethod(null,callback,[payload]);
  check(PlayState.instance.currentCameraZoom==0.55,'source default zoom not applied');
  check(Math.abs(FlxG.camera.zoom-1.19)<0.000001,'source pulse did not use new resting zoom: '+FlxG.camera.zoom);
  check(PlayState.instance.camHUD.zoom==1.063,'source HUD tween not applied');
  var other=EngineCompat.hxcSongEventPayload(['Other Event','', '', '', 4100]);
  Reflect.callMethod(null,callback,[other]);
  check(Math.abs(FlxG.camera.zoom-1.19)<0.000001,'handler fired for another event');
  trace('authored-zoom-event-ok');
 }}
}}
'''
        with tempfile.TemporaryDirectory(prefix="hxc-zoom-owner-", dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(temp),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "Main", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("authored-zoom-event-ok", result.stdout)

    @unittest.skipIf(not (DONOR / 'v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/events/Zoom Rabbit.hxc').is_file(), 'mounted event donor fixtures are unavailable')
    def test_mounted_overlap_audit_identifies_only_direct_flash_as_native_duplicate(self):
        concert = (DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/stages/concert.hxc").read_text()
        miku = (DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/stages/miku.hxc").read_text()

        focus = concert[concert.index('if (name == "FocusCamera")'):concert.index('if (name == "ending")')]
        self.assertIn("currentCameraZoom", focus)
        self.assertNotIn("camera.flash", focus)

        rabbit = miku[miku.index("if (name == 'Zoom Rabbit')"):miku.index("if (name == 'Alt Idle Rabbit')")]
        self.assertIn("speakers", rabbit)
        self.assertNotIn("camera.flash", rabbit)

        flash = concert[concert.index('if (name == "Flash")'):concert.index('if (name == "ROLLING-TIME")')]
        self.assertIn("FlxG.camera.flash", flash)

    def test_hxc_camera_flash_claims_native_side_once(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        source = """
class SyntheticStage extends ScriptedStage {
    override function onSongEvent(event:SongEventScriptEvent):Void {
        if (event.eventData.eventKind == 'Flash')
            FlxG.camera.flash(0xFFFFFFFF, 0.75);
    }
}
"""
        main = f'''import hscript.Interp;
import hscript.Parser;
import haxe.Json;

class FakeCamera {{
    public var flashes:Int = 0;
    public function new() {{}}
    public function flash(_color:Int, _duration:Float, ?_force:Bool = false):Void flashes++;
}}

class FlxG {{
    public static var camera:FakeCamera = new FakeCamera();
}}

class Main {{
    static function fail(message:String):Void throw message;

    static function main() {{
        var result = HxcCompat.analyze({json.dumps(source)}, 'synthetic/stage.hxc');
        var generated = result.generatedHscript;
        if (generated.indexOf('HxcCompatRuntime.hxcCameraFlash(event, FlxG.camera') < 0)
            fail('direct HXC camera flash was not lowered to the owner bridge');
        var interp = new Interp();
        interp.variables.set('FlxG', FlxG);
        interp.variables.set('HxcCompatRuntime', HxcCompatRuntime);
        interp.execute(new Parser().parseString(generated));
        var payload = EngineCompat.hxcSongEventPayload([
            'Flash', Json.stringify({{value1: '0.75', value2: ''}}), '', '', 0
        ]);
        var callback:Dynamic = interp.variables.get('songEvent');
        if (callback == null)
            fail('songEvent callback missing');
        Reflect.callMethod(null, callback, [payload]);
        if (FlxG.camera.flashes != 1)
            fail('HXC camera effect was not applied exactly once: ' + FlxG.camera.flashes);
        if (payload.nativeHandled != true || payload.handled != true)
            fail('HXC callback did not claim the native event side');
        var nativeCalls = payload.nativeHandled == true ? 0 : 1;
        if (nativeCalls != 0)
            fail('native route would double-apply the claimed event');
        trace('hxc-event-owner-ok');
    }}
}}
'''
        with tempfile.TemporaryDirectory(prefix="hxc-event-owner-", dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(temp),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "Main", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-event-owner-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
