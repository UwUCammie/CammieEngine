"""C++ codegen regression for mixed note rows sorted by the real comparator.

The Haxe interpreter does not reproduce hxcpp's inference of untyped sort
parameters as Array<Int>. Inspect generated C++ and check row values in the
interpreter. A separate game probe covers the actual native runtime path.
"""
from haxe_test_support import HAXE_COMMAND

import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def section_sort(importer: str) -> str:
    source = (ROOT / "source" / importer).read_text()
    start = source.index("sectionNotes.sort(function", source.index("static function buildSections"))
    end = source.index(");", start) + 2
    return source[start:end]


class ImporterNoteSortCppCodegenTest(unittest.TestCase):
    def test_real_section_comparators_keep_mixed_rows_in_cpp_codegen(self):
        if not HAXE.is_file() or not (ROOT / ".haxelib/hxcpp/4,3,2").is_dir():
            self.skipTest("portable Haxe/hxcpp toolchain is unavailable")
        codename_sort = section_sort("CodenameImporter.hx")
        vslice_sort = section_sort("VSliceImporter.hx")
        source = f'''class Main {{
  static function fail(message:String):Void throw message;
  static function input():Array<Dynamic> {{
    return [
      [100.25, 0, 0, null, null, null, null, null, null, null, null, null, null, {{id:"late"}}],
      [100.0625, 45, 12.375, 1, null, null, null, null, null, null, null, null, null, {{id:"early"}}],
      [100.125, 4, 0, null, null, null, null, null, null, null, null, null, null, {{id:"middle"}}]
    ];
  }}
  static function check(rows:Array<Dynamic>, label:String):Void {{
    if (rows.length != 3 || rows[0][0] != 100.0625 || rows[1][0] != 100.125
        || rows[2][0] != 100.25) fail(label + ": fractional sort order changed");
    if (rows[0][1] != 45 || rows[0][2] != 12.375 || rows[0][3] != 1
        || rows[0][4] != null || rows[0][13].id != "early"
        || rows[1][13].id != "middle" || rows[2][13].id != "late")
      fail(label + ": mixed native note row coerced");
  }}
  static function codename(rows:Array<Dynamic>):Array<Dynamic> {{
    var sectionNotes:Array<Dynamic> = rows.copy();
    {codename_sort}
    return sectionNotes;
  }}
  static function vslice(rows:Array<Dynamic>):Array<Dynamic> {{
    var sectionNotes:Array<Dynamic> = rows.copy();
    {vslice_sort}
    return sectionNotes;
  }}
  static function main():Void {{
    check(codename(input()), "codename");
    check(vslice(input()), "vslice");
    Sys.println("NOTE_SORT_ROWS_OK");
  }}
}}
'''
        # The checkout path contains spaces and hxcpp's Build.xml parser splits
        # several absolute include paths. Haxe's no-compilation mode still
        # emits the exact C++ types without invoking that parser.
        with tempfile.TemporaryDirectory(prefix="codename-note-sort-", dir=ROOT / "tmp") as folder:
            work = Path(folder)
            env = os.environ.copy()
            env["HAXEPATH"] = str(ROOT / ".tools/haxe")
            env["NEKOPATH"] = str(ROOT / ".tools/neko")
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["PATH"] = os.pathsep.join((env["HAXEPATH"], env["NEKOPATH"], env.get("PATH", "")))
            env["LD_LIBRARY_PATH"] = os.pathsep.join((env["NEKOPATH"], env.get("LD_LIBRARY_PATH", "")))
            (work / "Main.hx").write_text(source, newline='\n')
            compile_result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "-main", "Main", "-cpp", str(work / "cpp"),
                 "-D", "no-compilation"],
                cwd=work, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(compile_result.returncode, 0,
                             compile_result.stdout + compile_result.stderr)
            generated = (work / "cpp/src/Main.cpp").read_text()
            for method in ("codename", "vslice"):
                body = generated[generated.index(f"Main_obj::{method}("):]
                self.assertIn("int _hx_run(::cpp::VirtualArray a,::cpp::VirtualArray b)",
                              body[:600], f"{method} comparator lost dynamic row typing")
            legacy = source.replace("function(a:Array<Dynamic>, b:Array<Dynamic>)", "function(a,b)")
            (work / "Main.hx").write_text(legacy, newline='\n')
            legacy_result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "-main", "Main", "-cpp", str(work / "cpp-legacy"),
                 "-D", "no-compilation"],
                cwd=work, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(legacy_result.returncode, 0,
                             legacy_result.stdout + legacy_result.stderr)
            legacy_generated = (work / "cpp-legacy/src/Main.cpp").read_text()
            for method in ("codename", "vslice"):
                body = legacy_generated[legacy_generated.index(f"Main_obj::{method}("):]
                self.assertIn("int _hx_run(::Array< int > a,::Array< int > b)", body[:600],
                              f"{method} negative control no longer reproduces hxcpp coercion")
            (work / "Main.hx").write_text(source, newline='\n')
            interpreted = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "-main", "Main", "--interp"],
                                          cwd=work, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(interpreted.returncode, 0, interpreted.stdout + interpreted.stderr)
            self.assertIn("NOTE_SORT_ROWS_OK", interpreted.stdout)


if __name__ == "__main__":
    unittest.main()
