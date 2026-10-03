"""Vs Tricky expurgation mechanic contracts at the engine/HXC compat layer.

Covers the reported gameplay regressions on the mounted Vs Tricky donor:

* The sign-post chain: the translated ``tricky.ExpurgationSignEvent`` adapter
  must hand the parsed chart payload (native Int/Bool values) to the
  ``tricky.ExpurgationSign`` module scope, and that module places its sprite
  with the donor strumline API (``strumline.x + getXPos(lane)``) which the
  native ``Strumline`` class has to expose.
* The gremlin HP drain: the donor drain is tween-percent driven, so identical
  simulated wall time must produce identical health at 60 Hz and 240 Hz, the
  engine's module update dispatch must pass real elapsed seconds through
  without rescaling, and the chart event's ``hpToTake`` percent (drain STOPS
  at that percent of the starting health) must survive the whole pipeline.
* The gremlin follow: the hold tween must chase the player icon's live bar
  position (the donor's ``healthBar.x + width * remap(perct) - 101`` target)
  instead of a collapsed 0% target, which requires hscript float arithmetic
  to keep Float semantics in compiled hxcpp builds (the interpreter never
  truncated them, so only headless gameplay exposed the bug).

The fixtures never launch the game and never write to the mounted donor tree.
"""
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
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods/v-slice/Vs Tricky")
SIGN_EVENT = DONOR / "scripts/events/ExpurgationSignEvent.hxc"
SIGN_MODULE = DONOR / "scripts/modules/ExpurgationSign.hxc"
GREMLIN_MODULE = DONOR / "scripts/modules/ExpurgationGremlin.hxc"
GREMLIN_EVENT = DONOR / "scripts/events/ExpurgationGremlinEvent.hxc"
STRUMLINE_SOURCE = ROOT / "source/Strumline.hx"
HSCRIPT_INTERP = ROOT / ".haxelib/hscript/2,5,0/hscript/Interp.hx"
IMPORTED_SIGN_SHEET = (ROOT / "export/release/linux/bin/assets/imported_mods"
                       "/v-slice-vs-tricky-5cb4ba5ba3/images/mechanics/Sign_Post_Mechanic.xml")


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain unavailable")
class VsTrickyExpurgationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.have_donor = all(path.is_file() for path in
                             (SIGN_EVENT, SIGN_MODULE, GREMLIN_MODULE, STRUMLINE_SOURCE,
                              GREMLIN_EVENT, HSCRIPT_INTERP, IMPORTED_SIGN_SHEET))

    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        if not self.have_donor:
            self.skipTest("mounted Vs Tricky donor is unavailable")
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="vs-tricky-expurgation-", dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(source, newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            return subprocess.run(
                [
                    *HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                    "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                    "-main", "Main", "--interp",
                ], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
            )

    def test_sign_event_chain_reaches_module_scope_with_native_payload(self):
        """songEvent(kind) -> module scriptCall('appear', [native type, flipX])
        -> the module sprite is placed via playerStrumline.x + getXPos(3)."""
        main = f'''import hscript.Parser;
import hscript.Interp;
import haxe.Json;

class FakeAnimController {{
  public var played:Array<String> = [];
  public var finishCallback:Dynamic;
  public function new() {{}}
  public function addByPrefix(name:String, prefix:String, fps:Int, looped:Bool):Void
    played.push(name + ':' + prefix);
  public function addByIndices(name:String, prefix:String, indices:Array<Int>, postfix:String, fps:Int, ?looped:Bool):Void
    played.push(name + ':' + prefix);
  public function play(name:String, ?force:Dynamic, ?reversed:Dynamic, ?frame:Dynamic):Void
    played.push('play:' + name);
}}
class FakeSprite {{
  public var x:Float = 0; public var y:Float = 0;
  public var width:Float = 512; public var height:Float = 512;
  public var angle:Float = 0; public var flipX:Bool = false; public var flipY:Bool = false;
  public var antialiasing:Bool = false;
  public var zIndex:Float = 0;
  public var cameras:Array<Dynamic> = null;
  public var animation:FakeAnimController;
  public function new(px:Float = 0, py:Float = 0) {{ x = px; y = py; animation = new FakeAnimController(); }}
  public function setGraphicSize(w:Int, ?h:Int):Void {{ width = w; }}
}}
class FakeStrumline {{
  public var x:Float = 732;
  public var isDownscroll:Bool = false;
  public var xPosCalls:Array<Dynamic> = [];
  public function new() {{}}
  public function getXPos(direction:Float):Float {{ xPosCalls.push(direction); return direction * 112; }}
}}
class FakeStage {{
  public function new() {{}}
  public function refresh():Void {{}}
}}
class FakePlayStateInstance {{
  public var camHUD:Dynamic = {{}};
  public var playerStrumline:FakeStrumline;
  public var curStage:FakeStage;
  public var added:Array<Dynamic> = [];
  public function new() {{ playerStrumline = new FakeStrumline(); curStage = new FakeStage(); }}
  public function add(sprite:Dynamic):Void added.push(sprite);
  public function refresh():Void {{}}
}}
class FakePlayState {{ public static var instance:FakePlayStateInstance; }}
class FlxEaseStub {{ public static var expoOut:Dynamic = null; }}
class FlxTweenStub {{
  public static var created:Int = 0;
  public static function tween(target:Dynamic, values:Dynamic, duration:Float, ?options:Dynamic):Dynamic {{
    created++;
    return target;
  }}
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function put(interp:Interp, name:String, value:Dynamic):Void interp.variables.set(name, value);
  static var moduleCalls:Array<Dynamic> = [];
  static var cachedTextures:Array<String> = [];
  static function main() {{
    var playStateInstance = new FakePlayStateInstance();
    FakePlayState.instance = playStateInstance;

    // The real translated ExpurgationSign module runs in its own scope, the
    // same topology PlayState uses for HXC module scopes.
    var moduleInterp = new Interp();
    var runtimeStub:Dynamic = {{
      cacheFunkinTexture: function(root:Dynamic, key:Dynamic):Dynamic {{
        cachedTextures.push(Std.string(key));
        return null;
      }},
      createFunkinSpriteSparrow: function(root:Dynamic, px:Dynamic, py:Dynamic, key:Dynamic):Dynamic
        return new FakeSprite(px, py),
      setZIndex: function(sprite:Dynamic, z:Dynamic, mode:String):Void
        Reflect.setField(sprite, 'zIndex', z),
      safeTween: function(target:Dynamic, values:Dynamic, duration:Dynamic, ?options:Dynamic):Dynamic
        return FlxTweenStub.tween(target, values, duration, options)
    }};
    put(moduleInterp, 'PlayState', FakePlayState);
    put(moduleInterp, 'hxcAssetRoot', '');
    put(moduleInterp, 'Std', Std);
    put(moduleInterp, 'Math', Math);
    put(moduleInterp, 'HxcCompatRuntime', runtimeStub);
    put(moduleInterp, 'FlxEase', FlxEaseStub);
    put(moduleInterp, 'FlxTween', FlxTweenStub);
    var moduleResult = HxcCompat.analyze(sys.io.File.getContent({hx_string(str(SIGN_MODULE))}),
      'scripts/modules/ExpurgationSign.hxc');
    if (!moduleResult.moduleSafe || !moduleResult.moduleInitializationSafe)
      fail('sign module is not eligible for runtime dispatch: ' + moduleResult.moduleSafetyReasons.join(','));
    var moduleSource = moduleResult.generatedHscript;
    moduleInterp.execute(new Parser().parseString(moduleSource));
    if (cachedTextures.length != 3 || cachedTextures[0] != 'mechanics/Sign_Post_Mechanic'
      || cachedTextures[1] != 'mechanics/HP GREMLIN' || cachedTextures[2] != 'notes/NOTE_death')
      fail('literal texture constructor cache did not execute');

    // The event adapter's hxcGetModule bridge mirrors PlayState's module proxy:
    // scriptCall resolves the method on the module scope and calls it.
    var eventInterp = new Interp();
    put(eventInterp, 'PlayState', FakePlayState);
    put(eventInterp, 'hxcGetModule', function(name:Dynamic):Dynamic {{
      return {{
        scriptCall: function(methodName:String, ?args:Array<Dynamic>):Dynamic {{
          moduleCalls.push([name, methodName, args]);
          var method:Dynamic = moduleInterp.variables.get(methodName);
          if (method == null) fail('module scope has no ' + methodName);
          return Reflect.callMethod(null, method, args == null ? [] : args);
        }}
      }};
    }});
    var eventSource = HxcCompat.analyze(sys.io.File.getContent({hx_string(str(SIGN_EVENT))}),
      'scripts/events/ExpurgationSignEvent.hxc').generatedHscript;
    eventInterp.execute(new Parser().parseString(eventSource));

    // The importer stores V-Slice event values as JSON in the legacy v1 slot.
    var payload = EngineCompat.hxcSongEventPayload([
      'tricky.ExpurgationSignEvent', Json.stringify({{type: 1, flipX: true}}), '', '', 0]);
    var callback:Dynamic = eventInterp.variables.get('songEvent');
    if (callback == null) fail('sign event adapter did not emit a songEvent hook');
    Reflect.callMethod(null, callback, [payload]);

    if (moduleCalls.length != 1 || moduleCalls[0][0] != 'tricky.ExpurgationSign'
      || moduleCalls[0][1] != 'appear') fail('sign module did not receive its kind\\'s appear');
    var args:Array<Dynamic> = moduleCalls[0][2];
    if (args == null || args.length != 2) fail('appear arity');
    if (!Std.isOfType(args[0], Int) || args[0] != 1) fail('sign type must stay a native Int');
    if (!Std.isOfType(args[1], Bool) || args[1] != true) fail('sign flipX must stay a native Bool');

    if (playStateInstance.added.length != 1) fail('sign sprite was not added to PlayState');
    var sign:FakeSprite = playStateInstance.added[0];
    // donor placement: strumline.x + getXPos(3) - 400, then the type 1 offset
    if (sign.x != 732 + 3 * 112 - 400 - 130) fail('sign x must use strumline.x + getXPos(3): ' + sign.x);
    if (sign.y != -980) fail('upscroll type 1 sign y: ' + sign.y);
    if (!sign.flipX) fail('sign flipX was not applied');
    if (sign.animation.played.indexOf('play:sign') < 0) fail('sign animation was not played');
    if (sign.zIndex != 1500) fail('sign z index was not applied');
    var lanes:Array<Dynamic> = playStateInstance.playerStrumline.xPosCalls;
    if (lanes.length < 1 || lanes[lanes.length - 1] != 3) fail('donor getXPos(3) was not consulted');

    // The adapter is self-filtering: foreign kinds must not reach the module.
    moduleCalls.resize(0);
    var foreign = EngineCompat.hxcSongEventPayload(['Focus Camera', '0', '0', '', 0]);
    Reflect.callMethod(null, callback, [foreign]);
    if (moduleCalls.length != 0) fail('a foreign event kind reached the sign module');

    Sys.println('expurgation-sign-chain-ok');
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("expurgation-sign-chain-ok", result.stdout)

    def test_native_strumline_exposes_donor_lane_geometry(self):
        """The native Strumline must implement the donor V-Slice API imported
        modules call: getXPos/lane wrap, killNote, and the isDownscroll read."""
        strumline = STRUMLINE_SOURCE.read_text()
        self.assertIn("public var isDownscroll(get, never):Bool", strumline)
        self.assertIn("public static var INITIAL_OFFSET:Float", strumline)
        get_x = strumline[strumline.index("public function getXPos("):strumline.index("public function killNote(")]
        kill = strumline[strumline.index("public function killNote("):strumline.index("\t/**\n\t * Adjust only receptor spacing")]
        get_x = get_x.replace("StrumNote", "StrumNoteStub")
        # the fixture stays flixel-free: the note stub models the FlxBasic surface
        # killNote relies on (visible/alive/exists + kill())
        kill = kill.replace("FlxBasic", "BasicStub")
        main = f'''class StrumNoteStub {{
  public var x:Float;
  public function new(x:Float) {{ this.x = x; }}
}}
class BasicStub {{
  public var visible:Bool = true;
  public var alive:Bool = true;
  public var exists:Bool = true;
  public function new() {{}}
  public function kill():Void {{ alive = false; exists = false; }}
}}
class Probe {{
  public var x:Float;
  public var members:Array<StrumNoteStub>;
  public function new(x:Float, members:Array<StrumNoteStub>) {{
    this.x = x;
    this.members = members;
  }}
{get_x}
{kill}
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var members:Array<StrumNoteStub> = [];
    for (i in 0...4) members.push(new StrumNoteStub(732 + i * 112));
    var line = new Probe(732, members);
    // donor contract: line.x + getXPos(dir) is the lane's live world position
    for (dir in 0...4)
      if (line.x + line.getXPos(dir) != members[dir].x) fail('lane world position at ' + dir);
    if (line.getXPos(3) != 336) fail('lane 3 offset: ' + line.getXPos(3));
    if (line.getXPos(-1) != 336) fail('negative direction must wrap like the donor');
    if (line.getXPos(4) != 0) fail('direction must wrap modulo the lane count');
    if (line.getXPos(0) != 0) fail('lane 0 offset: ' + line.getXPos(0));

    var native = new BasicStub();
    var wrapper:Dynamic = {{nativeNote: native}};
    line.killNote(wrapper);
    if (native.visible || native.exists) fail('killNote must hide and kill the wrapped note');
    line.killNote(null);
    line.killNote({{}});
    Sys.println('expurgation-strumline-contract-ok');
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("expurgation-strumline-contract-ok", result.stdout)

    def test_gremlin_drain_is_frame_rate_independent(self):
        """The gremlin HP drain is tween-percent driven, so equal simulated
        wall time must produce equal health at 60 Hz and 240 Hz; the drain must
        take the authored duration instead of completing instantly."""
        main = f'''import hscript.Parser;
import hscript.Interp;

class GTimer {{
  public static var all:Array<GTimer> = [];
  public var time:Float = 0;
  public var elapsed:Float = 0;
  public var fired:Bool = false;
  public var active:Bool = false;
  public var callback:Dynamic;
  public function new() {{}}
  public function start(t:Float, cb:Dynamic):GTimer {{
    time = t; callback = cb; elapsed = 0; fired = false; active = true; all.push(this);
    return this;
  }}
  public function reset(?t:Float):GTimer {{ elapsed = 0; return this; }}
  public static function begin():Void all.resize(0);
  public static function advance(dt:Float):Void {{
    for (timer in all) {{
      if (!timer.active || timer.fired) continue;
      timer.elapsed += dt;
      if (timer.elapsed >= timer.time) {{
        timer.fired = true;
        timer.active = false;
        timer.callback(timer);
      }}
    }}
  }}
}}
class GTween {{
  public static var all:Array<GTween> = [];
  public var target:Dynamic; public var values:Dynamic; public var duration:Float;
  public var elapsed:Float = 0; public var done:Bool = false;
  public var onUpdate:Dynamic; public var onComplete:Dynamic;
  public function new(target:Dynamic, values:Dynamic, duration:Float, ?options:Dynamic) {{
    this.target = target; this.values = values; this.duration = duration;
    if (options != null) {{ onUpdate = options.onUpdate; onComplete = options.onComplete; }}
    all.push(this);
  }}
  public function get_percent():Float return duration <= 0 ? 1 : elapsed / duration;
  public static function begin():Void all.resize(0);
  public static function advance(dt:Float):Void {{
    var list = all.copy();
    for (tween in list) {{
      if (tween.done) continue;
      tween.elapsed += dt;
      if (tween.elapsed >= tween.duration) {{
        tween.elapsed = tween.duration;
        if (tween.onUpdate != null) tween.onUpdate(tween);
        tween.done = true;
        if (tween.onComplete != null) tween.onComplete(tween);
      }} else if (tween.onUpdate != null) tween.onUpdate(tween);
    }}
  }}
}}
class FlxMathStub {{
  public static function lerp(a:Float, b:Float, t:Float):Float return a + (b - a) * t;
  public static function remapToRange(value:Float, start1:Float, stop1:Float, start2:Float, stop2:Float):Float
    return start2 + (stop2 - start2) * ((value - start1) / (stop1 - start1));
}}
class PathsStub {{ public static function sound(name:String, ?lib:String):String return name; }}
class FlxEaseStub {{ public static var elasticIn:Dynamic = null; }}
class FakeAnimController {{
  public var finishCallback:Dynamic;
  public var played:Array<String> = [];
  public function new() {{}}
  public function addByIndices(name:String, prefix:String, indices:Array<Int>, postfix:String, fps:Int, ?looped:Bool):Void
    played.push(name + ':' + prefix);
  public function play(name:String, ?force:Dynamic, ?reversed:Dynamic, ?frame:Dynamic):Void
    played.push('play:' + name);
}}
class FakeSprite {{
  public var x:Float = 0; public var y:Float = 0;
  public var width:Float = 512; public var height:Float = 512;
  public var flipY:Bool = false; public var antialiasing:Bool = false;
  public var cameras:Array<Dynamic> = null;
  public var animation:FakeAnimController;
  public function new(px:Float = 0, py:Float = 0) {{ x = px; y = py; animation = new FakeAnimController(); }}
  public function setGraphicSize(w:Int, ?h:Int):Void {{ width = w; }}
}}
class GStrumline {{ public var isDownscroll:Bool = false; public function new() {{}} }}
class GPlayStateInstance {{
  public var health:Float = 2.0;
  public var iconP1:Dynamic = {{x: 600.0}};
  public var healthBarBG:Dynamic = {{y: 600.0}};
  public var healthBar:Dynamic = {{x: 400.0, width: 500.0}};
  public var camHUD:Dynamic = {{}};
  public var playerStrumline:GStrumline;
  public function new() {{ playerStrumline = new GStrumline(); }}
  public function add(sprite:Dynamic):Void {{}}
  public function remove(sprite:Dynamic):Void {{}}
}}
class GPlayState {{ public static var instance:GPlayStateInstance; }}
class Main {{
  static function fail(value:String):Void throw value;
  static function put(interp:Interp, name:String, value:Dynamic):Void interp.variables.set(name, value);
  static function runScenario(rate:Int, seconds:Float):Array<Float> {{
    GTimer.begin();
    GTween.begin();
    var instance = new GPlayStateInstance();
    GPlayState.instance = instance;
    var runtimeStub:Dynamic = {{
      createFunkinSpriteSparrow: function(root:Dynamic, px:Dynamic, py:Dynamic, key:Dynamic):Dynamic
        return new FakeSprite(px, py),
      freeplayPlaySound: function(path:Dynamic):Dynamic return null,
      setZIndex: function(sprite:Dynamic, z:Dynamic, mode:String):Void {{}},
      safeTween: function(target:Dynamic, values:Dynamic, duration:Dynamic, ?options:Dynamic):Dynamic
        return new GTween(target, values, duration, options)
    }};
    var interp = new Interp();
    put(interp, 'PlayState', GPlayState);
    put(interp, 'hxcAssetRoot', '');
    put(interp, 'Std', Std);
    put(interp, 'Math', Math);
    put(interp, 'HxcCompatRuntime', runtimeStub);
    put(interp, 'FlxTimer', GTimer);
    put(interp, 'FlxMath', FlxMathStub);
    put(interp, 'FlxEase', FlxEaseStub);
    put(interp, 'Paths', PathsStub);
    var generated = HxcCompat.analyze(sys.io.File.getContent({hx_string(str(GREMLIN_MODULE))}),
      'scripts/modules/ExpurgationGremlin.hxc').generatedHscript;
    interp.execute(new Parser().parseString(generated));
    var appear:Dynamic = interp.variables.get('appear');
    if (appear == null) fail('gremlin module did not emit appear');
    // the song script's timer call: drain 40% of current health over 3 seconds
    Reflect.callMethod(null, appear, [40, 3, false]);
    var samples:Array<Float> = [];
    var dt:Float = 1.0 / rate;
    for (i in 0...Math.round(seconds * rate)) {{
      GTimer.advance(dt);
      GTween.advance(dt);
      samples.push(instance.health);
    }}
    return samples;
  }}
  static function sampleAt(samples:Array<Float>, rate:Int, time:Float):Float {{
    return samples[Std.int(Math.round(time * rate)) - 1];
  }}
  static function main() {{
    var low = runScenario(60, 4.5);
    var high = runScenario(240, 4.5);
    var ultra = runScenario(480, 4.5);
    // timeline: 0.14s woosh timer -> 1s grab tween -> 3s hold/drain tween
    for (spec in [
      {{time: 1.0, equal: 2.0}},   // grab tween: no drain yet
      {{time: 4.2, equal: 0.8}}    // drain finished at lerp end (40% of 2.0)
    ])
      for (pair in [
        {{name: '60fps', value: sampleAt(low, 60, spec.time)}},
        {{name: '240fps', value: sampleAt(high, 240, spec.time)}},
        {{name: '480fps', value: sampleAt(ultra, 480, spec.time)}}
      ])
        if (Math.abs(pair.value - spec.equal) > 1e-9)
          fail('drain at ' + pair.name + ' t=' + spec.time + ': ' + pair.value + ' != ' + spec.equal);
    for (time in [1.5, 2.0, 3.0, 4.0]) {{
      var at60 = sampleAt(low, 60, time);
      var at240 = sampleAt(high, 240, time);
      var at480 = sampleAt(ultra, 480, time);
      // tick quantization may offset a sample by at most one 60Hz tick of
      // drain progress (1.2 hp over 3s -> 0.0067); an fps-scaling regression
      // (tick-count driven drain) would diverge by orders of magnitude more
      if (Math.abs(at60 - at240) > 0.0075)
        fail('health diverged at t=' + time + ': 60fps=' + at60 + ' 240fps=' + at240);
      if (Math.abs(at60 - at480) > 0.0075)
        fail('health diverged at t=' + time + ': 60fps=' + at60 + ' 480fps=' + at480);
    }}
    var mid60 = sampleAt(low, 60, 3.0);
    if (mid60 >= 2.0 || mid60 <= 0.8) fail('drain must be progressive over the authored duration');
    Sys.println('expurgation-drain-fps-independent-ok');
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("expurgation-drain-fps-independent-ok", result.stdout)

    def test_update_hook_dispatch_passes_elapsed_seconds_unscaled(self):
        """PlayState broadcasts module update hooks with its own elapsed value;
        the argument adapter must pass real seconds through at any tick rate."""
        main = r'''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var hz240 = 1 / 240;
    var hz480 = 1 / 480;
    var hz30 = 1 / 30;
    var donor240:Array<Dynamic> = EngineCompat.callbackArguments('update', 'onUpdate', [hz240], true);
    if (donor240.length != 1 || (donor240[0]:Float) != hz240) fail('240Hz update elapsed was rescaled');
    var donor480:Array<Dynamic> = EngineCompat.callbackArguments('update', 'onUpdate', [hz480], true);
    if (donor480.length != 1 || (donor480[0]:Float) != hz480) fail('480Hz update elapsed was rescaled');
    var donor30:Array<Dynamic> = EngineCompat.callbackArguments('update', 'onUpdate', [hz30], true);
    if (donor30.length != 1 || (donor30[0]:Float) != hz30) fail('30Hz update elapsed was rescaled');
    var post240:Array<Dynamic> = EngineCompat.callbackArguments('updatePost', 'onUpdatePost', [hz240], true);
    if (post240.length != 1 || (post240[0]:Float) != hz240) fail('240Hz updatePost elapsed was rescaled');
    var canonical240:Array<Dynamic> = EngineCompat.callbackArguments('update', 'update', [hz240], false);
    if (canonical240.length != 1 || (canonical240[0]:Float) != hz240) fail('canonical update elapsed was rescaled');
    var beat240:Array<Dynamic> = EngineCompat.callbackArguments('beatHit', 'onBeatHit', [4], true);
    if (beat240.length != 0) fail('beat hook adapter changed');
    Sys.println('expurgation-elapsed-contract-ok');
  }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("expurgation-elapsed-contract-ok", result.stdout)

    def test_per_frame_health_drains_scale_with_real_seconds(self):
        """The engine's held-modifier drains (love/poison) were authored per
        frame at 60 FPS; they must scale through frameRateScale so their rate
        is real-second based instead of growing with the fps cap."""
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn(
            "health += loveMultiplier * (opponentPlayer ? -1 : 1) / 600000 * frameRateScale(elapsed);",
            play_state, "love drain must scale by frameRateScale")
        self.assertIn(
            "health -= poisonMultiplier * (opponentPlayer ? -1 : 1)/ 700000 * frameRateScale(elapsed);",
            play_state, "poison drain must scale by frameRateScale")
        scale = play_state[play_state.index("public static function frameRateScale("):
                           play_state.index("public static function characterAnimationName(")]
        main = f'''class ScaleProbe {{
{scale}
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    if (ScaleProbe.frameRateScale(1 / 60) != 1) fail('60Hz must be the authored reference rate');
    if (ScaleProbe.frameRateScale(1 / 240) != 0.25) fail('240Hz must quarter the per-frame amount');
    if (ScaleProbe.frameRateScale(1 / 480) != 0.125) fail('480Hz must scale the per-frame amount by one eighth');
    if (ScaleProbe.frameRateScale(1 / 30) != 2) fail('30Hz must double the per-frame amount');
    if (ScaleProbe.frameRateScale(0) != 0) fail('zero elapsed must contribute nothing');
    Sys.println('expurgation-modifier-drain-scaled-ok');
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("expurgation-modifier-drain-scaled-ok", result.stdout)


    def test_compiled_hscript_float_arithmetic_keeps_float_operands(self):
        """Compiled hxcpp hscript lowers the Dynamic `-`/`*`/`%` operators to
        INT arithmetic, truncating Float operands (`1477 * 0.67` -> 0) while
        the interpreter keeps full float semantics. The patched Interp must
        route those three binops through dpFloatAwareArith, which promotes to
        double math when either side is a Float and keeps Int math native."""
        interp = HSCRIPT_INTERP.read_text()
        for op in ("-", "*", "%"):
            self.assertIn(
                f'binops.set("{op}",function(e1,e2) {{ var a = me.expr(e1), b = me.expr(e2); '
                f'if( a == null || b == null ) {{ me.nullOperandDiagnose("{op}"); return null; }} '
                f'return me.dpFloatAwareArith("{op}", a, b); }});',
                interp, f"{op} binop must use dpFloatAwareArith")
        helper = interp[interp.index("function dpFloatAwareArith"):
                        interp.index("function nullOperandDiagnose")]
        self.assertIn("Std.isOfType(a, Float) || Std.isOfType(b, Float)", helper,
                      "promotion must trigger when either operand is a Float")

        main = f'''class ArithProbe {{
  public function new() {{}}
  public {helper}
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function desc(r:Dynamic):String {{
    var t = Type.typeof(r);
    if (t == TInt) return 'Int(' + r + ')';
    if (t == TFloat) return 'Float(' + r + ')';
    return Std.string(t);
  }}
  static function main() {{
    var probe = new ArithProbe();
    var cases:Array<Dynamic> = [
      {{op: "*", a: 1477, b: 0.67, want: 'Float(989.59)'}},
      {{op: "*", a: 2, b: 3.5, want: 'Float(7)'}},
      {{op: "-", a: 10, b: 0.5, want: 'Float(9.5)'}},
      {{op: "%", a: 7, b: 3, want: 'Int(1)'}},
      {{op: "*", a: 1477, b: 2, want: 'Int(2954)'}},
      {{op: "-", a: 9, b: 4, want: 'Int(5)'}}
    ];
    for (spec in cases) {{
      var got = desc(probe.dpFloatAwareArith(spec.op, spec.a, spec.b));
      if (got != spec.want) fail(spec.op + ' ' + spec.a + ',' + spec.b + ': ' + got + ' != ' + spec.want);
    }}
    Sys.println('expurgation-hscript-float-arith-ok');
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("expurgation-hscript-float-arith-ok", result.stdout)

    def test_chart_gremlin_drain_stops_at_donor_percent(self):
        """The chart event payload is {"duration":13,"persist":true,"hpToTake":20}
        with PlayState starting at 1.0 health: the donor drains TO 20% of the
        starting health over exactly the authored duration (0.8 hp over 13 s),
        instead of collapsing hpToTake to 0 and draining to zero."""
        main = f'''import hscript.Parser;
import hscript.Interp;

class GTimer {{
  public static var all:Array<GTimer> = [];
  public var time:Float = 0;
  public var elapsed:Float = 0;
  public var fired:Bool = false;
  public var active:Bool = false;
  public var callback:Dynamic;
  public function new() {{}}
  public function start(t:Float, cb:Dynamic):GTimer {{
    time = t; callback = cb; elapsed = 0; fired = false; active = true; all.push(this);
    return this;
  }}
  public function reset(?t:Float):GTimer {{ elapsed = 0; return this; }}
  public static function begin():Void all.resize(0);
  public static function advance(dt:Float):Void {{
    for (timer in all) {{
      if (!timer.active || timer.fired) continue;
      timer.elapsed += dt;
      if (timer.elapsed >= timer.time) {{
        timer.fired = true;
        timer.active = false;
        timer.callback(timer);
      }}
    }}
  }}
}}
class GTween {{
  public static var all:Array<GTween> = [];
  public var target:Dynamic; public var values:Dynamic; public var duration:Float;
  public var elapsed:Float = 0; public var done:Bool = false;
  public var onUpdate:Dynamic; public var onComplete:Dynamic;
  public function new(target:Dynamic, values:Dynamic, duration:Float, ?options:Dynamic) {{
    this.target = target; this.values = values; this.duration = duration;
    if (options != null) {{ onUpdate = options.onUpdate; onComplete = options.onComplete; }}
    all.push(this);
  }}
  public function get_percent():Float return duration <= 0 ? 1 : elapsed / duration;
  public static function begin():Void all.resize(0);
  public static function advance(dt:Float):Void {{
    var list = all.copy();
    for (tween in list) {{
      if (tween.done) continue;
      tween.elapsed += dt;
      if (tween.elapsed >= tween.duration) {{
        tween.elapsed = tween.duration;
        if (tween.onUpdate != null) tween.onUpdate(tween);
        tween.done = true;
        if (tween.onComplete != null) tween.onComplete(tween);
      }} else if (tween.onUpdate != null) tween.onUpdate(tween);
    }}
  }}
}}
class FlxMathStub {{
  public static function lerp(a:Float, b:Float, t:Float):Float return a + (b - a) * t;
  public static function remapToRange(value:Float, start1:Float, stop1:Float, start2:Float, stop2:Float):Float
    return start2 + (stop2 - start2) * ((value - start1) / (stop1 - start1));
}}
class PathsStub {{ public static function sound(name:String, ?lib:String):String return name; }}
class FlxEaseStub {{ public static var elasticIn:Dynamic = null; }}
class FakeAnimController {{
  public var finishCallback:Dynamic;
  public var played:Array<String> = [];
  public function new() {{}}
  public function addByIndices(name:String, prefix:String, indices:Array<Int>, postfix:String, fps:Int, ?looped:Bool):Void
    played.push(name + ':' + prefix);
  public function play(name:String, ?force:Dynamic, ?reversed:Dynamic, ?frame:Dynamic):Void
    played.push('play:' + name);
}}
class FakeSprite {{
  public var x:Float = 0; public var y:Float = 0;
  public var width:Float = 915; public var height:Float = 816;
  public var flipY:Bool = false; public var antialiasing:Bool = false;
  public var cameras:Array<Dynamic> = null;
  public var animation:FakeAnimController;
  public function new(px:Float = 0, py:Float = 0) {{ x = px; y = py; animation = new FakeAnimController(); }}
  public function setGraphicSize(w:Int, ?h:Int):Void {{ width = w; }}
}}
class GStrumline {{ public var isDownscroll:Bool = false; public function new() {{}} }}
class GPlayStateInstance {{
  public var health:Float = 1.0;
  public var iconP1:Dynamic = {{x: 600.0}};
  public var healthBarBG:Dynamic = {{y: 600.0}};
  public var healthBar:Dynamic = {{x: 400.0, width: 500.0}};
  public var camHUD:Dynamic = {{}};
  public var playerStrumline:GStrumline;
  public function new() {{ playerStrumline = new GStrumline(); }}
  public function add(sprite:Dynamic):Void {{}}
  public function remove(sprite:Dynamic):Void {{}}
}}
class GPlayState {{ public static var instance:GPlayStateInstance; }}
class Main {{
  static function fail(value:String):Void throw value;
  static function put(interp:Interp, name:String, value:Dynamic):Void interp.variables.set(name, value);
  static function runScenario(rate:Int, holdSeconds:Float):Array<Float> {{
    GTimer.begin();
    GTween.begin();
    var instance = new GPlayStateInstance();
    GPlayState.instance = instance;
    var runtimeStub:Dynamic = {{
      createFunkinSpriteSparrow: function(root:Dynamic, px:Dynamic, py:Dynamic, key:Dynamic):Dynamic
        return new FakeSprite(px, py),
      freeplayPlaySound: function(path:Dynamic):Dynamic return null,
      setZIndex: function(sprite:Dynamic, z:Dynamic, mode:String):Void {{}},
      safeTween: function(target:Dynamic, values:Dynamic, duration:Dynamic, ?options:Dynamic):Dynamic
        return new GTween(target, values, duration, options)
    }};
    var interp = new Interp();
    put(interp, 'PlayState', GPlayState);
    put(interp, 'hxcAssetRoot', '');
    put(interp, 'Std', Std);
    put(interp, 'Math', Math);
    put(interp, 'HxcCompatRuntime', runtimeStub);
    put(interp, 'FlxTimer', GTimer);
    put(interp, 'FlxMath', FlxMathStub);
    put(interp, 'FlxEase', FlxEaseStub);
    put(interp, 'Paths', PathsStub);
    var generated = HxcCompat.analyze(sys.io.File.getContent({hx_string(str(GREMLIN_MODULE))}),
      'scripts/modules/ExpurgationGremlin.hxc').generatedHscript;
    interp.execute(new Parser().parseString(generated));
    var appear:Dynamic = interp.variables.get('appear');
    if (appear == null) fail('gremlin module did not emit appear');
    // the expurgation-hard chart row: hpToTake 20, duration 13, persist true
    Reflect.callMethod(null, appear, [20, 13, true]);
    var samples:Array<Float> = [];
    var dt:Float = 1.0 / rate;
    var total:Float = 0.14 + 1.0 + holdSeconds;
    for (i in 0...Math.round(total * rate)) {{
      GTimer.advance(dt);
      GTween.advance(dt);
      samples.push(instance.health);
    }}
    return samples;
  }}
  static function main() {{
    var low = runScenario(60, 13.2);
    var high = runScenario(240, 13.2);
    var ultra = runScenario(480, 13.2);
    var lastLow = low[low.length - 1];
    var lastHigh = high[high.length - 1];
    var lastUltra = ultra[ultra.length - 1];
    // donor contract: health stops at hpToTake percent of the START health
    if (Math.abs(lastLow - 0.2) > 1e-6) fail('drain must stop at 0.2, got ' + lastLow);
    if (Math.abs(lastHigh - 0.2) > 1e-6) fail('240Hz drain diverged: ' + lastHigh);
    if (Math.abs(lastUltra - 0.2) > 1e-6) fail('480Hz drain diverged: ' + lastUltra);
    // halfway through the 13 s hold the donor sits at lerp(1.0, 0.2, 0.5) = 0.6
    var mid = low[Std.int((0.14 + 1.0 + 6.5) * 60) - 1];
    if (Math.abs(mid - 0.6) > 0.05) fail('mid-drain health ' + mid + ' != ~0.6');
    // drain rate contract: (1.0 - 0.2) hp over 13 s, no faster
    var early = low[Std.int((0.14 + 1.0 + 1.3) * 60) - 1];
    if (Math.abs(early - (1.0 - 0.8 * 0.1)) > 0.02) fail('early drain rate wrong: ' + early);
    Sys.println('expurgation-chart-drain-stops-at-donor-percent-ok');
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("expurgation-chart-drain-stops-at-donor-percent-ok", result.stdout)

    def test_gremlin_hold_tween_chases_the_drained_icon_position(self):
        """The donor gremlin grabs the player icon and drags it along the bar:
        the grab tween heads for iconP1.x - 140 and the hold tween's x target
        is the icon's position at the drained health (healthBar.x +
        width * remap(perct) - 26 - 75), so sprite and icon land together.
        For the chart row (hpToTake 20 from 1.0 health) perct = 10."""
        main = f'''import hscript.Parser;
import hscript.Interp;

class FTimer {{
  public static var all:Array<FTimer> = [];
  public var time:Float = 0;
  public var elapsed:Float = 0;
  public var fired:Bool = false;
  public var active:Bool = false;
  public var callback:Dynamic;
  public function new() {{}}
  public function start(t:Float, cb:Dynamic):FTimer {{
    time = t; callback = cb; elapsed = 0; fired = false; active = true; all.push(this);
    return this;
  }}
  public function reset(?t:Float):FTimer {{ elapsed = 0; return this; }}
  public static function begin():Void all.resize(0);
  public static function advance(dt:Float):Void {{
    for (timer in all) {{
      if (!timer.active || timer.fired) continue;
      timer.elapsed += dt;
      if (timer.elapsed >= timer.time) {{
        timer.fired = true;
        timer.active = false;
        timer.callback(timer);
      }}
    }}
  }}
}}
class FTween {{
  public static var all:Array<FTween> = [];
  public var target:Dynamic; public var values:Dynamic; public var duration:Float;
  public var elapsed:Float = 0; public var done:Bool = false;
  public var onUpdate:Dynamic; public var onComplete:Dynamic;
  public function new(target:Dynamic, values:Dynamic, duration:Float, ?options:Dynamic) {{
    this.target = target; this.values = values; this.duration = duration;
    if (options != null) {{ onUpdate = options.onUpdate; onComplete = options.onComplete; }}
    all.push(this);
  }}
  public function get_percent():Float return duration <= 0 ? 1 : elapsed / duration;
  public static function begin():Void all.resize(0);
  public static function advance(dt:Float):Void {{
    var list = all.copy();
    for (tween in list) {{
      if (tween.done) continue;
      tween.elapsed += dt;
      if (tween.elapsed >= tween.duration) {{
        tween.elapsed = tween.duration;
        if (tween.onUpdate != null) tween.onUpdate(tween);
        tween.done = true;
        if (tween.onComplete != null) tween.onComplete(tween);
      }} else if (tween.onUpdate != null) tween.onUpdate(tween);
    }}
  }}
}}
class FlxMathStub {{
  public static function lerp(a:Float, b:Float, t:Float):Float return a + (b - a) * t;
  public static function remapToRange(value:Float, start1:Float, stop1:Float, start2:Float, stop2:Float):Float
    return start2 + (stop2 - start2) * ((value - start1) / (stop1 - start1));
}}
class PathsStub {{ public static function sound(name:String, ?lib:String):String return name; }}
class FlxEaseStub {{ public static var elasticIn:Dynamic = null; }}
class FakeAnimController {{
  public var finishCallback:Dynamic;
  public function new() {{}}
  public function addByIndices(name:String, prefix:String, indices:Array<Int>, postfix:String, fps:Int, ?looped:Bool):Void {{}}
  public function play(name:String, ?force:Dynamic, ?reversed:Dynamic, ?frame:Dynamic):Void {{}}
}}
class FakeSprite {{
  public var x:Float = 0; public var y:Float = 0;
  public var width:Float = 915; public var height:Float = 816;
  public var flipY:Bool = false; public var antialiasing:Bool = false;
  public var cameras:Array<Dynamic> = null;
  public var animation:FakeAnimController;
  public function new(px:Float = 0, py:Float = 0) {{ x = px; y = py; animation = new FakeAnimController(); }}
  public function setGraphicSize(w:Int, ?h:Int):Void {{ width = w; }}
}}
class FStrumline {{ public var isDownscroll:Bool = false; public function new() {{}} }}
class FPlayStateInstance {{
  public var health:Float = 1.0;
  public var iconP1:Dynamic = {{x: 600.0}};
  public var healthBarBG:Dynamic = {{y: 600.0}};
  public var healthBar:Dynamic = {{x: 400.0, width: 500.0}};
  public var camHUD:Dynamic = {{}};
  public var playerStrumline:FStrumline;
  public function new() {{ playerStrumline = new FStrumline(); }}
  public function add(sprite:Dynamic):Void {{}}
  public function remove(sprite:Dynamic):Void {{}}
}}
class FPlayState {{ public static var instance:FPlayStateInstance; }}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var instance = new FPlayStateInstance();
    FPlayState.instance = instance;
    var runtimeStub:Dynamic = {{
      createFunkinSpriteSparrow: function(root:Dynamic, px:Dynamic, py:Dynamic, key:Dynamic):Dynamic
        return new FakeSprite(px, py),
      freeplayPlaySound: function(path:Dynamic):Dynamic return null,
      setZIndex: function(sprite:Dynamic, z:Dynamic, mode:String):Void {{}},
      safeTween: function(target:Dynamic, values:Dynamic, duration:Dynamic, ?options:Dynamic):Dynamic
        return new FTween(target, values, duration, options)
    }};
    var interp = new Interp();
    interp.variables.set('PlayState', FPlayState);
    interp.variables.set('hxcAssetRoot', '');
    interp.variables.set('Std', Std);
    interp.variables.set('Math', Math);
    interp.variables.set('HxcCompatRuntime', runtimeStub);
    interp.variables.set('FlxTimer', FTimer);
    interp.variables.set('FlxMath', FlxMathStub);
    interp.variables.set('FlxEase', FlxEaseStub);
    interp.variables.set('Paths', PathsStub);
    var generated = HxcCompat.analyze(sys.io.File.getContent({hx_string(str(GREMLIN_MODULE))}),
      'scripts/modules/ExpurgationGremlin.hxc').generatedHscript;
    interp.execute(new Parser().parseString(generated));
    var appear:Dynamic = interp.variables.get('appear');
    if (appear == null) fail('gremlin module did not emit appear');
    Reflect.callMethod(null, appear, [20, 13, true]);

    // spawn: the gremlin appears at the player icon, on the HUD
    var gremlin:FakeSprite = cast(instance.addedSprites[0], FakeSprite);
    if (gremlin.x != 600.0) fail('gremlin must spawn at iconP1.x, got ' + gremlin.x);
    if (gremlin.y != instance.healthBarBG.y - 325) fail('gremlin y anchor wrong: ' + gremlin.y);

    // grab phase: 0.14 s timer, then a 1 s tween toward iconP1.x - 140
    FTimer.advance(0.15);
    FTween.advance(0.016);
    if (FTween.all.length < 1) fail('grab tween missing');
    var grab = FTween.all[0];
    if (grab.duration != 1.0) fail('grab tween duration ' + grab.duration);
    if (grab.values.x != 600.0 - 140) fail('grab target must be iconP1.x - 140, got ' + grab.values.x);

    // hold phase: the drag tween must chase the icon's position at the
    // drained health: perct = 10 -> remap 90 -> 400 + 500 * 0.9 - 26 - 75
    FTween.advance(1.01);
    if (FTween.all.length < 2) fail('hold tween missing');
    var hold = FTween.all[FTween.all.length - 1];
    if (hold.duration != 13.0) fail('hold tween duration ' + hold.duration);
    var expected = (400.0 + 500.0 * (FlxMathStub.remapToRange(10, 0, 100, 100, 0) * 0.01) - 26) - 75;
    if (hold.values.x != expected) fail('hold target ' + hold.values.x + ' != icon position ' + expected);
    Sys.println('expurgation-gremlin-follow-contract-ok');
  }}
}}
'''
        # the FakeSprite additions need recording for the spawn assertion
        main = main.replace("public function add(sprite:Dynamic):Void {}",
                            "public var addedSprites:Array<Dynamic> = [];\n  public function add(sprite:Dynamic):Void { addedSprites.push(sprite); }")
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("expurgation-gremlin-follow-contract-ok", result.stdout)

    @unittest.skipUnless(IMPORTED_SIGN_SHEET.is_file(), "imported Tricky atlas fixture is unavailable")
    def test_sparrow_frame_size_semantics_match_donor(self):
        """FunkinSprite.createSparrow and the native createFunkinSpriteSparrow
        both end in flixel's set_frames: sprite.width becomes the first
        frame's UNTRIMMED sourceSize (frameWidth attr), so the module's
        `setGraphicSize(Std.int(width * 0.67))` always yields scale 0.67 and
        the visible sign is the trimmed art at 67% - donor sizing. Pin the
        math against the real imported Sign_Post_Mechanic atlas."""
        import re
        xml = IMPORTED_SIGN_SHEET.read_text(encoding="utf-8", errors="replace")
        first = re.search(r'<SubTexture [^>]*>', xml).group(0)
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', first))
        trimmed = int(attrs["width"])
        source_w = int(attrs.get("frameWidth", attrs["width"]))
        self.assertEqual((trimmed, source_w), (270, 1477),
                         "imported sign atlas changed; re-check expectations")

        main = f'''class FrameStub {{
  public var frameW:Float; public var frameH:Float;
  public var srcW:Float; public var srcH:Float;
  public var name:String;
  public function new(name:String, fw:Float, fh:Float, sw:Float, sh:Float) {{
    this.name = name; frameW = fw; frameH = fh; srcW = sw; srcH = sh;
  }}
}}
class SparrowProbe {{
  public var frames:Array<FrameStub>;
  public var frameWidth:Float; public var frameHeight:Float;
  public var width:Float; public var height:Float;
  public var scaleX:Float = 1; public var scaleY:Float = 1;
  public var currentIndex:Int = 0;
  public function new(frames:Array<FrameStub>) {{
    this.frames = frames;
    // flixel FlxSprite.set_frames: frame = frames[0]; resetFrameSize()
    setFrame(0);
  }}
  public function setFrame(index:Int):Void {{
    // flixel set_frame -> resetFrameSize: frameWidth = Std.int(sourceSize)
    currentIndex = index;
    frameWidth = frames[index].srcW;
    frameHeight = frames[index].srcH;
    width = frameWidth;
    height = frameHeight;
  }}
  public function setGraphicSize(w:Float, ?h:Float):Void {{
    if (w <= 0 && h <= 0) return;
    scaleX = w / frameWidth;
    scaleY = scaleX;
  }}
  public function playFirstFrame():Void setFrame(0);
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    // frame 0 of the donor sheet: trimmed art 270x761 drawn from an
    // untrimmed 1477x1318 canvas, exactly as the XML declares
    var sheet = new SparrowProbe([new FrameStub('Signature Stop Sign 10000', 270, 761, 1477, 1318)]);
    if (sheet.width != 1477) fail('sparrow width must be the untrimmed sourceSize, got ' + sheet.width);
    sheet.setGraphicSize(Std.int(sheet.width * 0.67));
    if (Math.abs(sheet.scaleX - (989 / 1477)) > 1e-6) fail('sign scale must be 0.6696, got ' + sheet.scaleX);
    var visible = 270 * sheet.scaleX;
    // donor renders the visible sign ~181 px wide: about one receptor wide
    if (visible < 170 || visible > 200) fail('visible sign width ' + visible);
    // switching to a later animation frame keeps scale and re-derives width
    sheet.setFrame(0);
    if (sheet.scaleX < 0.66 || sheet.scaleX > 0.68) fail('scale must survive frame changes');
    Sys.println('expurgation-sparrow-frame-size-ok');
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("expurgation-sparrow-frame-size-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
