"""One per-row event driver for Psych, modern and historical Nightmare Vision.

SourceEventPreparation.pushView runs a built view through the engine hooks.
The historical two-pass preparation calls it for both of its passes; its
pinned behaviour is covered by test_nv_historical_event_preparation.
"""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function view(name:String, time:Float):SourceEventNote
  return new SourceEventNote({time:time, name:name, v1:'', v2:'', order:0}, 0);
 static function main():Void {
  // Without a name map nothing is recorded and no first push fires.
  var log:Array<String> = [];
  var hooks:SourceEventPreparation.SourceEventPreparationHooks = {
   firstPush:function(e) log.push('first:' + e.event),
   push:function(e) log.push('push:' + e.event)
  };
  SourceEventPreparation.pushView(view('A', 1), null, hooks);
  check(log.join('|') == 'push:A', 'no map means no first push ' + log.join('|'));
  var names:Map<String, Bool> = new Map();
  SourceEventPreparation.pushView(view('A', 1), names, hooks);
  SourceEventPreparation.pushView(view('A', 2), names, hooks);
  check(log.join('|') == 'push:A|first:A|push:A|push:A' && names.exists('A'), 'first push once per name ' + log.join('|'));
  // A map without a firstPush hook still records the name, as prepare always did.
  var quiet:Map<String, Bool> = new Map();
  SourceEventPreparation.pushView(view('B', 1), quiet, {});
  check(quiet.exists('B'), 'name recorded without a hook');

  // The time is read before the early-trigger callback runs.
  var moved = view('C', 100);
  SourceEventPreparation.pushView(moved, null, {earlyOffset:function(e):Null<Float> {e.strumTime = 800; return 30;}});
  check(moved.strumTime == 70, 'offset subtracts from the time read first: ' + moved.strumTime);
  var kill = view('Kill Henchmen', 1000);
  SourceEventPreparation.pushView(kill, null, {earlyOffset:function(e):Null<Float> return null});
  check(kill.strumTime == 720, 'built-in default applies when scripts give no answer');
  // The default follows the name the scripts leave on the event, as the
  // Nightmare Vision sources read it after their offset callbacks.
  var renamed = view('Plain', 1000);
  SourceEventPreparation.pushView(renamed, null, {earlyOffset:function(e):Null<Float> {e.event = 'Kill Henchmen'; return 0;}});
  check(renamed.strumTime == 720, 'default uses the name after the callback: ' + renamed.strumTime);
  var unrenamed = view('Kill Henchmen', 1000);
  SourceEventPreparation.pushView(unrenamed, null, {earlyOffset:function(e):Null<Float> {e.event = 'Plain'; return null;}});
  check(unrenamed.strumTime == 1000, 'a renamed built-in loses its default: ' + unrenamed.strumTime);

  // prepare is the same per-row driver over views it builds itself.
  var built:Array<SourceEventNote> = [];
  var order:Array<String> = [];
  SourceEventPreparation.prepare([{time:5., name:'D', v1:'', v2:'', order:0}, {time:6., name:'D', v1:'', v2:'', order:1}], 0, built,
   {beforeFirstPush:function(e) order.push('unique:' + built.length), firstPush:function(e) order.push('first'), push:function(e) order.push('push')});
  check(order.join('|') == 'unique:1|first|push|unique:2|push', 'prepare order ' + order.join('|'));
 }
}
'''


class SourceEventPushViewTest(unittest.TestCase):
	def test_push_view(self):
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			work = FixturePath(folder)
			(work / 'Main.hx').write_text(MAIN, newline='\n')
			for name in ('SourceEventNote', 'SourceEventPreparation'):
				(work / (name + '.hx')).write_text((ROOT / 'source' / (name + '.hx')).read_text(encoding='utf-8'), newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'], cwd=ROOT,
									capture_output=True, text=True, timeout=60)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

	def test_historical_preparation_uses_the_shared_driver(self):
		legacy = (ROOT / 'source/NightmareVisionLegacyEventPreparation.hx').read_text(encoding='utf-8')
		self.assertEqual(legacy.count('SourceEventPreparation.pushView('), 2)
		self.assertIn('SourceEventPreparation.pushView(entry.event, null, publishRow);', legacy)
		self.assertNotIn('event.strumTime = time -', legacy)


if __name__ == '__main__':
	unittest.main()
