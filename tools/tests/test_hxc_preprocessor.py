"""Scripted classes only keep the `#if` branches a native desktop build compiles."""
from haxe_test_support import HAXE_COMMAND

import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


def run_main(main_source: str, *defines: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        (Path(folder) / "Main.hx").write_text(main_source, newline="\n")
        for name in ("HxcPreprocessor.hx", "HxcScriptIdentity.hx"):
            (Path(folder) / name).write_text((ROOT / "source" / name).read_text(encoding="utf-8"), newline="\n")
        extra = [part for define in defines for part in ("-D", define)]
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", folder, *extra, "-main", "Main", "--interp"],
            cwd=ROOT, capture_output=True, text=True,
        )


class HxcPreprocessorTest(unittest.TestCase):
    def test_branches_conditions_and_offsets(self):
        result = run_main(r'''class Main {
  static function fail(value:String):Void throw value;
  static function squash(value:String):String return StringTools.trim(~/\s+/g.replace(value, " "));
  static function main() {
    var defines = ["desktop" => "1", "haxe" => "4.3.0"];
    var nested = "a();\n#if desktop\n  b();\n  #if mobile\n  c();\n  #else\n  d();\n  #end\n#else\n  e();\n#end\nf();";
    var out = HxcPreprocessor.apply(nested, defines);
    if (squash(out) != "a(); b(); d(); f();") fail("nested: " + squash(out));
    if (out.length != nested.length || out.split("\n").length != nested.split("\n").length) fail("offsets moved");
    if (squash(HxcPreprocessor.apply("#if (mobile || web) x(); #elseif desktop y(); #else z(); #end", defines)) != "y();") fail("elseif");
    if (squash(HxcPreprocessor.apply("#if !(mobile || web) keep(); #end", defines)) != "keep();") fail("negated group");
    if (squash(HxcPreprocessor.apply("#if (desktop && !FEATURE_X) on(); #else off(); #end", defines)) != "on();") fail("unknown define is false");
    if (squash(HxcPreprocessor.apply("#if (haxe >= \"4.0.0\") new(); #else old(); #end", defines)) != "new();") fail("version compare");
    if (squash(HxcPreprocessor.apply("#if (haxe < \"4.0.0\") new(); #else old(); #end", defines)) != "old();") fail("version compare below");
    // Directives inside strings and comments are text, not blocks.
    var quoted = "#if mobile x(); #else trace('#end'); // #end\n y(); #end";
    if (squash(HxcPreprocessor.apply(quoted, defines)) != "trace('#end'); // #end y();") fail("quoted: " + squash(HxcPreprocessor.apply(quoted, defines)));
    if (HxcPreprocessor.apply("var c = '#'.code; x.y = 2;", defines) != "var c = '#'.code; x.y = 2;") fail("plain text changed");
    if (HxcPreprocessor.apply(null, defines) != null) fail("null source");
    if (!HxcPreprocessor.evaluate("desktop") || HxcPreprocessor.evaluate("mobile") || HxcPreprocessor.evaluate("web")) fail("engine defines");
  }
}
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_library_version_comparisons_use_the_build_versions(self):
        # Built against flixel 6: a script's 5.x fallback branch must lose.
        result = run_main(r'''class Main {
  static function fail(value:String):Void throw value;
  static function squash(value:String):String return StringTools.trim(~/\s+/g.replace(value, " "));
  static function main() {
    var out = HxcPreprocessor.apply("#if (flixel >= \"5.0.0\") modern(); #else legacy(); #end");
    if (squash(out) != "modern();") fail("flixel version: " + squash(out));
    if (!HxcPreprocessor.evaluate("flixel < \"7.0.0\"")) fail("flixel upper bound");
    if (!HxcPreprocessor.evaluate("haxe >= \"4.0.0\"")) fail("haxe version");
    if (!HxcPreprocessor.evaluate("openfl")) fail("library without a version is still defined");
  }
}
''', "flixel=6.1.2")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_class_scan_only_sees_the_desktop_branch(self):
        result = run_main(r'''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var source = "#if mobile\nclass Touch extends Module {}\n#else\nclass Desk extends Module {\n  function onCreate() {\n    #if mobile\n    touchOnly();\n    #end\n    shared();\n  }\n}\n#end\n";
    var classes = HxcScriptIdentity.classDeclarations(source);
    if (classes.length != 1 || classes[0].name != "Desk") fail("class list");
    if (classes[0].source.indexOf("touchOnly") >= 0) fail("mobile branch kept in class body");
    if (classes[0].source.indexOf("shared();") < 0) fail("desktop body lost");
    if (source.substring(classes[0].start, classes[0].start + 10) != "class Desk") fail("offsets point at the original");
    var identity = HxcScriptIdentity.inspect(source, "module", "Desk");
    if (identity == null || identity.family != "module") fail("identity");
  }
}
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_quote_inside_a_regex_literal_does_not_hide_directives(self):
        result = run_main(r'''class Main {
  static function fail(value:String):Void throw value;
  static function squash(value:String):String return StringTools.trim(~/\s+/g.replace(value, " "));
  static function main() {
    var defines = ["desktop" => "1"];
    // Read as a string, the apostrophe would run to the next quote and the
    // mobile branch would survive.
    var source = "var r = ~/it's/i;\n#if mobile\ntouch();\n#else\ndesk();\n#end\nvar q = 'x';";
    var out = squash(HxcPreprocessor.apply(source, defines));
    if (out != "var r = ~/it's/i; desk(); var q = 'x';") fail("regex: " + out);
    if (HxcPreprocessor.apply(source, defines).length != source.length) fail("offsets moved");
  }
}
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
