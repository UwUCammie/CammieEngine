"""Focused routing and lifecycle coverage for native HXC StoryMenu modules."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class HxcStoryMenuRoutingTest(unittest.TestCase):
    def test_song_companions_follow_selected_owner_once(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            selected = temp / "selected"
            older = temp / "older"
            paths = [
                older / "scripts/songs/shared.hxc",
                selected / "scripts/songs/shared.hxc",
                older / "scripts/songs/older-only.hxc",
                selected / "scripts/songs/selected-only.hxc",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("class Fixture extends Song {}", newline='\n')
            haxe_paths = ", ".join(json.dumps(str(path)) for path in paths)
            main = f'''class Main {{
  static function main() {{
    var paths = [{haxe_paths}];
    var result = HxcScriptDiscovery.preferFamilyPaths(paths,
      [{json.dumps(str(selected))}, {json.dumps(str(older))}], "song");
    if (result.length != 3
      || result.indexOf({json.dumps(str(selected / "scripts/songs/shared.hxc"))}) < 0
      || result.indexOf({json.dumps(str(older / "scripts/songs/shared.hxc"))}) >= 0
      || result.indexOf({json.dumps(str(older / "scripts/songs/older-only.hxc"))}) < 0
      || result.indexOf({json.dumps(str(selected / "scripts/songs/selected-only.hxc"))}) < 0)
      throw result;
  }}
}}'''
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(temp),
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("preferFamilyPaths(paths, roots, 'song')",
                      (ROOT / "source/PlayState.hx").read_text())

    def test_relative_module_identity_manifest_precedence_and_level_id(self):
        main = r'''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var path = "scripts/modules/StoryConfirmMouth.hxc";
    if (!HxcStoryMenuRouting.sameModuleIdentity(path, "./scripts/modules/StoryConfirmMouth.hxc"))
      fail("same relative module path did not share identity");
    if (HxcStoryMenuRouting.sameModuleIdentity(path, "scripts/characters/StoryConfirmMouth.hxc"))
      fail("distinct modules with the same basename were collapsed");
    if (HxcStoryMenuRouting.moduleIdentity("../outside.hxc") != "")
      fail("traversal path became a module identity");
    if (!HxcStoryMenuRouting.candidateWins(1, "root/selected.hxc", 2, "root/older.hxc"))
      fail("earlier manifest root did not win");
    if (HxcStoryMenuRouting.candidateWins(2, "root/later.hxc", 1, "root/selected.hxc"))
      fail("older manifest root displaced the selected root");
    if (!HxcStoryMenuRouting.candidateWins(2, "a/path.hxc", 2, "b/path.hxc"))
      fail("deterministic path tie-break");
    if (!HxcStoryMenuRouting.levelMatches("clown", "clown")
      || HxcStoryMenuRouting.levelMatches("clown", "Clown"))
      fail("level id comparison changed HXC string equality");
    var weekNums = [0, 2, 4];
    if (HxcStoryMenuRouting.sourceWeekIndex(1, weekNums) != 2)
      fail("filtered StoryMenu row lost its source week index");
    if (HxcStoryMenuRouting.sourceWeekIndex(4, weekNums) != 4)
      fail("out-of-range StoryMenu mapping did not preserve its visible index");
  }
}'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(temp),
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_module_paths_use_manifest_precedence_without_collapsing_other_files(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            selected = temp / "selected"
            older = temp / "older"
            paths = [
                older / "scripts/modules/shared.hxc",
                selected / "scripts/modules/shared.hxc",
                older / "scripts/modules/nested/same-name.hxc",
                selected / "scripts/modules/other/same-name.hxc",
                older / "scripts/events/shared.hxc",
                selected / "scripts/events/shared.hxc",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("class Fixture extends Module {}", newline='\n')
            haxe_paths = ", ".join(json.dumps(str(path)) for path in paths)
            main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var paths = [{haxe_paths}];
    var result = HxcScriptDiscovery.preferFamilyPaths(paths,
      [{json.dumps(str(selected))}, {json.dumps(str(older))}], "module");
    if (result.length != 5) fail("wrong number of files after exact-path dedup: " + result);
    if (result.indexOf({json.dumps(str(selected / "scripts/modules/shared.hxc"))}) < 0
      || result.indexOf({json.dumps(str(older / "scripts/modules/shared.hxc"))}) >= 0)
      fail("earlier manifest owner did not win: " + result);
    if (result.indexOf({json.dumps(str(older / "scripts/modules/nested/same-name.hxc"))}) < 0
      || result.indexOf({json.dumps(str(selected / "scripts/modules/other/same-name.hxc"))}) < 0)
      fail("different relative module paths were collapsed: " + result);
    if (result.indexOf({json.dumps(str(older / "scripts/events/shared.hxc"))}) < 0
      || result.indexOf({json.dumps(str(selected / "scripts/events/shared.hxc"))}) < 0)
      fail("non-module files were changed: " + result);
  }}
}}'''
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(temp),
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_story_runtime_uses_manifest_roots_and_releases_owned_objects(self):
        runtime = (ROOT / "source/HxcStoryMenuRuntime.hx").read_text()
        state = (ROOT / "source/StoryMenuState.hx").read_text()
        self.assertIn("CompatScriptManifest.rootsInPrecedence(manifest)", runtime)
        self.assertIn("rootPriorityBySong", runtime)
        self.assertIn("HxcStoryMenuRouting.sameModuleIdentity", runtime)
        self.assertIn("scope.timer.cancel()", runtime)
        self.assertIn("scope.sprite.animation.onFrameChange.remove(scope.frameCallback)", runtime)
        self.assertIn("owner.hxcRemoveOwnedStorySprite(scope.sprite)", runtime)
        self.assertIn("hxcStoryMenuRuntime.dispose()", state)
        self.assertIn("hxcStoryMenuRuntime.handlesCurrentSelection()", state)

        selection_start = state.index("function selectWeek()")
        selection_end = state.index("\n\t/** Current native story level", selection_start)
        selection = state[selection_start:selection_end]
        self.assertIn("HxcStoryMenuRouting.sourceWeekIndex(curWeek, weekNums)", selection)
        self.assertIn("weekNames[sourceWeekIndex]", selection)
        self.assertIn("PlayState.storyWeekNum = sourceWeekIndex", selection)
        current_level_start = state.index("public function hxcStoryMenuCurrentLevelId")
        current_level_end = state.index("\n\t/** Songs belonging", current_level_start)
        current_level = state[current_level_start:current_level_end]
        self.assertIn("HxcStoryMenuRouting.sourceWeekIndex(curWeek, weekNums)", current_level)

        transition_start = state.index("public function hxcStartImportedStorySelection")
        transition_end = state.index("\n\tfunction changeDifficulty", transition_start)
        transition = state[transition_start:transition_end]
        self.assertIn("LoadingState.loadAndSwitchState(new PlayState())", transition)
        self.assertIn("FlxG.sound.music.stop()", transition)
        self.assertNotIn("ModifierState", transition)
        self.assertNotIn("skipModifierMenu", transition)


if __name__ == "__main__":
    unittest.main()
