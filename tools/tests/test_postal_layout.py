from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PostalLayoutTest(unittest.TestCase):
    def test_layout_initializes_and_updates_with_its_assets(self):
        fixture_asset = ROOT / 'assets/images/custom_ui/ui_layouts/postal.hscript'
        if not fixture_asset.is_file():
            self.skipTest(f'mounted Postal layout fixture unavailable: {fixture_asset}')
        state = (ROOT / 'source/PlayState.hx').read_text()
        declaration = re.search(r'[^\n]*public var iconOverride[^\n]*', state).group(0)
        fixture = (ROOT / 'tools/tests/fixtures/PostalLayoutTest.hx').read_text()
        fixture = fixture.replace('state={health:1.0,iconOverride:false}', 'state=new RuntimeState()')
        fixture += '\nclass RuntimeState {public var health=1.0; public function new(){} '+declaration+'}\n'
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'PostalLayoutTest.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                 '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-main', 'PostalLayoutTest', '--interp'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
