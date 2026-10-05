"""Compare the source quant helper against the pinned donor algorithms and palette."""

import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from tools.tests.test_psych_character_scope import extract_method


ROOT = Path(__file__).resolve().parents[2]
DONOR_NOTE_UTIL = ROOT.parent / "fnf_sources/NightmareVision/source/funkin/utils/NoteUtil.hx"


def extract_array_literal(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("[", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "[":
            depth += 1
        elif source[index] == "]":
            depth -= 1
            if depth == 0:
                return source[opening:index + 1]
    raise AssertionError(f"unterminated array: {marker}")


MAIN = r'''class Main {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function sameColors(actual:Array<Int>,r:Int,g:Int,b:Int,message:String):Void
  check(actual.length==3 && actual[0]==r && actual[1]==g && actual[2]==b,message);
 static function expectError(action:Void->Void,fragment:String,message:String):Void {
  var error=""; try action() catch(value:Dynamic) error=Std.string(value);
  check(error.indexOf(fragment)>=0,message+": "+error);
 }
 static function main():Void {
  for(row in -384...385) {
   var candidates=[row/48.0,(row+0.49)/48.0,(row+0.51)/48.0,
    (row-0.49)/48.0,(row-0.51)/48.0];
   for(beat in candidates)
    check(NightmareVisionQuantColorCompat.getQuant(beat)==DonorNoteUtil.getQuant(beat),
     "beat grid differs from donor at "+beat);
  }
  // Tempo converts song time into the beat before this helper is called. Equal
  // beats at different tempos must therefore select the same donor quant.
  for(bpm in [60.0,90.0,120.0,240.0]) {
   var beat=7.375;
   var milliseconds=beat*60000.0/bpm;
   var restoredBeat=milliseconds*bpm/60000.0;
   check(NightmareVisionQuantColorCompat.getQuant(restoredBeat)==DonorNoteUtil.getQuant(beat),
    "quant lookup acquired an unintended BPM dependency");
  }
  for(quant in DonorNoteUtil.quants) {
   var donorIndex=DonorNoteUtil.quants.indexOf(quant);
   var donor=DonorNoteUtil.quantDefaultColors[donorIndex];
   var first=NightmareVisionQuantColorCompat.defaultColors(quant);
   sameColors(first,donor.r,donor.g,donor.b,"quant palette differs for "+quant);
   var independent=NightmareVisionQuantColorCompat.defaultColors(quant);
   check(first!=independent,"default quant palette must be a fresh array");
   first[0]=0;
   check(independent[0]==donor.r,"mutating a returned palette leaked into the helper");
  }
  expectError(function() NightmareVisionQuantColorCompat.defaultColors(6),
   "Unsupported quant subdivision", "unknown quant must fail explicitly");

  var prefs:Dynamic={arrowRGBquant:[[0xFF010203,0xFF040506,0xFF070809],[1,2,3]]};
  var pressed=NightmareVisionQuantColorCompat.pressedColors(prefs);
  sameColors(pressed,0xFF010203,0xFF040506,0xFF070809,
   "pressed receptor palette must read only the owner's first quant row");
  var pressedCopy=NightmareVisionQuantColorCompat.pressedColors(prefs);
  check(pressed!=pressedCopy,"pressed colors must be copied per caller");
  pressed[0]=0;
  check(prefs.arrowRGBquant[0][0]==0xFF010203 && pressedCopy[0]==0xFF010203,
   "pressed palette mutation leaked into owner preferences or another call");

  expectError(function() NightmareVisionQuantColorCompat.pressedColors(null),
   "Missing owner preferences", "missing owner preferences should be diagnosed");
  expectError(function() NightmareVisionQuantColorCompat.pressedColors({}),
   "arrowRGBquant must be an array", "missing preference table should be diagnosed");
  expectError(function() NightmareVisionQuantColorCompat.pressedColors({arrowRGBquant:[]}),
   "arrowRGBquant[0] must be an RGB array", "empty preference table should be diagnosed");
  expectError(function() NightmareVisionQuantColorCompat.pressedColors({arrowRGBquant:[[1,2]]}),
   "must contain three colors", "short preference row should be diagnosed");
  var invalidRow:Array<Dynamic>=[1,"bad",3];
  expectError(function() NightmareVisionQuantColorCompat.pressedColors({arrowRGBquant:[invalidRow]}),
   "must be an integer color", "invalid preference channel should be diagnosed");
  trace("NV_QUANT_COLORS_OK");
 }
}'''


class NightmareVisionQuantColorCompatTest(unittest.TestCase):
    def test_helper_matches_donor_grid_and_colors_without_shared_mutability(self):
        if not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        donor = DONOR_NOTE_UTIL.read_text(encoding="utf-8")
        quant_literal = extract_array_literal(donor, "public static final quants:Array<Int>")
        color_literal = extract_array_literal(donor, "public static var quantDefaultColors:Array<ColorList>")
        get_quant = extract_method(donor, "public static function getQuant(beat:Float)")
        get_quant = get_quant.replace("Conductor.beatToNoteRow", "DonorConductor.beatToNoteRow")
        get_quant = get_quant.replace("Conductor.ROWS_PER_MEASURE", "DonorConductor.ROWS_PER_MEASURE")
        donor_haxe = r'''typedef ColorList = { ?r:Int, ?g:Int, ?b:Int }
class DonorConductor {
 public static inline var ROWS_PER_BEAT:Int=48;
 public static inline var ROWS_PER_MEASURE:Int=192;
 public static inline function beatToNoteRow(beat:Float):Int return Math.round(beat*ROWS_PER_BEAT);
}
class DonorNoteUtil {
 public static final quants:Array<Int> = ''' + quant_literal + r''';
 public static var quantDefaultColors:Array<ColorList> = ''' + color_literal + ";\n" + get_quant + "\n}\n"
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(MAIN, newline="\n")
            (work / "DonorNoteUtil.hx").write_text(donor_haxe, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NV_QUANT_COLORS_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
