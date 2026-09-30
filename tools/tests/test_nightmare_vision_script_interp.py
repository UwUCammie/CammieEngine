"""Run the NMV name-resolution adapter against the pinned HScript runtime."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class NightmareVisionScriptInterpTest(unittest.TestCase):
    def test_parent_shared_and_import_name_resolution(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
class Actor {
 public var counter:Int = 0;
 public var flag:Bool = false;
 public var nullable:Dynamic = null;
 public var shadow:Int = 4;
 public var imported:Dynamic = 'parent-import';
 public var importNull:Dynamic = 'parent-null';
 var propertyValue:Int = 8;
 public var property(get, set):Int;
 public function new() {}
 function get_property():Int return propertyValue;
 function set_property(value:Int):Int { propertyValue = value; return value; }
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function run(interp:NightmareVisionScriptInterp,
  parser:NightmareVisionScriptParser, source:String):Void
  interp.execute(parser.parseString(source));
 static function main():Void {
  var actor = new Actor();
  var shared:Map<String, Dynamic> = [
   'counter' => 300, 'shadow' => 900, 'imported' => 'shared-import',
   'importNull' => 'shared-null', 'sharedCounter' => 3,
   'sharedZero' => 0, 'sharedFalse' => false, 'sharedNull' => null
  ];
  var interp = new NightmareVisionScriptInterp(actor, shared);
  interp.variables.set('shadow', 0);
  interp.variables.set('presetNull', null);
  interp.variables.set('presetFalse', false);
  interp.imports.set('imported', 'import-map');
  interp.imports.set('importNull', null);

  var parser = new NightmareVisionScriptParser();
  run(interp, parser,
   'selectedShadow=shadow; shadow=2; selectedImported=imported; '
   + 'selectedImportNull=importNull; selectedPresetNull=presetNull; '
   + 'selectedPresetFalse=presetFalse; presetFalse=true; '
   + 'counter += 4; prefixValue=++counter; postfixValue=counter++; '
   + 'parentFlagBefore=flag; flag=!flag; parentNullBefore=nullable==null; nullable=12; '
   + 'sharedCounter += 2; prefixShared=++sharedCounter; postfixShared=sharedCounter++; '
   + 'sharedZeroSeen=sharedZero; sharedFalseSeen=sharedFalse; sharedNullSeen=sharedNull; '
   + 'property += 2;');

  check(interp.variables.get('selectedShadow') == 0 && interp.variables.get('shadow') == 2
   && actor.shadow == 4 && shared.get('shadow') == 900,
   'preset value 0 did not shadow parent/shared fields on read and write');
  check(interp.variables.get('selectedImported') == 'import-map'
   && interp.variables.get('selectedImportNull') == null,
   'imports did not resolve after presets and before parent/shared, including null');
  check(interp.variables.get('selectedPresetNull') == null
   && interp.variables.get('selectedPresetFalse') == false
   && interp.variables.get('presetFalse') == true,
   'preset lookup/write lost null or false values');
  check(actor.counter == 6 && interp.variables.get('prefixValue') == 5
   && interp.variables.get('postfixValue') == 5 && shared.get('counter') == 300,
   'prefix/postfix or compound assignment did not write through to the parent');
  check(interp.variables.get('parentFlagBefore') == false && actor.flag == true,
   'false parent field was not resolved and written through');
  check(interp.variables.get('parentNullBefore') == true && actor.nullable == 12,
   'null parent field was not resolved as present and writable');
  check(actor.property == 10,
   'computed parent property did not use its discovered getter/setter');
  check(shared.get('sharedCounter') == 7 && interp.variables.get('prefixShared') == 6
   && interp.variables.get('postfixShared') == 6,
   'shared field compound/prefix/postfix updates did not retain donor semantics');
  check(interp.variables.get('sharedZeroSeen') == 0
   && interp.variables.get('sharedFalseSeen') == false
   && interp.variables.exists('sharedNullSeen') && interp.variables.get('sharedNullSeen') == null,
   'shared lookup did not preserve zero, false, or null');

  run(interp, parser, 'sharedCounter=9;');
  check(shared.get('sharedCounter') == 9 && interp.variables.get('sharedCounter') == 9,
   'plain shared assignment did not update the shared slot and materialize a preset');
  run(interp, parser, 'var counter=40; counter+=1; counter=42; localCounter=counter;');
  check(interp.variables.get('localCounter') == 42 && interp.variables.get('counter') == 42
   && actor.counter == 6,
   'local assignment did not retain local precedence and donor preset materialization');
  run(interp, parser, 'counter+=1; postLocalShadow=counter;');
  check(interp.variables.get('postLocalShadow') == 43 && actor.counter == 6,
   'materialized local did not become a higher-priority preset on the next execution');

  // Exercise the donor-facing declaration syntax through the separate NMV
  // parser adapter, which lowers `public` to the shared-field metadata AST.
  run(interp, parser, 'public var published = 11;');
  check(shared.get('published') == 11, 'top-level sharable variable was not published');
  run(interp, parser, 'public function triple(value) return value * 3;');
  check(shared.exists('triple'), 'top-level sharable function was not published');
  var other = new NightmareVisionScriptInterp(null, shared);
  run(other, parser, 'published += 4; sharedCall=triple(7);');
  check(shared.get('published') == 15 && other.variables.get('sharedCall') == 21,
   'a second interpreter could not read/write the shared map');

  HxcCompatRuntime.clear();
  var zTarget = new Actor();
  interp.variables.set('zTarget', zTarget);
  run(interp, parser, 'zBefore=zTarget.zIndex; zTarget.zIndex=10; zWritten=zTarget.zIndex; '
   + 'zTarget.zIndex += 4; zAfter=zTarget.zIndex;');
  check(interp.variables.get('zBefore') == 0 && interp.variables.get('zWritten') == 10
   && interp.variables.get('zAfter') == 14 && HxcCompatRuntime.getZIndex(zTarget) == 14,
   'zIndex property reads/writes did not use the engine compatibility side table');

  interp.release();
  check(interp.parent == null && interp.sharedFields == null && interp.parentFields.length == 0
   && !interp.variables.exists('shadow') && !interp.imports.exists('imported'),
   'release retained parent, shared-map, import, or variable references');
  check(shared.get('published') == 15,
   'release incorrectly cleared the group-owned shared map');
  other.release();
 }
}'''

        runtime_stub = '''class HxcCompatRuntime {
 static var targets:Array<Dynamic> = [];
 static var values:Array<Int> = [];
 static function indexOf(target:Dynamic):Int return targets.indexOf(target);
 public static function clear():Void { targets.resize(0); values.resize(0); }
 public static function getZIndex(target:Dynamic):Dynamic {
  var index = indexOf(target);
  return index < 0 ? 0 : values[index];
 }
 public static function setZIndex(target:Dynamic, value:Dynamic, ?op:String='='):Dynamic {
  var current = getZIndex(target);
  var next = Std.int(Std.parseFloat(Std.string(value)));
  switch (op) {
   case '+=': next = current + next;
   case '-=': next = current - next;
   case '*=': next = current * next;
   case '/=': if (next != 0) next = Std.int(current / next);
  }
  var index = indexOf(target);
  if (index < 0) { targets.push(target); values.push(next); }
  else values[index] = next;
  return next;
 }
}'''

        with tempfile.TemporaryDirectory(prefix="nmv-interp-", dir=ROOT / "tmp") as scratch:
            (Path(scratch) / "Main.hx").write_text(fixture)
            (Path(scratch) / "HxcCompatRuntime.hx").write_text(runtime_stub)
            for defines in ([], ['-D', 'hscriptPos']):
                with self.subTest(defines=defines):
                    result = subprocess.run(
                        [str(HAXE), "-cp", str(ROOT / "source"),
                         "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", scratch]
                        + defines + ["--run", "Main"],
                        cwd=ROOT, capture_output=True, text=True, timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
