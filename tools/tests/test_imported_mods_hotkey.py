"""The imported-owner chooser shortcut remains reachable under HXC menus."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(marker)


class ImportedModsHotkeyTest(unittest.TestCase):
    def test_shortcut_routes_before_overlay_for_both_menu_modes(self):
        source = (ROOT / "source/MainMenuState.hx").read_text()
        update = extract_method(source, "override function update(elapsed:Float)")
        helper = extract_method(source, "function tryOpenImportedMods():Bool")
        shortcut = update.index("if (tryOpenImportedMods())")
        overlay = update.index("if (hxcOverlaySpec != null)")
        self.assertLess(shortcut, overlay)
        self.assertIn("updateHxcMenuOverlay();", update[overlay:])
        self.assertIn("super.update(elapsed);", update[overlay:])
        self.assertIn("new CodenameImportedModsState()", helper)
        self.assertIn("selectedSomethin = true;", helper)

        fixture = f'''class FakeKeys {{ public var justPressed:Dynamic = {{I:false}}; public function new() {{}} }}
class FlxG {{ public static var keys:FakeKeys = new FakeKeys(); }}
class CodenameImportedModsState {{ public function new() {{}} }}
class LoadingState {{
  public static var target:Dynamic;
  public static function loadAndSwitchState(value:Dynamic):Void target=value;
}}
class Main {{
  var selectedSomethin:Bool = false;
  public function new() {{}}
{helper}
  function route(overlayPresent:Bool):String {{
    if (tryOpenImportedMods()) return 'imported';
    if (overlayPresent) return 'overlay';
    return 'native';
  }}
  static function main():Void {{
    for (overlayPresent in [false, true]) {{
      var state = new Main();
      FlxG.keys.justPressed.I = true;
      if (state.route(overlayPresent) != 'imported' || !state.selectedSomethin
          || !Std.isOfType(LoadingState.target, CodenameImportedModsState))
        throw 'I did not reach Imported Mods with overlay=' + overlayPresent;
      FlxG.keys.justPressed.I = false;
      if (state.route(overlayPresent) != (overlayPresent ? 'overlay' : 'native'))
        throw 'non-I menu route changed with overlay=' + overlayPresent;
    }}
    var nativeMenu = new Main();
    FlxG.keys.justPressed.I = false;
    if (nativeMenu.route(false) != 'native') throw 'native menu path changed';
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder)
            (path / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "--run", "Main"],
                cwd=folder, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
