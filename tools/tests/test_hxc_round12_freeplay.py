"""Regression coverage for the mounted TAKEOVER Freeplay HXC modules."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
MODULE_ROOT = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules"
)
MODULES = {
    "catfight": MODULE_ROOT / "CatFightFreeplayFix.hxc",
    "doki": MODULE_ROOT / "FreeplayFixes.hxc",
    "preferences": MODULE_ROOT / "DokiPreferences.hxc",
}


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@unittest.skipUnless(
    HAXE.is_file() and all(path.is_file() for path in MODULES.values()),
    "portable Haxe toolchain or mounted TAKEOVER Freeplay HXC modules unavailable",
)
class MountedHxcRound12FreeplayTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-round12-freeplay-", dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            return subprocess.run(
                [
                    str(HAXE),
                    "-cp", str(ROOT / "source"),
                    "-cp", folder,
                    "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                    "-main", "Main", "--interp",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_mounted_freeplay_modules_are_bounded_and_donors_unchanged(self):
        before = {name: path.read_bytes() for name, path in MODULES.items()}
        catfight = hx_string(MODULES["catfight"].read_text(errors="ignore"))
        doki = hx_string(MODULES["doki"].read_text(errors="ignore"))
        catfight_path = hx_string(str(MODULES["catfight"]))
        doki_path = hx_string(str(MODULES["doki"]))
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var catfight = HxcCompat.analyze({catfight}, {catfight_path});
    var doki = HxcCompat.analyze({doki}, {doki_path});
    var preferences = HxcCompat.analyze({hx_string(MODULES["preferences"].read_text(errors="ignore"))}, {hx_string(str(MODULES["preferences"]))});
    if (!catfight.moduleSafe || !catfight.moduleInitializationSafe
      || hasCode(catfight, "unsupported-hxc-module-body")
      || hasCode(catfight, "unsupported-hxc-callback-body")
      || hasCode(catfight, "unsupported-hxc-script")
      || catfight.generatedHscript.indexOf("currentFreeplayState.grpCapsules") < 0
      || catfight.generatedHscript.indexOf("currentFreeplayState.hxcSelectedIndex") < 0
      || catfight.generatedHscript.indexOf("currentFreeplayState.curSelected") >= 0
      || catfight.generatedHscript.indexOf("hxcSubStateInit(\\\"CatfightPopup\\\")") < 0
      || catfight.generatedHscript.indexOf("HxcCompatRuntime.handleCatFightUpdate") >= 0
      || catfight.generatedHscript.indexOf("HxcCompatRuntime.setCatfightChoice") >= 0
      || catfight.generatedHscript.indexOf("__hxcStore") < 0
      || catfight.generatedHscript.indexOf("ScriptedMusicBeatSubState") >= 0)
      fail("generic Freeplay confirm bridge: " + catfight.moduleSafetyReasons.join(",")
        + "\\n" + catfight.generatedHscript);
    if (!doki.moduleSafe || !doki.moduleInitializationSafe
      || hasCode(doki, "unsupported-hxc-module-body")
      || hasCode(doki, "unsupported-hxc-callback-body")
      || hasCode(doki, "unsupported-hxc-script")
      || doki.generatedHscript.indexOf("HxcCompatRuntime.applyFreeplayCustomization(event.targetState, null") < 0
      || doki.generatedHscript.indexOf("HxcCompatRuntime.applyFreeplayCustomization(currentFreeplayState, event.capsule") < 0
      || doki.generatedHscript.indexOf("save = __hxcStore.getSave()") < 0
      || doki.generatedHscript.indexOf("freeplay/freeplayCapsule/takeoverweektypes") < 0
      || doki.generatedHscript.indexOf("applyDokiFreeplay") >= 0)
      fail("FreeplayFixes adapter: " + doki.moduleSafetyReasons.join(",")
        + "\\n" + doki.generatedHscript);
    if (!preferences.moduleInitializationSafe
      || preferences.generatedHscript.indexOf("seedStoreDefaults(__hxcStore, defaultOptions, \\\"TakeoverOptions\\\")") < 0)
      fail("authored preference defaults were not lowered generically: "
        + preferences.moduleSafetyReasons.join(",") + "\\n" + preferences.generatedHscript);
    new Parser().parseString(catfight.generatedHscript);
    new Parser().parseString(doki.generatedHscript);
    new Parser().parseString(preferences.generatedHscript);

    var freeplay = sys.io.File.getContent("source/FreeplayState.hx");
    if (freeplay.indexOf("refreshHxcConfirm") < 0
      || freeplay.indexOf("consumeFor(currentSongKey") < 0
      || freeplay.indexOf("public var hxcSelectedIndex(get, never):Int") < 0
      || freeplay.indexOf("public var hxcDifficultyIndex(get, set):Int") < 0
      || freeplay.indexOf("public var hxcCategoryId(get, set):String") < 0
      || freeplay.indexOf("hxcInstallCatfightConfirm") >= 0
      || freeplay.indexOf("catfight") >= 0
      || freeplay.indexOf("hxcApplyImportedFreeplayCustomization") < 0
      || freeplay.indexOf("hxcApplyDokiFreeplay") >= 0
      || freeplay.indexOf("hxcCatfightPopup") >= 0)
      fail("native Freeplay boundaries missing");
    Sys.println("round12-freeplay-mounted-ok");
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("round12-freeplay-mounted-ok", result.stdout)
        for name, path in MODULES.items():
            self.assertEqual(before[name], path.read_bytes(), f"donor changed: {{name}}")

    def test_partial_freeplay_graphs_remain_unsupported(self):
        main = '''import hscript.Parser;
class Main {
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }
  static function main() {
    var generic = HxcCompat.analyze(
      "class GenericConfirm extends Module { function onUpdate(event) { "
        + "var capsule = FlxG.state.subState.grpCapsules.members[FlxG.state.subState.curSelected]; "
        + "if (capsule != null && FlxG.state.subState.curSelected != 0 "
        + "&& FlxG.state.subState.curDifficulty >= 0 && capsule.freeplayData.data.id == 'other-song') "
        + "FlxG.state.subState.curCategory = 'other-category'; "
        + "capsule.onConfirm = function() { "
        + "FlxG.state.subState.persistentUpdate = false; "
        + "FlxG.state.subState.openSubState(ScriptedMusicBeatSubState.init('ChoiceState')); }; } }",
      "scripts/modules/generic-confirm.hxc");
    if (!generic.moduleSafe || !generic.moduleInitializationSafe
      || hasCode(generic, "unsupported-hxc-module-body")
      || hasCode(generic, "unsupported-hxc-callback-body")
      || generic.generatedHscript.indexOf("currentFreeplayState.grpCapsules") < 0
      || generic.generatedHscript.indexOf("currentFreeplayState.hxcSelectedIndex") < 0
      || generic.generatedHscript.indexOf("currentFreeplayState.hxcDifficultyIndex") < 0
      || generic.generatedHscript.indexOf("currentFreeplayState.hxcCategoryId") < 0
      || generic.generatedHscript.indexOf("currentFreeplayState.curSelected") >= 0
      || generic.generatedHscript.indexOf("currentFreeplayState.curDifficulty") >= 0
      || generic.generatedHscript.indexOf("currentFreeplayState.curCategory") >= 0
      || generic.generatedHscript.indexOf("hxcSubStateInit(\\\"ChoiceState\\\")") < 0
      || generic.generatedHscript.indexOf("CatfightPopup") >= 0)
      fail("generic prompt adapter: " + generic.moduleSafetyReasons.join(",")
        + "\\n" + generic.generatedHscript);

    var deepGraph = HxcCompat.analyze(
      "class UnsafeCapsule extends Module { function onUpdate(event) { "
        + "var capsule = FlxG.state.subState.grpCapsules.members[0]; "
        + "trace(capsule.freeplayData.data.untrustedGraph); } }",
      "scripts/modules/unsafe-capsule.hxc");
    if (deepGraph.moduleSafe || (!hasCode(deepGraph, "unsupported-hxc-module-body")
      && !hasCode(deepGraph, "unsupported-hxc-callback-body")))
      fail("unbounded capsule graph was whitelisted");

    var genericPreferences = HxcCompat.analyze(
      "class GenericOptions extends Module { "
        + "var defaults = { enabled: true, count: 3 }; "
        + "function new() { if (!Save.instance.modOptions.exists('engine-options')) "
        + "Save.instance.modOptions.set('engine-options', defaults); "
        + "Save.instance.flush(); save = Save.instance.modOptions.get('engine-options'); } "
        + "function readOptions() { return EnginePreferences.getEngineSave(); } }",
      "scripts/modules/generic-options.hxc");
    if (!genericPreferences.moduleInitializationSafe
      || genericPreferences.generatedHscript.indexOf("seedStoreDefaults(__hxcStore, defaults, \\\"engine-options\\\")") < 0
      || genericPreferences.generatedHscript.indexOf("__hxcStore.getSave()") < 0
      || genericPreferences.generatedHscript.indexOf("getEngineSave()") >= 0)
      fail("generic namespaced preference facade: "
        + genericPreferences.moduleSafetyReasons.join(",") + "\\n" + genericPreferences.generatedHscript);
    new Parser().parseString(genericPreferences.generatedHscript);

    var runtime = sys.io.File.getContent("source/HxcCompatRuntime.hx");
    var compat = sys.io.File.getContent("source/HxcCompat.hx");
    if (runtime.indexOf("gfCountdown") >= 0 || runtime.indexOf("getDokiSave") >= 0
      || compat.indexOf("DokiPreferences") >= 0 || compat.indexOf("TakeoverOptions") >= 0)
      fail("a donor-specific preference default remains in production compatibility code");
    Sys.println("round12-freeplay-safety-ok");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("round12-freeplay-safety-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
