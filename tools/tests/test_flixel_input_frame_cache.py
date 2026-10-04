"""Pin Flixel action memoization to game update frames at sub-millisecond FPS."""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND
from tools import patch_flixel_input_frame_cache as patcher


ROOT = Path(__file__).resolve().parents[2]
FLIXEL_DIR = ROOT / ".haxelib/flixel/6,1,2/flixel"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for offset in range(brace, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return source[start:offset + 1]
    raise AssertionError(f"unterminated Haxe method: {marker}")


def write_haxe(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8", newline="\n")


def upstream_game_source(source: str) -> str:
    if "dpui-input-frame-field" not in source:
        return source
    return source.replace(
        patcher.INPUT_UPDATE_METHOD + patcher.INPUT_UPDATE_MARKER,
        patcher.INPUT_UPDATE_METHOD,
        1,
    ).replace(patcher.NEW_TICKS_FIELD, patcher.OLD_TICKS_FIELD, 1)


def upstream_action_source(source: str) -> str:
    if "dpui-input-frame-cache" not in source:
        return source
    return (
        source.replace(patcher.NEW_ACTION_ASSIGNMENT, patcher.OLD_ACTION_ASSIGNMENT, 1)
        .replace(patcher.NEW_ACTION_GUARD, patcher.OLD_ACTION_GUARD, 1)
        .replace(patcher.NEW_ACTION_CACHE_FIELD, patcher.OLD_ACTION_CACHE_FIELD, 1)
    )


class FlixelInputFrameCacheTests(unittest.TestCase):
    def test_patch_is_idempotent_and_rejects_partial_or_drifted_sources(self):
        game = upstream_game_source((FLIXEL_DIR / "FlxGame.hx").read_text(encoding="utf-8"))
        action = upstream_action_source(
            (FLIXEL_DIR / "input/actions/FlxAction.hx").read_text(encoding="utf-8")
        )

        patched_game = patcher.patch_game_source(game)
        patched_action = patcher.patch_action_source(action)
        self.assertEqual(patcher.patch_game_source(patched_game), patched_game)
        self.assertEqual(patcher.patch_action_source(patched_action), patched_action)

        update_input = extract_method(patched_game, "\tfunction updateInput():Void")
        self.assertLess(update_input.index(patcher.INPUT_UPDATE_MARKER), update_input.index("FlxG.inputs.update();"))
        self.assertIn("FlxG.game.inputFrame", patched_action)
        self.assertNotIn("_timestamp == FlxG.game.ticks", patched_action)

        partial_game = game.replace(patcher.OLD_TICKS_FIELD, patcher.NEW_TICKS_FIELD, 1)
        with self.assertRaisesRegex(ValueError, "partial"):
            patcher.patch_game_source(partial_game)
        with self.assertRaisesRegex(ValueError, "not unique"):
            patcher.patch_action_source(action.replace(patcher.OLD_ACTION_GUARD, "", 1))

    def test_patch_files_preserves_line_endings_and_validates_both_sources_first(self):
        game = upstream_game_source((FLIXEL_DIR / "FlxGame.hx").read_text(encoding="utf-8"))
        action = upstream_action_source(
            (FLIXEL_DIR / "input/actions/FlxAction.hx").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory(prefix="flixel-input-patch-") as directory:
            flixel_dir = Path(directory) / "flixel"
            game_path = flixel_dir / "FlxGame.hx"
            action_path = flixel_dir / "input/actions/FlxAction.hx"
            game_path.parent.mkdir(parents=True)
            action_path.parent.mkdir(parents=True)
            game_path.write_bytes(game.replace("\n", "\r\n").encode("utf-8"))
            action_path.write_bytes(action.replace("\n", "\r\n").encode("utf-8"))

            self.assertTrue(patcher.patch_files(flixel_dir))
            self.assertFalse(patcher.patch_files(flixel_dir))
            for path in (game_path, action_path):
                data = path.read_bytes()
                self.assertIn(b"dpui-input-frame-", data)
                self.assertNotIn(b"\n", data.replace(b"\r\n", b""))

            failing_dir = Path(directory) / "failing/flixel"
            bad_game = failing_dir / "FlxGame.hx"
            bad_action = failing_dir / "input/actions/FlxAction.hx"
            bad_game.parent.mkdir(parents=True)
            bad_action.parent.mkdir(parents=True)
            original_game = game.encode("utf-8")
            original_action = action.replace(patcher.OLD_ACTION_ASSIGNMENT, "", 1).encode("utf-8")
            bad_game.write_bytes(original_game)
            bad_action.write_bytes(original_action)

            with self.assertRaisesRegex(ValueError, "not unique"):
                patcher.patch_files(failing_dir)
            self.assertEqual(bad_game.read_bytes(), original_game)
            self.assertEqual(bad_action.read_bytes(), original_action)

    def test_action_cache_refreshes_on_each_update_even_when_ticks_do_not_advance(self):
        action_source = patcher.patch_action_source(
            (FLIXEL_DIR / "input/actions/FlxAction.hx").read_text(encoding="utf-8")
        )
        method = extract_method(action_source, "\tpublic function check():Bool")
        cache_field = re.search(r"(?m)^\tvar _inputFrame:Int = -1; // dpui-input-frame-cache$", action_source)
        self.assertIsNotNone(cache_field)

        with tempfile.TemporaryDirectory(prefix="flixel-input-frame-") as directory:
            source_root = Path(directory) / "src"
            write_haxe(source_root, "flixel/FlxG.hx", """package flixel;
class FlxG {
    public static var game:Dynamic;
}
""")
            write_haxe(source_root, "flixel/input/actions/FlxActionInput.hx", """package flixel.input.actions;
class FlxActionInput {
    public var destroyed:Bool = false;
    public var active:Bool = false;
    public var checks:Int = 0;
    public function new() {}
    public function update():Void {}
    public function check(action:FlxAction):Bool {
        checks++;
        return active;
    }
}
""")
            write_haxe(source_root, "flixel/input/actions/FlxAction.hx", """package flixel.input.actions;
import flixel.FlxG;
class FlxAction {
    public var inputs:Array<FlxActionInput>;
    public var triggered:Bool = false;
    var _x:Null<Float> = null;
    var _y:Null<Float> = null;
""" + cache_field.group(0) + """
    public function new(input:FlxActionInput) {
        inputs = [input];
    }

""" + method + """
}
""")
            write_haxe(source_root, "Main.hx", """import flixel.FlxG;
import flixel.input.actions.FlxAction;
import flixel.input.actions.FlxActionInput;

class Main {
    static function main():Void {
        var input = new FlxActionInput();
        var action = new FlxAction(input);
        FlxG.game = {ticks: 400, inputFrame: 10};

        input.active = true;
        if (!action.check()) throw "new press was not observed";
        input.active = false;
        if (!action.check()) throw "same-frame action cache was not reused";
        if (input.checks != 1) throw "action was checked more than once in one update";

        // FlxGame's millisecond ticks can stay constant across many uncapped
        // updates. A new inputFrame must still poll the released edge.
        FlxG.game.inputFrame++;
        if (action.check()) throw "stale action result survived into the next update";
        if (input.checks != 2) throw "new update frame did not refresh the action cache";

        input.active = true;
        FlxG.game.inputFrame++;
        if (!action.check()) throw "next update's press was missed";
        trace("PASS: FlxAction refreshes per update frame at a fixed millisecond tick");
    }
}
""")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(source_root), "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS: FlxAction refreshes per update frame", result.stdout)

    def test_launchers_and_build_cache_include_the_patch(self):
        run_sh = (ROOT / "run.sh").read_text(encoding="utf-8")
        run_bat = (ROOT / "run.bat").read_text(encoding="utf-8")
        self.assertIn("tools/patch_flixel_input_frame_cache.py", run_sh)
        self.assertIn("tools\\patch_flixel_input_frame_cache.py", run_bat)
        from tools import launch_cache
        self.assertIn("tools/patch_flixel_input_frame_cache.py", launch_cache.HELPERS)


if __name__ == "__main__":
    unittest.main()
