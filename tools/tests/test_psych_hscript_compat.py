"""Fail-closed normalization and discovery for plain Psych `.hx` callbacks."""
from haxe_test_support import HAXE_COMMAND

import json
from pathlib import Path
from haxe_test_support import FixturePath as Path
import shutil
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
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


MAIN = r'''import haxe.Json;
import hscript.Interp;
import hscript.Parser;
import sys.io.File;

class FakeStrumCamera {
  public var name:String;
  public function new(name:String) this.name = name;
}

class FakeStrumCameraManager {
  public var list:Array<FakeStrumCamera>;
  public var operations:Array<String> = [];
  public function new(list:Array<FakeStrumCamera>) this.list = list;
  public function remove(camera:FakeStrumCamera, ?defaultDrawTarget:Bool = true):FakeStrumCamera {
    operations.push('remove:' + camera.name + ':' + defaultDrawTarget);
    list.remove(camera);
    return camera;
  }
  public function add(camera:FakeStrumCamera, ?defaultDrawTarget:Bool = true):FakeStrumCamera {
    operations.push('add:' + camera.name + ':' + defaultDrawTarget);
    list.push(camera);
    return camera;
  }
}

class FakeFlxG {
  public static var cameras:FakeStrumCameraManager;
}

class FakeFlxRect {}

class Main {
  static function main():Void {
    var args = Sys.args();
    if (args[0] == "normalize" || args[0] == "runtime-normalize") {
      Sys.println(Json.stringify(PsychHscriptCompat.normalize(File.getContent(args[1]), args[0] == "runtime-normalize")));
      return;
    }
    if (args[0] == "execute-strumcam") {
      executeStrumCam(args[1]);
      Sys.println("ok");
      return;
    }
    var chart:Dynamic = {song:{song:"song", stage:"arena"}};
    var plan = PsychScriptDiscovery.discover(args[1], "song", chart);
    var selected:Array<String> = [];
    for (entry in plan.scripts) selected.push(entry.scope + "|" + entry.name + "|" + entry.path);
    Sys.println(Json.stringify(selected));
  }

  static function executeStrumCam(path:String):Void {
    var converted = PsychHscriptCompat.normalize(File.getContent(path));
    if (!converted.supported) throw 'example StrumCam was rejected: ' + converted.diagnostics;
    if (!StringTools.startsWith(converted.source, PsychHscriptCompat.TRANSLATED_MARKER))
      throw 'normalized source lost its marker';

    var world = new FakeStrumCamera('world');
    var other = new FakeStrumCamera('other');
    var hud = new FakeStrumCamera('hud');
    FakeFlxG.cameras = new FakeStrumCameraManager([world, other, hud]);
    var game:Dynamic = {camHUD:hud, camOther:other};
    var interp = new Interp();
    var plainPsychHscript = StringTools.startsWith(converted.source, PsychHscriptCompat.TRANSLATED_MARKER);
    interp.variables.set('__psychPlainHscript', plainPsychHscript);
    interp.variables.set('FlxG', FakeFlxG);
    if (interp.variables.get('__psychPlainHscript') == true) {
      interp.variables.set('game', game);
      interp.variables.set('FlxCamera', FakeStrumCamera);
      interp.variables.set('FlxRect', FakeFlxRect);
      interp.variables.set('Paths', {});
    }
    interp.execute(new Parser().parseString(converted.source));
    var hook:Dynamic = interp.variables.get('onCreatePost');
    if (hook == null) throw 'normalized StrumCam did not define onCreatePost';
    hook();

    var cameras = FakeFlxG.cameras;
    if (cameras.list.length != 3 || cameras.list[0] != world
      || cameras.list[1] != hud || cameras.list[2] != other)
      throw 'camera order mismatch: ' + [for (camera in cameras.list) camera.name];
    var expected = [
      'remove:hud:false', 'remove:other:false', 'add:hud:false', 'add:other:false'
    ];
    if (cameras.operations.join('|') != expected.join('|'))
      throw 'camera operations mismatch: ' + cameras.operations;
  }
}
'''


