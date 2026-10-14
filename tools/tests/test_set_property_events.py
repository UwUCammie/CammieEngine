from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

HAXE = ROOT / '.tools/haxe/haxe'


def set_property_case_body():
    source = (ROOT / 'source/PlayState.hx').read_text()
    start = source.index("case 'Set Property':", source.index('switch (EngineCompat.eventName(e.name))'))
    end = source.index('\n\t\t\tdefault:', start)
    return source[start:end]


class SetPropertyTest(unittest.TestCase):
    def _run(self, fixture: str):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'SetPropertyFixture.hx').write_text(fixture, newline='\n')
            return subprocess.run(
                [*HAXE_COMMAND, '-cp', folder, '-cp', str(ROOT / '.haxelib/hscript/2,5,0'),
                 '-main', 'SetPropertyFixture', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=300)

    def test_atlas_and_event_switch(self):
        fixtures = [
            ROOT / 'assets/images/custom_chars/infidelitybfnew/char.png',
            ROOT / 'assets/images/custom_chars/infidelitybfnew/char.xml',
        ]
        if not all(path.is_file() for path in fixtures):
            self.skipTest('mounted Infidelity character fixtures unavailable: ' + ', '.join(str(path) for path in fixtures))
        # 1) Paths.getCharacterJson (sliced from Paths.hx) against the real
        #    ported character folder on disk
        # 2) a real hscript Interp seeded like PluginManager must resolve
        #    Paths.getCharacterJson (before the fix: EUnknownVariable)
        paths_source = (ROOT / 'source/Paths.hx').read_text()
        gcj_start = paths_source.index('static public function getCharacterJson')
        gcj_end = paths_source.index('\n\t}', gcj_start)
        gcj_body = paths_source[gcj_start:gcj_end]

        fixture = '''import hscript.Parser;
import hscript.Interp;
class OpenFlAssets {
	public static function exists(path:String, ?type:Int):Bool {
		return sys.FileSystem.exists(path);
	}
}
class FlxAtlasFrames {
	public static function fromTexturePackerJson(png:String, json:String):Atlas {
		var text = sys.io.File.getContent(json);
		var parsed:Dynamic = haxe.Json.parse(text);
		var names:Array<String> = Reflect.fields(parsed.frames);
		return new Atlas(png, names);
	}
}
class Atlas {
	public var png:String;
	public var names:Array<String>;
	public function new(png:String, names:Array<String>) {
		this.png = png;
		this.names = names;
	}
}
class DynamicAtlasFrames {
	public static function fromTexturePackerJson(png:String, json:String):Atlas {
		return FlxAtlasFrames.fromTexturePackerJson(png, json);
	}
}
class Paths {
	static var TEXT = 0;
	static function getPath(file:String, ?type:Int, ?library:String):String {
		return 'assets/' + file;
	}
''' + gcj_body + '''
	}
}
class SetPropertyFixture {
	static function main() {
		var frames = Paths.getCharacterJson('infidelitybfnew');
		if (frames == null) throw 'getCharacterJson returned null';
		if (frames.png != 'assets/images/custom_chars/infidelitybfnew/char.png')
			throw 'wrong png path: ' + frames.png;
		if (frames.names.length != 405) throw 'expected 405 frames, got ' + frames.names.length;
		var hit = false;
		for (f in frames.names) if (f.indexOf('BF idle dance') == 0) hit = true;
		if (!hit) throw 'atlas frame names not prefixed as scripts expect';
		if (Paths.getCharacterJson('definitely-not-a-char') != null) throw 'missing char must be null';

		var interp = new Interp();
		interp.variables.set('Paths', Paths);
		var parser = new Parser();
		var program = parser.parseString('function init(char) { var tex = Paths.getCharacterJson("infidelitybfnew"); return tex.names.length; }');
		interp.execute(program);
		var result = interp.variables.get('init')(null);
		if (result != 405) throw 'hscript init failed, got ' + result;
		Sys.println('ok');
	}
}
'''
        result = self._run(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_no_unhandled_set_property_keys_in_corpus(self):
        keys = set()
        for path in (ROOT / 'assets/data').glob('**/*.json'):
            try:
                text = path.read_text(errors='ignore')
            except OSError:
                continue
            if '"Set Property"' not in text:
                continue
            for match in re.finditer(r'\[\s*"Set Property"\s*,\s*"([^"]+)"', text):
                keys.add(match.group(1))
        # events are dispatched to stage/modchart scripts before the engine
        # switch; keys a script handles itself stay inert in the engine
        script_handled = set()
        for path in list((ROOT / 'assets/data').glob('**/*.hscript')) + list((ROOT / 'assets/images/custom_stages').glob('*.hscript')):
            try:
                text = path.read_text(errors='ignore')
            except OSError:
                continue
            for key in keys:
                if f'"{key}"' in text:
                    script_handled.add(key)
        # The event goes through the script property writer, so any key a
        # script setProperty can reach is handled; the Psych spellings the
        # old per-key switch knew are real aliases on PlayState.
        case_body = set_property_case_body()
        self.assertIn('setEventProperty(', case_body)
        self.assertNotIn('switch', case_body)
        play = (ROOT / 'source/PlayState.hx').read_text()
        for alias in ['camZoomingMult', 'camZoomingDecay', 'cameraSpeed']:
            self.assertIn('@:keep public var ' + alias + '(get, set):Float;', play)
        missing = [] if 'setEventProperty(' in case_body else sorted(keys - script_handled)
        self.assertEqual(missing, [], f'Set Property keys with no handler: {missing}')

    def test_plugin_manager_seeds_paths(self):
        source = (ROOT / 'source/PluginManager.hx').read_text()
        self.assertIn('variables.set("Paths", Paths)', source,
                      'hscript interps must expose Paths or ported char scripts throw EUnknownVariable')


if __name__ == '__main__':
    unittest.main()
