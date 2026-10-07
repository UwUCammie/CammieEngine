"""Exercise the shared JSON printer against the pinned TJSON parser."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP

import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe" / ("haxe.exe" if os.name == "nt" else "haxe")
SOURCE = ROOT / "source"
TJSON = ROOT / ".haxelib/tjson/1,4,0"


FIXTURE = r'''import tjson.TJSON;

class UnicodeSafeJsonFixtureClass {
  public var label:String;
  public function new(label:String) this.label = label;
}

class UnicodeSafeJsonFixture {
  static function check(condition:Bool, message:String):Void {
    if (!condition) throw message;
  }

  static function expectString(value:Dynamic, expected:String, message:String):Void {
    check(Std.isOfType(value, String) && (cast value:String) == expected,
      message + ": " + Std.string(value));
  }

  static function main():Void {
    var controls = "before" + String.fromCharCode(8) + "middle" + String.fromCharCode(12) + "after";
    var tjsonText = UnicodeSafeJson.stringify({value: controls});
    check(tjsonText.indexOf("\\u0008") >= 0, "backspace was not emitted as a TJSON-supported Unicode escape");
    check(tjsonText.indexOf("\\u000C") >= 0, "form-feed was not emitted as a TJSON-supported Unicode escape");
    check(tjsonText.indexOf("\\b") < 0 && tjsonText.indexOf("\\f") < 0,
      "TJSON-incompatible short control escapes were emitted");
    var tjsonValue:Dynamic = TJSON.parse(tjsonText, "UnicodeSafeJson TJSON control round-trip");
    expectString(Reflect.field(tjsonValue, "value"), controls, "TJSON control characters did not round-trip");

    var shared = {label: "shared value"};
    var standardText = UnicodeSafeJson.stringifyStandard({
      instance: new UnicodeSafeJsonFixtureClass("class fields"),
      first: shared,
      second: shared,
      controls: controls
    });
    check(standardText.indexOf("_hxcls") < 0, "standard JSON unexpectedly emitted TJSON class metadata");
    check(standardText.indexOf("@~obRef#") < 0, "standard JSON unexpectedly emitted TJSON reference markers");
    var standardValue:Dynamic = haxe.Json.parse(standardText);
    expectString(Reflect.field(Reflect.field(standardValue, "instance"), "label"),
      "class fields", "standard JSON class-field metadata did not round-trip");
    expectString(Reflect.field(Reflect.field(standardValue, "first"), "label"),
      "shared value", "standard JSON first repeated object did not round-trip");
    expectString(Reflect.field(Reflect.field(standardValue, "second"), "label"),
      "shared value", "standard JSON second repeated object did not round-trip");
    expectString(Reflect.field(standardValue, "controls"), controls,
      "standard JSON controls did not round-trip");
    Sys.println("unicode-safe-json-roundtrip-ok");
  }
}
'''


class UnicodeSafeJsonTest(unittest.TestCase):
    def test_tjson_control_round_trip_and_standard_json_extensions(self):
        if not HAXE.is_file() or not TJSON.is_dir():
            self.skipTest("portable Haxe or pinned TJSON is unavailable")

        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="unicode-safe-json-", dir=TEST_TMP) as directory:
            work = Path(directory)
            (work / "UnicodeSafeJsonFixture.hx").write_text(FIXTURE, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(SOURCE), "-cp", str(TJSON), "-cp", str(work),
                 "--run", "UnicodeSafeJsonFixture"],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(TEST_TMP)},
                capture_output=True,
                text=True,
                timeout=60,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unicode-safe-json-roundtrip-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