STAGE_FALLBACK_FIXTURE = r'''import haxe.Json;
import haxe.io.Path;
import hscript.Parser;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef CompatTranslation = {
  var hscript:Null<String>;
  var diagnostics:Array<Dynamic>;
}

typedef HxcTranslation = {
  var generatedHscript:Null<String>;
  var diagnostics:Array<Dynamic>;
}

class FNFAssets {
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return File.getContent(path);
  public static function getHscript(path:String):Null<String> return null;
}

class Song {
  public static function storageFolder(_song:Dynamic):String return 'song';
}

class LuaCompat {
  public static function translate(_source:String, _path:String, ?_allowEmbeddedHscript:Bool = false):CompatTranslation
    return {hscript:'function onCreate() {}', diagnostics:[]};
}

class PsychStageCompat {
  public static function translateFile(_path:String):CompatTranslation
    return {hscript:'function onCreate() {}', diagnostics:[]};
}

class HxcCompat {
  public static function translate(_source:String, _path:String):HxcTranslation
    return {generatedHscript:'', diagnostics:[]};
}

class StageFallbackFixture {
  public var SONG:Dynamic;
  var root:String;
  public var selected:Array<String> = [];

  public function new(root:String) {
    this.root = root;
    SONG = {song:'song', stage:'Stage'};
  }

  function compatScriptRoots():Array<String> return [root];
  function compatPsychOwnerForScript(path:String):Null<String>
    return path.toLowerCase().startsWith(root.toLowerCase()) ? root : null;
  function applyPsychStageJson(_path:String, _scopedRoot:String):Void {}

  __GET_COMPATIBLE_HSCRIPT__

  __LOAD_PSYCH_STAGE_COMPAT__

  function makeHaxeState(_scope:String, path:String, filename:String,
      ?sourceOverride:String, ?_characterRole:String, ?_characterOverride:Dynamic,
      ?_metadataSink:Dynamic, ?_extraPsychOwnerRoot:String):Void {
    var source = sourceOverride == null ? getCompatibleHscript(path + filename) : sourceOverride;
    if (source == null) throw 'No compatible HScript/Lua module found at ' + path + filename;
    // Match the runtime's important boundary: a disabled-source comment parses
    // successfully, so unsupported .hx must return null before it can mask Lua.
    new Parser().parseString(source);
    selected.push(filename);
  }

  public function run():Void {
    if (!loadPsychStageCompat()) throw 'no stage script was loaded';
  }

  static function main():Void {
    var fixture = new StageFallbackFixture(Sys.args()[0]);
    fixture.run();
    Sys.println(Json.stringify(fixture.selected));
  }
}
'''


