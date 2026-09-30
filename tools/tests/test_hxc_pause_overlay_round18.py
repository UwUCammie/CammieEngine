"""Round 18: bounded native HXC pause-overlay specs and cleanup boundaries."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
DOKI = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/SUBSTATES/DokiPause.hxc"


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


class HxcPauseOverlayRound18Test(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            command = [
                str(HAXE),
                "-cp", str(ROOT / "source"),
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp", folder,
                "-main", "Main", "--interp",
            ]
            return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)

    def test_renamed_complete_pause_helper_lowers_only_data_and_native_boundary(self):
        source = r'''
class RenamedPauseOverlay extends Module {
    var targetPauseState = null;
    var metadata;
    var menuEntryText;
    var currentMenuEntries = [];
    var itmColor:Int = 0xFFFF7CFF;
    var selColor:Int = 0xFFFFCFFF;
    function createUniversalMenu() {
        var logo = new FlxSprite(-260, 0).loadGraphic(Paths.image("PauseLogo"));
        var atlas = Paths.getSparrowAtlas("PauseAtlas");
        var info = new FlxText(0, 15, 0, "Song", 32);
        info.setFormat(Paths.font("Title.ttf"), 32);
        var menuFont = Paths.font("Menu.ttf");
        for (entry in currentMenuEntries) if (entry.text == "Change Difficulty") trace(entry.text);
    }
    function onSubStateOpenEnd(event) {
        if (Std.isOfType(event.targetState, PauseSubState)) {
            targetPauseState = event.targetState;
            targetPauseState.remove(metadata);
            targetPauseState.remove(menuEntryText);
            var art = Paths.image("pause/" + PlayState.SONG.player2);
            createUniversalMenu();
        }
    }
    function onSubStateCloseBegin(event) {
        targetPauseState = null;
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function has(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "synthetic/renamed/substates/Pause.hxc");
    if (result.kind != "module" || result.pauseSpec == null) fail("pause spec missing: " + result.kind);
    if (!result.moduleSafe || !result.moduleInitializationSafe) fail("module safety");
    if (has(result, "unsupported-hxc-module-body") || has(result, "unsupported-hxc-callback-body")) fail("partial pause warning");
    if (!has(result, "hxc-pause-overlay-adapter")) fail("pause diagnostic missing");
    if (result.generatedHscript.indexOf("applyPauseOverlay") < 0
      || result.generatedHscript.indexOf("clearPauseOverlay") < 0) fail("native pause boundary missing: " + result.generatedHscript);
    if (result.generatedHscript.indexOf("currentMenuEntries") >= 0
      || result.generatedHscript.indexOf("menuEntryText") >= 0
      || result.generatedHscript.indexOf("metadata") >= 0
      || result.generatedHscript.indexOf("new FlxSprite") >= 0
      || result.generatedHscript.indexOf("FlxG.state") >= 0
      || result.generatedHscript.indexOf("Application.current.window.close") >= 0) fail("donor graph leaked: " + result.generatedHscript);
    var spec:Dynamic = result.pauseSpec;
    if (spec.artPrefix != "pause/" || spec.logo != "PauseLogo" || spec.atlas != "PauseAtlas") fail("literal config missing");
    if (spec.hiddenLabels.length != 1 || spec.hiddenLabels[0] != "Change Difficulty") fail("hidden label missing");
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_partial_pause_shape_stays_diagnosed(self):
        source = r'''
class PartialPause extends Module {
    var targetPauseState = null;
    function createUniversalMenu() { var art = Paths.image("pause/" + PlayState.SONG.player2); }
    function onSubStateOpenEnd(event) { targetPauseState = event.targetState; }
}
'''
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "synthetic/renamed/substates/Partial.hxc");
    if (result.pauseSpec != null) fail("partial pause was accepted");
    var found = false;
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-module-body") found = true;
    if (!found) fail("partial pause warning missing");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_doki_pause_is_read_only_and_parseable(self):
        if not DOKI.exists():
            self.skipTest("DokiPause donor is not mounted")
        before = DOKI.read_bytes()
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(DOKI.read_text(errors="ignore"))}, "{DOKI.as_posix()}");
    if (result.pauseSpec == null) fail("mounted pause spec missing");
    new Parser().parseString(result.generatedHscript);
    if (result.generatedHscript.indexOf("currentMenuEntries") >= 0) fail("metadata graph emitted");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(DOKI.read_bytes(), before, "DokiPause donor changed")

    def test_runtime_boundary_is_noop_without_native_owner_and_host_owns_cleanup(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    HxcCompatRuntime.clear();
    if (HxcCompatRuntime.applyPauseOverlay(null, "assets/imported_mods/root", {id: "safe"})) fail("unowned apply escaped");
    if (HxcCompatRuntime.clearPauseOverlay(null)) fail("unowned clear escaped");
    var accepted = HxcPauseSpec.fromDynamic({id: "pause", hiddenLabels: ["Change Difficulty"], itemColor: 0xFFFF7CFF});
    if (accepted == null || accepted.hiddenLabels.length != 1) fail("typed pause spec validation");
    var rejected = HxcPauseSpec.fromDynamic(null);
    if (rejected != null) fail("null pause spec accepted");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        runtime = (ROOT / "source/HxcCompatRuntime.hx").read_text()
        host = (ROOT / "source/PauseSubState.hx").read_text()
        self.assertIn("applyPauseOverlay", runtime)
        self.assertIn("clearPauseOverlay", runtime)
        self.assertIn("hxcApplyPauseOverlay", host)
        self.assertIn("hxcClearPauseOverlay", host)
        self.assertIn("HxcStateAssetScope.scopedAssetPath", host)
        self.assertIn("PlayState.instance.practiceMode", host)


if __name__ == "__main__":
    unittest.main()
