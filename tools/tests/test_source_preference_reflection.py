"""Owner-scoped Psych/Nightmare Vision ClientPrefs class reflection paths."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


FIXTURE = r'''
using StringTools;

class PlayState {}
class FlxG {}
class Judge {
    public static var sickJudge:Float = 45;
    public static var goodJudge:Float = 90;
    public static var badJudge:Float = 135;
    public static var shitJudge:Float = 166;
}
class PsychClientPrefsCompat {
    public static var data:Dynamic = {sickWindow:21.0, goodWindow:81.0, badWindow:121.0};
}
class OptionsHandler {
    public static var options:Dynamic = {showNoteSplashes:true};
}
class RuntimeSmokeHarness {
    public static function enabled():Bool return false;
}
class EngineCompat {
    public static function propertyPath(path:Dynamic):String {
        return path == null ? '' : StringTools.replace(StringTools.trim(Std.string(path)), '\\', '.');
    }
    public static function legacyClassProperty(className:String, path:String):String {
        if (className == null || path == null) return '';
        var classKey = className.toLowerCase();
        if (classKey != 'clientprefs' && classKey != 'backend.clientprefs'
            && classKey != 'funkin.data.clientprefs') return '';
        return switch (path.toLowerCase()) {
            case 'ratingoffset' | 'data.ratingoffset': 'ratingOffset';
            case 'sickwindow' | 'data.sickwindow': 'sickWindow';
            case 'goodwindow' | 'data.goodwindow': 'goodWindow';
            case 'badwindow' | 'data.badwindow': 'badWindow';
            default: '';
        };
    }
}

class SourcePreferenceReflectionFixture {
    var sourceScoreNightmare:Bool = false;
    var nightmareVisionPrefs:Dynamic = null;
    var psychClientPrefs:Dynamic = null;
    var psychGameOverDeathDelaySeconds:Float = 0;
    var psychGameOverOverrides:Map<String, Dynamic> = [];
    var psychFlxGGameTicksProbeEmitted:Bool = false;
    var pixelUI:Bool = false;
    public var lastReadTarget:Dynamic;
    public var lastReadPath:String = '';
    public var lastWriteTarget:Dynamic;
    public var lastWritePath:String = '';

__METHODS__

    public function new() {}

    public function sourceScoreLedgerActive():Bool return false;

    function compatReadPath(target:Dynamic, path:String):Dynamic {
        lastReadTarget = target;
        lastReadPath = path;
        if (target == null) return null;
        var value:Dynamic = target;
        if (path == null || StringTools.trim(path) == '') return value;
        for (part in path.split('.')) {
            if (part == '') continue;
            value = Reflect.getProperty(value, part);
            if (value == null) return null;
        }
        return value;
    }

    function compatWritePath(target:Dynamic, path:String, value:Dynamic):Bool {
        lastWriteTarget = target;
        lastWritePath = path;
        if (target == null || path == null || StringTools.trim(path) == '') return false;
        var parts = path.split('.');
        var owner:Dynamic = target;
        while (parts.length > 1) {
            var part = parts.shift();
            owner = Reflect.getProperty(owner, part);
            if (owner == null) return false;
        }
        Reflect.setProperty(owner, parts[0], value);
        return true;
    }

    function psychGameOverClassPropertyKey(_className:Dynamic, _path:Dynamic):Null<String> return null;
    function compatResolveClass(name:Dynamic):Dynamic {
        if (name == null) return null;
        return switch (StringTools.trim(Std.string(name)).toLowerCase()) {
            case 'flixel.flxg': FlxG;
            case 'states.playstate' | 'playstate': PlayState;
            default: null;
        };
    }
    function compatClassPropertyPath(_classValue:Dynamic, path:Dynamic):String
        return EngineCompat.propertyPath(path);
    function compatFlxGStaticRoot(_root:String):Dynamic return null;
    function tracePsychFlxGGameTicksProbe(_className:Dynamic, _path:String, _normalized:String,
        _classValue:Dynamic, _rootValue:Dynamic, _result:Dynamic):Void {}

    static function fail(message:String):Void throw message;
    static function check(value:Bool, message:String):Void if (!value) fail(message);

    static function main():Void {
        var psychData:Dynamic = {ratingOffset:4, sickWindow:31.5, goodWindow:77.0, badWindow:128.0};
        var psychWrapper:Dynamic = {data:psychData, sickWindow:999.0};
        var psych = new SourcePreferenceReflectionFixture();
        psych.psychClientPrefs = psychWrapper;
        check(psych.compatGetPropertyFromClass('ClientPrefs', 'sickWindow') == 31.5,
            'legacy Psych flat read did not reach ClientPrefs.data');
        check(psych.lastReadTarget == psychWrapper && psych.lastReadPath == 'data.sickWindow',
            'legacy Psych read lost the modern data object identity/path');
        check(psych.compatGetPropertyFromClass('backend.ClientPrefs', 'data') == psychData,
            'modern ClientPrefs.data read did not return the live object');
        check(psych.compatGetPropertyFromClass('funkin.data.ClientPrefs', 'data.ratingOffset') == 4,
            'modern Psych data-prefixed read changed');
        psych.compatSetPropertyFromClass('ClientPrefs', 'sickWindow', 42.25);
        check(psych.lastWriteTarget == psychWrapper && psych.lastWritePath == 'data.sickWindow'
            && psychData.sickWindow == 42.25,
            'legacy Psych flat write did not mutate the live modern data object');
        check(psychWrapper.sickWindow == 999.0,
            'legacy Psych write incorrectly created or changed a flat wrapper field');
        psych.compatSetPropertyFromClass('backend.ClientPrefs', 'data.ratingOffset', -7);
        check(psychData.ratingOffset == -7 && psych.lastWritePath == 'data.ratingOffset',
            'modern Psych data-prefixed write changed');

        var ownerAView:Dynamic = {ratingOffset:8, sickWindow:52.5};
        var ownerBView:Dynamic = {ratingOffset:-3, sickWindow:19.0};
        var ownerA = new SourcePreferenceReflectionFixture();
        ownerA.sourceScoreNightmare = true;
        ownerA.psychClientPrefs = psychWrapper;
        ownerA.nightmareVisionPrefs = {view:ownerAView};
        var ownerB = new SourcePreferenceReflectionFixture();
        ownerB.sourceScoreNightmare = true;
        ownerB.psychClientPrefs = psychWrapper;
        ownerB.nightmareVisionPrefs = {view:ownerBView};
        check(ownerA.compatGetPropertyFromClass('funkin.data.ClientPrefs', 'data.ratingOffset') == 8,
            'NV data-prefixed alias was not flattened onto its owner view');
        check(ownerA.lastReadTarget == ownerAView && ownerA.lastReadPath == 'ratingOffset',
            'NV class reflection did not use the exact owner view');
        ownerA.compatSetPropertyFromClass('ClientPrefs', 'data.sickWindow', 60.0);
        check(ownerA.lastWriteTarget == ownerAView && ownerA.lastWritePath == 'sickWindow'
            && ownerAView.sickWindow == 60.0,
            'NV flattened write did not update its owner-local preference');
        check(ownerBView.sickWindow == 19.0 && psychData.sickWindow == 42.25,
            'NV owner write leaked into another owner or the Psych preference object');
        check(ownerB.compatGetPropertyFromClass('ClientPrefs', 'sickWindow') == 19.0,
            'second NV owner did not retain its own preference view');

        var native = new SourcePreferenceReflectionFixture();
        check(native.compatGetPropertyFromClass('ClientPrefs', 'ratingOffset') == 0.0,
            'native ratingOffset fallback changed');
        check(native.compatGetPropertyFromClass('ClientPrefs', 'sickWindow') == Judge.sickJudge
            && native.compatGetPropertyFromClass('backend.ClientPrefs', 'goodWindow') == Judge.goodJudge
            && native.compatGetPropertyFromClass('ClientPrefs', 'badWindow') == Judge.badJudge,
            'native judgement-window fallback changed');
    }
}
'''


class SourcePreferenceReflectionTest(unittest.TestCase):
    def test_source_class_preferences_keep_owner_identity_and_dialect_paths(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        methods = []
        for marker in (
            "function compatSourceClientPrefs(",
            "function compatSourcePreferencePath(",
            "function compatPropertySeparator(",
            "function compatGetPropertyFromClass(",
            "function compatSetPropertyFromClass(",
        ):
            methods.append(extract_method(play_state, marker))
        fixture = FIXTURE.replace("__METHODS__", "\n\n".join(methods))

        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="source-preference-reflection-", dir=TEST_TMP) as folder:
            Path(folder, "SourcePreferenceReflectionFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-main", "SourcePreferenceReflectionFixture", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
