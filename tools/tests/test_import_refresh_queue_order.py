"""Pin the order in which queued retained-import refreshes start."""
from haxe_test_support import FixturePath as Path, haxe_command
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var busy:Map<String,Bool> = new Map();
  var isBusy = function(record:Dynamic) return busy.exists(record.id);
  var units = function(record:Dynamic) return ImportRefreshProgress.estimatedWorkUnits(record.estimatedWorkUnits);
  var queue:Array<Dynamic> = [{id:"large",estimatedWorkUnits:3668},{id:"medium",estimatedWorkUnits:676},
   {id:"small",estimatedWorkUnits:62},{id:"tie",estimatedWorkUnits:62}];
  check(ImportRefreshQueueOrder.nextIndex(queue,isBusy,units) == 2,
   "the smallest queued package must refresh first");
  busy.set("small",true);
  check(ImportRefreshQueueOrder.nextIndex(queue,isBusy,units) == 3,
   "an owner in use is skipped and an equal-sized package takes its turn");
  busy.set("tie",true);
  check(ImportRefreshQueueOrder.nextIndex(queue,isBusy,units) == 1,
   "the next smallest runnable package follows");
  busy.set("medium",true); busy.set("large",true);
  check(ImportRefreshQueueOrder.nextIndex(queue,isBusy,units) == -1,
   "nothing starts while every queued owner is in use");
  var unknown:Array<Dynamic> = [{id:"a"},{id:"b",estimatedWorkUnits:20}];
  check(ImportRefreshQueueOrder.nextIndex(unknown,function(_) return false,units) == 1,
   "a record without an estimate uses the shared default size");
  check(ImportRefreshQueueOrder.nextIndex([],isBusy,units) == -1, "an empty queue has no next record");
  check(ImportRefreshQueueOrder.nextIndex(null,isBusy,units) == -1, "an absent queue has no next record");
  Sys.println("queue-order-ok");
 }
}
'''


class ImportRefreshQueueOrderTest(unittest.TestCase):
    def test_smallest_runnable_refresh_starts_first(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            (Path(temp) / 'Main.hx').write_text(MAIN, newline='\n')
            result = subprocess.run(
                [*haxe_command(), '-cp', str(ROOT / 'source'), '-cp', temp, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('queue-order-ok', result.stdout)

    def test_manager_selects_through_the_shared_order(self):
        source = (ROOT / 'source/ImportRefreshManager.hx').read_text(encoding='utf-8')
        self.assertIn('ImportRefreshQueueOrder.nextIndex(queue,', source)
        self.assertNotIn('while (index < queue.length && runtimeOwnersBusyLocked', source)


if __name__ == '__main__':
    unittest.main()
