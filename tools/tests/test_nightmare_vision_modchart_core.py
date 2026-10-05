"""Executable parity checks for the source-only Nightmare Vision modifier port."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
FLIXEL = ROOT / ".haxelib/flixel/6,1,2"
DONOR = ROOT.parent / "fnf_sources/NightmareVision/source/funkin/game/modchart"


class NightmareVisionModchartCoreTest(unittest.TestCase):
    def test_note_def_scale_is_a_live_alias_for_source_base_scale(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        note_source = (ROOT / "source/Note.hx").read_text()
        declarations = "\n".join(
            line.strip()
            for line in note_source.splitlines()
            if line.strip() in (
                "@:keep public var baseScale(get, set):FlxPoint;",
                "@:keep public var defScale(get, set):FlxPoint;",
                "@:keep public var baseScale(get, never):FlxPoint;",
            )
        )
        self.assertIn("baseScale(get, never)", declarations)
        self.assertIn("defScale(get, set)", declarations)
        methods = "\n".join(
            extract_method(note_source, marker)
            for marker in (
                "function get_baseScale()",
                "function set_defScale(value:FlxPoint)",
                "function get_defScale()",
            )
        )
        fixture = f'''
class FlxPoint {{
 public var x:Float;
 public var y:Float;
 public function new(x:Float, y:Float) {{ this.x = x; this.y = y; }}
 public static function get(x:Float = 0, y:Float = 0):FlxPoint return new FlxPoint(x, y);
 public function set(x:Float, y:Float):FlxPoint {{ this.x = x; this.y = y; return this; }}
 public function put():Void {{}}
}}

class Main {{
 var nightmareVisionBaseScalePoint:FlxPoint;
 var scale:FlxPoint;
 public function new():Void {{}}
 {declarations}
 {methods}

 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main() {{
  var note = new Main();
  note.scale = FlxPoint.get(0.6, 0.6);
  var legacy = note.defScale;
  check(legacy == note.baseScale, 'aliases did not resolve to one point');
  check(Reflect.getProperty(note, 'baseScale') == legacy,
   'reflection-backed script access did not resolve the property');
  legacy.set(0.7, 0.7);
  check(note.baseScale.x == 0.7 && note.baseScale.y == 0.7,
   'legacy mutation did not update source base scale');
  var replacement = FlxPoint.get(1.2, 1.4);
  note.defScale = replacement;
  check(note.defScale == legacy && note.baseScale == legacy
   && legacy.x == 1.2 && legacy.y == 1.4,
   'historical defScale assignment did not update the shared point');
  legacy.x = 0.4;
  check(note.baseScale.x == 0.4,
   'mutation through the canonical point was not visible through the alias');
 }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_registry_timeline_and_builtin_geometry_execute(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        if not FLIXEL.is_dir():
            self.skipTest("pinned Flixel 6.1.2 sources are unavailable")

        fixture = r'''
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModchartTimeline;
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartObject;
import nightmarevision.modchart.NightmareVisionModchartMath;
import nightmarevision.modchart.NightmareVisionModchartTransform;
import nightmarevision.modchart.NightmareVisionModchartVector;
import flixel.tweens.FlxEase;

class Main {
 static var randomState:Float = 1234567;
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function near(actual:Float, expected:Float, message:String, epsilon:Float = 0.0001):Void
  if (Math.isNaN(actual) || Math.abs(actual - expected) > epsilon)
   fail(message + ': expected ' + expected + ', got ' + actual);

 static function nextRandom():Float {
  randomState = (randomState * 48271) % 2147483647;
  return randomState / 2147483647;
 }

 static function referenceRotate(position:NightmareVisionModchartVector,
  originX:Float, originY:Float, height:Float,
  xAngle:Float, yAngle:Float, zAngle:Float):NightmareVisionModchartVector {
  var x = position.x - originX;
  var y = position.y - originY;
  var z = position.z * height;
  var x1 = x * Math.cos(zAngle) - y * Math.sin(zAngle);
  var y1 = x * Math.sin(zAngle) + y * Math.cos(zAngle);
  var x2 = z * Math.cos(xAngle) - y1 * Math.sin(xAngle);
  var y2 = z * Math.sin(xAngle) + y1 * Math.cos(xAngle);
  var x3 = x1 * Math.cos(yAngle) - x2 * Math.sin(yAngle);
  var z3 = x1 * Math.sin(yAngle) + x2 * Math.cos(yAngle);
  return new NightmareVisionModchartVector(originX + x3, originY + y2, z3 / height);
 }

 static function referencePerspective(position:NightmareVisionModchartVector,
  width:Float, height:Float):Void {
  if (Math.abs(position.z) < NightmareVisionModchartMath.EPSILON) return;
  var tangent = NightmareVisionModchartMath.fastSin(Math.PI / 4)
   / NightmareVisionModchartMath.fastCos(Math.PI / 4);
  var clipped = position.z - 1;
  if (clipped > 0) clipped = 0;
  var z = -clipped;
  position.x = (position.x - width / 2) / tangent / z + width / 2;
  position.y = (position.y - height / 2) / tangent / z + height / 2;
  position.z = z;
 }

 static function referenceRotation(registry:NightmareVisionModifierRegistry,
  ctx:NightmareVisionModchartContext, data:Int, player:Int, visualDiff:Float,
  rotationKind:Int):NightmareVisionModchartVector {
  var xAngle:Float;
  var yAngle:Float;
  var zAngle:Float;
  var originX = NightmareVisionModchartTransform.baseX(ctx, data, player);
  if (rotationKind == 1) {
   var root = 'centerrotateX';
   xAngle = registry.value(root, player);
   yAngle = registry.getSubmodValue(root, 'centerrotateY', player);
   zAngle = registry.getSubmodValue(root, 'centerrotateZ', player);
   originX = ctx.width * 0.5;
  } else if (rotationKind == 2) {
   var root = 'localrotateX';
   xAngle = registry.value(root, player) + registry.getSubmodValue(root, 'localrotate' + data + 'X', player);
   yAngle = registry.getSubmodValue(root, 'localrotateY', player)
    + registry.getSubmodValue(root, 'localrotate' + data + 'Y', player);
   zAngle = registry.getSubmodValue(root, 'localrotateZ', player)
    + registry.getSubmodValue(root, 'localrotate' + data + 'Z', player);
   originX = ctx.width * 0.5;
   var laneOffset = ctx.width * 0.5 - ctx.noteWidth * (ctx.keys / 2) - 100;
   originX += player == 0 ? laneOffset : -laneOffset;
  } else {
   var root = 'rotateX';
   xAngle = registry.value(root, player);
   yAngle = registry.getSubmodValue(root, 'rotateY', player);
   zAngle = registry.getSubmodValue(root, 'rotateZ', player);
  }
  var start = new NightmareVisionModchartVector(
   NightmareVisionModchartTransform.baseX(ctx, data, player),
   NightmareVisionModchartTransform.baseY(ctx.noteWidth) + visualDiff, 0);
  var rotationOriginX = rotationKind == 1 ? ctx.width * 0.5
   : (rotationKind == 2 ? originX : NightmareVisionModchartTransform.baseX(ctx, data, player));
  var result = referenceRotate(start, rotationOriginX, ctx.height * 0.5, ctx.height,
   xAngle, yAngle, zAngle);
  referencePerspective(result, ctx.width, ctx.height);
  return result;
 }

 static function main() {
  var registry = new NightmareVisionModifierRegistry(4);
  check(registry.isRegistered('reverse') && registry.isRegistered('transform3Z-a')
   && registry.isRegistered('noteSplashAlpha3') && registry.isRegistered('xmod3'),
   'source roots/submodifier families were not registered');
  check(!registry.isRegistered('scriptedExample') && registry.isRegistered('drunkZOffset'),
   'registered source submods or unsupported scripted names diverged');
  near(registry.value('noteSpawnTime', 0), 2000, 'source misc default');
  near(registry.value('xmod', 1), 1, 'source xmod default');
  check(registry.activeFamilies(0).join(',') == 'mini,reverse,confusion,stealth,xmod,perspectiveDONTUSE',
   'always-executed roots or source order changed');
  var playerZeroFamilies = registry.activeFamilies(0);
  var playerOneFamilies = registry.activeFamilies(1);
  check(playerZeroFamilies == registry.activeFamilies(0),
   'stable active root list was rebuilt for the same player');
  registry.setValue('drunk', 0.1, 0);
  var activeDrunkFamilies = registry.activeFamilies(0);
  check(activeDrunkFamilies != playerZeroFamilies && activeDrunkFamilies.indexOf('drunk') >= 0,
   'root activation did not invalidate the cached family list');
  registry.setValue('drunk', 0.25, 0);
  check(registry.activeFamilies(0) == activeDrunkFamilies,
   'continuous nonzero tween value rebuilt the active family list');
  check(registry.activeFamilies(1) == playerOneFamilies && playerOneFamilies.indexOf('drunk') < 0,
   'player-local activation invalidated another player list');
  registry.setValue('drunk', 0, 0);
  check(registry.activeFamilies(0) != activeDrunkFamilies
   && registry.activeFamilies(0).indexOf('drunk') < 0,
   'root deactivation did not invalidate the cached family list');
  var unsupported = false;
  try registry.setValue('madeUpMod', 1) catch (_:Dynamic) unsupported = true;
  check(unsupported, 'unsupported scripted modifier was accepted');

  // Same-step Set->Ease captures Set's new value, then uses the exact FlxEase.
  var timeline = new NightmareVisionModchartTimeline(registry);
  timeline.queueSet(2, 'drunk', 0.25);
  timeline.queueEase(2, 4, 'drunk', 1, 'quadOut');
  timeline.update(1.99);
  near(registry.value('drunk', 0), 0, 'future event ran early');
  timeline.update(2);
  near(registry.value('drunk', 0), 0.25, 'same-step ease did not capture current value');
  timeline.update(3);
  near(registry.value('drunk', 0), 0.8125, 'quadOut midpoint diverged from FlxEase');
  timeline.update(4);
  near(registry.value('drunk', 0), 1, 'ease endpoint was not inclusive');
  check(timeline.pendingCount() == 2, 'inclusive endpoint prematurely retired per-player events');
  timeline.update(4.01);
  near(registry.value('drunk', 1), 1, 'overdue per-player ease did not finish');
  check(timeline.pendingCount() == 0, 'finished ease was retained');
  timeline.queueEase(5, 7, 'drunk', 0, FlxEase.quadIn, 0);
  timeline.update(5);
  timeline.update(6);
  near(registry.value('drunk', 0), 0.75, 'direct EaseFunction was not called at normalized time');
  timeline.update(7);
  near(registry.value('drunk', 0), 0, 'direct EaseFunction endpoint diverged');
  var unknown = false;
  try timeline.queueSet(5, 'scriptedExample', 1) catch (_:Dynamic) unknown = true;
  check(unknown, 'unsupported modifier event was silently queued');

  var ctx = new NightmareVisionModchartContext(800, 600, 4, 112, 0, 0, 1, 500, false, false);
  var transform = new NightmareVisionModchartTransform(registry);
  registry.setValue('drunk', 0, 0);
  var note = new NightmareVisionModchartObject();
  note.player = 0;
  note.data = 0;
  note.width = 112;
  note.height = 112;
  var position = transform.getPosition(ctx, note, 100, 100, 0);
  near(position.x, 305, 'source lane-zero X');
  near(position.y, 206, 'source base Y plus visual delta');
  registry.setSubmodValue('drunk', 'drunkZOffset', 1, 0);
  position = transform.getPosition(ctx, note, 100, 100, 0);
  near(position.z, 0, 'registered but source-unused drunkZOffset had no effect');
  registry.setSubmodValue('drunk', 'drunkZOffset', 0, 0);

  registry.setValue('reverse', 1);
  position = transform.getPosition(ctx, note, 100, 100, 0);
  near(position.y, 394, 'reverse 100 percent geometry');
  registry.setValue('reverse', 0.5);
  position = transform.getPosition(ctx, note, 100, 100, 0);
  near(position.y, 300, 'reverse midpoint placement');
  registry.setValue('reverse', 0);
  var down = new NightmareVisionModchartContext(800, 600, 4, 112, 0, 0, 1, 500, true, false);
  position = transform.getPosition(down, note, 100, 100, 0);
  near(position.y, 394, 'downscroll reverse complement');

  registry.setValue('flip', 1);
  position = transform.getPosition(ctx, note, 0, 0, 0);
  near(position.x, 641, 'flip lane geometry');
  registry.setValue('flip', 0);
  registry.setValue('invert', 1);
  position = transform.getPosition(ctx, note, 0, 0, 0);
  near(position.x, 417, 'invert lane geometry');
  registry.setValue('invert', 0);

  registry.setValue('opponentSwap', 1);
  position = transform.getPosition(ctx, note, 0, 0, 0);
  near(position.x, 153, 'opponent swap source base-X exchange');
  registry.setValue('opponentSwap', 0);

  registry.setValue('drunk', 1);
  ctx = new NightmareVisionModchartContext(800, 600, 4, 112, 1000, 0, 1, 500, false, false);
  position = transform.getPosition(ctx, note, 0, 0, 0);
  near(position.x, 305 + NightmareVisionModchartMath.fastCos(1) * 56, 'drunk fastCos displacement');

  registry.setValue('drunk', 0);
  registry.setValue('tipsy', 1, 0);
  registry.setValue('tipsySpeed', 0.5, 0);
  ctx = new NightmareVisionModchartContext(800, 600, 4, 112, 1000, 0, 1, 500, false, false);
  position = transform.getPosition(ctx, note, 0, 0, 0);
  near(position.y, 106 + NightmareVisionModchartMath.fastCos(1.8) * 44.8, 'tipsy source displacement');
  registry.setValue('tipsy', 0, 0);

  registry.setValue('beat', 1, 0);
  ctx = new NightmareVisionModchartContext(800, 600, 4, 112, 0, 0.2, 1, 500, false, false);
  position = transform.getPosition(ctx, note, 0, 0, 0);
  near(position.x, 305 + 30 * NightmareVisionModchartMath.fastSin(Math.PI / 2), 'beat pulse geometry');
  registry.setValue('beat', 0, 0);

  registry.setValue('receptorScroll', 1, 0);
  ctx = new NightmareVisionModchartContext(800, 600, 4, 112, 1000, 0, 1, 500, false, false);
  position = transform.getPosition(ctx, note, 0, 0, 0);
  near(position.y, 50 + (438 - 56) * (1 - (1000 / 1500 - Math.floor(1000 / 1500))) + 56,
   'receptor-scroll source interpolation');
  registry.setValue('receptorScroll', 0, 0);

  registry.setValue('transformX', 5, 0);
  registry.setSubmodValue('transformX', 'transformY', 7, 0);
  position = transform.getPosition(ctx, note, 0, 0, 0);
  near(position.x, 310, 'transform-X root offset');
  near(position.y, 113, 'transform-Y global submod offset');
  registry.setValue('transformX', 0, 0);
  registry.setSubmodValue('transformX', 'transformY', 0, 0);

  registry.setSubmodValue('boost', 'wave', 1, 0);
  ctx = new NightmareVisionModchartContext(800, 600, 4, 112, 0, 0, 1, 500, false, false);
  position = transform.getPosition(ctx, note, 38, 38, 0);
  near(position.y, 144 + 20 * NightmareVisionModchartMath.fastSin(1), 'boost wave source displacement');
  registry.setSubmodValue('boost', 'wave', 0, 0);

  registry.setValue('rotateZ', Math.PI / 2, 0);
  position = transform.getPosition(ctx, note, 0, 0, 0);
  near(position.x, 499, 'rotate-Z around receptor axis');
  near(position.y, 300, 'rotate-Z source origin');
  registry.setValue('rotateZ', 0, 0);

  // Compare the allocation-free rotate paths with the former vector-based
  // equations over deterministic randomized inputs and all three origins.
  for (iteration in 0...45) {
   var rotationKind = iteration % 3;
   var player = iteration % 2;
   var data = iteration % 4;
   var visualDiff = (nextRandom() - 0.5) * 900;
   var xAngle = (nextRandom() - 0.5) * 5;
   var yAngle = (nextRandom() - 0.5) * 5;
   var zAngle = (nextRandom() - 0.5) * 5;
   var laneX = (nextRandom() - 0.5) * 2;
   var laneY = (nextRandom() - 0.5) * 2;
   var laneZ = (nextRandom() - 0.5) * 2;
   registry.setValue('rotateX', 0, player);
   registry.setSubmodValue('rotateX', 'rotateY', 0, player);
   registry.setSubmodValue('rotateX', 'rotateZ', 0, player);
   registry.setValue('centerrotateX', 0, player);
   registry.setSubmodValue('centerrotateX', 'centerrotateY', 0, player);
   registry.setSubmodValue('centerrotateX', 'centerrotateZ', 0, player);
   registry.setValue('localrotateX', 0, player);
   registry.setSubmodValue('localrotateX', 'localrotateY', 0, player);
   registry.setSubmodValue('localrotateX', 'localrotateZ', 0, player);
   for (lane in 0...4) for (axis in ['X', 'Y', 'Z'])
    registry.setSubmodValue('localrotateX', 'localrotate' + lane + axis, 0, player);
   if (rotationKind == 0) {
    registry.setValue('rotateX', xAngle, player);
    registry.setSubmodValue('rotateX', 'rotateY', yAngle, player);
    registry.setSubmodValue('rotateX', 'rotateZ', zAngle, player);
   } else if (rotationKind == 1) {
    registry.setValue('centerrotateX', xAngle, player);
    registry.setSubmodValue('centerrotateX', 'centerrotateY', yAngle, player);
    registry.setSubmodValue('centerrotateX', 'centerrotateZ', zAngle, player);
   } else {
    registry.setValue('localrotateX', xAngle, player);
    registry.setSubmodValue('localrotateX', 'localrotate' + data + 'X', laneX, player);
    registry.setSubmodValue('localrotateX', 'localrotateY', yAngle, player);
    registry.setSubmodValue('localrotateX', 'localrotate' + data + 'Y', laneY, player);
    registry.setSubmodValue('localrotateX', 'localrotateZ', zAngle, player);
    registry.setSubmodValue('localrotateX', 'localrotate' + data + 'Z', laneZ, player);
   }
   note.player = player;
   note.data = data;
   var actual = transform.getPosition(ctx, note, visualDiff, 0, ctx.beat);
   var expected = referenceRotation(registry, ctx, data, player, visualDiff, rotationKind);
   near(actual.x, expected.x, 'randomized rotate X parity');
   near(actual.y, expected.y, 'randomized rotate Y parity');
   near(actual.z, expected.z, 'randomized rotate Z parity');
  }
  registry.setValue('rotateX', 0, 0);
  registry.setSubmodValue('rotateX', 'rotateY', 0, 0);
  registry.setSubmodValue('rotateX', 'rotateZ', 0, 0);
  registry.setValue('centerrotateX', 0, 0);
  registry.setSubmodValue('centerrotateX', 'centerrotateY', 0, 0);
  registry.setSubmodValue('centerrotateX', 'centerrotateZ', 0, 0);
  registry.setValue('localrotateX', 0, 0);
  registry.setSubmodValue('localrotateX', 'localrotateY', 0, 0);
  registry.setSubmodValue('localrotateX', 'localrotateZ', 0, 0);
  for (lane in 0...4) for (axis in ['X', 'Y', 'Z'])
   registry.setSubmodValue('localrotateX', 'localrotate' + lane + axis, 0, 0);
  var ownedPosition = transform.getPosition(ctx, note, 0, 0, ctx.beat);
  var ownedX = ownedPosition.x;
  var scratchPosition = new NightmareVisionModchartVector(12, 34, 56);
  var scratchResult = transform.getPositionInto(ctx, note, 0, 0, ctx.beat, scratchPosition);
  check(scratchResult == scratchPosition, 'caller-owned position output was replaced');
  check(transform.getPosition(ctx, note, 0, 0, ctx.beat) != ownedPosition,
   'public getPosition no longer returns caller-owned storage');
  var inactiveObject = new NightmareVisionModchartObject();
  inactiveObject.active = false;
  scratchPosition.x = 99;
  scratchPosition.y = 88;
  scratchPosition.z = 77;
  transform.getPositionInto(ctx, inactiveObject, 0, 0, ctx.beat, scratchPosition);
  near(scratchPosition.x, 0, 'inactive scratch X was not reset');
  near(scratchPosition.y, 0, 'inactive scratch Y was not reset');
  near(scratchPosition.z, 0, 'inactive scratch Z was not reset');
  registry.setValue('flip', 0.25, 0);
  transform.getPositionInto(ctx, note, 0, 0, ctx.beat, scratchPosition);
  near(ownedPosition.x, ownedX, 'later scratch updates mutated a retained getPosition result');
  registry.setValue('flip', 0, 0);

  registry.setSubmodValue('transformX', 'transformZ', 0.5, 0);
  position = transform.getPosition(ctx, note, 0, 0, 0);
  near(position.x, 210, 'perspective X projection');
  near(position.y, -88, 'perspective Y projection');
  near(position.z, 0.5, 'perspective depth');
  registry.setSubmodValue('transformX', 'transformZ', 0, 0);

  var receptor = new NightmareVisionModchartObject(NightmareVisionModchartObject.RECEPTOR);
  receptor.player = 0;
  receptor.data = 0;
  receptor.width = 100;
  receptor.height = 100;
  registry.setValue('confusion', 30, 0);
  registry.setSubmodValue('confusion', 'noteAngle', 5, 0);
  registry.setSubmodValue('confusion', 'note0Angle', 10, 0);
  transform.updateObject(ctx, note, transform.getPosition(ctx, note, 0, 0, 0), 0);
  transform.updateObject(ctx, receptor, transform.getPosition(ctx, receptor, 0, 0, 0), 0);
  near(note.angle, 45, 'note confusion aggregate');
  near(receptor.angle, 30, 'receptor confusion aggregate');

  // Donor AlphaModifier's indexed splash lookup spelling does not match the
  // registered submod spelling; the unregistered per-lane lookup remains zero.
  var splash = new NightmareVisionModchartObject(NightmareVisionModchartObject.NOTE_SPLASH);
  splash.player = 0;
  splash.data = 0;
  registry.setSubmodValue('stealth', 'noteSplashAlpha0', 1, 0);
  transform.updateObject(ctx, splash, transform.getPosition(ctx, splash, 0, 0, 0), 0);
  near(splash.rgbAlpha, 1, 'source splash indexed-alpha lookup behavior');
  registry.setSubmodValue('stealth', 'noteSplashAlpha', 0.25, 0);
  transform.updateObject(ctx, splash, transform.getPosition(ctx, splash, 0, 0, 0), 0);
  near(splash.rgbAlpha, 0.75, 'source splash root-alpha multiplier');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(FLIXEL), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_renderer_snapshots_base_scale_hold_geometry_and_visual_state(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        if not FLIXEL.is_dir():
            self.skipTest("pinned Flixel 6.1.2 sources are unavailable")

        fixture = r'''
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartObject;
import nightmarevision.modchart.NightmareVisionModchartTransform;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
import nightmarevision.modchart.NightmareVisionModchartSkinOffsets;

@:access(nightmarevision.modchart.NightmareVisionModchartRenderer)
class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function near(actual:Float, expected:Float, message:String, epsilon:Float = 0.0001):Void
  if (Math.isNaN(actual) || Math.abs(actual - expected) > epsilon)
   fail(message + ': expected ' + expected + ', got ' + actual);

 static function fakeNote(isHold:Bool = false):Dynamic {
  var baseScale:Dynamic = {x:2.0, y:2.0};
  Reflect.setField(baseScale, 'set', function(x:Float, y:Float):Dynamic {
   Reflect.setField(baseScale, 'x', x);
   Reflect.setField(baseScale, 'y', y);
   return baseScale;
  });
  return {
   x:0.0, y:0.0, width:50.0, height:100.0, frameWidth:50.0, frameHeight:100.0,
   scale:{x:2.0, y:2.0}, baseScale:baseScale, defScale:baseScale,
   offset:{x:0.0, y:0.0}, origin:{x:0.0, y:0.0},
   active:true, noteData:0, direction:2, ID:3, strumTime:900.0, multSpeed:1.0,
   isSustainNote:isHold, isSustainEnd:false, wasGoodHit:isHold,
   antialiasing:true, alpha:0.6, animation:{curAnim:{name:isHold ? 'hold' : 'Scroll'}},
   centerOrigin:function():Void {}, centerOffsets:function():Void {}
  };
 }

 static function main() {
  check(NightmareVisionModchartRenderer.number(42, -1) == 42,
   'native integer snapshot value changed');
  var preciseFloat:Float = 0.12345678901234566;
  check(NightmareVisionModchartRenderer.number(preciseFloat, -1) == preciseFloat,
   'native float snapshot value lost precision');
  near(NightmareVisionModchartRenderer.number('6.25', -1), 6.25,
   'numeric string snapshot fallback');
  near(NightmareVisionModchartRenderer.number(null, 7), 7,
   'null snapshot fallback');
  near(NightmareVisionModchartRenderer.number('invalid', -8), -8,
   'malformed string snapshot fallback');
  near(NightmareVisionModchartRenderer.number(Math.NaN, 9), 9,
   'NaN snapshot fallback');
  near(NightmareVisionModchartRenderer.number(Math.POSITIVE_INFINITY, 10), 10,
   'infinite snapshot fallback');

  var registry = new NightmareVisionModifierRegistry(4);
  var transform = new NightmareVisionModchartTransform(registry);
  var skin = {
   noteOffsets:[[3.0, 4.0]], receptorOffsets:[[7.0, 8.0]],
   sustainOffsets:[[5.0, 6.0]], susEndOffsets:[[9.0, 10.0]],
   splashOffsets:[[11.0, 12.0]], sustainSplashOffsets:[[13.0, 14.0]]
  };
  var offsets = new NightmareVisionModchartSkinOffsets(4, skin);
  var applied = 0;
  var unsupported:Array<String> = [];
  var renderer = new NightmareVisionModchartRenderer(transform, offsets,
   function(sprite, state):Void applied++, function(message:String):Void unsupported.push(message));
  var ctx = new NightmareVisionModchartContext(800, 600, 4, 112, 0, 0, 1, 500, false, false);
  var note = fakeNote();
  renderer.configureNote(note);
  registry.setValue('mini', 0.5, 0);
  registry.setValue('stealth', 0.4, 0);
  var visual = renderer.updateNote(ctx, note, 0, 0, 0, 0, 0, 0);
  near(note.scale.x, 1, 'mini scale used captured source baseline');
  near(note.scale.y, 1, 'mini Y scale used captured source baseline');
  near(visual.baseScaleX, 2, 'visual state retained unmodified source base scale X');
  near(visual.baseScaleY, 2, 'visual state retained unmodified source base scale Y');
  near(note.alpha, 0.6, 'source alphaMod was not incorrectly copied into FlxSprite.alpha');
  near(visual.alphaMod, 1, 'source alpha transform retained');
  check(visual.rgbFlash > 0, 'source stealth glow result was dropped');
  check(applied == 1, 'owner-local visual bridge was not called');
  check(unsupported.length == 0, 'active visual bridge still reported unsupported glow');
  near(visual.spriteOffsetX, 3, 'tap note offsets exclude sustain offsets');
  near(visual.spriteOffsetY, 4, 'tap note Y offsets exclude sustain offsets');
  near(visual.position.x, NightmareVisionModchartTransform.baseX(ctx, 0, 0),
   'valid noteData zero did not precede direction and ID fallbacks');

  var fallbackNote = fakeNote();
  fallbackNote.noteData = 'invalid';
  fallbackNote.direction = '0';
  fallbackNote.offsetX = 'invalid';
  fallbackNote.typeOffsetX = '7';
  fallbackNote.offsetY = null;
  fallbackNote.typeOffsetY = '-4.5';
  renderer.configureNote(fallbackNote);
  var fallbackVisual = renderer.updateNote(ctx, fallbackNote, 0, 0, 0, 0, 0, 0);
  near(fallbackVisual.position.x, NightmareVisionModchartTransform.baseX(ctx, 0, 0),
   'malformed primary lane did not fall through to numeric-string direction');
  near(fallbackVisual.spriteOffsetX, 10, 'malformed offset did not use numeric-string fallback');
  near(fallbackVisual.spriteOffsetY, -0.5, 'null offset did not use numeric-string fallback');
  fallbackNote.noteData = null;
  fallbackVisual = renderer.updateNote(ctx, fallbackNote, 0, 0, 0, 0, 0, 0);
  near(fallbackVisual.position.x, NightmareVisionModchartTransform.baseX(ctx, 0, 0),
   'null primary lane did not fall through to direction');
  fallbackNote.offsetX = '6.25';
  fallbackNote.offsetY = '2.5';
  fallbackVisual = renderer.updateNote(ctx, fallbackNote, 0, 0, 0, 0, 0, 0);
  near(fallbackVisual.spriteOffsetX, 9.25, 'numeric-string primary offset did not precede fallback');
  near(fallbackVisual.spriteOffsetY, 6.5, 'numeric-string primary Y offset did not precede fallback');
  renderer.release(fallbackNote);

  var retainedPosition = visual.position;
  var retainedPositionX = retainedPosition.x;
  renderer.updateNote(ctx, note, 0, 0, 0, 0, 0, 0);
  near(note.scale.x, 1, 'repeated frame compounded mini scale');
  near(note.scale.y, 1, 'repeated frame compounded mini Y scale');
  registry.setValue('flip', 0.25, 0);
  visual = renderer.updateNote(ctx, note, 0, 0, 0, 0, 0, 0);
  check(visual.position != retainedPosition,
   'renderer mutated a retained visual-state position instead of replacing its snapshot');
  near(retainedPosition.x, retainedPositionX,
   'later renderer updates mutated a retained visual-state position');
  registry.setValue('flip', 0, 0);
  registry.setValue('mini', 0, 0);
  registry.setValue('stealth', 0, 0);
  visual = renderer.updateNote(ctx, note, 0, 0, 0, 0, 0, 0);
  near(visual.alphaMod, 1, 'reused render snapshot retained stale stealth alpha');
  near(visual.rgbFlash, 0, 'reused render snapshot retained stale stealth glow');
  near(note.scale.x, 2, 'reused render snapshot retained stale mini scale');
  registry.setValue('mini', 0.5, 0);
  registry.setValue('stealth', 0.4, 0);

  // Historical note scripts call defScale.set() before renderer setup. The
  // current source uses baseScale for the same mutable baseline, and scripts
  // may continue tweening it after setup.
  var legacyScaleNote = fakeNote();
  legacyScaleNote.defScale.set(0.7, 0.7);
  check(legacyScaleNote.baseScale == legacyScaleNote.defScale,
   'legacy defScale and source baseScale did not share one point');
  renderer.configureNote(legacyScaleNote);
  visual = renderer.updateNote(ctx, legacyScaleNote, 0, 0, 0, 0, 0, 0);
  near(legacyScaleNote.scale.x, 0.35, 'pre-config defScale was ignored for X');
  near(legacyScaleNote.scale.y, 0.35, 'pre-config defScale was ignored for Y');
  near(visual.baseScaleX, 0.7, 'pre-config source baseline X was not exposed');
  legacyScaleNote.baseScale.set(1.2, 1.4);
  visual = renderer.updateNote(ctx, legacyScaleNote, 0, 0, 0, 0, 0, 0);
  near(legacyScaleNote.scale.x, 0.6, 'post-config baseScale change was not observed on X');
  near(legacyScaleNote.scale.y, 0.7, 'post-config baseScale change was not observed on Y');
  near(visual.baseScaleX, 1.2, 'post-config baseScale X was stale');
  near(visual.baseScaleY, 1.4, 'post-config baseScale Y was stale');

  var warned = 0;
  var noBridge = new NightmareVisionModchartRenderer(transform, offsets, null,
   function(message:String):Void if (message.indexOf('stealthGlow') >= 0) warned++);
  var noBridgeNote = fakeNote();
  noBridge.configureNote(noBridgeNote);
  noBridge.updateNote(ctx, noBridgeNote, 0, 0, 0, 0, 0, 0);
  noBridge.updateNote(ctx, noBridgeNote, 0, 0, 0, 0, 0, 0);
  check(warned == 1, 'unsupported active glow was not diagnosed once');

  // A source sustain segment's tail geometry determines angle, scale, and clip.
  registry.setValue('mini', 0, 0);
  registry.setValue('stealth', 0, 0);
  ctx = new NightmareVisionModchartContext(800, 600, 4, 112, 1000, 0, 1, 500, false, false);
  registry.setValue('rotateX', 0.27, 0);
  registry.setSubmodValue('rotateX', 'rotateY', -0.14, 0);
  registry.setSubmodValue('rotateX', 'rotateZ', 0.31, 0);
  var rotatedHold = fakeNote(true);
  renderer.configureNote(rotatedHold);
  var holdObject = new NightmareVisionModchartObject();
  holdObject.player = 0;
  holdObject.data = 0;
  var expectedHead = transform.getPosition(ctx, holdObject, 15, 0, ctx.beat);
  var expectedTail = transform.getPosition(ctx, holdObject, 145, 120, 0);
  var expectedHoldAngle = Math.atan2(expectedTail.y - expectedHead.y,
   expectedTail.x - expectedHead.x) * 180 / Math.PI - 90;
  var expectedHoldDistance = Math.sqrt(Math.pow(expectedTail.x - expectedHead.x, 2)
   + Math.pow(expectedTail.y - expectedHead.y, 2));
  visual = renderer.updateNote(ctx, rotatedHold, 0, 15, 0, 145, 120, 0,
   {x:250.0, y:100.0, width:112.0, height:100.0, sustainReduce:false}, 125, false);
  near(visual.position.x, expectedHead.x, 'sustain scratch retained transformed head X');
  near(visual.position.y, expectedHead.y, 'sustain scratch retained transformed head Y');
  near(visual.holdAngle, expectedHoldAngle, 'sustain tail used its independent transformed endpoint');
  near(visual.holdSegmentDistance, expectedHoldDistance,
   'sustain geometry used both independently transformed endpoints');
  renderer.release(rotatedHold);
  registry.setValue('rotateX', 0, 0);
  registry.setSubmodValue('rotateX', 'rotateY', 0, 0);
  registry.setSubmodValue('rotateX', 'rotateZ', 0, 0);

  var hold = fakeNote(true);
  renderer.configureNote(hold);
  var strum = {x:250.0, y:100.0, width:112.0, height:100.0, sustainReduce:true};
  visual = renderer.updateNote(ctx, hold, 0, 0, 0, 100, 100, 0, strum, 125, false);
  near(visual.holdAngle, 0, 'source tail angle');
  near(hold.angle, 0, 'tail angle copied to live note');
  near(visual.holdSegmentDistance, 100, 'source endpoint distance');
  near(visual.holdSegmentDuration, 125, 'exact source sustain segment duration was retained');
  check(!visual.isSustainEnd, 'explicit source body-segment flag was ignored');
  near(hold.scale.y, 100 / 99, 'source hold body height formula');
  near(visual.baseScaleY, 100 / 99, 'source hold baseline scale was exposed for draw offsets');
  check(visual.clipApplied, 'source sustain clip did not run');
  near(visual.clipY, Math.sqrt(44 * 44 + 1) / (100 / 99), 'source clip distance formula');
  near(visual.clipWidth, 50, 'source clip frame width');
  near(hold.clipRect.y, visual.clipY, 'clip rectangle copied to live sprite');
  near(visual.spriteOffsetX, 8, 'source sustain base/type offsets');
  near(visual.spriteOffsetY, 10, 'source sustain Y offsets');

  var firstClipY = visual.clipY;
  var firstHoldScale = hold.scale.y;
  visual = renderer.updateNote(ctx, hold, 0, 0, 0, 100, 100, 0, strum, 125, false);
  near(hold.scale.y, firstHoldScale, 'repeated source hold update compounded scale');
  near(visual.clipY, firstClipY, 'repeated source clip did not reset its geometry');
  near(hold.clipRect.height, hold.frameHeight - firstClipY,
   'repeated source clip retained a prior reduced rectangle height');

  registry.setValue('mini', 0.5, 0);
  var holdEnd = fakeNote(true);
  holdEnd.animation.curAnim.name = 'holdend';
  renderer.configureNote(holdEnd);
  visual = renderer.updateNote(ctx, holdEnd, 0, 0, 0, 0, 0, 0, strum, 125, true);
  check(visual.isSustainEnd, 'explicit source sustain-end flag was ignored');
  near(holdEnd.scale.y, 1, 'hold-end scale was incorrectly stretched as a body');
  near(visual.spriteOffsetX, 17, 'source sustain-end offset');
  near(visual.spriteOffsetY, 20, 'source sustain-end Y offset');

  renderer.release(hold);
  check(renderer.visualState(hold) == null, 'retired note snapshot was retained');
  renderer.configureNote(hold);
  check(renderer.visualState(hold) != null, 'released note could not be configured again');
  renderer.release(holdEnd);
  renderer.destroy();
  check(renderer.visualState(hold) == null, 'renderer teardown retained note snapshots');
  check(renderer.applyVisual == null && renderer.onUnsupportedFeature == null
   && renderer.skinOffsets.readLive == null, 'renderer teardown retained scene callbacks');

  var receptor = {x:0.0, y:0.0, width:100.0, height:100.0, frameWidth:100.0,
   frameHeight:100.0, scale:{x:1.0, y:1.0}, offset:{x:0.0, y:0.0}, origin:{x:0.0, y:0.0},
   active:true, noteData:0, ID:0, animation:{curAnim:{name:'static'}},
   centerOrigin:function():Void {}, centerOffsets:function():Void {}};
  renderer.configureReceptor(receptor);
  visual = renderer.updateReceptor(ctx, receptor, 0);
  near(visual.spriteOffsetX, 7, 'receptor source offsets');
  var splash = {x:0.0, y:0.0, width:30.0, height:30.0, frameWidth:30.0, frameHeight:30.0,
   scale:{x:1.0, y:1.0}, offset:{x:0.0, y:0.0}, origin:{x:0.0, y:0.0},
   active:true, direction:0, animation:{curAnim:{name:'note0-0'}},
   centerOrigin:function():Void {}, centerOffsets:function():Void {}};
  renderer.configureSplash(splash);
  visual = renderer.updateSplash(ctx, splash, 'noteSplash', 0, 0);
  near(visual.spriteOffsetX, 11, 'note splash source offsets');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(FLIXEL), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_registry_and_formula_names_are_backed_by_supplied_source(self):
        if not DONOR.is_dir():
            self.skipTest("supplied Nightmare Vision source tree is unavailable")
        registry = (ROOT / "source/nightmarevision/modchart/NightmareVisionModifierRegistry.hx").read_text()
        transform = (ROOT / "source/nightmarevision/modchart/NightmareVisionModchartTransform.hx").read_text()
        manager = (DONOR / "ModManager.hx").read_text()
        families = {
            "reverse": "ReverseModifier",
            "confusion": "ConfusionModifier",
            "perspectiveDONTUSE": "PerspectiveModifier",
            "opponentSwap": "OpponentModifier",
            "flip": "FlipModifier",
            "invert": "InvertModifier",
            "drunk": "DrunkModifier",
            "beat": "BeatModifier",
            "stealth": "AlphaModifier",
            "receptorScroll": "ReceptorScrollModifier",
            "mini": "ScaleModifier",
            "transformX": "TransformModifier",
            "infinite": "InfinitePathModifier",
            "boost": "AccelModifier",
            "xmod": "XModifier",
            "rotateX": "RotateModifier",
            "localrotateX": "LocalRotateModifier",
        }
        for name, source_class in families.items():
            with self.subTest(name=name):
                self.assertIn("'" + name + "'", registry)
                self.assertTrue(any(source_class in line for line in manager.splitlines()))
        for formula in [
            "applyReverse", "applyOpponentSwap", "applyFlip", "applyInvert", "applyDrunk",
            "applyBeat", "applyReceptorScroll", "applyTransform", "applyInfinitePath",
            "applyBoost", "applyRotate", "applyLocalRotate", "applyPerspective",
            "applyConfusion", "applyAlpha", "applyScale", "applyXMod",
        ]:
            self.assertIn(formula, transform)

        alpha = (DONOR / "modifiers/AlphaModifier.hx").read_text()
        self.assertIn("'noteSplashAlpha$i'", alpha)
        self.assertIn("'noteSplash${splash.noteData}Alpha'", alpha)
        self.assertIn("'sustainSplash${splash.noteData}Alpha'", alpha)
        self.assertIn("'noteSplash' + object.data + 'Alpha'", transform)
        self.assertIn("'sustainSplash' + object.data + 'Alpha'", transform)


if __name__ == "__main__":
    unittest.main()
