"""Codename's runtime FlxKey values match Flixel's enum abstract."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CodenameFlxKeyFacadeTest(unittest.TestCase):
    def test_shift_and_none_match_native_codes(self):
        source = '''class Fixture {
 static function main() {
  var codes = CodenameFlxKeyFacade.snapshot();
  if (Reflect.field(codes, "SHIFT") != (flixel.input.keyboard.FlxKey.SHIFT : Int)
   || Reflect.field(codes, "NONE") != (flixel.input.keyboard.FlxKey.NONE : Int))
   throw "FlxKey facade code mismatch";
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Fixture.hx").write_text(source)
            env = os.environ.copy()
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["PATH"] = os.pathsep.join((str(ROOT / ".tools/haxe"),
                                             str(ROOT / ".tools/neko"), env.get("PATH", "")))
            env["LD_LIBRARY_PATH"] = os.pathsep.join((str(ROOT / ".tools/neko"),
                                                        env.get("LD_LIBRARY_PATH", "")))
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder,
                 "-cp", str(ROOT / "source"), "-lib", "flixel", "--run", "Fixture"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