class PsychHscriptCompatTest(unittest.TestCase):
    def run_haxe(self, arguments):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            shutil.copy(ROOT / "source/PsychHscriptCompat.hx", temp / "PsychHscriptCompat.hx")
            shutil.copy(ROOT / "source/PsychScriptDiscovery.hx", temp / "PsychScriptDiscovery.hx")
            (temp / "Main.hx").write_text(MAIN, newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "--run", "Main", *map(str, arguments)],
                cwd=folder,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        if arguments[0] == "execute-strumcam":
            self.assertEqual(result.stdout.strip(), "ok")
            return None
        return json.loads(result.stdout)

    def normalize(self, source):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source_path = Path(folder) / "script.hx"
            source_path.write_text(source, newline="\n")
            return self.run_haxe(["normalize", source_path])

    def test_runtime_normalization_preserves_direct_imports_for_iris_resolution(self):
        source = 'import haxe.crypto.Md5;\nimport flixel.FlxG;\nfunction onCreate() return Md5.encode("test");'
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "native.hx"
            path.write_text(source, encoding="utf-8")
            result = self.run_haxe(["runtime-normalize", path])
        self.assertTrue(result["supported"], result["diagnostics"])
        self.assertEqual(result["strippedImports"], [])
        self.assertIn(source, result["source"].replace("\r\n", "\n"))

    def test_strumcam_imports_are_masked_without_changing_script_or_comments(self):
        source = '''import flixel.math.FlxRect; // unused Psych import
import /* keep this note */ flixel.FlxCamera;
import flixel.FlxG;
// import flixel.FlxSprite;
var example = "import flixel.FlxSprite;";
function onCreatePost() {
  FlxG.cameras.add(game.camHUD, false);
}
'''
        result = self.normalize(source)

        self.assertTrue(result["supported"])
        self.assertEqual(result["strippedImports"], [
            "flixel.math.FlxRect", "flixel.FlxCamera", "flixel.FlxG",
        ])
        normalized = result["source"]
        self.assertTrue(normalized.startswith("/* psych-hscript-translated */\n"))
        self.assertIn("// unused Psych import", normalized)
        self.assertIn("/* keep this note */", normalized)
        self.assertIn("// import flixel.FlxSprite;", normalized)
        self.assertIn('"import flixel.FlxSprite;"', normalized)
        self.assertIn("FlxG.cameras.add(game.camHUD, false);", normalized)
        self.assertEqual(normalized.count("import flixel.FlxG;"), 0)

    def test_example_strumcam_plain_callback_is_within_the_supported_surface(self):
        # This mirrors the imported example mod's data/im-also-steve/StrumCam.hx.
        source = '''import flixel.math.FlxRect;
import flixel.FlxCamera;

function onCreatePost() {
  FlxG.cameras.remove(game.camHUD, false);
  FlxG.cameras.remove(game.camOther, false);
  FlxG.cameras.add(game.camHUD, false);
  FlxG.cameras.add(game.camOther, false);
}
'''
        result = self.normalize(source)

        self.assertTrue(result["supported"], result["diagnostics"])
        self.assertEqual(result["strippedImports"], ["flixel.math.FlxRect", "flixel.FlxCamera"])
        self.assertIn("function onCreatePost()", result["source"])
        self.assertIn("FlxG.cameras.add(game.camOther, false);", result["source"])

    def test_example_strumcam_reorders_hud_cameras_without_moving_world_camera(self):
        source = '''import flixel.math.FlxRect;
import flixel.FlxCamera;

function onCreatePost() {
  FlxG.cameras.remove(game.camHUD, false);
  FlxG.cameras.remove(game.camOther, false);
  FlxG.cameras.add(game.camHUD, false);
  FlxG.cameras.add(game.camOther, false);
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            source_path = Path(folder) / "StrumCam.hx"
            source_path.write_text(source, newline="\n")
            self.run_haxe(["execute-strumcam", source_path])

    def test_runtime_glue_gates_hx_loading_and_marker_scoped_bindings(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        loader_start = play_state.index("function getCompatibleHscript(")
        loader_end = play_state.index("\n\t/** Keep Lua table rules", loader_start)
        loader = play_state[loader_start:loader_end]
        self.assertIn("lower.endsWith('.hx')", loader)
        self.assertIn("compatPsychOwnerForScript(normalized) != null", loader)
        self.assertIn("PsychHscriptCompat.normalize", loader)

        state_start = play_state.index("function makeHaxeState(")
        state_end = play_state.index("\n\tfunction makeHaxeStateUI(", state_start)
        state = play_state[state_start:state_end]
        self.assertIn(
            "interp.variables.set('__psychPlainHscript', source.startsWith(PsychHscriptCompat.TRANSLATED_MARKER));",
            state,
        )
        bindings_start = state.index("if (interp.variables.get('__psychPlainHscript') == true)")
        bindings_end = state.index("seedHxcCharacterCompat", bindings_start)
        bindings = state[bindings_start:bindings_end]
        self.assertIn("interp.variables.set('game', this);", bindings)
        self.assertIn("interp.variables.set('FlxRect', FlxRect);", bindings)
        self.assertIn("PsychOwnerPaths.create(compatPsychOwnerForScript(path + filename))", bindings)

    def test_compiled_unknown_and_aliased_import_forms_fail_closed(self):
        cases = {
            "package demo;\nclass Stage {}": "Compiled Haxe declaration `package`",
            "class Stage { public function new() {} }": "Compiled Haxe declaration `class`",
            "import flixel.fake.Missing;\nfunction onCreate() {}": "not in the seeded Psych HScript import allowlist",
            "import flixel.FlxG as Game;\nfunction onCreate() {}": "Only direct, allowlisted imports are supported",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                result = self.normalize(source)
                self.assertFalse(result["supported"])
                self.assertEqual(result["source"], "")
                self.assertTrue(any(expected in diagnostic for diagnostic in result["diagnostics"]))
                self.assertTrue(all(diagnostic.startswith("[psych-hscript-unsupported]")
                                    for diagnostic in result["diagnostics"]))

    def test_lexical_context_does_not_treat_function_code_or_literals_as_imports(self):
        source = '''// import unknown.Type;
