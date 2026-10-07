from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

from haxe_test_support import HAXE, HAXE_COMMAND, ROOT


DONOR = ROOT.parent / 'fnf_sources/NightmareVision/source/funkin'


def shader_source(path):
    source = path.read_text(encoding='utf-8')
    start = source.index("@:glFragmentSource('") + len("@:glFragmentSource('")
    end = source.index("')", start)
    return '\n'.join(line.rstrip() for line in textwrap.dedent(source[start:end]).splitlines()).strip()


class NightmareVisionNativeTitleMenuTests(unittest.TestCase):
    def test_color_swap_keeps_pinned_donor_shader_and_controls(self):
        donor = DONOR / 'game/shaders/ColorSwap.hx'
        native = ROOT / 'source/NightmareVisionColorSwap.hx'
        self.assertEqual(shader_source(native), shader_source(donor))

        source = native.read_text(encoding='utf-8')
        for field in ('hue', 'saturation', 'brightness', 'daAlpha', 'flash'):
            self.assertIn(f'public var {field}(default, set):Float', source)
        self.assertIn('shader.u_alpha.value = [1]', source)
        self.assertIn('shader.u_flash.value = [0]', source)

    def test_native_states_keep_source_visuals_callbacks_and_owner_routes(self):
        title = (ROOT / 'source/NightmareVisionTitleState.hx').read_text(encoding='utf-8')
        menu = (ROOT / 'source/NightmareVisionMainMenuState.hx').read_text(encoding='utf-8')

        for asset in (
            'menus/title/logoBumpin', 'menus/title/gfDanceTitle',
            'menus/title/titleEnter', 'menus/title/newgrounds_logo',
        ):
            self.assertIn(asset, title)
        for callback in ('onStartIntro', 'onCreatePost', 'onEnter', 'onSkipIntro'):
            self.assertIn("scriptGroup.call('" + callback + "'", title)
        self.assertIn('new NightmareVisionColorSwap()', title)
        self.assertIn('var introEndingText:Array<String>', title)

        for asset in ('menus/menuBG', 'menus/menuDesat', 'menus/mainmenu/menu_'):
            self.assertIn(asset, menu)
        for callback in ('onCreate', 'onUpdatePost', 'onSelect', 'onChangeSelection'):
            self.assertIn("scriptGroup.call('" + callback + "'", menu)
        self.assertIn('var optionShit:Array<String>', menu)
        self.assertIn('session.switchWithTransition(factory, transition)', menu)
        self.assertIn('session.menuVocals', menu)
        self.assertNotIn('FreeplayState.vocals', menu)
        self.assertNotIn('new MainMenuState(', menu)
        self.assertNotIn('new TitleState(', title)

    @unittest.skipUnless(HAXE.exists(), 'portable Haxe toolchain is not bootstrapped')
    def test_color_swap_setters_update_the_actual_uniform_values(self):
        with tempfile.TemporaryDirectory(prefix='nv-title-color-swap-') as temporary:
            fixture = Path(temporary)
            (fixture / 'flixel/system').mkdir(parents=True)
            shutil.copy2(ROOT / 'source/NightmareVisionColorSwap.hx', fixture / 'NightmareVisionColorSwap.hx')
            (fixture / 'flixel/system/FlxAssets.hx').write_text(textwrap.dedent('''\
                package flixel.system;
                class FlxAssets {}
                class Uniform { public var value:Array<Float> = [0]; public function new() {} }
                class FlxShader {
                    public var u_hue:Uniform = new Uniform();
                    public var u_saturation:Uniform = new Uniform();
                    public var u_brightness:Uniform = new Uniform();
                    public var u_alpha:Uniform = new Uniform();
                    public var u_flash:Uniform = new Uniform();
                    public function new() {}
                }
            '''), encoding='utf-8')
            (fixture / 'Main.hx').write_text(textwrap.dedent('''\
                class Main {
                    static function check(value:Bool, message:String):Void
                        if (!value) throw message;
                    static function main():Void {
                        var swap = new NightmareVisionColorSwap();
                        check(swap.hue == 0 && swap.saturation == 0 && swap.brightness == 0,
                            'source HSV defaults');
                        check(swap.daAlpha == 1 && swap.flash == 0, 'source alpha and flash defaults');
                        check(swap.shader.u_alpha.value[0] == 1 && swap.shader.u_flash.value[0] == 0,
                            'default shader uniforms');
                        swap.hue = 0.25;
                        swap.saturation = -0.4;
                        swap.brightness = 0.7;
                        swap.daAlpha = 0.35;
                        swap.flash = 0.8;
                        check(swap.shader.u_hue.value[0] == 0.25, 'hue uniform update');
                        check(swap.shader.u_saturation.value[0] == -0.4, 'saturation uniform update');
                        check(swap.shader.u_brightness.value[0] == 0.7, 'brightness uniform update');
                        check(swap.shader.u_alpha.value[0] == 0.35, 'alpha uniform update');
                        check(swap.shader.u_flash.value[0] == 0.8, 'flash uniform update');
                        trace('source-shaped ColorSwap uniform checks passed');
                    }
                }
            '''), encoding='utf-8')
            command = [*HAXE_COMMAND, '-cp', str(fixture), '-main', 'Main', '--interp']
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('source-shaped ColorSwap uniform checks passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
