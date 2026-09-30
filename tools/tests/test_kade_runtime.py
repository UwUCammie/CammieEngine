"""Runtime-boundary coverage for the mounted HellBeats Kade modchart."""

from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
KADE_ROOT = DONOR / "hellbeats_kade_engine/HellBeats Kade Engine"
KADE_MODCHART = KADE_ROOT / "assets/data/tutorial/modchart.lua"
KADE_CHART = KADE_ROOT / "assets/data/tutorial/tutorial.json"
KADE_OFFSET = KADE_ROOT / "assets/data/tutorial/0.offset"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


def run_haxe(source: str, *, include_source: bool = True) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        path = Path(folder) / "KadeRuntimeFixture.hx"
        path.write_text(source)
        command = [str(HAXE), "-cp", folder]
        if include_source:
            command.extend(["-cp", str(ROOT / "source"), "-cp", str(HSCRIPT)])
        command.extend(["-main", "KadeRuntimeFixture", "--interp"])
        return subprocess.run(
            command,
            cwd=ROOT,
            env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
            capture_output=True,
            text=True,
            timeout=300,
        )


class KadeRuntimeTest(unittest.TestCase):
    @unittest.skipUnless(KADE_MODCHART.is_file(), "mounted HellBeats donor is unavailable")
    def test_tutorial_modchart_executes_against_fake_native_receptors_and_camera(self):
        path = str(KADE_MODCHART).replace("\\", "\\\\").replace('"', '\\"')
        fixture = f'''import hscript.Interp;
import hscript.Parser;
import sys.io.File;

class KadeRuntimeFixture {{
  static function fail(message:String):Void throw message;
  static function close(actual:Float, expected:Float, label:String):Void {{
    if (Math.abs(actual - expected) > 0.0001)
      fail(label + ": expected " + expected + ", got " + actual);
  }}
  static function main() {{
    var path = "{path}";
    var converted = LuaCompat.translate(File.getContent(path), path);
    if (!converted.supported)
      fail("mounted Tutorial Lua was diagnosed: " + converted.diagnostics.join(" | "));
    var interp = new Interp();
    var defaultX:Array<Float> = [];
    var defaultY:Array<Float> = [];
    for (i in 0...8) {{
      defaultX.push(100 + i);
      defaultY.push(200 + i);
    }}
    var actorX:Array<Float> = [];
    var actorY:Array<Float> = [];
    var actorXIndex:Array<Int> = [];
    var actorYIndex:Array<Int> = [];
    var zoomTarget:Array<Float> = [];
    var zoomDuration:Array<Float> = [];
    interp.variables.set("Math", Math);
    interp.variables.set("Std", Std);
    interp.variables.set("makeRangeArray", function(max:Int, ?min:Int = 0):Array<Int> {{
      var values:Array<Int> = [];
      for (i in min...max) values.push(i);
      return values;
    }});
    interp.variables.set("difficulty", 1);
    interp.variables.set("curStep", 500);
    interp.variables.set("songPos", 1000.0);
    interp.variables.set("bpm", 120.0);
    interp.variables.set("crochet", 500.0);
    interp.variables.set("luaGetDefaultStrum", function(index:Dynamic, axis:Dynamic):Float {{
      var i = Std.int(index);
      return StringTools.trim(Std.string(axis)).toLowerCase() == "x" ? defaultX[i] : defaultY[i];
    }});
    interp.variables.set("setActorX", function(value:Dynamic, index:Dynamic):Void {{
      actorX.push(Std.parseFloat(Std.string(value)));
      actorXIndex.push(Std.int(index));
    }});
    interp.variables.set("setActorY", function(value:Dynamic, index:Dynamic):Void {{
      actorY.push(Std.parseFloat(Std.string(value)));
      actorYIndex.push(Std.int(index));
    }});
    interp.variables.set("tweenCameraZoom", function(value:Dynamic, duration:Dynamic):Void {{
      zoomTarget.push(Std.parseFloat(Std.string(value)));
      zoomDuration.push(Std.parseFloat(Std.string(duration)));
    }});
    interp.execute(new Parser().parseString(converted.hscript));
    var start:Dynamic = interp.variables.get("start");
    var update:Dynamic = interp.variables.get("update");
    var playerOneTurn:Dynamic = interp.variables.get("playerOneTurn");
    var playerTwoTurn:Dynamic = interp.variables.get("playerTwoTurn");
    if (start == null || update == null || playerOneTurn == null || playerTwoTurn == null)
      fail("Tutorial lifecycle callbacks were not materialized");
    start("Tutorial");

    // Normal and pre-threshold hard difficulty must leave all receptors alone.
    update(0.016);
    if (actorX.length != 0 || actorY.length != 0)
      fail("difficulty 1 unexpectedly moved receptors");
    interp.variables.set("difficulty", 2);
    interp.variables.set("curStep", 400);
    update(0.016);
    if (actorX.length != 0 || actorY.length != 0)
      fail("step 400 unexpectedly moved receptors");

    // The donor uses songPos/bpm plus immutable defaultStrum baselines.
    interp.variables.set("curStep", 401);
    update(0.016);
    if (actorX.length != 8 || actorY.length != 8)
      fail("hard update did not move all eight receptors");
    for (i in 0...8) {{
      if (actorXIndex[i] != i || actorYIndex[i] != i)
        fail("receptor index " + i + " was routed to the wrong lane");
      var beat = (1000.0 / 1000.0) * (120.0 / 60.0);
      close(actorX[i], defaultX[i] + 32 * Math.sin((beat + i * 0.25) * Math.PI), "x" + i);
      close(actorY[i], defaultY[i] + 32 * Math.cos((beat + i * 0.25) * Math.PI), "y" + i);
    }}

    // A refreshed legacy bpm/songPos pair changes the next frame's motion.
    actorX.resize(0); actorY.resize(0); actorXIndex.resize(0); actorYIndex.resize(0);
    interp.variables.set("songPos", 1500.0);
    interp.variables.set("bpm", 180.0);
    update(0.016);
    var changedBeat = (1500.0 / 1000.0) * (180.0 / 60.0);
    close(actorX[0], defaultX[0] + 32 * Math.sin(changedBeat * Math.PI), "live bpm/songPos x0");
    close(actorY[0], defaultY[0] + 32 * Math.cos(changedBeat * Math.PI), "live bpm/songPos y0");

    playerTwoTurn();
    playerOneTurn();
    if (zoomTarget.length != 2 || zoomDuration.length != 2)
      fail("player turn callbacks did not request camera tweens");
    close(zoomTarget[0], 1.3, "playerTwoTurn zoom");
    close(zoomTarget[1], 1.0, "playerOneTurn zoom");
    close(zoomDuration[0], 2.0, "playerTwoTurn duration");
    close(zoomDuration[1], 2.0, "playerOneTurn duration");
    Sys.println("OK");
  }}
}}
'''
        result = run_haxe(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_kade_bpm_alias_tracks_the_live_conductor(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("setAllHaxeVar('bpm', Conductor.bpm);", play_state)
        self.assertEqual(play_state.count('interp.variables.set("bpm", Conductor.bpm);'), 2)
        method = extract_method(play_state, "function syncLegacyKadeGlobals")
        method = method.replace("function syncLegacyKadeGlobals", "static function syncLegacyKadeGlobals", 1)
        fixture = f'''class Conductor {{
  public static var songPosition:Float = 0;
  public static var bpm:Float = 120;
}}
class KadeRuntimeFixture {{
  static var values:Map<String, Dynamic> = [];
  static function setAllHaxeVar(name:String, value:Dynamic):Void values.set(name, value);
  {method}
  static function main() {{
    Conductor.songPosition = 1000;
    Conductor.bpm = 120;
    syncLegacyKadeGlobals();
    if (values.get("songPos") != 1000 || values.get("bpm") != 120)
      throw "initial Kade timing globals were not mirrored";
    Conductor.songPosition = 1500;
    Conductor.bpm = 180;
    syncLegacyKadeGlobals();
    if (values.get("songPos") != 1500 || values.get("bpm") != 180)
      throw "BPM-change Kade timing globals were not refreshed";
    Sys.println("OK");
  }}
}}
'''
        result = run_haxe(fixture, include_source=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_needs_voices_without_a_donor_voice_file_degrades_to_silent_track(self):
        if not KADE_CHART.is_file():
            self.skipTest("mounted HellBeats chart is unavailable")
        chart = json.loads(KADE_CHART.read_text())
        self.assertTrue(chart["song"]["needsVoices"])
        self.assertFalse((KADE_CHART.parent / "Voices.ogg").exists())
        play_state = (ROOT / "source/PlayState.hx").read_text()
        method = extract_method(play_state, "private function initializeVocalTracks")
        fixture = f'''class FlxSound {{
  public var looped:Bool = true;
  public var volume:Float = 1;
  public var playing:Bool = false;
  public function new() {{}}
  public function play():Void playing = true;
  public function pause():Void playing = false;
  public function stop():Void playing = false;
}}
class SoundList {{
  public var count:Int = 0;
  public function new() {{}}
  public function add(sound:FlxSound):Void count++;
}}
class SoundManager {{
  public var list:SoundList;
  public function new() {{ list = new SoundList(); }}
}}
class FlxG {{ public static var sound:SoundManager = new SoundManager(); }}
class FNFAssets {{
  public static function exists(path:String):Bool return false;
  public static function getSound(path:String):Dynamic return null;
}}
class VocalTracks {{
  public var tracks:Array<FlxSound>;
  public function new(primary:FlxSound, ?extra:Array<FlxSound>) {{
    tracks = [primary];
    if (extra != null) for (sound in extra) tracks.push(sound);
  }}
}}
class FakeSong {{
  public var song:String = "Tutorial";
  public var needsVoices:Bool = true;
  public var vocalStems:Array<Dynamic> = [];
  public function new() {{}}
}}
class KadeRuntimeFixture {{
  var SONG:FakeSong = new FakeSong();
  var vocals:FlxSound;
  var vocalTracks:VocalTracks;
  function resolveNativeVocalStem(file:String):String return file;
  function loadVocalTrack(path:String):FlxSound return null;
  {method}
  public function new() {{}}
  static function main() {{
    var host = new KadeRuntimeFixture();
    host.initializeVocalTracks("assets/songs/Tutorial/Voices.ogg");
    if (host.vocals == null || host.vocalTracks == null)
      throw "missing Voices.ogg did not create a silent vocal track";
    if (host.vocalTracks.tracks.length != 1 || FlxG.sound.list.count != 1)
      throw "silent vocal fallback was not registered exactly once";
    Sys.println("OK");
  }}
}}
'''
        result = run_haxe(fixture, include_source=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[vocal-fallback]", result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    @unittest.skipUnless(KADE_OFFSET.is_file(), "mounted HellBeats offset fixture is unavailable")
    def test_empty_offset_is_inert_and_nonempty_offset_only_diagnoses(self):
        self.assertEqual(KADE_OFFSET.read_text().strip(), "")
        play_state = (ROOT / "source/PlayState.hx").read_text()
        method = extract_method(play_state, "function diagnoseLegacyKadeOffset")
        fixture = f'''class FNFAssets {{
  public static var raw:String = "";
  public static function exists(path:String):Bool return true;
  public static function getText(path:String):String return raw;
}}
class KadeRuntimeFixture {{
  var SONG:Dynamic = {{song:"Tutorial"}};
  var legacyOffsetDiagnosticEmitted:Bool = false;
  {method}
  public function new() {{}}
  static function main() {{
    var empty = new KadeRuntimeFixture();
    FNFAssets.raw = "  \\n";
    empty.diagnoseLegacyKadeOffset();
    Sys.println("EMPTY_OK");
    var nonempty = new KadeRuntimeFixture();
    FNFAssets.raw = "12.5";
    nonempty.diagnoseLegacyKadeOffset();
    Sys.println("NONEMPTY_OK");
  }}
}}
'''
        result = run_haxe(fixture, include_source=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = result.stdout + result.stderr
        self.assertIn("EMPTY_OK", output)
        self.assertIn("NONEMPTY_OK", output)
        self.assertIn("[kade-offset-unsupported]", output)


if __name__ == "__main__":
    unittest.main()
