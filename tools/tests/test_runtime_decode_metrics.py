"""Smoke-only bitmap timing retains cache semantics and bounded output."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_haxe_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated Haxe method: {marker}")


class RuntimeDecodeMetricsTest(unittest.TestCase):
    def test_disabled_reset_hits_and_misses(self):
        fixture = r'''
class Main {
 static function check(condition:Bool, message:String):Void {
  if (!condition) throw message;
 }
 static function main() {
  var cache:Map<String,String> = [];
  var lookup = function(key:String):String {
   var found = cache.get(key);
   if (found != null) RuntimeDecodeMetrics.recordHit();
   return found;
  };
  var next = 0;
  var load = function():String {
   next++;
   RuntimeDecodeMetrics.recordMiss(next == 2 ? 2.0 : 5.0);
   return 'bitmap-' + next;
  };
  var store = function(key:String, value:String):String {
   cache.set(key, value);
   return value;
  };
  RuntimeDecodeMetrics.reset(false);
  DiskBitmapCache.getOrLoad('sheet',true,lookup,load,store);
  var off:Dynamic = RuntimeDecodeMetrics.snapshot();
  check(off.bitmapCacheHits == 0 && off.bitmapCacheMisses == 0
   && off.bitmapDecodeMs == 0, 'disabled instrumentation counted a decode');
  RuntimeDecodeMetrics.reset(true);
  check(DiskBitmapCache.getOrLoad('sheet',true,lookup,load,store) == 'bitmap-1',
   'cache hit changed bitmap value');
  check(DiskBitmapCache.getOrLoad('sheet',false,lookup,load,store) == 'bitmap-2',
   'uncached request reused bitmap');
  check(DiskBitmapCache.getOrLoad('sheet',true,lookup,load,store) == 'bitmap-1',
   'uncached request overwrote cached bitmap');
  check(DiskBitmapCache.getOrLoad('sheet',false,lookup,load,store) == 'bitmap-3',
   'second uncached request reused bitmap');
  RuntimeDecodeMetrics.recordMiss(-7);
  var on:Dynamic = RuntimeDecodeMetrics.snapshot();
  check(on.bitmapCacheHits == 2 && on.bitmapCacheMisses == 3,
   'hit/miss accounting changed');
  check(on.bitmapDecodeMs == 7.0 && on.bitmapMaxDecodeMs == 5.0,
   'decode duration/max accounting changed');
  RuntimeDecodeMetrics.reset(false);
  var cleared:Dynamic = RuntimeDecodeMetrics.snapshot();
  check(cleared.bitmapCacheHits == 0 && cleared.bitmapCacheMisses == 0
   && cleared.bitmapDecodeMs == 0 && cleared.bitmapMaxDecodeMs == 0,
   'reset leaked metrics into the next song');
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            temporary = Path(folder)
            for name in ("RuntimeDecodeMetrics.hx", "DiskBitmapCache.hx"):
                shutil.copy(ROOT / "source" / name, temporary / name)
            (temporary / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_decode_and_phase_boundaries_are_instrumented(self):
        assets = (ROOT / "source/FNFAssets.hx").read_text()
        harness = (ROOT / "source/RuntimeSmokeHarness.hx").read_text()
        state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("RuntimeDecodeMetrics.recordHit();", assets)
        self.assertIn("BitmapData.fromFile(path)", assets)
        self.assertIn("RuntimeDecodeMetrics.recordMiss((Sys.time() - startedAt) * 1000)", assets)
        self.assertIn("RuntimeDecodeMetrics.reset(true);", harness)
        self.assertIn("RuntimeDecodeMetrics.reset(false);", harness)
        for phase in (
            "initial_characters",
            "events_normalized",
            "audio_paths_resolved",
            "instrument_loaded",
            "vocal_tracks_loaded",
            "note_generation_started",
            "first_note_constructed",
            "last_note_constructed",
            "chart_generated",
            "swap_characters_preloaded",
            "stage_loaded",
        ):
            self.assertIn(f"RuntimeSmokeHarness.markLoadPhase('{phase}');", state)
        self.assertIn("else if (noteConstructionCount % 256 == 0)", state)
        self.assertIn("RuntimeSmokeHarness.markLoadPhase('notes_constructed_' + noteConstructionCount);", state)
        self.assertIn("runSmokeNoteGenerationStep(daSection, authoredRowIndex,", state)
        self.assertIn("RuntimeSmokeHarness.markNoteGenerationFailure(sectionIndex, rowIndex,", state)
        for phase in ('head-constructor', 'head-legacy-row', 'head-psych-skin',
                      'head-smoke-visual', 'sustain-constructor', 'sustain-legacy-row',
                      'sustain-psych-skin', 'lift-constructor'):
            self.assertIn(f"'{phase}'", state)
        head_compat_phases = ('head-legacy-row', 'head-psych-skin', 'head-smoke-visual')
        phase_positions = [state.index(f"'{phase}'") for phase in head_compat_phases]
        self.assertEqual(phase_positions, sorted(phase_positions),
                         'head compatibility diagnostics must preserve operation order')
        for phase in head_compat_phases:
            self.assertIn(f"authoredSustain, 'head', 0, '{phase}', function():Dynamic", state)
        self.assertIn("if (traceNoteConstruction)\n\t\t\t\t\t\tswagNote = cast runSmokeNoteGenerationStep", state)
        self.assertIn("authoredTime:Dynamic = traceNoteConstruction", state)
        self.assertIn("authoredLane:Dynamic = traceNoteConstruction", state)
        self.assertIn("authoredSustain:Dynamic = traceNoteConstruction", state)
        self.assertIn("throw error;", state)
        failure_marker = "public static function markNoteGenerationFailure("
        self.assertIn(failure_marker, harness)
        failure_method = harness[harness.index(failure_marker):]
        for field in ('section: section', 'row: row', 'authoredTime: authoredTime',
                      'authoredLane: authoredLane', 'authoredSustain: authoredSustain',
                      'objectKind: objectKind', 'objectIndex: objectIndex', 'phase: phase', 'error: error'):
            self.assertIn(field, failure_method)
        ordered_phases = (
            "events_normalized",
            "audio_paths_resolved",
            "instrument_loaded",
            "vocal_tracks_loaded",
            "note_generation_started",
            "first_note_constructed",
            "last_note_constructed",
        )
        positions = [state.index(f"RuntimeSmokeHarness.markLoadPhase('{phase}');") for phase in ordered_phases]
        self.assertEqual(positions, sorted(positions), "chart generation phase markers moved out of order")

    @unittest.skipUnless((ROOT / ".tools/haxe/haxe").is_file(), "portable Haxe is unavailable")
    def test_smoke_note_failure_context_rethrows_the_same_error(self):
        state = (ROOT / "source/PlayState.hx").read_text()
        helper = extract_haxe_method(state, "private function runSmokeNoteGenerationStep(")
        helper = helper.replace("private function", "static function", 1)
        fixture = """
