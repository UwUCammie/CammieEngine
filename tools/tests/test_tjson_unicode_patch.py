"""Regression coverage for the pinned TJSON Unicode preservation patch."""
from haxe_test_support import HAXE_COMMAND

import hashlib
import importlib.util
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
SPEC = importlib.util.spec_from_file_location(
    "patch_tjson_unicode", ROOT / "tools/patch_tjson_unicode.py"
)
PATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCHER)


FIXTURE = r'''import sys.io.File;
import tjson.TJSON;

class TJSONUnicodeFixture {
  static function expectString(value:Dynamic, expected:String, label:String):Void {
    if (!Std.isOfType(value, String) || (cast value:String) != expected)
      throw label + " did not round-trip: " + Std.string(value);
  }

  static function check(value:Dynamic):Void {
    expectString(Reflect.field(value, "Café 🎵"), "literal 🎶", "literal Unicode key/value");
    expectString(Reflect.field(value, "lowerHex"), "é", "lowercase hexadecimal escape");
    expectString(Reflect.field(value, "surrogatePair"), "🎵", "surrogate-pair escape");
    var rows:Array<Dynamic> = cast Reflect.field(value, "rows");
    if (rows == null || rows.length != 1)
      throw "trailing-comma array did not parse";
    expectString(Reflect.field(rows[0], "name"), "child 🎵", "literal astral child value");
  }

  static function main():Void {
    var input = File.getContent(Sys.args()[0]);
    var parsed:Dynamic = TJSON.parse(input, "unicode JSONC fixture");
    check(parsed);
    var encoded = TJSON.encode(parsed, "simple");
    var roundTrip:Dynamic = TJSON.parse(encoded, "unicode encoded fixture");
    check(roundTrip);
    Sys.println("unicode-roundtrip-ok");
  }
}
'''

UNICODE_JSONC = r'''{
  // Keep one leading space after this comment for TJSON's line scanner.
  'Café 🎵': 'literal 🎶',
  'lowerHex': '\u00e9',
  'surrogatePair': '\ud83c\udfb5',
  'rows': [
    {'name': 'child 🎵',},
  ],
}
'''


class TJSONUnicodePatchTest(unittest.TestCase):
    def test_pinned_patch_is_idempotent_and_rejects_source_drift(self):
        installed = PATCHER.TJSON_SOURCE.read_bytes()
        patched = PATCHER.patch_source(installed)

        self.assertEqual(hashlib.sha256(patched).hexdigest(), PATCHER.PATCHED_SHA256)
        self.assertEqual(PATCHER.patch_source(patched), patched)
        with self.assertRaisesRegex(ValueError, "differs from pinned"):
            PATCHER.patch_source(patched + b"// unexpected source drift\n")

    def test_haxe_parse_encode_preserves_literal_unicode_keys_and_escape_forms(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe is unavailable")

        patched = PATCHER.patch_source(PATCHER.TJSON_SOURCE.read_bytes())
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "tjson").mkdir()
            (work / "tjson/TJSON.hx").write_bytes(patched)
            (work / "TJSONUnicodeFixture.hx").write_text(FIXTURE, encoding="utf-8", newline='\n')
            input_file = work / "unicode.jsonc"
            input_file.write_text(UNICODE_JSONC, encoding="utf-8", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "TJSONUnicodeFixture", str(input_file)],
                cwd=ROOT,
                env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=60,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unicode-roundtrip-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
