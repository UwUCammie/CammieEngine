"""Regression coverage for generic HXC null-safe compatibility adapters."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


def hx_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@unittest.skipUnless(HAXE.is_file() and HSCRIPT.is_dir(), "portable Haxe/HScript toolchain unavailable")
class HxcNullRuntimeCompatTest(unittest.TestCase):
    def run_fixture(self, source: str):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-null-runtime-", dir=ROOT / "tmp") as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source, newline='\n')
            return subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp", str(ROOT / "source"),
                    "-cp", str(HSCRIPT),
                    "-cp", folder,
                    "-main", "Main", "--interp",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_null_safe_string_and_owner_scoped_mutable_constants(self):
        character = r'''
class HairProbe extends Character {
    function new() {}
    override function onCreate(event) {
        this.color = 0xFFFFFFFF;
        if (this.animation.curAnim != null && this.animation.curAnim.name.startsWith('hair'))
            this.color = 0xFF000000;
    }
}
'''
        difficulty = r'''
class DifficultyProbe extends Module {
    function new() { super('difficulty-probe'); }
    var laneShift = Constants.STRUMLINE_X_OFFSET;
    override function onCreate(event) {
        if (!Constants.DEFAULT_DIFFICULTY_LIST_FULL.contains('alt'))
            Constants.DEFAULT_DIFFICULTY_LIST_FULL.push('alt');
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var character = HxcCompat.analyze({hx_string(character)}, "scripts/characters/hair-probe.hxc");
    if (character.generatedHscript.indexOf("hxcCharacter().color") < 0
      || character.generatedHscript.indexOf("HxcCompatRuntime.stringStartsWith(hxcCharacter().animation.curAnim.name") < 0)
      fail("character member lowering missing: " + character.generatedHscript);
    var difficulty = HxcCompat.analyze({hx_string(difficulty)}, "scripts/modules/difficulty-probe.hxc");
    if (difficulty.generatedHscript.indexOf("HxcCompatRuntime.constantsForRoot(hxcAssetRoot).DEFAULT_DIFFICULTY_LIST_FULL") < 0)
      fail("rooted Constants list lowering missing: " + difficulty.generatedHscript);
    if (difficulty.generatedHscript.indexOf("HxcCompatRuntime.constantsForRoot(hxcAssetRoot).STRUMLINE_X_OFFSET") < 0)
      fail("source strumline constant lowering missing: " + difficulty.generatedHscript);
    new Parser().parseString(character.generatedHscript);
    new Parser().parseString(difficulty.generatedHscript);

    if (HxcCompatRuntime.stringStartsWith(null, "hair")
      || HxcCompatRuntime.stringStartsWith("other", "hair")
      || HxcCompatRuntime.stringStartsWith("hairFall", null)
      || !HxcCompatRuntime.stringStartsWith("hairFall", "hair"))
      fail("null-safe startsWith semantics");

    HxcCompatRuntime.clear();
    HxcCompatRuntime.bindActiveState({{song: "first"}});
    var rootA = "assets/imported_mods/owner-a";
    var rootB = "assets/imported_mods/owner-b";
    var constantsA = HxcCompatRuntime.constantsForRoot(rootA);
    var listA:Array<Dynamic> = cast Reflect.field(constantsA, "DEFAULT_DIFFICULTY_LIST_FULL");
    if (listA.length != 3 || listA[0] != "easy" || listA[1] != "normal" || listA[2] != "hard")
      fail("default difficulty list contents");
    listA.push("alt");
    var sameOwner:Array<Dynamic> = cast Reflect.field(
      HxcCompatRuntime.constantsForRoot(rootA), "DEFAULT_DIFFICULTY_LIST_FULL");
    var otherOwner:Array<Dynamic> = cast Reflect.field(
      HxcCompatRuntime.constantsForRoot(rootB), "DEFAULT_DIFFICULTY_LIST_FULL");
    if (!sameOwner.contains("alt") || otherOwner.contains("alt"))
      fail("Constants list was not mutable and owner scoped");

    HxcCompatRuntime.bindActiveState({{song: "second"}});
    var nextSong:Array<Dynamic> = cast Reflect.field(
      HxcCompatRuntime.constantsForRoot(rootA), "DEFAULT_DIFFICULTY_LIST_FULL");
    if (nextSong.contains("alt"))
      fail("Constants list leaked across PlayState sessions");
    HxcCompatRuntime.clear();
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hxc_start_temporarily_binds_character_and_seeds_freeplay_type(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("interp.variables.set('FreeplayState', FreeplayState);", play_state)
        self.assertIn("var bindCharacterStart = isHxcSource && characterRole != null", play_state)
        self.assertIn("hxcCharacterCallbackActor = characterOverride == null", play_state)
        self.assertIn("hxcCharacterCallbackActor = previousStartActor;", play_state)
        self.assertIn("hxcCharacterCallbackRole = previousStartRole;", play_state)

    def test_destroy_callbacks_accept_shared_hxc_lifecycle_payload(self):
        main = r'''import hscript.Parser;
import hscript.Interp;
class Main {
  static function main() {
    var sources = [
      "class NoArgDestroy extends Module { override function onDestroy() { trace('closed'); } }",
      "class EventDestroy extends Module { override function onDestroy(event:ScriptEvent) { trace('closed'); } }"
    ];
    for (source in sources) {
      var converted = HxcCompat.analyze(source, 'scripts/modules/destroy-probe.hxc');
      if (converted.generatedHscript.indexOf('function destroy(') < 0)
        throw 'destroy callback missing';
      var interp = new Interp();
      interp.variables.set('trace', function(_value:Dynamic) {});
      interp.execute(new Parser().parseString(converted.generatedHscript));
      var callback:Dynamic = interp.variables.get('destroy');
      callback(EngineCompat.hxcLifecyclePayload('destroy'));
    }
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
