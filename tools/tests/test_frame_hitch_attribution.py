"""Smoke pacing reports each slow frame once and says where the time went."""
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_native_asset_resolution import extract_method

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class FrameHitchAttributionTest(unittest.TestCase):
    def run_fixture(self, name, body):
        fixture = 'class ' + name + ''' {
 static function fail(message:String):Void throw message;
 static var t:FrameHitchTracker;
 static var now:Float = 1000;
 static var reports:Array<String> = [];
 // one frame: update and draw, then OpenFL render, then idle until the next one
 static function frame(work:Float, render:Float, idle:Float, heapStart:Float, heapEnd:Float):Bool {
  t.beginFrame(now, heapStart);
  now += work;
  var slow = t.endFrame(now, heapEnd);
  if (slow) reports.push(t.cause());
  t.beginRender(now);
  now += render;
  t.endRender(now);
  now += idle;
  return slow;
 }
 static function main() {
  t = new FrameHitchTracker();
''' + body + '''
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / (name + ".hx")).write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "--run", name],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_one_slow_update_is_reported_once(self):
        self.run_fixture("HitchOnceFixture", '''
  for (i in 0...3) if (frame(3, 1, 12, 100, 101)) fail("normal frame reported");
  if (!frame(40, 1, 0, 101, 102)) fail("40 ms update not reported");
  if (Math.abs(t.insideMs - 40) > 0.001) fail("inside time wrong: " + t.insideMs);
  // The next frame's gap is long only because of the slow frame before it.
  if (frame(3, 1, 12, 102, 103)) fail("frame after a slow one was reported again");
  if (t.gapMs < 40) fail("gap should still carry the slow frame");
  if (t.outsideMs > 1) fail("slow frame leaked into outside time: " + t.outsideMs);
  if (reports.join(",") != "update-draw") fail("causes: " + reports.join(","));
''')

    def test_slow_render_and_idle_are_attributed_to_the_next_frame(self):
        self.run_fixture("HitchRenderFixture", '''
  frame(3, 1, 12, 100, 100);
  frame(2, 300, 0, 100, 100);
  if (!frame(2, 1, 12, 100, 100)) fail("300 ms render gap not reported");
  if (Math.abs(t.renderMs - 300) > 0.001) fail("render time wrong: " + t.renderMs);
  if (t.cause() != "render") fail("cause: " + t.cause());
  frame(2, 1, 200, 100, 100);
  if (!frame(2, 1, 12, 100, 100)) fail("200 ms stall not reported");
  if (t.cause() != "outside" || Math.abs(t.outsideMs - 200) > 0.001) fail("outside: " + t.outsideMs);
''')

    def test_heap_drop_marks_a_collection(self):
        self.run_fixture("HitchHeapFixture", '''
  frame(3, 1, 12, 500, 520);
  if (!frame(90, 1, 0, 520, 300)) fail("collection frame not reported");
  if (!t.collectedInside || t.collectedOutside) fail("collection not seen inside the frame");
  if (t.heapDropBytes != 220) fail("drop: " + t.heapDropBytes);
  // a drop between frames is a collection outside update and draw
  frame(3, 1, 12, 250, 260);
  if (!t.collectedOutside || t.collectedInside) fail("collection between frames missed");
  frame(3, 1, 12, 260, 270);
  if (t.collectedInside || t.collectedOutside) fail("growth read as a collection");
  if (t.suspectedCollections != 2) fail("count: " + t.suspectedCollections);
  // no heap figure available
  frame(3, 1, 12, -1, -1);
  if (t.collectedInside || t.collectedOutside) fail("missing figures read as a collection");
''')

    def test_allocation_total_counts_growth_only(self):
        self.run_fixture("HitchAllocFixture", '''
  frame(3, 1, 12, 100, 110);
  frame(3, 1, 12, 115, 60);
  frame(3, 1, 12, 70, 75);
  // 10 + 5 of growth, the collection drop, then 10 + 5 again
  if (t.takeAllocatedBytes() != 30) fail("allocated: " + t.allocatedBytes);
  if (t.takeAllocatedBytes() != 0) fail("total not cleared");
  frame(3, 1, 12, 80, 81);
  if (t.takeAllocatedBytes() != 6) fail("next window wrong");
