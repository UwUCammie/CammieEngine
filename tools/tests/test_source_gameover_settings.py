"""Owner-scoped Psych/Nightmare Vision GameOver settings contracts."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]


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
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class SourceGameOverSettingsTest(unittest.TestCase):
    def test_defaults_and_overlay_keys_are_present_in_pinned_donors(self):
        donor_root = ROOT.parent / "fnf_sources"
        settings_source = (ROOT / "source/SourceGameOverSettings.hx").read_text(encoding="utf-8")
        psych = (donor_root / "FNF-PsychEngine/source/substates/GameOverSubstate.hx").read_text(
            encoding="utf-8"
        )
        nightmare = (
            donor_root
            / "NightmareVision/source/funkin/states/substates/GameOverSubstate.hx"
        ).read_text(encoding="utf-8")
        psych_reset = extract_method(psych, "public static function resetVariables()")
        nv_reset = extract_method(nightmare, "public static function resetVariables()")
        nv_constructor = extract_method(nightmare, "public function new(?character:Character)")
        psych_play_state = (donor_root / "FNF-PsychEngine/source/states/PlayState.hx").read_text(
            encoding="utf-8"
        )

        for field in ("characterName", "deathSoundName", "loopSoundName", "endSoundName"):
            self.assertIn(f"public var {field}:Null<String>;", settings_source)

        for value in ("bf-dead", "fnf_loss_sfx", "gameOver", "gameOverEnd"):
            self.assertIn(f"= '{value}'", psych_reset)
            self.assertIn(f"= '{value}'", nv_reset)
        self.assertIn("deathDelay = 0", psych_reset)
        self.assertIn("if(GameOverSubstate.deathDelay > 0)", psych_play_state)
        self.assertIn("new FlxTimer().start(GameOverSubstate.deathDelay", psych_play_state)
        for field, setting in (
            ("gameOverChar", "characterName"),
            ("gameOverSound", "deathSoundName"),
            ("gameOverLoop", "loopSoundName"),
            ("gameOverEnd", "endSoundName"),
        ):
            self.assertIn(
                f"_song.{field}.trim().length > 0) {setting} = _song.{field}",
                psych_reset,
            )
        for field, setting in (
            ("gameoverCharacter", "characterName"),
            ("gameoverInitialDeathSound", "deathSoundName"),
            ("gameoverLoopDeathSound", "loopSoundName"),
            ("gameoverConfirmDeathSound", "endSoundName"),
        ):
            self.assertIn(f"{setting} = character.{field} ?? {setting}", nv_constructor)

    def test_donor_defaults_chart_reset_live_writes_and_nv_character_overlays(self):
        fixture = r'''
import SourceGameOverSettings;

class Main {
 static function fail(message:String):Void throw message;
 static function check(value:Bool, message:String):Void if (!value) fail(message);
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ': expected [' + Std.string(expected)
   + '], got [' + Std.string(actual) + ']');

 static function throws(action:Void->Void, fragment:String, message:String):Void {
  var caught = false;
  try action() catch (error:Dynamic) caught = Std.string(error).indexOf(fragment) >= 0;
  check(caught, message);
 }

 static function main():Void {
  var psych = new SourceGameOverSettings(SourceGameOverSettings.PSYCH, {
   gameOverChar: '  chart-dead  ', gameOverSound: '   ',
   gameOverLoop: null, gameOverEnd: 'chart-end'
  });
  eq(psych.characterName, '  chart-dead  ', 'Psych keeps a nonblank chart value verbatim');
  eq(psych.deathSoundName, 'fnf_loss_sfx', 'Psych blank chart sound falls back');
  eq(psych.loopSoundName, 'gameOver', 'Psych null chart loop falls back');
  eq(psych.endSoundName, 'chart-end', 'Psych chart end sound overrides default');
  eq(psych.deathDelay, 0, 'Psych delay starts at zero');

  psych.write('characterName', 'stage-dead');
  psych.write('deathSoundName', 'stage-loss');
  psych.write('deathDelay', 0.15);
  eq(psych.read('characterName'), 'stage-dead', 'Psych live setting writes read back');
  eq(psych.read('deathSoundName'), 'stage-loss', 'Psych sound write reads back');
  eq(psych.read('deathDelay'), 0.15, 'Psych delay write reads back');
  psych.resetVariables();
  eq(psych.characterName, '  chart-dead  ', 'Psych reset reapplies chart character');
  eq(psych.deathSoundName, 'fnf_loss_sfx', 'Psych reset reapplies chart fallback');
  eq(psych.deathDelay, 0, 'Psych reset clears live delay');

  var otherPsych = new SourceGameOverSettings(SourceGameOverSettings.PSYCH, null);
  eq(otherPsych.characterName, 'bf-dead', 'separate owner starts with independent defaults');
  eq(otherPsych.deathSoundName, 'fnf_loss_sfx', 'separate owner has no prior sound write');

  var nv = new SourceGameOverSettings(SourceGameOverSettings.NIGHTMARE,
   {gameOverChar: 'ignored-chart-value'});
  eq(nv.characterName, 'bf-dead', 'NV reset uses donor default and ignores Psych chart fields');
  eq(nv.deathSoundName, 'fnf_loss_sfx', 'NV death sound default matches donor');
  eq(nv.loopSoundName, 'gameOver', 'NV loop sound default matches donor');
  eq(nv.endSoundName, 'gameOverEnd', 'NV end sound default matches donor');
  nv.applyCharacter({
   gameoverCharacter: null, gameoverInitialDeathSound: null,
   gameoverLoopDeathSound: null, gameoverConfirmDeathSound: null
  });
  eq(nv.characterName, 'bf-dead', 'NV null character metadata preserves default');
  eq(nv.deathSoundName, 'fnf_loss_sfx', 'NV null initial sound preserves default');
  nv.applyCharacter({
   gameoverCharacter: 'nv-dead', gameoverInitialDeathSound: '',
   gameoverLoopDeathSound: 'nv-loop', gameoverConfirmDeathSound: ''
  });
  eq(nv.characterName, 'nv-dead', 'NV character metadata overrides name');
  eq(nv.deathSoundName, '', 'NV empty initial sound is a non-null override');
  eq(nv.loopSoundName, 'nv-loop', 'NV metadata overrides loop sound');
  eq(nv.endSoundName, '', 'NV empty confirm sound is a non-null override');
  eq(nv.read('deathSoundName'), '', 'NV canonical facade read keeps empty string');
  eq(nv.write('characterName', 'script-dead'), 'script-dead', 'NV canonical write returns value');
  eq(nv.characterName, 'script-dead', 'NV canonical write updates owner settings');
  nv.resetVariables();
  eq(nv.characterName, 'bf-dead', 'NV reset discards prior character overlay');
  eq(nv.deathSoundName, 'fnf_loss_sfx', 'NV reset discards prior empty sound overlay');

  nv.write('endSoundName', 'only-nv');
  eq(otherPsych.endSoundName, 'gameOverEnd', 'NV writes cannot leak into another owner');
  throws(function() nv.read('deathDelay'), 'Psych-only', 'NV does not expose Psych-only delay');
  throws(function() nv.write('unknown', 'value'), 'unknown setting', 'unknown settings are rejected');
  psych.write('deathDelay', -0.1);
  eq(psych.deathDelay, -0.1, 'negative Psych delay remains a typed Float setting');
  check(!(psych.deathDelay > 0), 'negative delay must take the donor immediate-transition path');
  psych.write('deathDelay', Math.NaN);
  check(Math.isNaN(psych.deathDelay), 'Psych delay preserves NaN Float writes');
  check(!(psych.deathDelay > 0), 'NaN delay must take the donor immediate-transition path');
  psych.write('deathDelay', 0.15);
  check(psych.deathDelay > 0, 'positive delay must take the donor timer path');
  throws(function() psych.write('deathDelay', '0.15'), 'must be a number',
   'non-numeric values cannot be assigned to the donor Float setting');
}
}
'''

        with tempfile.TemporaryDirectory(prefix="source-gameover-settings-", dir=ROOT / "tmp") as scratch:
            scratch = FixturePath(scratch)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
