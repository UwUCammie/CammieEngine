"""Codename character-swap preload metadata must be validated dynamically."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'
SOURCE = ROOT / 'source/PlayState.hx'


def preload_metadata_helper(source):
    start = source.index('static function codenameSwapPreloadParams(')
    end = source.index('\n\t}', start) + len('\n\t}')
    return source[start:end].replace('static function', 'public static function', 1)


class CodenameSwapPreloadTest(unittest.TestCase):
    def test_metadata_guard_accepts_only_complete_character_swap_payloads(self):
        helper = preload_metadata_helper(SOURCE.read_text())
        fixture = '''
class Probe {
''' + helper + '''
}
class Test {
	static function main() {
		var valid:Array<Dynamic> = [true, 1, "unused", "bf-alt"];
		var result = Probe.codenameSwapPreloadParams({name:"Change Character", params:valid});
		if (result == null || result[3] != "bf-alt") throw "valid swap metadata rejected";
		if (Probe.codenameSwapPreloadParams(null) != null) throw "null metadata accepted";
		if (Probe.codenameSwapPreloadParams({name:"Other", params:valid}) != null)
			throw "unrelated event accepted";
		if (Probe.codenameSwapPreloadParams({name:"Change Character", params:"bad"}) != null)
			throw "non-array metadata accepted";
		var shortParams:Array<Dynamic> = [true, 1, "unused"];
		var disabledParams:Array<Dynamic> = [false, 1, "unused", "bf-alt"];
		var nonStringParams:Array<Dynamic> = [true, 1, "unused", 7];
		if (Probe.codenameSwapPreloadParams({name:"Change Character", params:shortParams}) != null)
			throw "short metadata accepted";
		if (Probe.codenameSwapPreloadParams({name:"Change Character", params:disabledParams}) != null)
			throw "disabled swap accepted";
		if (Probe.codenameSwapPreloadParams({name:"Change Character", params:nonStringParams}) != null)
			throw "non-string character id accepted";
	}
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Test.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', tmp, '--main', 'Test', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
