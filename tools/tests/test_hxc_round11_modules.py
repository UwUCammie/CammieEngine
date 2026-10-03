"""Regression coverage for the remaining mounted TAKEOVER HXC modules."""
from haxe_test_support import HAXE_COMMAND

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
MODULE_ROOT = (
    Path("/run/media/cammie/External Storage/FNF-Example-Mods")
    / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules"
)
MODULES = {
    "countdown": MODULE_ROOT / "CountdownGF.hxc",
    "gameover": MODULE_ROOT / "DDTOGameOver.hxc",
    "costume": MODULE_ROOT / "CostumeMenuButtonv2.hxc",
}


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@unittest.skipUnless(
    HAXE.is_file() and all(path.is_file() for path in MODULES.values()),
    "portable Haxe toolchain or mounted TAKEOVER HXC modules unavailable",
)
class MountedHxcRound11ModulesTest(unittest.TestCase):
    def run_fixture(self, source: str) -> subprocess.CompletedProcess:
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-round11-", dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source, newline='\n')
            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            return subprocess.run(
                [
                    *HAXE_COMMAND,
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

    def test_three_mounted_modules_are_safe_and_use_bounded_callbacks(self):
        before = {name: path.read_bytes() for name, path in MODULES.items()}
        encoded = {
            name: hx_string(path.read_text(errors="ignore"))
            for name, path in MODULES.items()
        }
        paths = {name: hx_string(str(path)) for name, path in MODULES.items()}
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var countdown = HxcCompat.analyze({encoded['countdown']}, {paths['countdown']});
    var gameover = HxcCompat.analyze({encoded['gameover']}, {paths['gameover']});
    var costume = HxcCompat.analyze({encoded['costume']}, {paths['costume']});
    if (!countdown.moduleSafe || !countdown.moduleInitializationSafe
      || hasCode(countdown, "unsupported-hxc-module-body")
      || hasCode(countdown, "unsupported-hxc-callback-body")
      || countdown.generatedHscript.indexOf("function countdownStep") < 0)
      fail("CountdownGF adapter: " + countdown.moduleSafetyReasons.join(",")
        + "\\n" + countdown.generatedHscript);
    if (!gameover.moduleSafe || !gameover.moduleInitializationSafe
      || hasCode(gameover, "unsupported-hxc-module-body")
      || hasCode(gameover, "unsupported-hxc-callback-body")
      || gameover.generatedHscript.indexOf(
        'HxcCompatRuntime.handleImportedGameOverReplacement(event, hxcAssetRoot, '
          + '["sayori", "monika", "natsuki", "yuri", "yuri-crazy"], "bf-doki")') < 0
      || gameover.generatedHscript.indexOf("GameOverSubState.instance") >= 0)
      fail("DDTOGameOver adapter: " + gameover.moduleSafetyReasons.join(",")
        + "\\n" + gameover.generatedHscript);
    if (!costume.moduleSafe || !costume.moduleInitializationSafe
      || hasCode(costume, "unsupported-hxc-module-body")
      || hasCode(costume, "unsupported-hxc-callback-body")
      || costume.generatedHscript.indexOf("HxcCompatRuntime.addCostumeMenuItem(event.targetState") < 0
      || costume.generatedHscript.indexOf("createMenuItem") >= 0)
      fail("CostumeMenuButtonv2 adapter: " + costume.moduleSafetyReasons.join(",")
        + "\\n" + costume.generatedHscript);
    new Parser().parseString(countdown.generatedHscript);
    new Parser().parseString(gameover.generatedHscript);
    new Parser().parseString(costume.generatedHscript);

    var partial = HxcCompat.analyze(
      "class Partial extends Module {{ function onSubStateOpenEnd(event) {{ "
        + "GameOverSubState.instance.boyfriend.destroy(); }} }}",
      "scripts/modules/partial-ddto.hxc");
    if (partial.moduleSafe || !hasCode(partial, "unsupported-hxc-module-body"))
      fail("partial DDTO graph was whitelisted");
    Sys.println("round11-module-analysis-ok");
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("round11-module-analysis-ok", result.stdout)
        for name, path in MODULES.items():
            self.assertEqual(before[name], path.read_bytes(), f"donor changed: {name}")

    def test_countdown_callback_uses_the_namespaced_default_option(self):
        source = hx_string(MODULES["countdown"].read_text(errors="ignore"))
        path = hx_string(str(MODULES["countdown"]))
        main = f'''import hscript.Interp;
import hscript.Parser;
class FakeGirlfriend {{
  public var isDead:Bool = false;
  public var played:Array<String> = [];
  public function new() {{}}
  public function hasAnimation(name:String):Bool return name.indexOf("countdown") == 0;
  public function playAnimation(name:String, ?force:Bool = false):Void played.push(name);
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    HxcCompatRuntime.clear();
    var result = HxcCompat.analyze({source}, {path});
    var interp = new Interp();
    var gf = new FakeGirlfriend();
    var stage:Dynamic = {{getGirlfriend: function() return gf}};
    interp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    interp.variables.set("PlayState", {{instance: {{curStage: stage, isMinimalMode: false}}}});
    interp.variables.set("SONG", {{gf: "normal"}});
    interp.execute(new Parser().parseString(result.generatedHscript));
    var callback:Dynamic = interp.variables.get("countdownStep");
    if (callback == null) fail("generated countdown callback missing");
    var namespace = ~/openStore\\("([^"]+)"\\)/;
    if (!namespace.match(result.generatedHscript))
      fail("generated root-scoped store is missing");
    var store:Dynamic = HxcCompatRuntime.openStore(namespace.matched(1));
    if (store.getSave() != store
      || result.generatedHscript.indexOf("save = __hxcStore.getSave()") < 0)
      fail("CountdownGF did not receive its root-scoped Save facade");
    Reflect.setField(store, "gfCountdown", true);
    Reflect.callMethod(null, callback, [{{step: "THREE", eventCanceled: false}}]);
    if (gf.played.length != 1 || gf.played[0] != "countdownThree" || !gf.isDead)
      fail("THREE callback semantics");
    var before = gf.played.length;
    Reflect.callMethod(null, callback, [{{step: "TWO", eventCanceled: true}}]);
    if (gf.played.length != before) fail("canceled countdown callback ran");
    Reflect.callMethod(null, callback, [{{step: "GO", eventCanceled: false}}]);
    if (gf.played.length != 2 || gf.played[1] != "countdownGo" || gf.isDead)
      fail("GO callback semantics");
    Sys.println("round11-countdown-runtime-ok");
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("round11-countdown-runtime-ok", result.stdout)

    def test_native_boundaries_are_present_for_lifecycle_adapters(self):
        gameover = (ROOT / "source/GameOverSubstate.hx").read_text()
        menu = (ROOT / "source/MainMenuState.hx").read_text()
        compat = (ROOT / "source/HxcCompat.hx").read_text()
        runtime = (ROOT / "source/HxcCompatRuntime.hx").read_text()
        self.assertIn("hxcApplyImportedGameOverCharacter", gameover)
        self.assertIn("isImportedManifestRoot", gameover)
        self.assertIn("hxcAddCostumeMenuItem", menu)
        self.assertIn("asset-scope gap", menu)
        self.assertIn("handleImportedGameOverReplacement", runtime)
        self.assertIn("isListedGameOverPlayer", runtime)
        self.assertIn("addCostumeMenuItem", runtime)
        self.assertIn("seedStoreDefaults", compat)
        self.assertNotIn("gfCountdown", runtime)
        self.assertNotIn("isDokiGameOverPlayer", runtime)


if __name__ == "__main__":
    unittest.main()
