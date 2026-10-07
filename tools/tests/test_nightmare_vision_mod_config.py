"""Pinned Nightmare Vision applyModConfig order and owner effects."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe" / ("haxe.exe" if __import__("os").name == "nt" else "haxe")
IRIS = ROOT / ".haxelib/hscript-iris/1,1,3"


class NightmareVisionModConfigTest(unittest.TestCase):
    def run_haxe(self, body, fixture_files=None):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        fixture = r'''
class RecordingHost implements NightmareVisionModConfigHost {
 public var events:Array<String> = [];
 public var currentRoot:String = '';
 public var currentDirectory:String = '';
 public var livePack:Dynamic;
 public var windowTitle:String;
 public var windowIcon:String;
 public var transition:NightmareVisionModTransition;
 public var rpcId:String;
 public var font:String;
 public var prefixes:Map<String, String> = new Map();
 public var existingPaths:Map<String, Bool> = new Map();
 public var existingDirectories:Map<String, Bool> = new Map();
 public var failurePoint:String;

 public function new() {}
 function record(name:String):Void {
  events.push(name);
  if (failurePoint == name) throw 'host failure at ' + name;
 }
 public function defaultAppTitle():String { record('default-title'); return 'Engine Title'; }
 public function defaultRpcId():String { record('default-rpc'); return 'donor-rpc'; }
 public function resolveSelectedPath(path:String):String {
  record('path:' + path);
  return currentRoot + '/' + path;
 }
 public function resolveSelectedFont(key:String):String {
  record('font-path:' + key);
  return currentRoot + '/fonts/' + key;
 }
 public function pathExists(path:String):Bool {
  record('exists:' + path);
  return existingPaths.exists(path) && existingPaths.get(path);
 }
 public function selectedDirectoryExists(path:String):Bool {
  record('directory:' + Std.string(path));
  return existingDirectories.exists(path) && existingDirectories.get(path);
 }
 public function updateLiveConfig(directory:String, root:String, pack:Dynamic):Void {
  currentDirectory = directory;
  currentRoot = root;
  livePack = pack;
  record('live:' + Std.string(directory) + ':' + Std.string(root));
 }
 public function initializeOptions(directory:String, root:String):Void record('options:' + Std.string(directory) + ':' + Std.string(root));
 public function setWindowTitle(value:String):Void { windowTitle = value; record('title:' + value); }
 public function setWindowIcon(value:String):Void { windowIcon = value; record('icon:' + value); }
 public function reportMissingIcon(value:String):Void record('missing-icon:' + value);
 public function setTransition(value:NightmareVisionModTransition):Void {
  transition = value;
  record('transition:' + Type.enumConstructor(value)
   + (Type.enumConstructor(value) == 'SCRIPTED' ? ':' + Type.enumParameters(value)[0] : ''));
 }
 public function setRpcId(value:String):Void { rpcId = value; record('rpc:' + value); }
 public function setDefaultFont(value:String):Void { font = value; record('default-font:' + value); }
 public function setPrefix(field:String, value:String):Void { prefixes.set(field, value); record('prefix:' + field + ':' + value); }
}

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ': expected ' + Std.string(expected) + ', got ' + Std.string(actual));
 static function main() {
''' + body + r'''
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            write_flixel_point_stub(work)
            for relative, content in (fixture_files or {}).items():
                path = work / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(IRIS), "-cp", str(work),
                 "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_effect_order_fields_and_partial_icon_fallback(self):
        self.run_haxe(r'''
var root = 'assets/imported_mods/alpha';
var host = new RecordingHost();
var icon = root + '/images/branding/icon/custom.png';
var font = root + '/fonts/custom.ttf';
host.existingPaths.set(icon, true);
host.existingPaths.set(font, true);
host.existingDirectories.set('UI/custom/', true);
host.existingDirectories.set('combo-custom/', true);
host.existingDirectories.set('ratings-missing/', false);
host.existingDirectories.set('countdown-custom/', true);
var pack = {
 windowTitle:'Custom Window', iconFile:'branding/icon/custom', defaultTransition:'FaDe',
 discordClientID:'custom-client', defaultFont:'custom.ttf', uiPrefix:'UI/custom/',
 comboPrefix:'combo-custom/', ratingsPrefix:'ratings-missing/', countdownPrefix:'countdown-custom/',
 stateRedirects:{TitleState:'modTitle'}
};
new NightmareVisionModConfigApplier(host).apply(pack, 'alpha', root);
eq(host.events.join('\n'), [
 'live:alpha:' + root,
 'options:alpha:' + root,
 'title:Custom Window',
 'path:images/branding/icon/icon64.png',
 'path:images/branding/icon/custom.png',
 'exists:' + icon,
 'icon:' + icon,
   'transition:FADE',
 'rpc:custom-client',
 'font-path:custom.ttf',
 'exists:' + font,
 'font-path:custom.ttf',
 'default-font:' + font,
 'directory:UI/custom/',
 'prefix:UI_PREFIX:UI/custom/',
 'directory:combo-custom/',
 'prefix:COMBO_PREFIX:combo-custom/',
 'directory:ratings-missing/',
 'prefix:RATINGS_PREFIX:UI/ratings/',
 'directory:countdown-custom/',
 'prefix:COUNTDOWN_PREFIX:countdown-custom/'
].join('\n'), 'source callback order or selected prefix behavior');
check(host.livePack == pack, 'live redirect context did not receive the selected config');
eq(host.windowIcon, icon, 'configured icon');
eq(host.windowTitle, 'Custom Window', 'configured title');
  eq(Type.enumConstructor(host.transition), 'FADE', 'case-insensitive fade transition');
eq(host.rpcId, 'custom-client', 'configured RPC id');
eq(host.font, font, 'configured font path');
eq(host.prefixes.get('UI_PREFIX'), 'UI/custom/', 'valid UI prefix');
eq(host.prefixes.get('RATINGS_PREFIX'), 'UI/ratings/', 'missing prefix fallback');
''')

    def test_absent_values_use_donor_defaults_and_missing_icon_keeps_default(self):
        self.run_haxe(r'''
var root = 'assets/imported_mods/beta';
var host = new RecordingHost();
var fallbackIcon = root + '/images/branding/icon/icon64.png';
host.existingPaths.set(root + '/images/missing/icon.png', false);
new NightmareVisionModConfigApplier(host).apply({iconFile:'missing/icon'}, 'beta', root);
eq(host.windowTitle, 'Engine Title', 'missing title default');
eq(host.windowIcon, fallbackIcon, 'missing icon replaced source fallback');
check(host.events.indexOf('missing-icon:missing/icon') >= 0, 'missing icon did not report source error');
  eq(Type.enumConstructor(host.transition), 'SWIPE', 'absent transition default');
eq(host.rpcId, 'donor-rpc', 'absent RPC id did not restore donor default');
eq(host.font, root + '/fonts/vcr.ttf', 'absent font fallback');
eq(host.prefixes.get('UI_PREFIX'), 'UI/', 'absent UI prefix');
eq(host.prefixes.get('COMBO_PREFIX'), 'UI/combo/', 'absent combo prefix');
eq(host.prefixes.get('RATINGS_PREFIX'), 'UI/ratings/', 'absent ratings prefix');
eq(host.prefixes.get('COUNTDOWN_PREFIX'), 'UI/countdown/', 'absent countdown prefix');
check(host.events.indexOf('default-title') >= 0 && host.events.indexOf('default-rpc') >= 0,
 'missing-value defaults did not come through host');
''')

    def test_scripted_transition_preserves_original_case(self):
        self.run_haxe(r'''
var host = new RecordingHost();
new NightmareVisionModConfigApplier(host).apply({defaultTransition:'MyCustomFade'}, 'owner', 'assets/imported_mods/owner');
  eq(host.events[6], 'transition:SCRIPTED:MyCustomFade', 'scripted transition key case');
''')

    def test_callback_error_keeps_prior_effects_and_context_config_assignment(self):
        self.run_haxe(r'''
var mods = new NightmareVisionModsContext('assets/imported_mods/alpha', 'alpha');
var host = new RecordingHost();
host.failurePoint = 'icon:' + 'assets/imported_mods/alpha/images/branding/icon/icon64.png';
mods.bindConfigHost(host);
var thrown = false;
try mods.applyModConfig() catch (error:Dynamic) thrown = Std.string(error).indexOf('host failure') >= 0;
check(thrown, 'host error did not propagate');
eq(mods.currentModConfig.name, 'Alpha', 'failed callback rolled back current config assignment');
eq(host.windowTitle, 'Before icon', 'earlier window title effect was lost');
eq(host.transition, null, 'later transition ran after icon callback failure');
var secondBindRejected = false;
try mods.bindConfigHost(new RecordingHost()) catch (_:Dynamic) secondBindRejected = true;
check(secondBindRejected, 'live owner allowed its native host to be replaced');
mods.release();
var unbound = new NightmareVisionModsContext('assets/imported_mods/alpha', 'alpha');
var missingHostRejected = false;
try unbound.applyModConfig() catch (error:Dynamic)
 missingHostRejected = Std.string(error).indexOf('[nightmare-vision-mod-config-host-missing]') >= 0;
check(missingHostRejected && unbound.currentModConfig.name == 'Alpha',
 'unbound config application hid the partial assignment or silently skipped native effects');
unbound.release();
''', {
            'assets/imported_mods/alpha/meta.json': '{"name":"Alpha","windowTitle":"Before icon"}',
        })

    def test_family_owner_selection_controls_options_and_paths_without_apply_switch(self):
        self.run_haxe(r'''
var alpha = 'assets/imported_mods/alpha';
var beta = 'assets/imported_mods/beta';
var session = new NightmareVisionModFamilySession('alpha', alpha,
 [{directory:'alpha', root:alpha}, {directory:'beta', root:beta}], null, null);
var mods = new NightmareVisionModsContext(alpha, 'alpha', session);
var host = new RecordingHost();
mods.bindConfigHost(host);
mods.applyModConfig('beta');
eq(mods.currentModDirectory, 'alpha', 'explicit config lookup switched active owner');
eq(mods.currentModConfig.name, 'Beta', 'explicit family config was not loaded');
check(host.events.indexOf('options:alpha:' + alpha) >= 0, 'options initialized for lookup directory instead of active owner');
eq(host.currentRoot, alpha, 'Paths selection followed explicit config lookup');
var priorEffects = host.events.length;
mods.currentModDirectory = 'beta';
eq(host.events.length, priorEffects, 'directory assignment applied config before source requested it');
mods.applyModConfig();
eq(mods.currentModConfig.name, 'Beta', 'selected beta config');
eq(host.currentRoot, beta, 'native config host did not follow selected family member');
check(host.events.indexOf('options:beta:' + beta) >= 0, 'selected owner options were not initialized');
mods.release();
''', {
            'assets/imported_mods/alpha/meta.json': '{"name":"Alpha"}',
            'assets/imported_mods/beta/meta.json': '{"name":"Beta"}',
        })


if __name__ == "__main__":
    unittest.main()
