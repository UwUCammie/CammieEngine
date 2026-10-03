"""Execute Iris indexed reads and writes, including null receiver recovery."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"
IRIS = ROOT / ".haxelib" / "hscript-iris" / "1,1,3"


class NightmareVisionNullCollectionsTest(unittest.TestCase):
    def test_indexed_collection_semantics_and_callback_recovery(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
class Main {
 static function fail(message:String):Void throw message;
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void {
  if (actual != expected) fail(message + ': expected ' + expected + ', got ' + actual);
 }
 static function events(actual:Array<String>, expected:String, message:String):Void
  eq(actual.join(','), expected, message);
 static function expectNullFailure(group:NightmareVisionScriptGroup, errors:Array<String>,
  order:Array<String>, callback:String, expectedOrder:String):Void {
  order.resize(0);
  var before = errors.length;
  eq(group.call(callback), NightmareVisionScriptGroup.CONTINUE_FUNC,
   callback + ' did not report a script failure');
  events(order, expectedOrder, callback + ' changed Iris evaluation order or evaluated an operand twice');
  eq(errors.length, before + 1, callback + ' did not report exactly one error');
  if (errors[errors.length - 1].indexOf('[nightmare-vision-script-null-access]') < 0)
   fail(callback + ' did not report the actionable null-access diagnostic: ' + errors[errors.length - 1]);
 }

 static function main():Void {
  var order:Array<String> = [];
  var array:Array<Dynamic> = [10];
  var map:Map<String, Dynamic> = new Map();
  map.set('key', 8);
  var interp = new NightmareVisionScriptInterp();
  interp.variables.set('arrayGetter', function():Dynamic { order.push('array'); return array; });
  interp.variables.set('arrayIndex', function():Int { order.push('index'); return 0; });
  interp.variables.set('mapGetter', function():Dynamic { order.push('map'); return map; });
  interp.variables.set('mapIndex', function():String { order.push('key'); return 'key'; });
  interp.variables.set('rhs', function():Int { order.push('rhs'); return 5; });
  interp.variables.set('array', array);
  interp.variables.set('map', map);
  var parser = new NightmareVisionScriptParser();

  interp.execute(parser.parseString('readValue = arrayGetter()[arrayIndex()];'));
  eq(interp.variables.get('readValue'), 10, 'array read returned the wrong element');
  events(order, 'array,index', 'array read order');

  order.resize(0);
  interp.execute(parser.parseString('arrayGetter()[arrayIndex()] = rhs();'));
  eq(array[0], 5, 'array assignment failed');
  events(order, 'rhs,array,index', 'plain assignment order');

  order.resize(0);
  interp.execute(parser.parseString('arrayGetter()[arrayIndex()] += rhs();'));
  eq(array[0], 10, 'array compound assignment failed');
  events(order, 'array,index,rhs', 'compound assignment order');

  order.resize(0);
  interp.execute(parser.parseString('prefixResult = ++arrayGetter()[arrayIndex()];'));
  eq(array[0], 11, 'array prefix increment failed to write');
  eq(interp.variables.get('prefixResult'), 11, 'array prefix increment returned the wrong value');
  events(order, 'array,index', 'prefix increment order');

  order.resize(0);
  interp.execute(parser.parseString('postfixResult = arrayGetter()[arrayIndex()]++;'));
  eq(array[0], 12, 'array postfix increment failed to write');
  eq(interp.variables.get('postfixResult'), 11, 'array postfix increment returned the wrong value');
  events(order, 'array,index', 'postfix increment order');

  order.resize(0);
  interp.execute(parser.parseString('mapRead = mapGetter()[mapIndex()];'));
  eq(interp.variables.get('mapRead'), 8, 'map read failed');
  events(order, 'map,key', 'map read order');

  order.resize(0);
  interp.execute(parser.parseString('mapGetter()[mapIndex()] = rhs();'));
  eq(map.get('key'), 5, 'map assignment failed');
  events(order, 'rhs,map,key', 'map assignment order');

  order.resize(0);
  interp.execute(parser.parseString('mapGetter()[mapIndex()] += rhs();'));
  eq(map.get('key'), 10, 'map compound assignment failed');
  events(order, 'map,key,rhs', 'map compound assignment order');

  order.resize(0);
  interp.execute(parser.parseString('mapPrefix = ++mapGetter()[mapIndex()];'));
  eq(map.get('key'), 11, 'map prefix increment failed to write');
  eq(interp.variables.get('mapPrefix'), 11, 'map prefix increment returned the wrong value');
  events(order, 'map,key', 'map prefix increment order');

  order.resize(0);
  interp.execute(parser.parseString('mapPostfix = mapGetter()[mapIndex()]++;'));
  eq(map.get('key'), 12, 'map postfix increment failed to write');
  eq(interp.variables.get('mapPostfix'), 11, 'map postfix increment returned the wrong value');
  events(order, 'map,key', 'map postfix increment order');

  // Preserve Iris's direct index behavior: no clamping or bounds rewriting.
  interp.execute(parser.parseString('array[4] = 91; outOfRangeRead = array[12];'));
  eq(array[4], 91, 'out-of-range assignment was redirected to a different index');
  eq(interp.variables.get('outOfRangeRead'), null,
   'out-of-range read did not retain Iris array semantics');
  map.set('missing', null);
  interp.execute(parser.parseString('missingMapValue = map["missing"];'));
  eq(interp.variables.get('missingMapValue'), null,
   'a present map with a null value was mistaken for a null collection');
  interp.release();

  var errors:Array<String> = [];
  var callbackOrder:Array<String> = [];
  var group = new NightmareVisionScriptGroup(null,
   function(name:String, phase:String, error:Dynamic):Void
    errors.push(name + '#' + phase + ': ' + Std.string(error)));
  var module = group.loadSource('null-collections.hx', '
   var attempts = 0;
   function readNull() return nullCollection()[markIndex()];
   function assignNull() { nullCollection()[markIndex()] = markRhs(); return 1; }
   function compoundNull() { nullCollection()[markIndex()] += markRhs(); return 2; }
   function prefixNull() return ++nullCollection()[markIndex()];
   function postfixNull() return nullCollection()[markIndex()]++;
   function recover() {
    attempts++;
    if (attempts == 1) return nullCollection()[markIndex()];
    return 42;
   }
   function good() return 17;
  ', function(scriptInterp:NightmareVisionScriptInterp):Void {
   scriptInterp.variables.set('nullCollection', function():Dynamic {
    callbackOrder.push('collection'); return null;
   });
   scriptInterp.variables.set('markIndex', function():Int {
    callbackOrder.push('index'); return 0;
   });
   scriptInterp.variables.set('markRhs', function():Int {
    callbackOrder.push('rhs'); return 7;
   });
  });
  if (module == null) fail('null collection callback module failed to load: ' + errors.join('\n'));

  expectNullFailure(group, errors, callbackOrder, 'readNull', 'collection,index');
  expectNullFailure(group, errors, callbackOrder, 'assignNull', 'rhs,collection,index');
  expectNullFailure(group, errors, callbackOrder, 'compoundNull', 'collection,index');
  expectNullFailure(group, errors, callbackOrder, 'prefixNull', 'collection,index');
  expectNullFailure(group, errors, callbackOrder, 'postfixNull', 'collection,index');

  callbackOrder.resize(0);
  var beforeRecovery = errors.length;
  eq(group.call('recover'), NightmareVisionScriptGroup.CONTINUE_FUNC,
   'failing callback did not return the host continuation value');
  events(callbackOrder, 'collection,index', 'failing callback order');
  eq(errors.length, beforeRecovery + 1, 'failing callback did not report one error');
  eq(group.call('good'), 17, 'another callback did not run after a null collection failure');
  callbackOrder.resize(0);
  eq(group.call('recover'), 42, 'same callback could not recover after its first failure');
  eq(errors.length, beforeRecovery + 1, 'recovered callback reported a stale error');
  group.destroy();
 }
}'''

        with tempfile.TemporaryDirectory(prefix="nmv-null-collections-", dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            write_flixel_point_stub(work)
            (work / "Main.hx").write_text(fixture, newline='\n')
            for defines in ([], ["-D", "hscriptPos"]):
                with self.subTest(defines=defines):
                    result = subprocess.run(
                        [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", scratch]
                        + defines + ["--run", "Main"],
                        cwd=ROOT, capture_output=True, text=True, timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