''')

    def test_second_update_before_draw_stays_in_the_same_frame(self):
        self.run_fixture("HitchDoubleStepFixture", '''
  frame(3, 1, 12, 100, 100);
  t.beginFrame(now, 100);
  now += 20;
  t.beginFrame(now, 100);
  now += 20;
  if (!t.endFrame(now, 100)) fail("two 20 ms steps in one frame not reported");
  if (Math.abs(t.insideMs - 40) > 0.001) fail("frame lost its first step: " + t.insideMs);
  if (t.endFrame(now + 5, 100)) fail("closing twice reported twice");
''')

    def test_harness_work_is_reported_with_the_frame(self):
        self.run_fixture("HitchHarnessFixture", '''
  t.beginFrame(now, 1);
  t.addHarnessTime(30);
  now += 45;
  if (!t.endFrame(now, 1)) fail("not reported");
  if (t.harnessMs != 30) fail("harness time: " + t.harnessMs);
  t.beginFrame(now, 1);
  now += 3;
  t.endFrame(now, 1);
  if (t.harnessMs != 0) fail("harness time carried over: " + t.harnessMs);
''')

    def test_harness_wiring(self):
        source = (ROOT / "source/RuntimeSmokeHarness.hx").read_text(encoding="utf-8")
        post = extract_method(source, "static function onFramePostDraw(")
        self.assertIn("hitchTracker.endFrame(now, currentHeapBytes(), currentLargeBytes(), currentReservedBytes())", post)
        self.assertNotIn("frameDelta > 33.4 ||", post)
        for field in ("previousRenderMs", "outsideMs", "collectedInside", "collectedOutside",
                      "heapDropBytes", "largeGrowthBeforeDropBytes", "largeTriggerSuspected",
                      "harnessMs", "cause"):
            self.assertIn(field + ":", post)
        pre = extract_method(source, "static function onFramePreUpdate(")
        self.assertIn("hitchTracker.beginFrame(frameStart, currentHeapBytes(), currentLargeBytes(), currentReservedBytes())", pre)
        # the per-5-second note geometry burst stays out of pacing runs
        live = extract_method(source, "public static function markLiveNightmareVisionNote(")
        self.assertIn("config().pacingOnly == true", live)
        summary = extract_method(source, "static function emitFrameSummary(")
        self.assertIn("allocatedBytes: config().pacingOnly == true ? hitchTracker.takeAllocatedBytes() : null", summary)
        emit = extract_method(source, "static function emit(")
        self.assertIn("hitchTracker.addHarnessTime(", emit)
        self.assertNotIn("stream.close();", emit)
        append = extract_method(source, "static function appendLogLine(")
        self.assertIn("logStream.flush();", append)
        render = extract_method(source, "static function installRenderTiming(")
        self.assertIn("onRenderTimingEnd, false, -500", render)
        # OpenFL's render listener broadcasts ENTER_FRAME, so flixel's whole update
        # and draw runs inside it. A listener ahead of OpenFL's would time update,
        # draw and render together and report every slow update a second time as
        # a slow render. The window opens after flixel's draw instead.
        self.assertEqual(render.count("window.onRender.add("), 1)
        self.assertEqual(source.count("hitchTracker.beginRender("), 1)
        # The render window opens with one clock read, shared by the hitch tracker
        # and the per-window render mean.
        begin = post.index("renderWindowStart = nowMs();")
        self.assertGreater(post.index("hitchTracker.beginRender(renderWindowStart)"), begin)
        rendered = extract_method(source, "static function onRenderTimingEnd(")
        self.assertIn("hitchTracker.endRender(now);", rendered)
        self.assertIn("renderCosts.push(now - renderWindowStart);", rendered)
        self.assertGreater(begin, post.index("hitchTracker.endFrame("))
        self.assertGreater(begin, post.index("emitFrameSummary();"))
        openfl = ROOT / ".haxelib/openfl/9,5,2/src/openfl/display/Stage.hx"
        if openfl.exists():
            limeRender = extract_method(openfl.read_text(encoding="utf-8"),
                                        "private function __onLimeRender(")
            self.assertLess(limeRender.index("Event.ENTER_FRAME"), limeRender.index("__render(context)"))

    def test_large_heap_growth_before_a_drop_names_the_trigger(self):
        self.run_fixture("HitchLargeFixture", '''
  var mb = 1024.0 * 1024.0;
  // Frame helper without the large figures leaves the attribution alone.
  frame(3, 1, 12, 100, 100);
  if (t.largeBytes != -1 || t.largeGrowthBeforeDropBytes != 0) fail("large figures invented");
  // First collection only sets the baseline: nothing measured it from a collection.
  t.beginFrame(now, 500 * mb, 100 * mb, 600 * mb); now += 3; t.endFrame(now, 510 * mb, 130 * mb, 600 * mb); now += 13;
  t.beginFrame(now, 300 * mb, 20 * mb, 600 * mb); now += 3; t.endFrame(now, 300 * mb, 20 * mb, 600 * mb); now += 13;
  if (!t.collectedOutside) fail("drop not seen");
  if (t.largeGrowthBeforeDropBytes != 30 * mb) fail("growth from first sample: " + t.largeGrowthBeforeDropBytes);
  if (t.largeTriggerSuspected || t.largeTriggeredCollections != 0) fail("classified without a collection baseline");
  // Large heap grows past max(40 MB, blocks of 580 MB) before the next drop: large trigger.
  t.beginFrame(now, 400 * mb, 300 * mb, 900 * mb); now += 3; t.endFrame(now, 960 * mb, 560 * mb, 1200 * mb); now += 13;
  if (t.largeTriggerSuspected) fail("growth alone flagged a trigger");
  t.beginFrame(now, 320 * mb, 30 * mb, 1200 * mb); now += 3; t.endFrame(now, 320 * mb, 30 * mb, 1200 * mb); now += 13;
  if (t.largeGrowthBeforeDropBytes != 540 * mb) fail("growth: " + t.largeGrowthBeforeDropBytes);
  if (!t.largeTriggerSuspected || t.largeTriggeredCollections != 1) fail("large trigger missed");
  // Small large-heap growth before the next drop: block growth, not the large budget.
  t.beginFrame(now, 600 * mb, 35 * mb, 1200 * mb); now += 3; t.endFrame(now, 650 * mb, 40 * mb, 1200 * mb); now += 13;
  t.beginFrame(now, 300 * mb, 30 * mb, 1200 * mb); now += 3; t.endFrame(now, 300 * mb, 30 * mb, 1200 * mb); now += 13;
  if (!t.collectedOutside || t.largeTriggerSuspected || t.largeTriggeredCollections != 1) fail("block collection read as large");
  if (t.largeGrowthBeforeDropBytes != 10 * mb) fail("small growth: " + t.largeGrowthBeforeDropBytes);
  // The next frame without a drop clears the per-frame figures.
  t.beginFrame(now, 310 * mb, 31 * mb, 1200 * mb); now += 3; t.endFrame(now, 311 * mb, 31 * mb, 1200 * mb);
  if (t.largeGrowthBeforeDropBytes != 0 || t.largeTriggerSuspected) fail("figures carried over");
  // With a small block heap the 40 MB floor is the budget.
  var u = new FrameHitchTracker();
  u.beginFrame(0, 50 * mb, 10 * mb, 30 * mb); u.endFrame(1, 40 * mb, 5 * mb, 30 * mb);
  u.beginFrame(2, 80 * mb, 42 * mb, 80 * mb); u.endFrame(3, 30 * mb, 4 * mb, 80 * mb);
  if (!u.largeTriggerSuspected) fail("40 MB floor not used: growth " + u.largeGrowthBeforeDropBytes);
