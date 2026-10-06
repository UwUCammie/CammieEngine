"""Actual icon classes versus full pinned donors, with native animation methods."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_nv_multifield_routes import method
from source_icon_fixture_support import source_icon_fixture_files

ROOT = Path(__file__).resolve().parents[2]


class SourceHealthIconContractTest(unittest.TestCase):
    def test_source_sprite_loading_and_controls_match_complete_donors(self):
        files = source_icon_fixture_files()
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for name, source in files.items():
                p = temp / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(source)
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True)
            env = os.environ.copy()
            env['HAXEPATH'] = str(ROOT / '.tools/haxe')
            env['NEKOPATH'] = str(ROOT / '.tools/neko')
            env['HAXELIB_PATH'] = str(ROOT / '.haxelib')
            env['PATH'] = os.pathsep.join((env['HAXEPATH'], env['NEKOPATH'], env.get('PATH', '')))
            cpp = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory, '-main', 'Main', '-cpp', str(temp / 'cpp'), '-D', 'no-compilation'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            generated = (temp / 'cpp/src/NightmareVisionHealthIcon.cpp').read_text() if cpp.returncode == 0 else ''
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[:3000] + (result.stdout + result.stderr)[-3000:])
        self.assertEqual(cpp.returncode, 0, (cpp.stdout + cpp.stderr)[-8000:])
        self.assertIn('HX_FIELD_EQ(inName,"updateIconAnim")', generated)
        self.assertIn('updateIconAnim_dyn()', generated)
