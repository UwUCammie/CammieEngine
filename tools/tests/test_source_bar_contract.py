"""Full donor Bar comparisons with extracted actual Flixel group propagation."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from source_bar_fixture_support import bar_fixture_files

ROOT = Path(__file__).resolve().parents[2]


class SourceBarContractTest(unittest.TestCase):
    def test_actual_groups_match_both_source_bar_dialects(self):
        files = bar_fixture_files()
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for name, source in files.items():
                p = temp / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(source)
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True)
            (temp / 'CppMain.hx').write_text('class CppMain {static function main(){var o:SourceBarOwner={image:Paths.image,antialiasing:function()return false};var a=new PsychSourceBar(0,0,"bar",null,0,1,o);var b=new NightmareVisionBar(0,0,"bar",null,0,1,o);a.percent=25;b.percent=50;var ui:NightmareVisionIUiSprite=b;ui.alphaMultipler=.5;a.setColors(null,12);b.update(.1);}}')
            env = os.environ.copy()
            for key, suffix in [('HAXEPATH', 'haxe'), ('NEKOPATH', 'neko')]:
                env[key] = str(ROOT / '.tools' / suffix)
            env['HAXELIB_PATH'] = str(ROOT / '.haxelib')
            env['PATH'] = os.pathsep.join((env['HAXEPATH'], env['NEKOPATH'], env.get('PATH', '')))
            cpp = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'CppMain', '-cpp', str(temp / 'cpp'), '-D', 'no-compilation'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-8000:])
        self.assertEqual(cpp.returncode, 0, (cpp.stdout + cpp.stderr)[-8000:])
