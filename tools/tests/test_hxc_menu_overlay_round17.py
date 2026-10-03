"""Round 17: bounded native HXC main-menu specs and host boundaries."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
MIKU = DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/ui/MikuMainMenu.hxc"
DOKI = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/states/DokiMainMenuState.hxc"


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


class HxcMenuOverlayRound17Test(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source, newline='\n')
            command = [
                *HAXE_COMMAND,
                "-cp", str(ROOT / "source"),
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp", folder,
                "-main", "Main", "--interp",
            ]
            return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)

    @unittest.skipIf(not (MIKU.is_file() and DOKI.is_file()), 'mounted menu donor fixtures are unavailable')
    def test_renamed_module_and_state_lower_to_data_only_native_host_calls(self):
        miku = MIKU.read_text(errors="ignore")
        doki = DOKI.read_text(errors="ignore")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function has(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function forbidden(value:String):Bool {{
    return value.indexOf("FlxG.state") >= 0
      || value.indexOf("Application.current.window.close") >= 0
      || value.indexOf("SongRegistry") >= 0
      || value.indexOf("drinks-on-me") >= 0
      || value.indexOf("new FlxSprite") >= 0;
  }}
  static function main() {{
    var module = HxcCompat.analyze({hx_string(miku)}, "synthetic/renamed/ui/Overlay.hxc");
    if (module.kind != "module" || module.menuSpec == null) fail("module menu spec missing: " + module.kind);
    if (!module.moduleSafe || !module.moduleInitializationSafe) fail("module safety: " + module.moduleSafetyReasons.join(","));
    if (has(module, "unsupported-hxc-module-body") || has(module, "unsupported-hxc-callback-body")) fail("module warning remained");
    if (!has(module, "hxc-menu-overlay-adapter")) fail("module menu diagnostic missing");
    if (forbidden(module.generatedHscript)) fail("donor graph leaked into module adapter: " + module.generatedHscript);
    if (module.generatedHscript.indexOf("mountMainMenuOverlay") < 0) fail("module host call missing");

    var state = HxcCompat.analyze({hx_string(doki)}, "synthetic/renamed/states/Screen.hxc");
    if (state.kind != "state" || state.menuSpec == null) fail("state menu spec missing: " + state.kind);
    if (!has(state, "hxc-menu-state-materialized")) fail("state materialization diagnostic missing");
    if (!has(state, "hxc-menu-bounded-fallback")) fail("bounded donor action diagnostic missing");
    if (forbidden(state.generatedHscript)) fail("donor graph leaked into state adapter: " + state.generatedHscript);
    if (state.generatedHscript.indexOf("mountMainMenuOverlay") < 0
      || state.generatedHscript.indexOf("clearMainMenuOverlay") < 0)
      fail("state host lifecycle missing: " + state.generatedHscript);
    var stateSpec:Dynamic = state.menuSpec;
    if (stateSpec.items[2].route != "imported" || stateSpec.items[2].target != "CostumeSelectState")
      fail("root-scoped costume target missing");
    new Parser().parseString(module.generatedHscript);
    new Parser().parseString(state.generatedHscript);

    var pause = HxcCompat.analyze("class RenamedPause extends MusicBeatSubState {{ function onSubStateOpenEnd(event) {{ Application.current.window.close(); }} }}", "synthetic/renamed/SUBSTATES/Pause.hxc");
    if (pause.menuSpec != null) fail("pause overlay was recognized as a menu");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipIf(not (MIKU.is_file() and DOKI.is_file()), 'mounted menu donor fixtures are unavailable')
    def test_mounted_donors_are_read_only_and_generated_output_is_parseable(self):
        before_miku = MIKU.read_bytes()
        before_doki = DOKI.read_bytes()
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var m = HxcCompat.analyze({hx_string(MIKU.read_text(errors="ignore"))}, "{MIKU.as_posix()}");
    var d = HxcCompat.analyze({hx_string(DOKI.read_text(errors="ignore"))}, "{DOKI.as_posix()}");
    if (m.menuSpec == null || d.menuSpec == null) fail("mounted menu spec missing");
    new Parser().parseString(m.generatedHscript);
    new Parser().parseString(d.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(MIKU.read_bytes(), before_miku, "Miku donor changed")
        self.assertEqual(DOKI.read_bytes(), before_doki, "Doki donor changed")

    def test_runtime_boundary_is_noop_without_native_owner_and_cleanup_contract_is_explicit(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    HxcCompatRuntime.clear();
    if (HxcCompatRuntime.mountMainMenuOverlay(null, {id: "x", style: "text", items: []}, "assets/imported_mods/root")) fail("unowned mount escaped");
    if (HxcCompatRuntime.clearMainMenuOverlay(null)) fail("unowned clear escaped");
    if (HxcCompatRuntime.tickMainMenuOverlay()) fail("stale overlay heartbeat");
    if (HxcCompatRuntime.menuRouteNoOp("Exit Game")) fail("no-op route returned success");
    var accepted = HxcMenuSpec.fromDynamic({id: "safe", style: "text", items: [
      {id: "story", label: "Story", route: "story"},
      {id: "foreign", label: "Exit Game", route: "noop"}
    ]});
    if (accepted == null || accepted.items.length != 2) fail("typed spec validation");
    var rejected = HxcMenuSpec.fromDynamic({id: "unsafe", style: "text", items: [
      {id: "x", label: "X", route: "donor-class"}
    ]});
    if (rejected != null) fail("unbounded route accepted");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        factory = (ROOT / "source/HxcStateFactory.hx").read_text()
        host = (ROOT / "source/MainMenuState.hx").read_text()
        self.assertIn("entry.menuSpec", factory)
        self.assertIn("new HxcImportedMenuState(entry)", factory)
        self.assertIn("hxcClearMenuOverlay", host)
        self.assertIn("FlxG.cameras.remove(hxcOverlayCamera", host)
        self.assertIn("HxcStateAssetScope.scopedAssetPath", host)


if __name__ == "__main__":
    unittest.main()
