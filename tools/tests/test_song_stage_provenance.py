"""Runtime-only stage provenance distinguishes inferred values from chart edits."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class SongStageProvenanceTest(unittest.TestCase):
    def test_only_editor_autosaves_restore_the_runtime_marker(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        source = (ROOT / "source/Song.hx").read_text()
        methods = "\n".join(
            extract_method(source, marker)
            for marker in (
                "static function chartHasValue(",
                "public static function parseJSONshit(",
            )
        )
        fixture = r'''
import haxe.Json;
using StringTools;
typedef SwagSong = Dynamic;
class CoolUtil {
 public static function parseJson(raw:String):Dynamic return Json.parse(raw);
}
class Main {
 static function attachCompatChartAccessors(_:Dynamic,__:String,___:String):Void {}
''' + methods + r'''
 static function main():Void {
  var autosave=parseJSONshit('{"song":{"stage":"spooky","compatStageAuthored":false}}',true);
  if(Reflect.field(autosave,"compatStageAuthored")!=false)
   throw "editor autosave lost inferred-stage provenance";
  var editedAutosave=parseJSONshit('{"song":{"stage":"spookyEvil","compatStageAuthored":true}}',true);
  if(Reflect.field(editedAutosave,"compatStageAuthored")!=true)
   throw "editor autosave lost an authored stage edit";
  var source=parseJSONshit('{"song":{"stage":"spooky","compatStageAuthored":false}}');
  if(Reflect.field(source,"compatStageAuthored")!=true)
   throw "ordinary chart JSON must treat its explicit stage field as authored";
  var spoof=parseJSONshit('{"song":{"compatStageAuthored":true}}');
  if(Reflect.field(spoof,"compatStageAuthored")!=false)
   throw "ordinary chart JSON spoofed runtime provenance";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(folder), "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
