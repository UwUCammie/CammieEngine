"""Mounted V-Slice event payloads execute the donor HXC song-event handlers.

The V-Slice importer keeps unknown event values as ``Json.stringify(v)`` in the
legacy value-one slot.  This fixture feeds that exact representation through
``EngineCompat.hxcSongEventPayload`` and calls the generated HXC callback with
small fake runtime objects.  It intentionally does not build or launch the
game and never writes to the mounted donor tree.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
VSLICE = DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice"


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _find_event_values(chart: dict, names: set[str]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for event in chart.get("events", []):
        name = event.get("e")
        if name in names and name not in result:
            result[name] = event.get("v") or {}
    return result


class VSliceForeignHxcDispatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.charts = {
            "concert": VSLICE / "data/songs/fantasy-girl-01/fantasy-girl-01-chart.json",
            "concert2": VSLICE / "data/songs/future-sound/future-sound-chart.json",
            "miku": VSLICE / "data/songs/rabbit-hole/rabbit-hole-chart.json",
        }
        cls.scripts = {
            "concert": VSLICE / "scripts/stages/concert.hxc",
            "concert2": VSLICE / "scripts/stages/concert2.hxc",
            "miku": VSLICE / "scripts/stages/miku.hxc",
            "module": VSLICE / "scripts/modules/ChangeCharacterHandler.hxc",
        }

    def test_donor_foreign_events_reach_real_hxc_song_event_handlers(self):
        required = {
            "concert": {
                "Crowd-Appears", "camera", "Fade", "TWIM-SCREAM",
                "TWIM-ON/OFF", "ROLLING-TIME", "fixstuff", "Baka",
                "fixFinal", "ending", "Flash",
            },
            "concert2": {"screenScream", "tweenScreenR", "bye", "ending"},
            "miku": {"spotlight", "lightsBeat", "Alt Idle Rabbit"},
        }
        if not all(path.is_file() for path in (*self.charts.values(), *self.scripts.values())):
            self.skipTest("mounted V-Slice HXC/chart corpus is unavailable")

        events = {}
        for stage, path in self.charts.items():
            chart = json.loads(path.read_text())
            events[stage] = _find_event_values(chart, required[stage])
            # The first rabbit-hole spotlight is the donor's blackout setup
            # (4/0). Use its later 1/0 event so the executable fixture can
            # assert the handler's positive spotlight branch while still
            # sourcing the payload from the mounted chart.
            if stage == "miku" and events[stage]["spotlight"].get("value1") == "4":
                events[stage]["spotlight"] = next(
                    event.get("v") or {}
                    for event in chart.get("events", [])
                    if event.get("e") == "spotlight"
                    and (event.get("v") or {}).get("value1") == "1"
                )
            self.assertEqual(set(events[stage]), required[stage], stage)

        # This is the live dispatch boundary: Psych onEvent remains separate,
        # while every imported HXC scope receives the canonical songEvent hook.
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("var hxcEvent = EngineCompat.hxcSongEventPayload(", play_state)
        self.assertIn("callAllHScript('songEvent', [hxcEvent]);", play_state)

        stage_sources = {
            key: self.scripts[key].read_text(errors="ignore")
            for key in ("concert", "concert2", "miku")
        }
        module_source = self.scripts["module"].read_text(errors="ignore")
        main = self._fixture_source(stage_sources, module_source, events)
        with tempfile.TemporaryDirectory(prefix="foreign-hxc-dispatch-", dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(temp),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-main", "Main", "--interp"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("foreign-hxc-dispatch-ok", result.stdout)

    @staticmethod
    def _fixture_source(stage_sources, module_source, events):
        # Keep this fixture deliberately small: it only models properties and
        # calls used by the preserved event branches, never donor assets.
        encoded_events = {
            stage: [
                {"name": name, "values": json.dumps(values, ensure_ascii=False)}
                for name, values in sorted(values_by_name.items())
            ]
            for stage, values_by_name in events.items()
        }
        return f'''import hscript.Parser;
import hscript.Interp;
import haxe.Json;

class FakeVec {{
  public var x:Float = 1;
  public var y:Float = 1;
  public function new() {{}}
  public function set(nx:Float, ny:Float):Void {{ x = nx; y = ny; }}
}}

class FakeAnim {{
  public var last:String = '';
  public var finished:Bool = false;
  public var curAnim:Dynamic = null;
  public function new() {{}}
  public function play(name:String, ?restart:Bool = false):Void {{
    last = name;
    curAnim = {{name: name}};
  }}
  public function stop():Void {{ curAnim = null; }}
}}

class FakeObj {{
  public var visible:Bool = true;
  public var active:Bool = true;
  public var alpha:Float = 1;
  public var x:Float = 0;
  public var y:Float = 0;
  public var color:Int = 0xFFFFFFFF;
  public var idleSuffix:String = '';
  public var scale:FakeVec;
  public var scrollFactor:FakeVec;
  public var animation:FakeAnim;
  public var filters:Array<Dynamic> = [];
  public var shader:Dynamic;
  public function new() {{
    scale = new FakeVec();
    scrollFactor = new FakeVec();
    animation = new FakeAnim();
  }}
}}

class FakeStage {{
  public var dad:FakeObj;
  public var boyfriend:FakeObj;
  public function new(dad:FakeObj, boyfriend:FakeObj) {{ this.dad = dad; this.boyfriend = boyfriend; }}
  public function getDad():FakeObj return dad;
  public function getBoyfriend():FakeObj return boyfriend;
}}

class FakeGame {{
  public var curStage:FakeStage;
  public var currentStage:FakeStage;
  public var currentCameraZoom:Float = 0;
  public var camGame:FakeObj = new FakeObj();
  public var camHUD:FakeObj = new FakeObj();
  public var camCutscene:FakeObj = new FakeObj();
  public var comboPopUps:Dynamic = null;
  public function new(dad:FakeObj, boyfriend:FakeObj) {{
    curStage = new FakeStage(dad, boyfriend);
    currentStage = curStage;
  }}
}}

class FakeCamera {{
  public var flashes:Int = 0;
  public function new() {{}}
  public function flash(_color:Int, _duration:Float, ?_force:Bool = false):Void flashes++;
}}

class FlxG {{
  public static var onMobile:Bool = false;
  public static var camera:FakeCamera = new FakeCamera();
  public static var width:Int = 1280;
  public static var height:Int = 720;
}}

class FlxEase {{
  public static var quadInOut:Dynamic = null;
  public static var cubeOut:Dynamic = null;
  public static var cubeInOut:Dynamic = null;
  public static var elasticIn:Dynamic = null;
  public static var circOut:Dynamic = null;
  public static var sineInOut:Dynamic = null;
}}

class FlxColor {{
  public static var WHITE:Int = 0xFFFFFFFF;
  public static var BLACK:Int = 0xFF000000;
}}

class FlxTween {{
  static function assign(target:Dynamic, values:Dynamic):Void {{
    if (target == null || values == null) return;
    for (key in Reflect.fields(values)) Reflect.setProperty(target, key, Reflect.field(values, key));
  }}
  public static function tween(target:Dynamic, values:Dynamic, _duration:Float, ?_options:Dynamic):Dynamic {{
    assign(target, values);
    return target;
  }}
  public static function color(target:Dynamic, _duration:Float, _from:Dynamic, to:Dynamic):Dynamic {{
    if (target != null) Reflect.setProperty(target, 'color', to);
    return target;
  }}
  public static function cancelTweensOf(_target:Dynamic):Void {{}}
}}

class FlxTimer {{
  public static var starts:Int = 0;
  public var active:Bool = true;
  public function new() {{}}
  public function start(_time:Float, _callback:Dynamic):FlxTimer {{ starts++; return this; }}
  public function cancel():Void {{ active = false; }}
}}

class FlxRuntimeShader {{ public function new(_source:String) {{}} }}
class ShaderFilter {{ public function new(_shader:Dynamic) {{}} }}
class Assets {{ public static function getText(_path:String):String return ''; }}
class Paths {{ public static function frag(name:String):String return name; }}
class FakePlayState {{ public static var instance:FakeGame; }}
class Conductor {{ public static var instance:Dynamic = {{currentBeat: 0}}; }}

class Main {{
  static function fail(value:String):Void throw value;
  static function hasCallback(result:Dynamic):Bool {{
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if ((callback.sourceName == 'onSongEvent' || callback.canonicalName == 'songEvent')
        && callback.safe == true) return true;
    return false;
  }}
  static function hasDiagnostic(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>)) if (finding.code == code) return true;
    return false;
  }}
  static function put(interp:Interp, name:String, value:Dynamic):Void interp.variables.set(name, value);
  static function obj():FakeObj return new FakeObj();
  static function seeded(interp:Interp, name:String):FakeObj
    return cast interp.variables.get('__seed_' + name);
  static function seedCommon(interp:Interp, game:FakeGame, dad:FakeObj, bf:FakeObj):Void {{
    put(interp, 'PlayState', FakePlayState);
    put(interp, 'HxcCompatRuntime', HxcCompatRuntime);
    put(interp, 'FlxG', FlxG);
    put(interp, 'FlxTween', FlxTween);
    put(interp, 'FlxTimer', FlxTimer);
    put(interp, 'FlxEase', FlxEase);
    put(interp, 'FlxColor', FlxColor);
    put(interp, 'Std', Std);
    put(interp, 'Math', Math);
    put(interp, 'FlxRuntimeShader', FlxRuntimeShader);
    put(interp, 'ShaderFilter', ShaderFilter);
    put(interp, 'Assets', Assets);
    put(interp, 'Paths', Paths);
    put(interp, 'hxcAssetRoot', '');
    put(interp, 'game', game);
    put(interp, 'dad', dad);
    put(interp, 'boyfriend', bf);
    put(interp, 'getDad', function() return dad);
    put(interp, 'getBoyfriend', function() return bf);
    put(interp, 'contains', function(_value:Dynamic) return false);
    put(interp, 'members', []);
    put(interp, 'remove', function(_value:Dynamic) return null);
    put(interp, 'add', function(_value:Dynamic) return null);
    put(interp, 'hxcResetState', function() return null);
  }}
  static function executeWithObjects(interp:Interp, source:String, names:Array<String>):Void {{
    var setup = source;
    for (name in names) {{
      put(interp, '__seed_' + name, obj());
      setup += '\\n' + name + ' = __seed_' + name + ';';
    }}
    interp.execute(new Parser().parseString(setup));
  }}
  static function invoke(interp:Interp, name:String, values:Dynamic):Dynamic {{
    var payload = EngineCompat.hxcSongEventPayload([
      name, Json.stringify(values), '', '', 0
    ]);
    var callback:Dynamic = interp.variables.get('songEvent');
    if (callback == null) fail('songEvent callback missing for ' + name);
    Reflect.callMethod(null, callback, [payload]);
    return payload;
  }}
  static function runConcert(source:String, events:Array<Dynamic>):Void {{
    var result = HxcCompat.analyze(source, 'scripts/stages/concert.hxc');
    if (!hasCallback(result) || hasDiagnostic(result, 'unsupported-hxc-callback'))
      fail('concert songEvent was not classified safe');
    new Parser().parseString(result.generatedHscript);
    var interp = new Interp();
    var dad = obj(); var bf = obj(); var game = new FakeGame(dad, bf);
    FakePlayState.instance = game;
    seedCommon(interp, game, dad, bf);
    executeWithObjects(interp, result.generatedHscript + '\\nfunction __foreignProbe() return [zoomDad, zoomBf];', ['endBlack','crowd','FLASH','gradient2','effect','bgPink','world',
      'backRG','piano','gradient3','mikuSCREAM','gradient','speakerbg','base',
      'backBase','back','backTB','neru','teto']);
    put(interp, 'game', game); put(interp, 'dad', dad); put(interp, 'boyfriend', bf);
    seeded(interp, 'endBlack').alpha = 0;
    for (event in events) {{
      var beforeEnd = seeded(interp, 'endBlack').alpha;
      var beforeGradient = seeded(interp, 'gradient2').visible;
      var beforeFlash = FlxG.camera.flashes;
      var payload = invoke(interp, event.name, Json.parse(event.values));
      switch (event.name) {{
        case 'Crowd-Appears': if (seeded(interp, 'crowd').y != 676) fail('Crowd-Appears');
        case 'camera':
          var cameraValues:Dynamic = Reflect.callMethod(null, interp.variables.get('__foreignProbe'), []);
          if (cameraValues[0] != 0.6 || cameraValues[1] != 0.7) fail('camera values');
        case 'Fade': if (seeded(interp, 'FLASH').alpha != 1) fail('Fade values');
        case 'TWIM-SCREAM': if (!seeded(interp, 'mikuSCREAM').visible) fail('TWIM-SCREAM');
        case 'TWIM-ON/OFF': if (seeded(interp, 'gradient2').visible == beforeGradient) fail('TWIM-ON/OFF');
        case 'Flash':
          if (FlxG.camera.flashes != beforeFlash + 1 || payload.nativeHandled != true)
            fail('Flash native ownership');
        case 'ROLLING-TIME': if (bf.x != 1478 || bf.y != 540) fail('ROLLING-TIME');
        case 'fixstuff': if (bf.scrollFactor.x != 1 || game.currentCameraZoom != 0.65) fail('fixstuff');
        case 'Baka': if (dad.x != 450 || bf.x != 440 || game.currentCameraZoom != 1.2) fail('Baka');
        case 'fixFinal': if (dad.scrollFactor.x != 1 || game.currentCameraZoom != 0.6) fail('fixFinal');
        case 'ending': if (beforeEnd == seeded(interp, 'endBlack').alpha) fail('ending');
      }}
    }}
  }}
  static function runConcert2(source:String, events:Array<Dynamic>):Void {{
    var result = HxcCompat.analyze(source, 'scripts/stages/concert2.hxc');
    if (!hasCallback(result) || hasDiagnostic(result, 'unsupported-hxc-callback')) fail('concert2 callback');
    new Parser().parseString(result.generatedHscript);
    var interp = new Interp(); var dad = obj(); var bf = obj(); var game = new FakeGame(dad, bf);
    FakePlayState.instance = game; seedCommon(interp, game, dad, bf);
    executeWithObjects(interp, result.generatedHscript, ['endBlack','screenP','screenR1','screenR2','FLASH']);
    put(interp, 'game', game);
    for (event in events) {{
      invoke(interp, event.name, Json.parse(event.values));
      switch (event.name) {{
        case 'screenScream':
          var screenP:FakeObj = seeded(interp, 'screenP');
          if (screenP.x != -175 || screenP.y != -100) fail('screenScream');
        case 'tweenScreenR':
          if (seeded(interp, 'screenR1').x != 395) fail('tweenScreenR');
        case 'bye': if (FlxTimer.starts <= 0) fail('bye timer');
        case 'ending': if (seeded(interp, 'endBlack').alpha != 1) fail('concert2 ending');
      }}
    }}
  }}
  static function runMiku(source:String, events:Array<Dynamic>):Void {{
    var result = HxcCompat.analyze(source, 'scripts/stages/miku.hxc');
    if (!hasCallback(result) || hasDiagnostic(result, 'unsupported-hxc-callback')) fail('miku callback');
    new Parser().parseString(result.generatedHscript);
    var interp = new Interp(); var dad = obj(); var bf = obj(); var game = new FakeGame(dad, bf);
    FakePlayState.instance = game; seedCommon(interp, game, dad, bf);
    executeWithObjects(interp, result.generatedHscript, ['lightsBg','spotDad','spotBF','smokeBL','smokeBR','smokeFL','smokeFR',
      'bg','peps3','peps2','peps1','speakers0','speakers4','floorback','floor','crowd','flash']);
    put(interp, 'eventTimers', []); put(interp, 'bfNob', []); put(interp, 'dadNob', []);
    put(interp, 'game', game); put(interp, 'dad', dad); put(interp, 'bf', bf);
    for (event in events) {{
      invoke(interp, event.name, Json.parse(event.values));
      switch (event.name) {{
        case 'Alt Idle Rabbit': if (bf.idleSuffix != '-alt') fail('Alt Idle Rabbit');
        case 'lightsBeat':
          if (seeded(interp, 'lightsBg').animation.last != 'beat1') fail('lightsBeat');
        case 'spotlight':
          if (seeded(interp, 'spotDad').alpha != 1) fail('spotlight');
      }}
    }}
  }}
  static function runModule(source:String):Void {{
    var result = HxcCompat.analyze(source, 'scripts/modules/ChangeCharacterHandler.hxc');
    if (!hasCallback(result) || hasDiagnostic(result, 'unsupported-hxc-callback')) fail('module callback');
    new Parser().parseString(result.generatedHscript);
  }}
  static function main() {{
    var concert:Array<Dynamic> = {json.dumps(encoded_events['concert'], ensure_ascii=False)};
    var concert2:Array<Dynamic> = {json.dumps(encoded_events['concert2'], ensure_ascii=False)};
    var miku:Array<Dynamic> = {json.dumps(encoded_events['miku'], ensure_ascii=False)};
    runConcert({hx_string(stage_sources['concert'])}, concert);
    runConcert2({hx_string(stage_sources['concert2'])}, concert2);
    runMiku({hx_string(stage_sources['miku'])}, miku);
    runModule({hx_string(module_source)});
    Sys.println('foreign-hxc-dispatch-ok');
  }}
}}
'''


if __name__ == "__main__":
    unittest.main()