class RuntimeSmokeHarness {
 static public var marked:Dynamic;
 static public function markNoteGenerationFailure(section:Int, row:Int, authoredTime:String,
  authoredLane:String, authoredSustain:String, objectKind:String, objectIndex:Int,
  phase:String, error:String):Void {
  marked = {section: section, row: row, authoredTime: authoredTime,
   authoredLane: authoredLane, authoredSustain: authoredSustain, objectKind: objectKind,
   objectIndex: objectIndex, phase: phase, error: error};
 }
}
class Main {
""" + helper + """
 static function main():Void {
  var original:Dynamic = {message: 'original'};
  var observed:Dynamic = null;
  try runSmokeNoteGenerationStep(4, 12, '18000', '4', '247.3958', 'sustain', 2,
   'sustain-constructor', function():Dynamic throw original)
  catch (error:Dynamic) observed = error;
  if (observed != original) throw 'failure object was replaced';
  if (RuntimeSmokeHarness.marked.section != 4 || RuntimeSmokeHarness.marked.row != 12
   || RuntimeSmokeHarness.marked.authoredLane != '4'
   || RuntimeSmokeHarness.marked.objectKind != 'sustain'
   || RuntimeSmokeHarness.marked.objectIndex != 2
   || RuntimeSmokeHarness.marked.phase != 'sustain-constructor'
   || RuntimeSmokeHarness.marked.error.indexOf('original') < 0)
   throw 'failure context was incomplete';
 }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "-main", "Main", "--interp"],
                cwd=folder, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
