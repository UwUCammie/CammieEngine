"""Freeplay builds queued row icons inside a per-frame time box."""
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_native_asset_resolution import extract_method

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class FreeplayIconBuildBudgetTest(unittest.TestCase):
    def test_budget_stops_on_time_but_always_runs_one_item(self):
        fixture = r'''class FrameBudgetFixture {
 static function fail(message:String):Void throw message;
 static var now:Float = 100.0;
 static function drain(budget:FrameBudget, queued:Int, cost:Float):Int {
  budget.restart();
  var ran = 0;
  while (queued > 0 && budget.next()) { queued--; ran++; now += cost; }
  return ran;
 }
 static function main() {
  var budget = new FrameBudget(0.003, 4, function() return now);
  if (drain(budget, 10, 0.002) != 2) fail("2 ms builds in a 3 ms box must run twice");
  if (drain(budget, 10, 0.050) != 1) fail("a slow build must be the only one that frame");
  if (drain(budget, 10, 0.0) != 4) fail("free builds must still stop at the item cap");
  if (drain(budget, 3, 0.0) != 3) fail("a short queue must drain fully");
  if (drain(budget, 0, 0.0) != 0) fail("an empty queue ran something");
  // The first item is never refused, so the queue cannot stall.
  var tiny = new FrameBudget(0, 0, function() return now);
  if (drain(tiny, 5, 0.001) != 1) fail("a zero budget must still make progress");
  // Without an item cap only time limits the batch.
  var open = new FrameBudget(0.010, 0, function() return now);
  if (drain(open, 100, 0.001) != 10) fail("uncapped budget ignored its time box");
  // A clock that steps backwards ends the batch instead of running forever.
  var back = new FrameBudget(0.003, 0, function() return now);
  back.restart();
  if (!back.next()) fail("first item refused");
  now -= 5;
  if (back.next()) fail("a backwards clock allowed more work");
  if (back.count() != 1) fail("count is off");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / "FrameBudgetFixture.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / "source"), "--run", "FrameBudgetFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_icon_drain_uses_the_budget_and_lays_out_once(self):
        source = (ROOT / "source/FreeplayState.hx").read_text(encoding="utf-8")
        self.assertIn("var iconBuildBudget:FrameBudget = new FrameBudget(0.003, 4);", source)
        start = source.index("iconBuildBudget.restart();")
        drain = source[start:source.index("RuntimeSmokeHarness.profileSection('fp-update-icons'", start)]
        self.assertIn("while (iconQueue.length > 0 && iconBuildBudget.next())", drain)
        self.assertIn("buildIconFor(iconQueue.shift(), true)", drain)
        self.assertEqual(drain.count("applyListLayout();"), 1)
        self.assertLess(drain.index("buildIconFor("), drain.index("applyListLayout();"))
        self.assertIn("if (builtIcons && denseBrowser)", drain)
        self.assertNotIn("buildBudget--", source)
        build = extract_method(source, "function buildIconFor(")
        # A batch defers its layout; a single direct build still lays out.
        self.assertIn("if (denseBrowser && !deferLayout) { applyListLayout(); updateBrowserDetails(); }", build)
        self.assertIn("return false;", build)

    def test_library_refresh_reports_each_part_to_the_profiler(self):
        source = (ROOT / "source/FreeplayState.hx").read_text(encoding="utf-8")
        refresh = extract_method(source, "function reloadAfterImport(")
        sections = ["fp-refresh-rows", "fp-refresh-selection", "fp-refresh-import-availability",
                    "fp-refresh-availability", "fp-refresh-stars",
                    "fp-refresh-filter", "fp-refresh-hxc", "fp-refresh-layout"]
        positions = [refresh.index("profileSection('" + name + "'") for name in sections]
        self.assertEqual(positions, sorted(positions))
        # Timing is only taken when the harness is profiling.
        self.assertIn("var refreshProfile = RuntimeSmokeHarness.enabled();", refresh)
        self.assertEqual(refresh.count("if (refreshProfile)"), len(sections))
        # The forced availability pass inside the refresh is split further.
        availability = extract_method(source, "function refreshImportAvailability(")
        self.assertIn("var availabilityProfile = force && RuntimeSmokeHarness.enabled();", availability)
        parts = [availability.index("profileSection('" + name + "'")
                 for name in ("fp-avail-reconcile", "fp-avail-rows", "fp-avail-layout")]
        self.assertEqual(parts, sorted(parts))

    def test_library_refresh_compares_each_character_definition_once(self):
        source = (ROOT / "source/FreeplayState.hx").read_text(encoding="utf-8")
        refresh = extract_method(source, "function reloadAfterImport(")
        self.assertNotIn("Json.stringify(Reflect.field(oldChars", refresh)
        self.assertIn("characterDefinitionChanged(definitionChanges, oldChars, oldIconDefinitions, old.songCharacter, song.songCharacter)", refresh)
        helper = extract_method(source, "function characterDefinitionChanged(")
        fixture = r'''class DefinitionMemoFixture {
 static function fail(message:String):Void throw message;
 var charJson:Dynamic;
 var iconJson:Dynamic;
 function new() {}
 ''' + helper + r'''
 static function main() {
  var host = new DefinitionMemoFixture();
  var oldChars:Dynamic = {bf: {scale: 1}, dad: {scale: 1}};
  var oldIcons:Dynamic = {bf: {frames: 2}, dad: {frames: 2}};
  host.charJson = {bf: {scale: 1}, dad: {scale: 2}};
  host.iconJson = {bf: {frames: 2}, dad: {frames: 2}};
  var memo:Map<String, Bool> = new Map();
  for (round in 0...3) {
   if (host.characterDefinitionChanged(memo, oldChars, oldIcons, "bf", "bf")) fail("unchanged bf reported");
   if (!host.characterDefinitionChanged(memo, oldChars, oldIcons, "dad", "dad")) fail("changed dad missed");
  }
  if (!host.characterDefinitionChanged(memo, oldChars, oldIcons, "bf", "dad")) fail("renamed character missed");
  host.iconJson = {bf: {frames: 3}, dad: {frames: 2}};
  if (!host.characterDefinitionChanged(new Map(), oldChars, oldIcons, "bf", "bf")) fail("icon change missed");
  if (host.characterDefinitionChanged(new Map(), oldChars, oldIcons, "missing", "missing")) fail("absent on both sides");
  Sys.println("OK");
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / "DefinitionMemoFixture.hx").write_text(
                "import haxe.Json;\n" + fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "--run", "DefinitionMemoFixture"],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
