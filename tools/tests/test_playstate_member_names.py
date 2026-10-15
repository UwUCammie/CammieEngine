"""The HXC module gate takes PlayState's real members from the PlayState source.

HxcCompat used to keep its own copy of the PlayState members a module may
touch. It drifted (comboPopUps, startCountdown and other V-Slice facades were
missing), and a module that used one was silently dropped. The list now comes
from PlayStateMemberNames, which scans the PlayState source at compile time.
"""
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"

SYNTHETIC = r'''package;

class Base {
	public var inherited:Int = 0;
	public static var baseStatic:Int = 0;
}

class Sample extends Base {
	public var visibleField:Int = 0;
	var hiddenField:Int = 0;
	public static var staticField:Int = 0;
	// public var commentedField:Int = 0;
	/* public function blockComment() {} */
	@:keep public var property(get, never):Dynamic;
	@:keep override public function overridden():Void {
		var local = 'not { a member';
		var other = "also } not";
		var spliced = '${x > 1 ? '}' : '{'} public var fakeField';
		var pattern = ~/public var regexField\{/;
		if (true) {
			public_like();
		}
	}
	public final finalField:Int = 1;
	public inline function inlineMethod() return { a: 1 };
	private function privateMethod() {}
	public function new() {}
	public function afterNested():Void {}
}
'''

MODULE_TEMPLATE = '''class ExampleHudModule extends Module
{{
    function new() {{
        super("ExampleHudModule");
    }}

    override function onStateChangeEnd(event:StateChangeScriptEvent) {{
        if (PlayState.instance == null) return;
        setupHud();
    }}

    function setupHud() {{
        var state = PlayState.instance;
        {body}
    }}
}}
'''


def run_haxe(main_body, extra_files=None):
    TEST_TMP.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='playstate-members-', dir=TEST_TMP) as folder:
        path = Path(folder)
        for name, text in (extra_files or {}).items():
            (path / name).write_text(text, newline='\n')
        (path / 'Main.hx').write_text('class Main { static function main() {\n' + main_body + '\n} }\n', newline='\n')
        result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(HSCRIPT),
                                 '-cp', str(path), '-main', 'Main', '--interp'],
                                cwd=ROOT, text=True, capture_output=True, timeout=600)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout


class PlayStateMemberNamesTest(unittest.TestCase):
    def test_scanner_keeps_only_public_instance_members_of_the_class_body(self):
        out = run_haxe(
            'var source = ' + haxe_string(SYNTHETIC) + ';\n'
            'var parsed = PlayStateMemberNames.scan(source, "Sample");\n'
            'Sys.println("NAMES=" + parsed.names.join(","));\n'
            'Sys.println("PARENT=" + parsed.parent);\n'
            'var base = PlayStateMemberNames.scan(source, "Base");\n'
            'Sys.println("BASE=" + base.names.join(","));')
        lines = dict(line.split('=', 1) for line in out.splitlines() if '=' in line)
        self.assertEqual(lines['NAMES'].split(','),
                         ['visibleField', 'property', 'overridden', 'finalField', 'inlineMethod', 'afterNested'])
        self.assertEqual(lines['PARENT'], 'Base')
        self.assertEqual(lines['BASE'], 'inherited')

    def test_real_playstate_members_include_vslice_facades(self):
        out = run_haxe('Sys.println("NAMES=" + PlayStateMemberNames.collect().join(","));')
        names = set(out.split('NAMES=', 1)[1].strip().split(','))
        for member in ('comboPopUps', 'startCountdown', 'tweenScrollSpeed', 'defaultHUDCameraZoom',
                       'currentChart', 'camHUD', 'boyfriend'):
            self.assertIn(member, names)
        # Superclass members declared in this tree come along.
        self.assertIn('psychSourceTiming', names)
        # Statics are not instance members.
        self.assertNotIn('SONG', names)
        self.assertNotIn('instance', names)

    def test_a_fixture_playstate_does_not_replace_the_real_source(self):
        out = run_haxe('Sys.println("NAMES=" + PlayStateMemberNames.collect().join(","));',
                       {'PlayState.hx': 'class PlayState { public var onlyInStub:Int = 0; }'})
        names = set(out.split('NAMES=', 1)[1].strip().split(','))
        self.assertIn('comboPopUps', names)
        self.assertNotIn('onlyInStub', names)

    def analyze_reasons(self, body):
        module = MODULE_TEMPLATE.format(body=body)
        out = run_haxe(
            'var result = HxcCompat.analyze(' + haxe_string(module)
            + ', "scripts/modules/ExampleHudModule.hxc");\n'
            'Sys.println("REASONS=" + result.moduleSafetyReasons.join("|"));')
        line = [l for l in out.splitlines() if l.startswith('REASONS=')]
        self.assertTrue(line, out)
        return line[-1][len('REASONS='):]

    def test_gate_accepts_a_playstate_member_the_old_list_missed(self):
        reasons = self.analyze_reasons('state.tweenScrollSpeed(2.0, 1.0); state.defaultHUDCameraZoom = 1.0;')
        self.assertNotIn('unsafe helper setupHud', reasons)

    def test_gate_still_rejects_a_donor_only_member(self):
        reasons = self.analyze_reasons('state.donorOnlyPopups.offsets = [1, 2];')
        self.assertIn('unsafe helper setupHud', reasons)


def haxe_string(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


if __name__ == '__main__':
    unittest.main()
