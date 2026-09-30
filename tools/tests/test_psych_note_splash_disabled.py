"""Psych per-note splash data gates the shared native splash routes."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class PsychNoteSplashDisabledTest(unittest.TestCase):
    def test_note_local_psych_flag_gates_both_shared_splash_paths(self):
        note_source = (ROOT / "source/Note.hx").read_text()
        play_source = (ROOT / "source/PlayState.hx").read_text()
        is_disabled = extract_method(note_source, "public function isNoteSplashDisabled(")
        should_show = extract_method(play_source, "function shouldShowNoteSplash(")
        ordinary_hit = extract_method(play_source, "private function popUpScore(")
        hazard_splash = extract_method(play_source, "function splashHitCausesMissNote(")
        property_methods = []
        for marker in (
            "function compatPathTokens",
            "function compatPathIndex",
            "function compatReadPathPart",
            "function compatCoercePropertyValue",
            "function compatWritePathPart",
            "function compatReadPath(target:Dynamic",
            "function compatWritePath(target:Dynamic",
        ):
            method = extract_method(play_source, marker)
            method = method.replace(
                "function " + marker.split("function ", 1)[1],
                "static function " + marker.split("function ", 1)[1],
                1,
            )
            property_methods.append(method)

        self.assertIn("noteSplashData:Dynamic = {disabled: false}", note_source)
        self.assertIn("shouldShowNoteSplash(daNote)", ordinary_hit)
        self.assertIn("shouldShowNoteSplash(note)", hazard_splash)
        self.assertIn("strums.showNotesplash", hazard_splash)

        fixture = '''
class EngineCompat {
  public static function psychHealthColorArray(target:Dynamic, boyfriend:Dynamic,
      dad:Dynamic, gf:Dynamic, iconP1:Dynamic, iconP2:Dynamic):Array<Int> return [];
}
class FlxColor {
  public static function fromString(value:String):Null<Int> return null;
}
class PsychRGBShaderReference {}
class Note {
  public var noteSplashData:Dynamic = {disabled: false};
  public var isSustainNote = false;
  public var noteData = 2;
  public var hitHealth:Null<Float> = null;
  public var missHealth:Null<Float> = null;
  public function new() {}
__IS_DISABLED__
}
class FakeStrumline {
  public var showNotesplash = true;
  public var members:Array<Int> = [0, 1, 2, 3];
  public var spawned:Array<Int> = [];
  public function new() {}
  public function doSplash(lane:Int):Int { spawned.push(lane); return lane; }
}
class FakeSplashGroup {
  public var spawned:Array<Int> = [];
  public function new() {}
  public function add(lane:Int):Void spawned.push(lane);
}
class PsychNoteSplashFixture {
  public var useNoteSplashes = true;
  public var grpNoteSplashes:Dynamic = new FakeSplashGroup();
  public var codenameNoteSplashHandler:Dynamic = null;
  public var strums:FakeStrumline = new FakeStrumline();
  public function new() {}
  static var boyfriend:Dynamic;
  static var dad:Dynamic;
  static var gf:Dynamic;
  static var iconP1:Dynamic;
  static var iconP2:Dynamic;
  static function compatParseColor(value:Dynamic):Null<Int> return null;
__PROPERTY_METHODS__
__SHOULD_SHOW__
  function getNoteStrumline(note:Note):FakeStrumline return strums;
__HAZARD_SPLASH__
  static function main():Void {
    var state = new PsychNoteSplashFixture();
    var note = new Note();
    if (!state.shouldShowNoteSplash(note)) throw 'ordinary note splash was suppressed';
    if (!compatWritePath(note, 'noteSplashData.disabled', 'true'))
      throw 'nested Psych note splash property write failed';
    if (!note.isNoteSplashDisabled() || state.shouldShowNoteSplash(note))
      throw 'per-note Psych splash disable was ignored';
    if (!compatWritePath(note, 'noteSplashData.disabled', 'false'))
      throw 'nested Psych note splash re-enable failed';
    if (note.isNoteSplashDisabled() || !state.shouldShowNoteSplash(note))
      throw 'per-note Psych splash re-enable did not restore default behavior';
    state.splashHitCausesMissNote(note);
    if (state.strums.spawned.length != 1 || state.grpNoteSplashes.spawned[0] != 2)
      throw 'enabled hit-causes-miss note did not emit its splash';
    if (!compatWritePath(note, 'noteSplashData.disabled', true))
      throw 'nested Psych note splash disable failed';
    state.splashHitCausesMissNote(note);
    if (state.strums.spawned.length != 1)
      throw 'disabled hit-causes-miss note emitted a splash';
    if (!compatWritePath(note, 'noteSplashData.disabled', false))
      throw 'nested Psych note splash re-enable failed';
    state.strums.showNotesplash = false;
    state.splashHitCausesMissNote(note);
    if (state.strums.spawned.length != 1)
      throw 'line-level splash option was ignored';
    state.strums.showNotesplash = true;
    note.noteSplashData = null;
    if (note.isNoteSplashDisabled() || !state.shouldShowNoteSplash(note))
      throw 'missing optional splash data changed native behavior';
    note.noteSplashData = {};
    if (note.isNoteSplashDisabled() || !state.shouldShowNoteSplash(note))
      throw 'partial splash data changed native behavior';
    note.isSustainNote = true;
    if (state.shouldShowNoteSplash(note)) throw 'sustain segment emitted a splash';
    note.isSustainNote = false;
    state.useNoteSplashes = false;
    if (state.shouldShowNoteSplash(note)) throw 'global splash option was ignored';
    state.useNoteSplashes = true;
    state.grpNoteSplashes = null;
    if (state.shouldShowNoteSplash(note)) throw 'missing splash group was ignored';
  }
}
'''.replace("__IS_DISABLED__", is_disabled).replace(
            "__PROPERTY_METHODS__", "\n".join(property_methods)
        ).replace(
            "__SHOULD_SHOW__", should_show
        ).replace(
            "__HAZARD_SPLASH__", hazard_splash
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            Path(folder, "PsychNoteSplashFixture.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-main", "PsychNoteSplashFixture", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
