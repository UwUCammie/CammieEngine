"""Source NMV ScriptGroup ordering, cancellation, and lifecycle contracts."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionScriptGroupTest(unittest.TestCase):
    def test_return_flow_matches_supplied_source(self):
        donor = ROOT.parent / 'FNF-Example-Mods/misc/nightmare_vision_source_code/source/funkin/scripts/ScriptGroup.hx'
        if not donor.is_file():
            self.skipTest('supplied Nightmare Vision ScriptGroup source unavailable')
        source = donor.read_text()
        reference_method = 'public function call(' + source.split(
            'public function call(', 1)[1].split('\n\t/**', 1)[0]
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            (work / 'Main.hx').write_text(r'''
class ScriptConstants {
 public static var CONTINUE_FUNC = 0;
 public static var STOP_FUNC = 1;
 public static var HALT_FUNC = 2;
}
class RefModule {
 public var name:String;
 public var result:Dynamic;
 public var log:Array<String>;
 public function new(name:String, result:Dynamic, log:Array<String>) {
  this.name=name; this.result=result; this.log=log;
 }
 public function exists(event:String):Bool return event == 'event';
 public function call(event:String, args:Array<Dynamic>):Dynamic {
  log.push(name); return {returnValue:result};
 }
}
class ReferenceGroup {
 public var members:Array<RefModule> = [];
 public function new() {}
''' + reference_method.replace('?.returnValue', '.returnValue') + r'''
}
class Main {
 static function main() {
  var values:Array<Dynamic> = [null, 0, 1, 2, 7, false, '1', 1.5];
  var cases = 0;
  for (a in values) for (b in values) for (c in values)
   for (ignoreStops in [false,true]) for (exclude in [false,true]) {
    var actual = new NightmareVisionScriptGroup();
    var expected = new ReferenceGroup();
    var actualLog:Array<String> = [];
    var expectedLog:Array<String> = [];
    var results = [a,b,c];
    for (index in 0...results.length) {
     var name = 'scope' + index;
     var returned = results[index];
     expected.members.push(new RefModule(name, returned, expectedLog));
     var interp = new NightmareVisionScriptInterp();
     interp.variables.set('event', function():Dynamic {
      actualLog.push(name); return returned;
     });
     actual.addScript(new NightmareVisionScriptModule(name, interp,
      function(name, phase, error):Void { throw 'unexpected callback error'; }));
    }
    var exclusions = exclude ? ['scope1'] : [];
    var x:Dynamic = actual.call('event', null, ignoreStops, exclusions);
    var y:Dynamic = expected.call('event', null, ignoreStops, exclusions);
    if (x != y || actualLog.join(',') != expectedLog.join(','))
     throw 'source mismatch: ' + results + ', ignore=' + ignoreStops + ', exclude=' + exclude;
    actual.destroy(); cases++;
   }
  if (cases != 2048) throw 'missing return-flow cases';
 }
}
''')
            for defines in ([], ['-D', 'hscriptPos']):
                with self.subTest(defines=defines):
                    result = subprocess.run(
                        [str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                         '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(work)]
                        + defines + ['--main', 'Main', '--interp'], cwd=work,
                        capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_executed_callbacks_lifecycle_cancellation_and_failure_recovery(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            (work / 'Main.hx').write_text(r'''
import crowplexus.hscript.Parser;
class Parent {
 public var value:Int;
 public function new(value:Int) this.value = value;
}
class Main {
 static var log:Array<String> = [];
 static var errors:Array<String> = [];
 static function fail(message:String):Void throw message;
 static function eq(actual:Dynamic, expected:Dynamic):Void {
  if (actual != expected) fail('expected ' + expected + ', got ' + actual);
 }
 static function parsed(source:String):crowplexus.hscript.Expr {
  var parser = new Parser(); parser.allowTypes = true; parser.allowMetadata = true;
  return parser.parseString(source);
 }
 static function configure(interp:NightmareVisionScriptInterp):Void {
  interp.variables.set('record', function(text:String):Void log.push(text));
 }
 static function group():NightmareVisionScriptGroup {
  return new NightmareVisionScriptGroup(new Parent(4), function(name, phase, error):Void {
   errors.push(name + '#' + phase);
  });
 }
 static function main() {
  var g = group();
  var a = g.load('a', parsed('
   record(isRegistered() ? "registered" : "missing");
   function onLoad() record("load");
   function onCreate() record("wrong-create");
   function onCreatePost() { record("post"); return 0; }
   function event(n) { record("a:" + n); return 1; }
   function onDestroy() { record("destroy-a"); return 2; }
  '), function(interp):Void {
   configure(interp);
   interp.variables.set('isRegistered', function():Bool return g.exists('a'));
  });
  eq(log.join(','), 'registered,load');
  eq(g.load('a', parsed('record("duplicate");'), configure), null);
  eq(g.members.length, 1);
  eq(g.call('onCreatePost'), 0);
  eq(log.join(','), 'registered,load,post');
  var b = g.load('b', parsed('
   function event(n) { record("b:" + n); return 2; }
   function onDestroy() record("destroy-b");
  '), configure);
  var c = g.load('c', parsed('
   function event(n) { record("c:" + n); return 7; }
   function onDestroy() record("destroy-c");
  '), configure);
  log = [];
  eq(g.call('event', [3]), 1);
  eq(log.join(','), 'a:3,b:3'); // STOP continues; HALT retains STOP and stops group.
  log = [];
  eq(g.call('event', [4], true), 7);
  eq(log.join(','), 'a:4,b:4,c:4');
  log = [];
  eq(g.call('event', [5], false, ['a']), 0);
  eq(log.join(','), 'b:5'); // HALT alone is not STOP.
  log = [];
  eq(g.call('event', [6], false, ['b']), 7);
  eq(log.join(','), 'a:6,c:6');
  a.interp.variables.set('event', function(n):Dynamic return false);
  b.interp.variables.set('event', function(n):Dynamic return '1');
  c.interp.variables.set('event', function(n):Dynamic return 0.5);
  eq(g.call('event', [0]), 0); // Non-Int values do not cancel native work.
  a.interp.variables.set('event', function(n):Dynamic return 1);
  b.interp.variables.set('event', function(n):Dynamic return 0);
  c.interp.variables.set('event', function(n):Dynamic return null);
  eq(g.call('event', [0]), 1); // CONTINUE/null do not erase a prior STOP.
  g.set('sharedPreset', false);
  eq(a.interp.variables.get('sharedPreset'), false);
  eq(c.interp.variables.get('sharedPreset'), false);
  g.sharedFields.set('kept', 17);
  var previousParent = a.interp.parent;
  var replacement = new Parent(9);
  g.parent = replacement;
  eq(a.interp.parent, replacement);
  eq(c.interp.parent, replacement);
  log = [];
  g.clear();
  eq(log.join(','), 'destroy-a,destroy-b,destroy-c');
  eq(g.members.length, 0);
  eq(g.sharedFields.get('kept'), 17);
  eq(a.released, true); eq(b.released, true); eq(c.interp, null);
  g.clear(); eq(log.join(','), 'destroy-a,destroy-b,destroy-c');
  var next = g.load('a', parsed('function onDestroy() record("unexpected");'), configure);
  g.destroy(); g.destroy();
  eq(next.released, true); eq(g.sharedFields.exists('kept'), false);
  eq(g.parent, null); eq(g.load('new', parsed(''), configure), null);
  eq(log.join(','), 'destroy-a,destroy-b,destroy-c');

  // Errors in top-level execution remove the module, while callback failures
  // retain it and allow later calls to recover just as Iris does.
  g = group();
  var captured:NightmareVisionScriptInterp = null;
  eq(g.load('bad', parsed('throw "top-level";'), function(i):Void {
   captured = i;
  }), null);
  eq(g.exists('bad'), false); eq(captured.parent, null);
  eq(errors.pop(), 'bad#module');
  var recovering = g.load('bad', parsed('
   var attempts = 0;
   function onLoad() throw "load";
   function tick() { attempts++; if (attempts == 1) throw "first"; return 1; }
  '));
  eq(g.exists('bad'), true); eq(errors.pop(), 'bad#onLoad');
  eq(g.call('tick'), 0); eq(errors.pop(), 'bad#tick');
  eq(g.call('tick'), 1);
  recovering.interp.variables.set('invalid', 0);
  eq(g.call('invalid'), 0); eq(errors.pop(), 'bad#invalid');
  recovering.interp.variables.set('invalid', function():Int return 1);
  eq(g.call('invalid'), 1);
  eq(g.load('bindings', parsed(''), function(i):Void {
   captured = i; throw 'binding';
  }), null);
  eq(captured.parent, null); eq(errors.pop(), 'bindings#bindings');
  eq(g.exists('bindings'), false);

  // Removing a module does not destroy it; moving it copies group context.
  var other = group(); other.sharedFields.set('different', true);
  eq(g.removeScript(recovering), true); eq(recovering.released, false);
  eq(other.addScript(recovering), true);
  eq(recovering.interp.sharedFields, other.sharedFields);
  eq(recovering.interp.parent, other.parent);
  eq(other.addScript(recovering), false);
  eq(other.addScript(null), false);
  g.destroy(); other.clear(false); other.destroy();
  eq(recovering.released, true);
  eq(errors.length, 0);

  // Parse NMV's public declarations without rewriting comments or literals.
  // Public values/functions share a group; plain module locals remain private.
  g = group();
  var publicOwner = g.loadSource('owner.hx', '
   public var sharedCount:Int = 3;
   public function bump():Int { sharedCount++; return sharedCount; }
   var secret = 99;
   function ownSecret() return secret;
   function literal() return "public var untouched = 9";
  ');
  if (publicOwner == null) fail('public owner failed: ' + errors.join(','));
  var consumer = g.loadSource('consumer.hxs', '
   function onLoad() bump();
   function read() return sharedCount;
   function write(v) sharedCount = v;
  ');
  eq(consumer.call('read'), 4);
  eq(publicOwner.call('ownSecret'), 99);
  eq(g.sharedFields.exists('secret'), false);
  eq(publicOwner.call('literal'), 'public var untouched = 9');
  consumer.call('write', [0]); eq(g.sharedFields.get('sharedCount'), 0);
  eq(g.loadSource('parse-error.hx', 'public 123;'), null);
  eq(g.exists('parse-error.hx'), false); eq(errors.pop(), 'parse-error.hx#parse');
  eq(g.loadSource('consumer.hxs', 'this is invalid syntax'), null);
  eq(errors.length, 0); // Duplicate rejection happens before parsing.
  other = group(); eq(other.sharedFields.exists('sharedCount'), false);
  g.destroy(); other.destroy();
 }
}
''')
            for defines in ([], ['-D', 'hscriptPos']):
                with self.subTest(defines=defines):
                    result = subprocess.run(
                        [str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'),
                         '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', str(work)]
                        + defines + ['--main', 'Main', '--interp'], cwd=work,
                        capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
