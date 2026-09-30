"""Coverage for HXC parameter-default and camera-filter compatibility.

Three engine behaviors are pinned here:
1. Donor `?name` / `name = default` parameters must translate to hscript
   optional parameters with a literal-default guard, so native lifecycle
   dispatch with fewer arguments no longer throws.
2. FlxRuntimeShader/ShaderFilter field initializers must survive as state
   initializers; dropping them leaves null filter entries.
3. Donor `<camera>.filters = ...` writes must be lowered to the
   native-filter-validating HxcCompatRuntime.assignFilters helper.
"""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def hx_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class HxcDefaultArgsAndFiltersTest(unittest.TestCase):
    def _analyze(self, source: str, path: str) -> str:
        fixture = f'''import sys.io.File;
class DefaultArgsProbe {{
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, {hx_string(path)});
    trace(result.kind);
    trace(result.generatedHscript);
    for (diagnostic in result.diagnostics) trace(diagnostic.code + ":" + diagnostic.message);
  }}
}}
'''
        with tempfile.TemporaryDirectory(prefix="hxc-default-args-", dir=ROOT / "tmp") as folder:
            path_file = Path(folder) / "DefaultArgsProbe.hx"
            path_file.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", folder,
                 "--run", "DefaultArgsProbe"],
                cwd=folder, capture_output=True, text=True, timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_donor_default_parameters_become_optional_with_guard(self):
        source = '''import funkin.modding.module.Module;
class ScoreModule extends Module {
  public function onStateChangeEnd(event:ScriptEvent, fontSize:Int = 24):Void {
    super.onStateChangeEnd(event);
    scoreTxt = new FlxText(0, 0, 0, '', fontSize);
  }
}'''
        output = self._analyze(source,
                               "assets/imported_mods/synthetic/scripts/modules/Score.hxc")
        self.assertIn("function stateChangeEnd(event, ?fontSize)", output)
        self.assertIn("if (fontSize == null) fontSize = 24;", output)
        # The dropped-initializer arity failure must not come back.
        self.assertNotIn("function stateChangeEnd(event, fontSize) {", output)

    def test_explicit_optional_marker_is_preserved(self):
        source = '''import funkin.modding.module.Module;
class OptModule extends Module {
  override function onSongStart(?event:ScriptEvent):Void {
    super.onSongStart(event);
    trace('started');
  }
}'''
        output = self._analyze(source,
                               "assets/imported_mods/synthetic/scripts/modules/Opt.hxc")
        self.assertRegex(output, r"function songStart\(\?event\)")

    def test_runtime_shader_field_initializers_are_kept(self):
        source = '''import flixel.FlxSprite;
import flixel.addons.display.FlxRuntimeShader;
import openfl.filters.ShaderFilter;
import openfl.utils.Assets;
import funkin.Paths;
class ShaderStage extends BaseStage {
  var blend:FlxRuntimeShader = new FlxRuntimeShader(Assets.getText(Paths.frag("blend")));
  var filter:ShaderFilter = new ShaderFilter(blend);

  override function onCreate(event:ScriptEvent):Void {
    super.onCreate(event);
    var bar:FlxSprite = new FlxSprite(0, 0);
    bar.makeGraphic(100, 100, 0xFF000000);
    add(bar);
  }
}'''
        output = self._analyze(source,
                               "assets/imported_mods/synthetic/scripts/stages/ShaderStage.hxc")
        self.assertIn("var blend = new FlxRuntimeShader(Assets.getText(Paths.frag(\"blend\")));",
                      output)
        self.assertIn("var filter = new ShaderFilter(blend);", output)

    def test_camera_filter_writes_are_lowered_to_assign_filters(self):
        source = '''import flixel.FlxSprite;
class FilterStage extends BaseStage {
  var testFilter:ShaderFilter = new ShaderFilter(testShader);

  override function onSongStart(event:ScriptEvent):Void {
    super.onSongStart(event);
    game.camHUD.filters = [testFilter];
    game.camGame.filters = [];
  }
}'''
        output = self._analyze(source,
                               "assets/imported_mods/synthetic/scripts/stages/FilterStage.hxc")
        self.assertIn("HxcCompatRuntime.assignFilters(game.camHUD, [testFilter]);", output)
        self.assertIn("HxcCompatRuntime.assignFilters(game.camGame, []);", output)
        self.assertNotIn(".filters = [", output)

    def test_filter_comparison_is_not_rewritten(self):
        source = '''import funkin.modding.module.Module;
class CompareModule extends Module {
  function check():Bool {
    return game.camHUD.filters == null;
  }
}'''
        output = self._analyze(source,
                               "assets/imported_mods/synthetic/scripts/modules/Compare.hxc")
        self.assertIn("filters == null", output)
        self.assertNotIn("assignFilters", output)

    def test_flx_tween_tween_is_lowered_to_safe_tween(self):
        source = '''import flixel.tweens.FlxTween;
import funkin.modding.module.Module;
class TweenModule extends Module {
  override function onSongStart(event:ScriptEvent):Void {
    super.onSongStart(event);
    FlxTween.tween(PlayState.instance.currentStage, {alpha: 0, mystery: 1}, 0.4);
  }
}'''
        output = self._analyze(source,
                               "assets/imported_mods/synthetic/scripts/modules/Tween.hxc")
        self.assertIn("HxcCompatRuntime.safeTween(", output)
        self.assertNotIn("FlxTween.tween(", output)


if __name__ == "__main__":
    unittest.main()
