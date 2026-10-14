"""The Nightmare Vision note path reuses its per-call objects without changing results."""
from haxe_test_support import HAXE_COMMAND, FixturePath

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"


def run_fixture(test, name, body):
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
        work = Path(directory)
        (work / (name + ".hx")).write_text(body, encoding="utf-8", newline="\n")
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(FixturePath(SOURCE)), "-cp", str(FixturePath(work)),
             "--main", name, "--interp"],
            cwd=work, capture_output=True, text=True, timeout=120,
        )
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class NightmareVisionModchartAllocationTest(unittest.TestCase):
    def test_object_reset_matches_a_new_object(self):
        run_fixture(self, "ObjectResetFixture", r'''
import nightmarevision.modchart.NightmareVisionModchartObject;
import nightmarevision.modchart.NightmareVisionModchartVector;
class ObjectResetFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var fields = Type.getInstanceFields(NightmareVisionModchartObject).filter(function(name)
   return !Reflect.isFunction(Reflect.field(new NightmareVisionModchartObject(), name)) || name == 'flushLive'
    || name == 'readLive' || name == 'legacyClip' || name == 'legacySpeed');
  if (fields.length < 40) fail('expected every carrier field, saw ' + fields.length);
  for (kind in [null, 'receptor']) {
   var used = new NightmareVisionModchartObject('noteSplash');
   // Dirty every field with a value no default has.
   for (name in fields) {
    var current:Dynamic = Reflect.field(used, name);
    var dirty:Dynamic = switch (Type.typeof(current)) {
     case TBool: !current;
     case TInt, TFloat: 37.5;
     case TClass(String): 'dirty';
     default: name == 'livePosition' ? new NightmareVisionModchartVector(1, 2, 3)
      : name == 'nativeObject' ? {x:1} : function() {};
    };
    if (Type.typeof(current) == TNull && (name == 'flushLive' || name == 'readLive')) dirty = function() {};
    if (Type.typeof(current) == TNull && (name == 'legacyClip')) dirty = function(a:Float, b:Float) {};
    if (Type.typeof(current) == TNull && (name == 'legacySpeed')) dirty = function(a:Float) {};
    Reflect.setField(used, name, dirty);
   }
   var reset = used.reset(kind);
   if (reset != used) fail('reset must return the same carrier');
   var fresh = new NightmareVisionModchartObject(kind);
   for (name in fields) {
    var a:Dynamic = Reflect.field(reset, name);
    var b:Dynamic = Reflect.field(fresh, name);
    if (a != b) fail('field ' + name + ' after reset is ' + Std.string(a) + ', a new carrier has ' + Std.string(b));
   }
  }
 }
}
''')

    def test_context_reuse_only_returns_identical_values(self):
        run_fixture(self, "ContextReuseFixture", r'''
import nightmarevision.modchart.NightmareVisionModchartContext;
class ContextReuseFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var first = NightmareVisionModchartContext.reuse(null, 1280, 720, 4, 112, 1000, 2.5, 1.8, 500, false, false, true, 150);
  var again = NightmareVisionModchartContext.reuse(first, 1280, 720, 4, 112, 1000, 2.5, 1.8, 500, false, false, true, 150);
  if (again != first) fail('identical values built a new context');
  // keys below one are stored as one, so asking for zero again still matches.
  var clamped = NightmareVisionModchartContext.reuse(null, 1280, 720, 0, 112);
  if (NightmareVisionModchartContext.reuse(clamped, 1280, 720, 0, 112) != clamped) fail('clamped keys did not match');
  if (clamped.keys != 1) fail('keys were not clamped');
  // Every value is part of the match.
  var changed = [
   NightmareVisionModchartContext.reuse(first, 1281, 720, 4, 112, 1000, 2.5, 1.8, 500, false, false, true, 150),
   NightmareVisionModchartContext.reuse(first, 1280, 721, 4, 112, 1000, 2.5, 1.8, 500, false, false, true, 150),
   NightmareVisionModchartContext.reuse(first, 1280, 720, 5, 112, 1000, 2.5, 1.8, 500, false, false, true, 150),
   NightmareVisionModchartContext.reuse(first, 1280, 720, 4, 113, 1000, 2.5, 1.8, 500, false, false, true, 150),
   NightmareVisionModchartContext.reuse(first, 1280, 720, 4, 112, 1001, 2.5, 1.8, 500, false, false, true, 150),
   NightmareVisionModchartContext.reuse(first, 1280, 720, 4, 112, 1000, 2.6, 1.8, 500, false, false, true, 150),
   NightmareVisionModchartContext.reuse(first, 1280, 720, 4, 112, 1000, 2.5, 1.9, 500, false, false, true, 150),
   NightmareVisionModchartContext.reuse(first, 1280, 720, 4, 112, 1000, 2.5, 1.8, 501, false, false, true, 150),
   NightmareVisionModchartContext.reuse(first, 1280, 720, 4, 112, 1000, 2.5, 1.8, 500, true, false, true, 150),
   NightmareVisionModchartContext.reuse(first, 1280, 720, 4, 112, 1000, 2.5, 1.8, 500, false, true, true, 150),
   NightmareVisionModchartContext.reuse(first, 1280, 720, 4, 112, 1000, 2.5, 1.8, 500, false, false, false, 150),
   NightmareVisionModchartContext.reuse(first, 1280, 720, 4, 112, 1000, 2.5, 1.8, 500, false, false, true, 151)];
  for (i in 0...changed.length) if (changed[i] == first) fail('value ' + i + ' changed but the old context came back');
  var moved = changed[4];
  if (moved.songPosition != 1001 || moved.beat != 2.5) fail('new context lost its values');
  // NaN never equals itself, so a NaN input always gets a fresh context.
  var nan = NightmareVisionModchartContext.reuse(null, 1280, 720, 4, 112, Math.NaN);
  if (NightmareVisionModchartContext.reuse(nan, 1280, 720, 4, 112, Math.NaN) == nan) fail('NaN position was reused');
 }
}
''')

    def test_builtin_position_names_match_the_old_list(self):
        run_fixture(self, "CatalogFixture", r'''
class CatalogFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var old = ['reverse','perspectiveDONTUSE','opponentSwap','flip','invert','drunk','beat','receptorScroll',
   'transformX','infinite','path','boost','rotateX','localrotateX'];
  for (name in old) if (!NightmareVisionBuiltinCatalog.hasPosition(name)) fail(name + ' lost its position pass');
  for (name in ['stealth', 'mini', 'xmod', 'confusion', 'centerrotateX', 'Reverse', '', null])
   if (NightmareVisionBuiltinCatalog.hasPosition(name)) fail(Std.string(name) + ' gained a position pass');
 }
}
''')

    def test_position_pass_reads_the_sprite_once_for_read_only_modifiers(self):
        run_fixture(self, "ReadOnlyPassFixture", r'''
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModifierRegistry.NightmareVisionModifierExecution;
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartObject;
import nightmarevision.modchart.NightmareVisionModchartTransform;
import nightmarevision.modchart.NightmareVisionModchartVector;
class ReadOnlyPassFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var registry = new NightmareVisionModifierRegistry(4, 2, false);
  var log:Array<String> = [];
  var entries = new Map<String, NightmareVisionModifierExecution>();
  function entry(name:String, readsOnly:Null<Bool>):NightmareVisionModifierExecution {
   var made:NightmareVisionModifierExecution = {builtin:null,
    getPosition:function(time, diff, tDiff, beat, pos:NightmareVisionModchartVector, data, player, obj) {
     log.push(name); pos.x += 1; return pos;
    },
    updateObject:function(beat, obj, pos, player, kind) {}};
   if (readsOnly != null) made.positionReadsOnly = readsOnly;
   entries.set(name, made);
   return made;
  }
  entry('a', true); entry('b', true); entry('script', false); entry('c', true); entry('d', null); entry('e', true);
  var order = ['a', 'b', 'script', 'c', 'd', 'e'];
  registry.executionNames = function(player) return order;
  registry.executionEntry = function(name) return entries.get(name);
  var transform = new NightmareVisionModchartTransform(registry);
  var object = new NightmareVisionModchartObject('note');
  object.nativeObject = {active:true};
  object.readLive = function() log.push('read');
  var context = new NightmareVisionModchartContext(1280, 720, 4, 112);
  var pos = transform.getPositionInto(context, object, 0, 0, 0, new NightmareVisionModchartVector());
  // The first read-only modifier still refreshes, a second in a row has nothing
  // new to read, a script may write so it always refreshes, and so does an
  // entry that does not say it only reads.
  var expected = ['a', 'read', 'b', 'script', 'read', 'c', 'd', 'read', 'e'];
  if (log.join(',') != expected.join(',')) fail('read order was ' + log.join(',') + ', expected ' + expected.join(','));
  if (pos.x != NightmareVisionModchartTransform.baseX(context, 0, 0) + 6) fail('a modifier was skipped');
 }
}
''')

    def test_renderer_reuses_formula_carriers_and_skips_refused_fields(self):
        renderer = (SOURCE / "nightmarevision/modchart/NightmareVisionModchartRenderer.hx").read_text(encoding="utf-8")
        # The per-call formula carriers come from the depth pool, never from new.
        apply_position = renderer.split("public function applyInstancePosition(", 1)[1].split("\n\t}\n", 1)[0]
        apply_object = renderer.split("public function applyInstanceObject(", 1)[1].split("\n\t}\n", 1)[0]
        for body in (apply_position, apply_object):
            self.assertIn("borrowInstanceObject(kind)", body)
            self.assertNotIn("new NightmareVisionModchartObject", body)
            self.assertIn("releaseInstanceObject(object)", body)
        run_fixture(self, "RendererPoolFixture", r'''
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModchartObject;
import nightmarevision.modchart.NightmareVisionModchartTransform;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
class Refuses {
 public var x:Float = 0;
 public function new() {}
}
@:access(nightmarevision.modchart.NightmareVisionModchartRenderer)
class RendererPoolFixture {
 static function fail(message:String):Void throw message;
 static function main() {
  var renderer = new NightmareVisionModchartRenderer(new NightmareVisionModchartTransform(new NightmareVisionModifierRegistry(4)));
  var outer = renderer.borrowInstanceObject('note');
  outer.x = 5;
  var inner = renderer.borrowInstanceObject('receptor');
  if (inner == outer) fail('a nested formula call shared its caller carrier');
  if (outer.x != 5) fail('borrowing a nested carrier reset the outer one');
  if (inner.kind != 'receptor') fail('kind not applied');
  inner.nativeObject = {};
  renderer.releaseInstanceObject(inner);
  if (inner.nativeObject != null) fail('a released carrier kept its sprite');
  renderer.releaseInstanceObject(outer);
  var again = renderer.borrowInstanceObject('note');
  if (again != outer) fail('the carrier was not reused');
  if (again.x != 0) fail('a reused carrier kept old values');
  renderer.releaseInstanceObject(again);
  if (renderer.instanceDepth != 0) fail('depth did not return to zero');

  // A class without the field refuses it (hxcpp throws); the renderer stops trying.
  var writes = 0;
  NightmareVisionModchartRenderer.fieldWriter = function(target:Dynamic, name:String, value:Dynamic):Void {
   writes++;
   if (Type.getClass(target) != null) throw 'Invalid field:' + name;
   Reflect.setField(target, name, value);
  };
  var refused = new Refuses();
  var plain:Dynamic = {};
  NightmareVisionModchartRenderer.writeSourceOffset(refused, 1.5, 2.5);
  NightmareVisionModchartRenderer.writeSourceOffset(refused, 1.5, 2.5);
  NightmareVisionModchartRenderer.writeSourceOffset(new Refuses(), 1.5, 2.5);
  if (writes != 1) fail('a refusing class was asked ' + writes + ' times');
  NightmareVisionModchartRenderer.writeSourceOffset(plain, 1.5, 2.5);
  NightmareVisionModchartRenderer.writeSourceOffset(plain, 3.5, 4.5);
  if (writes != 5) fail('a plain object was not written every time');
  if (Reflect.field(plain, 'nightmareVisionSourceOffsetY') != 4.5) fail('a plain object lost its latest offset');
  if (Reflect.field(plain, 'nightmareVisionSourceOffsetX') != 3.5) fail('a plain object lost its source offset');
 }
}
''')


if __name__ == "__main__":
    unittest.main()
