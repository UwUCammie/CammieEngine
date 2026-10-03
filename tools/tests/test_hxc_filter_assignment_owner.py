"""Exercise the production camera-filter boundary with owned shader handles."""

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source: str, name: str) -> str:
    match = re.search(r"(?:public |static )*function " + re.escape(name) + r"\(", source)
    if match is None:
        raise AssertionError(name)
    start = match.start()
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(name)


class HxcFilterAssignmentOwnerTest(unittest.TestCase):
    def test_owned_handles_resolve_to_native_filters_and_invalid_values_drop(self):
        haxe = ROOT / ".tools/haxe/haxe"
        if not haxe.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        runtime = (ROOT / "source/HxcCompatRuntime.hx").read_text()
        play = (ROOT / "source/PlayState.hx").read_text()
        assign = method(runtime, "assignFilters")
        binding = method(play, "hxcRuntimeShaderBinding")
        resolver = method(play, "hxcResolveRuntimeShaderFilter")
        with tempfile.TemporaryDirectory(prefix="hxc-filter-owner-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            (scratch / "openfl/filters").mkdir(parents=True)
            (scratch / "openfl/filters/BitmapFilter.hx").write_text(
                "package openfl.filters; class BitmapFilter { public function new() {} }\n"
            , newline='\n')
            (scratch / "PlayState.hx").write_text(
                "import openfl.filters.BitmapFilter; using StringTools;\n"
                "class PlayState {\n"
                " public static var instance:PlayState;\n"
                " var hxcRuntimeShaderBindings:Map<String,Dynamic> = new Map();\n"
                " public function new() { instance = this; }\n"
                " public function add(handle:String,filter:Dynamic):Void "
                "hxcRuntimeShaderBindings.set(handle,{filter:filter});\n"
                + binding + "\n" + resolver + "\n}\n"
            , newline='\n')
            (scratch / "HxcCompatRuntime.hx").write_text(
                "class HxcCompatRuntime {\n"
                " static var activeState:Dynamic;\n"
                " public static function owner(value:Dynamic):Void activeState=value;\n"
                " static function resolveActiveState():Dynamic return PlayState.instance;\n"
                " static function runtimeField(value:Dynamic,name:String):Dynamic "
                "return Reflect.field(value,name);\n"
                + assign + "\n}\n"
            , newline='\n')
            (scratch / "Main.hx").write_text(
                "import openfl.filters.BitmapFilter;\n"
                "class Main {\n"
                " static function check(ok:Bool,message:String):Void if (!ok) throw message;\n"
                " static function main():Void {\n"
                "  var state=new PlayState(); HxcCompatRuntime.owner(state);\n"
                "  var native=new BitmapFilter(); var direct=new BitmapFilter();\n"
                "  state.add('hxc-shader-one',native);\n"
                "  var camera:Dynamic={filters:null};\n"
                "  HxcCompatRuntime.assignFilters(camera,"
                "['hxc-shader-one',null,'unknown',direct,23]);\n"
                "  check(camera.filters.length==2,'invalid entries reached the camera');\n"
                "  check(camera.filters[0]==native&&camera.filters[1]==direct,"
                "'owned filter identity/order changed');\n"
                "  HxcCompatRuntime.assignFilters(camera,[]);\n"
                "  check(camera.filters==null,'empty assignment did not clear filters');\n"
                " }\n}\n"
            , newline='\n')
            result = subprocess.run(
                [str(haxe), "-cp", str(scratch), "--interp", "-main", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
