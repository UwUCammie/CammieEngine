"""The V-Slice base game's addColor shader ships with the engine.

V-Slice scripts load it by name (Paths.frag('addColor')) and set its four
colour uniforms; mods do not carry it because the base game owns it.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class VSliceBaseAddColorShaderTest(unittest.TestCase):
    def test_shader_is_a_host_shader_with_the_base_game_uniforms(self):
        shader = (ROOT / 'assets/shaders/addColor.frag').read_text()
        self.assertTrue(shader.startswith('#pragma header'))
        for uniform in ('colorAlpha', 'colorRed', 'colorGreen', 'colorBlue'):
            self.assertRegex(shader, r'uniform\s+float\s+' + uniform + r'\s*;')
        self.assertIn('flixel_texture2D(bitmap, openfl_TextureCoordv)', shader)
        self.assertRegex(shader, r'gl_FragColor\s*=\s*min\(')
        # Imports look for host shaders in assets/shaders before reporting a
        # script's shader missing, so the file must sit exactly there.
        module = (ROOT / 'source/ModuleFunctions.hx').read_text()
        self.assertTrue(re.search(r"case 'frag': 'shaders';", module))


if __name__ == '__main__':
    unittest.main()