''')

    def test_profiled_spikes_carry_their_attribution(self):
        source = (ROOT / "source/RuntimeSmokeHarness.hx").read_text(encoding="utf-8")
        post = extract_method(source, "static function onFramePostDraw(")
        self.assertIn("else if (config().pacingOnly != true && now - frameStart > SPIKE_MS && profileEnabled())", post)
        pre = extract_method(source, "static function onFramePreUpdate(")
        for line in ("spikeHeapAtStart = currentHeapBytes();", "spikeQueuedNotesAtStart = queuedNoteCount();",
                     "frameScriptCallbacks = 0;"):
            self.assertIn(line, pre)
        spike = extract_method(source, "static function emitFrameSpike(")
        for field in ("slowestSection:", "slowestSectionMs:", "notesLeftQueue:", "scriptCallbacks:",
                      "heapDeltaBytes:", "collected:", "costMs:"):
            self.assertIn(field, spike)
        snapshot = extract_method(source, "static function frameHeapSnapshot(")
        self.assertIn("largeBytes: EngineMemory.largeBytes()", snapshot)
        self.assertIn("largeTriggeredCollections: hitchTracker.largeTriggeredCollections", snapshot)
        self.assertIn("largeAfterBytes: gc.largeAfter", source)
        # Already-sampled notes are found without building a string key.
        live = extract_method(source, "public static function markLiveNightmareVisionNote(")
        packed = live.index("nightmareVisionLivePackedSamples.exists(packed)")
        self.assertLess(packed, live.index("var key ="))

    def test_live_note_sample_keys_pack_without_collisions(self):
        source = (ROOT / "source/RuntimeSmokeHarness.hx").read_text(encoding="utf-8")
        live = extract_method(source, "public static function markLiveNightmareVisionNote(")
        condition = live[live.index("if (field >= -1") + 3:live.index(") {", live.index("if (field >= -1"))] + ")"
        formula = live[live.index("var packed = ") + len("var packed = "):live.index(";", live.index("var packed = "))]
        self.run_fixture("HitchPackedKeyFixture", '''
  var seen = new Map<Int, String>();
  var limit = 2147483647.0;
  for (field in [-1, 0, 1, 7, 255]) for (direction in [-1, 0, 3, 63]) for (kind in 0...3) for (bucket in [0, 1, 2, 19999]) {
   if (!(''' + condition + ''')) fail("usual value rejected");
   var packedFloat = ((bucket * 257.0 + field + 1) * 65 + direction + 1) * 3 + kind;
   if (packedFloat > limit) fail("packed key overflows: " + packedFloat);
   var packed = ''' + formula + ''';
   var label = field + ":" + direction + ":" + kind + ":" + bucket;
   if (seen.exists(packed)) fail("collision " + label + " with " + seen.get(packed));
   seen.set(packed, label);
  }
  var field = 256, direction = 0, bucket = 0;
  if (''' + condition + ''') fail("out of range field packed");
''')

    def test_unclosed_render_window_does_not_reach_the_next_frame(self):
        self.run_fixture("HitchRenderResetFixture", '''
  frame(3, 1, 12, 100, 100);
  t.beginFrame(now, 100);
  now += 3;
  t.endFrame(now, 100);
  // the end listener never ran for this window (minimised window, lost context)
  t.beginRender(now);
  now += 12;
  t.beginFrame(now, 100);
  now += 40;
  // a later render end arrives before flixel drew again
  t.endRender(now);
  t.endFrame(now, 100);
  t.beginFrame(now + 1, 100);
  if (t.renderMs != 0) fail("stale render window counted: " + t.renderMs);
  t.endFrame(now + 4, 100);
  t.beginRender(now + 4);
  t.endRender(now + 6);
  t.beginFrame(now + 10, 100);
  if (Math.abs(t.renderMs - 2) > 0.001) fail("next render lost: " + t.renderMs);
''')


if __name__ == "__main__":
    unittest.main()
