"""Script-facing gameplay members: UI skin name, note spawn window and plain counters."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, marker: str) -> str:
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
    raise AssertionError(marker)


class PsychPlayStateMemberSurfaceTest(unittest.TestCase):
    def test_members_are_declared_and_kept_for_reflection(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        for declaration in (
            "@:keep public static var stageUI(get, set):String;",
            "@:keep public static var uiPrefix(get, never):String;",
            "@:keep public static var uiPostfix(get, never):String;",
            "@:keep public var spawnTime(get, set):Float;",
            "@:keep public static var campaignMisses:Int = 0;",
            "@:keep public var botplaySine:Float = 0;",
        ):
            self.assertIn(declaration, play)
        # The spawn window scripts set is the one the spawner reads.
        self.assertIn("function get_spawnTime():Float return noteSpawnLookahead;", play)
        self.assertIn("function set_spawnTime(value:Float):Float return noteSpawnLookahead = clampSpawnTime(value);", play)
        self.assertIn("unspawnNotes[0].strumTime - Conductor.songPosition < noteSpawnLookahead", play)
        # A story song adds its misses to the week total next to its score; a reset clears both.
        story = play[play.index("\t\t\tcampaignScore += songScore;\n"):]
        self.assertLess(story.index("campaignMisses += songMisses;"), story.index("campaignScoreDef += songScoreDef;"))
        reset = method(play, "@:keep public static function resetSongInfos")
        self.assertIn("campaignMisses = 0;", reset)

    def test_ui_skin_name_drives_the_pixel_switch_and_splits_like_the_reference(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = play.index("\tvar storedStageUI:String = 'normal';")
        end = play.index("\t/** Botplay as scripts see it", start)
        surface = play[start:end] + "\n" + method(play, "\tpublic static function clampSpawnTime(")
        fixture = r'''class PlayState {
 public static var instance:PlayState;
 public var pixelUI:Bool = false;
 public function new() {}
__SURFACE__
}
class MemberSurfaceFixture {
 static function expect(value:String, prefix:String, postfix:String, pixel:Bool):Void {
  PlayState.stageUI = value;
  if (PlayState.stageUI != value) throw 'read back ' + value + ' as ' + PlayState.stageUI;
  if (PlayState.uiPrefix != prefix) throw value + ' prefix: ' + PlayState.uiPrefix;
  if (PlayState.uiPostfix != postfix) throw value + ' postfix: ' + PlayState.uiPostfix;
  if (PlayState.instance.pixelUI != pixel) throw value + ' pixel switch';
 }
 static function main():Void {
  // Nothing is playing: reads are neutral and writes go nowhere.
  if (PlayState.stageUI != 'normal' || PlayState.uiPrefix != '' || PlayState.uiPostfix != '') throw 'no state';
  PlayState.stageUI = 'pixel';
  if (PlayState.stageUI != 'normal') throw 'write without a state';

  PlayState.instance = new PlayState();
  expect('normal', '', '', false);
  expect('pixel', 'pixel', '-pixel', true);
  expect('retro-pixel', 'retro', '-pixel', true);
  expect('chalk', 'chalk', '', false);

  // Flipping the pixel switch directly wins over a name that disagrees with it.
  PlayState.instance.pixelUI = true;
  if (PlayState.stageUI != 'pixel' || PlayState.uiPostfix != '-pixel') throw 'pixel switch should show in the name';
  PlayState.stageUI = 'retro-pixel';
  PlayState.instance.pixelUI = false;
  if (PlayState.stageUI != 'normal' || PlayState.uiPrefix != '') throw 'cleared pixel switch should show in the name';
  PlayState.stageUI = null;
  if (PlayState.stageUI != 'normal') throw 'null name';

  // A new song starts from its own state, not the last song's name.
  PlayState.stageUI = 'retro-pixel';
  PlayState.instance = new PlayState();
  if (PlayState.stageUI != 'normal') throw 'name leaked into the next song';

  if (PlayState.clampSpawnTime(2000) != 2000 || PlayState.clampSpawnTime(0) != 0) throw 'ordinary spawn windows';
  if (PlayState.clampSpawnTime(-50) != 0) throw 'negative spawn window';
  if (PlayState.clampSpawnTime(9999999) != 10000) throw 'huge spawn window must be capped';
  if (PlayState.clampSpawnTime(Math.NaN) != 1500) throw 'unusable spawn window should fall back';
  Sys.println('OK');
 }
}
'''.replace("__SURFACE__", surface)
        with tempfile.TemporaryDirectory(prefix="member-surface-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            (scratch / "MemberSurfaceFixture.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(scratch), "--run", "MemberSurfaceFixture"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
