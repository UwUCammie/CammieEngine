"""Focused coverage for constructor-only FPS Plus/BaseStage stage adapters."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


def hx_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class HxcStageConstructorTest(unittest.TestCase):
    def _analyze(self, source: str, path: str):
        fixture = f'''import sys.io.File;
class StageConstructorProbe {{
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, {hx_string(path)});
    trace(result.kind);
    trace(result.stageConstructorBody);
    trace(result.generatedHscript);
    for (diagnostic in result.diagnostics) trace(diagnostic.code + ":" + diagnostic.message);
  }}
}}
'''
        with tempfile.TemporaryDirectory(prefix="hxc-stage-constructor-", dir=ROOT / "tmp") as folder:
            path_file = Path(folder) / "StageConstructorProbe.hx"
            path_file.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", folder,
                 "--run", "StageConstructorProbe"],
                cwd=folder, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_alley_balls_constructor_materializes_bg_sprite_and_layer(self):
        donor = DONOR / "whitty/data/stages/alleyBalls.hxc"
        if not donor.is_file():
            self.skipTest("mounted FPS Plus stage donor is unavailable")
        output = self._analyze(donor.read_text(),
                               "assets/imported_mods/fps-plus-whitty/scripts/stages/alleyBalls.hxc")
        self.assertIn("stage\n", output)
        self.assertIn("hxc-stage-constructor-adapter", output)
        self.assertIn("function start()", output)
        self.assertIn("HxcCompatRuntime.createBGSprite(hxcAssetRoot, 'alley/BallisticBackground'", output)
        self.assertIn("addSprite(bg, BEHIND_ALL);", output)
        self.assertIn('stage.applyStartOffset("bf", "x", 230, "add");', output)
        self.assertIn("setDefaultZoom(0.8);", output)
        self.assertNotIn("new BGSprite", output)
        self.assertNotIn("addToBackground", output)

    def test_reachable_fps_plus_stage_constructors_share_one_adapter(self):
        paths = [
            DONOR / "whitty/data/stages/facility.hxc",
            DONOR / "whitty/data/stages/alley.hxc",
        ]
        if not all(path.is_file() for path in paths):
            self.skipTest("mounted FPS Plus stage donors are unavailable")
        for donor in paths:
            output = self._analyze(donor.read_text(),
                                   "assets/imported_mods/fps-plus-whitty/scripts/stages/" + donor.name)
            self.assertIn("hxc-stage-constructor-adapter", output)
            self.assertIn("function start()", output)
            self.assertIn("addSprite(", output)
            self.assertNotIn("new BGSprite", output)
            self.assertNotIn("addToBackground", output)

    def test_unbounded_constructor_statements_are_not_emitted(self):
        source = '''import objects.BGSprite;
class SyntheticStage extends BaseStage {
  public function new() {
    super();
    var bg:BGSprite = new BGSprite('stage/bg', -10, -20, 1, 1, ['idle'], true);
    addToBackground(bg);
    Sys.command('donor-side-effect');
  }
}'''
        output = self._analyze(source, "assets/imported_mods/synthetic/scripts/stages/SyntheticStage.hxc")
        self.assertIn("createBGSprite(hxcAssetRoot", output)
        self.assertIn("addSprite(bg, BEHIND_ALL);", output)
        self.assertNotIn("Sys.command", output)

    def test_stage_constructor_reads_root_scoped_preferences(self):
        source = '''class SyntheticStage extends Stage {
  var save;
  function new() {
    super('synthetic');
    save = ThemePreferences.getThemeSave();
    Sys.command('donor-side-effect');
  }
  public function onCountdownStart(event) {
    if (save.bloom) camBG.visible = true;
  }
}'''
        output = self._analyze(source, "assets/imported_mods/synthetic/scripts/stages/SyntheticStage.hxc")
        self.assertIn("var __hxcStore = HxcCompatRuntime.openStore(", output)
        self.assertIn("save = __hxcStore.getSave();", output)
        self.assertNotIn("Sys.command", output)


if __name__ == "__main__":
    unittest.main()
