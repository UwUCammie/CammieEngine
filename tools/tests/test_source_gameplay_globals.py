"""The gameplay globals Lua and HScript imports read come from one shared provider."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]

# Names the reference Lua runtime defines in every state and this provider owns.
EXPECTED = {
    "bpm": "Float", "scrollSpeed": "Float", "songLength": "Float", "songName": "String",
    "songPath": "String", "loadedSongName": "String", "loadedSongPath": "String",
    "curStage": "String", "hasVocals": "Bool", "isStoryMode": "Bool", "seenCutscene": "Bool",
    "startedCountdown": "Bool", "difficulty": "Int", "difficultyName": "String",
    "difficultyPath": "String", "week": "String", "weekRaw": "Int", "deaths": "Int",
    "botPlay": "Bool", "practice": "Bool", "healthGainMult": "Float", "healthLossMult": "Float",
    "instakillOnMiss": "Bool", "curDecBeat": "Float", "curDecStep": "Float",
    "defaultBoyfriendX": "Float", "defaultBoyfriendY": "Float", "defaultOpponentX": "Float",
    "defaultOpponentY": "Float", "defaultGirlfriendX": "Float", "defaultGirlfriendY": "Float",
    "modFolder": "String", "currentModDirectory": "String", "luaDebugMode": "Bool",
    "luaDeprecatedWarnings": "Bool", "noteSkinPostfix": "String", "splashSkinPostfix": "String",
    "mustHitSection": "Bool", "altAnim": "Bool", "gfSection": "Bool",
}

STATE = r'''
 static function state():SourceGameplayGlobals.SourceGameplayState {
  return {
   songName: 'Test Song', songPath: 'test-song', songBpm: 150, songSpeed: 2.5, songLength: 90000,
   stage: 'alley', hasVocals: true, storyMode: true, difficulty: 2, difficultyName: 'Hard',
   week: '3', seenCutscene: false, startedCountdown: false, botPlay: true, practice: false,
   healthGainMult: 1.5, healthLossMult: 0.5, instakillOnMiss: true, deaths: 4,
   section: {mustHitSection: true, altAnim: true, gfSection: false},
   curDecBeat: 1.25, curDecStep: 5, boyfriendX: 770, boyfriendY: 100, opponentX: 100,
   opponentY: 120, girlfriendX: 400, girlfriendY: 130, modFolder: 'pack'
  };
 }
'''


def run_fixture(test, name, body, hscript=False):
    if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
        test.skipTest("portable Haxe interpreter is unavailable")
    with tempfile.TemporaryDirectory(prefix="source-gameplay-globals-", dir=ROOT / "tmp") as folder:
        scratch = Path(folder)
        (scratch / (name + ".hx")).write_text(body, encoding="utf-8", newline="\n")
        paths = ["-cp", str(ROOT / "source")] if hscript else []
        if hscript:
            paths += ["-cp", str(ROOT / ".haxelib/hscript/2,5,0")]
        else:
            (scratch / "SourceGameplayGlobals.hx").write_text(
                (ROOT / "source/SourceGameplayGlobals.hx").read_text(encoding="utf-8"),
                encoding="utf-8", newline="\n")
        result = subprocess.run([*HAXE_COMMAND, *paths, "-cp", str(scratch), "--run", name],
                                cwd=ROOT, capture_output=True, text=True, timeout=120)
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    return result.stdout


class SourceGameplayGlobalsTest(unittest.TestCase):
    def test_snapshot_defines_every_expected_global_with_its_type(self):
        checks = "\n".join(
            f"  expect(values, '{name}', {kind});" for name, kind in sorted(EXPECTED.items()))
        fixture = "class GlobalsSnapshotFixture {\n" + STATE + r'''
 static function expect(values:Map<String, Dynamic>, name:String, kind:Dynamic):Void {
  if (!values.exists(name)) throw 'missing global ' + name;
  var value:Dynamic = values.get(name);
  // Whole numbers are also Float, which is all a script can tell apart anyway.
  if (!Std.isOfType(value, kind)) throw name + ' has the wrong type: ' + Std.string(value);
 }
 static function main():Void {
  var values = SourceGameplayGlobals.snapshot(state());
__CHECKS__
  if (values.get('bpm') != 150 || values.get('scrollSpeed') != 2.5) throw 'chart values changed';
  if (values.get('botPlay') != true || values.get('practice') != false) throw 'mode flags changed';
  if (values.get('curStage') != 'alley' || values.get('deaths') != 4) throw 'stage or deaths changed';
  if (values.get('week') != '3' || values.get('weekRaw') != 3) throw 'numeric week lost its index';
  if (values.get('difficultyPath') != '-hard') throw 'difficulty suffix: ' + values.get('difficultyPath');
  if (values.get('defaultOpponentX') != 100 || values.get('defaultGirlfriendY') != 130) throw 'default positions';
  if (values.get('mustHitSection') != true || values.get('altAnim') != true || values.get('gfSection') != false)
   throw 'section flags';
  if (values.get('modFolder') != 'pack' || values.get('currentModDirectory') != 'pack') throw 'mod folder';

  // The helpers behind the less obvious entries.
  if (SourceGameplayGlobals.difficultyPath('Normal') != '' || SourceGameplayGlobals.difficultyPath(null) != '')
   throw 'default difficulty should have no suffix';
  if (SourceGameplayGlobals.weekIndex('Tutorial') != 0 || SourceGameplayGlobals.weekIndex(null) != 0)
   throw 'named week should read as the first week';
  if (SourceGameplayGlobals.folderName('assets/imported_mods/pack/') != 'pack'
   || SourceGameplayGlobals.folderName('a\\b\\c') != 'c' || SourceGameplayGlobals.folderName(null) != '')
   throw 'folder name';
  var empty = SourceGameplayGlobals.section(null);
  if (empty.get('mustHitSection') != false || empty.get('altAnim') != false) throw 'missing section should be all false';

  // Seeding keeps a value the host already exposes and marks the interpreter.
  var variables:Map<String, Dynamic> = ['bpm' => 99];
  SourceGameplayGlobals.seedMissing(variables, values);
  if (variables.get('bpm') != 99) throw 'seed replaced an existing global';
  if (variables.get('botPlay') != true) throw 'seed skipped a missing global';
  SourceGameplayGlobals.refresh(variables, 'botPlay', false);
  if (variables.get('botPlay') != false) throw 'refresh did not reach a seeded interpreter';
  var foreign:Map<String, Dynamic> = new Map();
  SourceGameplayGlobals.refresh(foreign, 'botPlay', true);
  if (foreign.exists('botPlay')) throw 'refresh leaked into an interpreter that was never seeded';
  Sys.println('OK');
 }
}
'''.replace("__CHECKS__", checks)
        self.assertIn("OK", run_fixture(self, "GlobalsSnapshotFixture", fixture))

    def test_lua_script_can_branch_and_do_arithmetic_on_seeded_globals(self):
        fixture = "import hscript.Parser;\nclass GlobalsLuaFixture {\n" + STATE + r'''
 static function main():Void {
  var source = "function onCreate()\n"
   + " if botPlay then\n"
   + "  x = defaultOpponentX + 1\n"
   + " else\n"
   + "  x = 'manual'\n"
   + " end\n"
   + " y = healthGainMult * 2\n"
   + "end\n";
  var translated = LuaCompat.translate(source, 'globals.lua');
  if (!translated.supported) throw translated.diagnostics.join(' | ');
  var interp = new LuaCompatInterp();
  SourceGameplayGlobals.seedMissing(interp.variables, SourceGameplayGlobals.snapshot(state()));
  interp.execute(new Parser().parseString(translated.hscript));
  Reflect.callMethod(null, interp.variables.get('onCreate'), []);
  if (interp.variables.get('x') != 101) throw 'botPlay branch or position arithmetic: ' + Std.string(interp.variables.get('x'));
  if (interp.variables.get('y') != 3) throw 'health multiplier arithmetic: ' + Std.string(interp.variables.get('y'));
  Sys.println('OK');
 }
}
'''
        self.assertIn("OK", run_fixture(self, "GlobalsLuaFixture", fixture, hscript=True))

    def test_both_seeds_read_the_shared_provider(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = play.index("\tfunction seedNightmareVision(")
        nightmare = play[start:play.index("\n\t}\n", start)]
        self.assertIn("SourceGameplayGlobals.snapshot(sourceGameplayState(", nightmare)
        # The inline literal map is gone, apart from the two difficulty overrides.
        self.assertNotIn("=> healthGainMultiplier", nightmare)
        self.assertNotIn("'botPlay' =>", nightmare)
        self.assertIn("fields.set('difficulty', nightmareVisionActiveDifficulty.currentDifficultyIndex);", nightmare)

        start = play.index("\tfunction seedEngineCompat(")
        psych = play[start:play.index("\n\t}\n", start)]
        self.assertIn("SourceGameplayGlobals.seedMissing(interp.variables, SourceGameplayGlobals.snapshot(", psych)

        # Every name the Nightmare Vision preset copies is one the provider defines.
        bindings = (ROOT / "source/NightmareVisionSourceBindings.hx").read_text(encoding="utf-8")
        names = re.search(r"gameplayNames:Array<String> = \[(.*?)\];", bindings, re.S).group(1)
        for name in re.findall(r"'([^']+)'", names):
            self.assertIn(name, EXPECTED, name)

        # Live values are refreshed where they change.
        self.assertIn("refreshSourceGameplayGlobal('altAnim'", play)
        self.assertIn("refreshSourceGameplayGlobal('curDecStep', decStep);", play)
        self.assertIn("refreshSourceGameplayGlobal('botPlay', botPlay);", play)

    def test_fractional_clock_moves_in_songs_that_do_not_drive_the_state_field(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")

        def member(marker, end):
            start = play.index(marker)
            return play[start:play.index(end, start)]

        surface = "\n".join((
            member("\tfunction refreshSourceGameplayGlobal(name:String", "\t/** The fractional step scripts see."),
            member("\tfunction sourceGameplayDecimalStep():Float", "\t/** The fractional clock moves every frame"),
            member("\tfunction refreshSourceGameplayFrameGlobals():Void {", "\tfunction seedEngineCompat("),
        ))
        fixture = r'''class PsychBeatClock {
 public static var step:Float = 0;
 public static function getDecimalStep():Float return step;
}
class FakeInterp {
 public var variables:Map<String, Dynamic> = new Map();
 public function new() {}
}
class PlayState {
 public var modManager:Dynamic = null;
 public var stages:Array<Dynamic> = [];
 public var curDecStep:Float = 0;
 public var curDecBeat:Float = 0;
 public var hscriptStates:Map<String, FakeInterp> = new Map();
 public var botPlay:Bool = false;
 var sourceGameplayGlobalsSeeded:Bool = false;
 var sourceGameplayGlobalsBotPlay:Bool = false;
 var sourceGameplayGlobalsDecStep:Float = Math.NaN;
 public function new() {}
 function sourceBotPlay():Bool return botPlay;
 public function seed(interp:FakeInterp):Void {
  SourceGameplayGlobals.seedMissing(interp.variables, ['curDecStep' => 0.0, 'curDecBeat' => 0.0, 'botPlay' => false]);
  sourceGameplayGlobalsSeeded = true;
 }
 public function frame():Void refreshSourceGameplayFrameGlobals();
__SURFACE__
}
class GlobalsClockFixture {
 static function main():Void {
  var state = new PlayState();
  var lua = new FakeInterp();
  var other = new FakeInterp();
  state.hscriptStates.set('lua', lua);
  state.hscriptStates.set('other', other);

  // Nothing was seeded yet, so a frame leaves every interpreter alone.
  PsychBeatClock.step = 3;
  state.frame();
  if (lua.variables.exists('curDecStep')) throw 'refresh ran before any seed';

  // A plain song: the state field stays at zero, the globals follow the clock.
  state.seed(lua);
  PsychBeatClock.step = 6.5;
  state.frame();
  if (lua.variables.get('curDecStep') != 6.5) throw 'step did not follow the clock: ' + lua.variables.get('curDecStep');
  if (lua.variables.get('curDecBeat') != 1.625) throw 'beat did not follow the clock: ' + lua.variables.get('curDecBeat');
  if (other.variables.exists('curDecStep')) throw 'refresh leaked into an interpreter that was never seeded';
  if (state.curDecStep != 0) throw 'the state field must be left to whoever drives it';

  // A song that drives the field itself keeps that sample, not a second one.
  state.stages.push('stage');
  state.curDecStep = 9.25;
  PsychBeatClock.step = 100;
  state.frame();
  if (lua.variables.get('curDecStep') != 9.25 || lua.variables.get('curDecBeat') != 2.3125)
   throw 'driven field was not used: ' + lua.variables.get('curDecStep');

  state.botPlay = true;
  state.frame();
  if (lua.variables.get('botPlay') != true) throw 'botplay switch did not reach the script';
  state.botPlay = false;
  state.frame();
  if (lua.variables.get('botPlay') != false) throw 'botplay switch did not turn back off';
  Sys.println('OK');
 }
}
'''.replace("__SURFACE__", surface)
        self.assertIn("OK", run_fixture(self, "GlobalsClockFixture", fixture))


if __name__ == "__main__":
    unittest.main()
