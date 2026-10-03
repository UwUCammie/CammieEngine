from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

HAXE = ROOT / '.tools/haxe/haxe'


def set_property_switch_body():
    source = (ROOT / 'source/PlayState.hx').read_text()
    start = source.index("case 'Set Property':")
    start = source.index('switch (k) {', start)
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
        # 1) the inner switch of 'Set Property' with the three ported keys
        # 2) Paths.getCharacterJson (sliced from Paths.hx) against the real
        #    ported character folder on disk
        # 3) a real hscript Interp seeded like PluginManager must resolve
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
	static var defaultCamZoom:Float = 1.05;
	static var camZoomIntensity:Float = 1;
	static var camZoomDecay:Float = 1;
	static var camGame = {angle: 0.0};
	static var camHUD = {angle: 0.0};
	static var camSpeed:Float = 0;
	static function parseF(v:String):Float {
		if (v == null || v == '') return 0;
		return Std.parseFloat(v);
	}
	static function fire(e:{v1:String, v2:String}) {
		var k = StringTools.trim(e.v1);
		var val = parseF(e.v2);
''' + set_property_switch_body() + '''
	}
	static function main() {
		fire({v1: 'defaultCamZoom', v2: '0.7'});
		if (defaultCamZoom != 0.7) throw 'defaultCamZoom not applied';
		fire({v1: 'camZoomingMult', v2: '2'});
		if (camZoomIntensity != 2) throw 'camZoomingMult not applied';
		fire({v1: 'camZoomingDecay', v2: '3.5'});
		if (camZoomDecay != 3.5) throw 'camZoomingDecay not applied';

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
        switch_body = set_property_switch_body()
        missing = sorted(k for k in keys - script_handled if ("case '" + k + "'") not in switch_body)
        self.assertEqual(missing, [], f'Set Property keys with no handler: {missing}')

    def test_plugin_manager_seeds_paths(self):
        source = (ROOT / 'source/PluginManager.hx').read_text()
        self.assertIn('variables.set("Paths", Paths)', source,
                      'hscript interps must expose Paths or ported char scripts throw EUnknownVariable')


if __name__ == '__main__':
    unittest.main()
