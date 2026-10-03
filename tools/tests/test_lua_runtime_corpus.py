"""Regression coverage for the shared Psych/Kade Lua runtime boundary.

The mounted donor tree is intentionally treated as read-only input.  These
tests exercise the production adapters with a small synthetic Haxe fixture and
then translate every mounted Lua script so the compatibility count stays
visible when the corpus or importer changes.
"""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


class LuaRuntimeCorpusTest(unittest.TestCase):
    def run_haxe(self, source, name, args=(), hscript=False):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            folder = Path(folder)
            (folder / f"{name}.hx").write_text(source, newline='\n')
            command = [*HAXE_COMMAND, "-cp", str(folder), "-cp", str(ROOT / "source")]
            if hscript:
                command += ["-cp", str(HSCRIPT)]
            # `--interp` treats trailing paths as compiler arguments. `--run`
            # is the portable interpreter mode which forwards them to Sys.args.
            command += ["--run", name, *map(str, args)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

    def test_engine_compat_callback_and_property_adapters(self):
        fixture = r'''
class EngineCompatSmoke {
  static function check(value:Bool, message:String) {
    if (!value) throw message;
  }
  static function main() {
    check(EngineCompat.functionStop(true), "boolean stop");
    check(EngineCompat.functionStop("Function_Stop"), "string stop");
    check(!EngineCompat.functionStop(false), "continue is not stop");
    check(EngineCompat.functionContinue(false), "boolean continue");
    check(EngineCompat.anyFunctionStop([false, "Function_Stop"]), "broadcast stop");
    check(!EngineCompat.anyFunctionStop([false, "Function_Continue"]), "broadcast continue");

    var missNames = EngineCompat.callbackNames("noteMiss");
    check(missNames.indexOf("onMissNote") >= 0, "onMissNote alias");
    var noteArgs = EngineCompat.callbackArguments("noteMiss", "onMissNote",
      [{ID: 17, noteData: 2, isSustainNote: false}, true, 2], false);
    check(noteArgs.length == 1 && noteArgs[0] == 17, "onMissNote id ABI");

    var eventArgs = EngineCompat.callbackArguments("onEvent", "onEvent",
      ["Flash", "0.2", "1", "extended"], false);
    check(eventArgs.length == 3 && eventArgs[2] == "1", "onEvent ABI");

    var ordinaryEnd = EngineCompat.callbackArguments("songEnd", "onEndSong",
      [EngineCompat.hxcLifecyclePayload("songEnd")], false);
    check(ordinaryEnd.length == 0, "ordinary onEndSong ABI");
    var hxcPayload = EngineCompat.hxcLifecyclePayload("songEnd");
    var hxcEnd = EngineCompat.callbackArguments("songEnd", "onSongEnd", [hxcPayload], true);
    check(hxcEnd.length == 1 && hxcEnd[0] == hxcPayload, "HXC songEnd payload");

    check(EngineCompat.legacyClassProperty("backend.ClientPrefs", "data.sickWindow") == "sickWindow",
      "ClientPrefs sickWindow");
    for (name in ["ratingOffset", "goodWindow", "badWindow", "shitWindow"])
      check(EngineCompat.legacyClassProperty("ClientPrefs", name) == name
        && EngineCompat.legacyClassProperty("backend.ClientPrefs", "data." + name) == name,
        "ClientPrefs timing field " + name);
    check(EngineCompat.legacyClassProperty("ClientPrefs", "splashAlpha") == "splashAlpha",
      "ClientPrefs splashAlpha");
    check(EngineCompat.legacyClassProperty("PlayState", "isPixelStage") == "isPixelStage",
      "PlayState isPixelStage");
  }
}
'''
        self.run_haxe(fixture, "EngineCompatSmoke")

    def test_lua_compat_synthetic_psych_callbacks(self):
        fixture = r'''
class LuaCompatSmoke {
  static function main() {
    var source = "function onStartCountdown()\n  return Function_Stop\nend\n"
      + "function onEvent(name, value1, value2)\n"
      + "  debugPrint(name, value1)\nend\n";
    var result = LuaCompat.translate(source, "synthetic.lua");
    if (!result.supported) throw result.diagnostics.join("\\n");
    if (result.hscript.indexOf("onStartCountdown") < 0) throw "callback was dropped";
    if (result.hscript.indexOf("Function_Stop") < 0) throw "sentinel was dropped";
    new hscript.Parser().parseString(result.hscript);
  }
}
'''
        self.run_haxe(fixture, "LuaCompatSmoke", hscript=True)

    def test_user_documentation_matches_the_current_corpus_gate(self):
        """Do not leave the prior 121/122 diagnostic state in user docs."""
        readme = (ROOT / "README.md").read_text()
        update_log = (ROOT / "updateLog.txt").read_text()
        report = (ROOT / "tools/reports/lua-runtime-corpus.md").read_text()
        for stale in ("121/122", "121 clean", "121 now translate"):
            self.assertNotIn(stale, readme)
            self.assertNotIn(stale, update_log)
        self.assertIn("122/122 clean", readme)
        self.assertIn("| Files translated without diagnostics | 121 | 122 |", report)

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_corpus_translation_count(self):
        fixture = r'''
using StringTools;
import sys.FileSystem;
import sys.io.File;
class LuaCorpusScan {
  static function collect(path:String, output:Array<String>):Void {
    for (entry in FileSystem.readDirectory(path)) {
      var child = path + "/" + entry;
      if (FileSystem.isDirectory(child)) collect(child, output);
      else if (entry.toLowerCase().endsWith(".lua")) output.push(child);
    }
  }
  static function main() {
    var files:Array<String> = [];
    collect(Sys.args()[0], files);
    var supported = 0;
    var unsupported = 0;
    var rawHaxeFiles = 0;
    var rawHaxeOccurrences = 0;
    for (path in files) {
      var result = LuaCompat.translate(File.getContent(path), path);
      if (result.supported) supported++; else unsupported++;
      var hasRaw = false;
      for (diagnostic in result.diagnostics)
        if (diagnostic.indexOf("lua-raw-haxe") >= 0) {
          hasRaw = true;
          rawHaxeOccurrences++;
        }
      if (hasRaw) rawHaxeFiles++;
    }
    Sys.println("FILES=" + files.length);
    Sys.println("SUPPORTED=" + supported);
    Sys.println("UNSUPPORTED=" + unsupported);
    Sys.println("RAW_HAXE_FILES=" + rawHaxeFiles);
    Sys.println("RAW_HAXE_DIAGNOSTICS=" + rawHaxeOccurrences);
  }
}
'''
        output = self.run_haxe(fixture, "LuaCorpusScan", args=(DONOR,), hscript=True)
        values = dict(re.findall(r"^(FILES|SUPPORTED|UNSUPPORTED|RAW_HAXE_FILES|RAW_HAXE_DIAGNOSTICS)=(\d+)$",
                                 output, re.MULTILINE))
        # The mounted donor set changes as mods are added and removed; the
        # invariant is a fully clean corpus, not a fixed file count.
        self.assertGreater(int(values["FILES"]), 0)
        self.assertEqual(values["FILES"], values["SUPPORTED"])
        self.assertEqual(values["UNSUPPORTED"], "0")
        self.assertEqual(values["RAW_HAXE_FILES"], "0")
        self.assertEqual(values["RAW_HAXE_DIAGNOSTICS"], "0")

        lua_files = [path for path in DONOR.rglob("*.lua")]
        self.assertEqual(len(lua_files), int(values["FILES"]))
        zero_loop = re.compile(r"runTimer\s*\([^\n)]*,[^\n)]*,\s*0\s*\)", re.IGNORECASE)
        self.assertGreaterEqual(sum(len(zero_loop.findall(path.read_text(errors="ignore"))) for path in lua_files), 8)

        callbacks = {
            # Keep known script surfaces present as the mounted corpus grows.
            "onEvent": 19,
            "onEndSong": 1,
            "onGameOverStart": 1,
            "onMissNote": 1,
        }
        for callback, expected in callbacks.items():
            pattern = re.compile(r"function\s+" + re.escape(callback) + r"\s*\(", re.IGNORECASE)
            self.assertGreaterEqual(sum(len(pattern.findall(path.read_text(errors="ignore"))) for path in lua_files),
                                    expected, callback)


if __name__ == "__main__":
    unittest.main()
