"""Initial HXC character callbacks wait for the chart stage and run once."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class HxcCharacterLifecycleQueueTest(unittest.TestCase):
    def test_queue_deduplicates_actor_adds_and_drains_after_stage_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "Main.hx").write_text('''
import HxcCharacterLifecycleQueue.HxcCharacterLifecycleCall;

class Actor {
  public var id:String;
  public function new(id:String) this.id = id;
}

class Main {
  static function fail(message:String):Void throw message;
  static function main() {
    var queue = new HxcCharacterLifecycleQueue();
    var gf = new Actor("gf");
    var dad = new Actor("dad");
    queue.enqueue(gf, "gf", null);
    queue.enqueue(gf, "gf", gf);
    queue.enqueue(dad, "dad", dad);
    if (queue.length != 2) fail("duplicate actor onAdd was queued");

    var stageReady = false;
    var seen:Array<String> = [];
    if (queue.length != 2 || seen.length != 0)
      fail("callbacks ran before the stage became ready");
    stageReady = true;
    var drained = queue.drain(function(entry:HxcCharacterLifecycleCall) {
      if (!stageReady) fail("onAdd ran before stage setup");
      if (entry.actorOverride == null)
        fail("construction-time actor override was lost");
      seen.push(entry.role + ":" + entry.actor.id);
    });
    if (drained != 2 || queue.length != 0)
      fail("drain did not consume the pending actor callbacks");
    if (seen.join(",") != "gf:gf,dad:dad")
      fail("queued callbacks changed order or actor binding: " + seen.join(","));
    if (queue.drain(function(_) {}) != 0)
      fail("drained callback ran a second time");
    trace("deferred character onAdd OK");
  }
}
''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("deferred character onAdd OK", result.stdout)

    def test_playstate_queues_until_stage_binding_then_flushes(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        self.assertRegex(source, re.compile(
            r"function callHxcCharacterAdded\(.*?\n\s*if \(curStage == null\) \{\n"
            r"\s*pendingHxcCharacterAdds\.enqueue\(actor, hxcCharacterRole\(role\), actorOverride\);\n"
            r"\s*return;\n\s*\}", re.S))
        start = source.index("\tpublic function swapStage(")
        end = source.index("\n\tfunction callCountdownTick(", start)
        # Both successful and failed replacement must publish the stage before
        # draining HXC actor callbacks. Other engines may refresh aliases in
        # between; adjacency of these statements is not the lifecycle contract.
        success, failure = source[start:end].split("} catch (error:Dynamic) {", 1)
        for branch in (success, failure):
            self.assertLess(branch.index("setAllHaxeVar('stage', curStage);"),
                            branch.index("flushPendingHxcCharacterAdded();"))


if __name__ == "__main__":
    unittest.main()