var quoted = 'import unknown.Type;';
function onCreate() {
  var text = "class Fake {}";
  // import another.Unknown;
  return text;
}
'''
        result = self.normalize(source)
        self.assertTrue(result["supported"], result["diagnostics"])
        self.assertEqual(result["strippedImports"], [])
        self.assertIn("// import unknown.Type;", result["source"])
        self.assertIn("'import unknown.Type;'", result["source"])
        self.assertIn('"class Fake {}"', result["source"])

    def test_discovery_includes_hx_in_global_song_and_selected_stage_scopes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            root = Path(folder) / "psych-mod"
            files = {
                "scripts/Global.HX": "function onCreate() {}",
                "data/Song/StrumCam.hx": "function onCreatePost() {}",
                "stages/Arena.hX": "function onCreate() {}",
                "scripts/disabled/Ignore.hx": "class Compiled {}",
            }
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline="\n")

            selected = self.run_haxe(["discover", root])

        entries = [(entry.split("|", 2)[0], entry.split("|", 2)[1],
                    Path(entry.split("|", 2)[2]).name.lower()) for entry in selected]
        self.assertEqual(set(entries), {
            ("global", "Global", "global.hx"),
            ("song", "song", "strumcam.hx"),
            ("stage", "arena", "arena.hx"),
        })

    def test_unsupported_compiled_stage_hx_does_not_hide_lua_sibling(self):
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        compatible = extract_method(play_state, "function getCompatibleHscript(")
        stage_loader = extract_method(play_state, "function loadPsychStageCompat():Bool")
        fixture_source = STAGE_FALLBACK_FIXTURE.replace(
            "__GET_COMPATIBLE_HSCRIPT__", compatible
        ).replace("__LOAD_PSYCH_STAGE_COMPAT__", stage_loader)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            for module in ("PsychHscriptCompat.hx", "PsychScriptDiscovery.hx"):
                shutil.copy(ROOT / "source" / module, temp / module)
            (temp / "StageFallbackFixture.hx").write_text(fixture_source, newline="\n")
            root = temp / "psych-mod"
            (root / "stages").mkdir(parents=True)
            (root / "stages" / "Stage.hx").write_text(
                "package demo;\nclass Stage {}\n", newline="\n"
            )
            (root / "stages" / "Stage.lua").write_text(
                "function onCreate() end\n", newline="\n"
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", folder, "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "--run", "StageFallbackFixture", str(root)],
                cwd=folder,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        self.assertTrue(output_lines, result.stderr)
        self.assertEqual(json.loads(output_lines[-1]), ["Stage.lua"], result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
