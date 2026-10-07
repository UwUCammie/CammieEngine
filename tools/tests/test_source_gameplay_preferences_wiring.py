"""Verify PlayState wiring for owner-local source gameplay preferences."""
from nv_field_fixture_support import write_nv_field_dependencies
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
PLAY_STATE = ROOT / "source/PlayState.hx"


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = None
    line_comment = False
    block_comment = False
    escaped = False
    index = brace
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in ("'", '"'):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError(f"unterminated Haxe method: {marker}")


MAIN = r'''package;
import haxe.ds.StringMap;

class MockPrefs {
 public var data:Dynamic;
 public var view:Dynamic;
 public var gameplaySettings:StringMap<Dynamic> = new StringMap();
 public var calls:Array<String> = [];
 public function new() {
  data = {guitarHeroSustains:true, ghostTapping:false, noReset:false};
  view = {ghostTapping:true, noReset:true};
 }
 public function getGameplaySetting(name:String, fallback:Dynamic):Dynamic {
  calls.push(name + ':' + Std.string(fallback));
  return gameplaySettings.exists(name) ? gameplaySettings.get(name) : fallback;
 }
}

class PlayState {
 public var sourceScoreNightmare:Bool = false;
 public var nightmareVisionPrefs:MockPrefs;
 public var psychClientPrefs:MockPrefs;
 public var playFields:NightmareVisionPlayFields = new NightmareVisionPlayFields();
 public var nightmareVisionFields:Array<NightmareVisionPlayFieldView> = [null, null];
 public var boyfriend:Dynamic = {name:'bf'};
 public var dad:Dynamic = {name:'dad'};
 public var healthGain:Float = 1;
 public var healthLoss:Float = 1;
 public var healthGainMultiplier:Float = 1;
 public var healthLossMultiplier:Float = 1;
 public var instakillOnMiss:Bool = false;
 public var guitarHeroSustains:Bool = false;
 public var practiceMode:Bool = false;
 public var demoMode:Bool = false;
 public var maxStepCatchUp:Int = 8;
 public function new() {}
__METHODS__
}

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) throw message + ': expected ' + Std.string(expected) + ', got ' + Std.string(actual);
 static function main():Void {
  var psych = new MockPrefs();
  psych.gameplaySettings.set('healthgain', -1.25);
  psych.gameplaySettings.set('healthloss', 2.75);
  psych.gameplaySettings.set('instakill', true);
  psych.gameplaySettings.set('practice', false);
  psych.gameplaySettings.set('botplay', false);
  psych.data.guitarHeroSustains = false;
  var psychHost = new PlayState();
  psychHost.psychClientPrefs = psych;
  psychHost.healthGainMultiplier = 1.8;
  psychHost.healthLossMultiplier = 2.2;
  // Native Practice and Demo (including smoke-set flags) survive source false defaults.
  psychHost.practiceMode = true;
  psychHost.demoMode = true;
  psychHost.initializeSourceGameplayPreferences(psych, false);
  eq(psychHost.healthGain, -1.25, 'source health gain is a separate owner factor');
  eq(psychHost.healthLoss, 2.75, 'source health loss is a separate owner factor');
  eq(psychHost.healthGainMultiplier, 1.8, 'source init must not overwrite native health multiplier');
  eq(psychHost.healthLossMultiplier, 2.2, 'source init must not overwrite native health multiplier');
  eq(psychHost.practiceMode, true, 'native practice mode composes with source setting');
  eq(psychHost.demoMode, true, 'native demo/smoke mode composes with source botplay');
  eq(psychHost.maxStepCatchUp, 0, 'demo mode retains native unlimited update cadence');
  eq(psychHost.guitarHeroSustains, false, 'source Psych sustain flag is captured at initialization');
  eq(psych.calls.join('|'), 'healthgain:1|healthloss:1|instakill:false|practice:false|botplay:false',
   'PlayState delegates creation sampling to the shared helper in donor order');
  psych.gameplaySettings.set('healthgain', 6.0);
  psych.data.guitarHeroSustains = true;
  eq(psychHost.healthGain, -1.25, 'created PlayState keeps sampled health values');
  eq(psychHost.guitarHeroSustains, false, 'created PlayState keeps sampled sustain flag');

  // NV CPU state reaches existing player fields only; late fields inherit the live demo state.
  var nv = new MockPrefs();
  nv.gameplaySettings.set('healthgain', 0.5);
  nv.gameplaySettings.set('healthloss', 1.5);
  nv.gameplaySettings.set('instakill', false);
  nv.gameplaySettings.set('practice', true);
  nv.gameplaySettings.set('botplay', true);
  var nvHost = new PlayState();
  nvHost.sourceScoreNightmare = true;
  nvHost.nightmareVisionPrefs = nv;
  nvHost.practiceMode = false;
  var playerField = new NightmareVisionPlayFieldView(0, function():Bool return nvHost.demoMode);
  var nonPlayerField = new NightmareVisionPlayFieldView(1, function():Bool return nvHost.demoMode);
  nonPlayerField.autoPlayed = false;
  nvHost.playFields.members = [playerField, nonPlayerField];
  nvHost.nightmareVisionFields = nvHost.playFields.members;
  nvHost.initializeSourceGameplayPreferences(nv, true);
  eq(nvHost.healthGain, 0.5, 'NV source gameplay health gain sampled');
  eq(nvHost.practiceMode, true, 'NV source practice flag is retained');
  eq(nvHost.demoMode, true, 'NV source botplay enables demo state');
  eq(nvHost.maxStepCatchUp, 0, 'source botplay sets unlimited update cadence');
  eq(playerField.autoPlayed, true, 'CPU state reaches an existing player-controlled field');
  eq(nonPlayerField.autoPlayed, false, 'CPU state leaves non-player field overrides alone');
  eq(nvHost.healthGainMultiplier, 1, 'NV source factor remains separate from native modifier');

  var lateHost = new PlayState();
  lateHost.sourceScoreNightmare = true;
  lateHost.nightmareVisionPrefs = nv;
  lateHost.nightmareVisionFields = [null, null];
  lateHost.initializeSourceGameplayPreferences(nv, true);
  eq(lateHost.getNightmareVisionField(0), null, 'source fields remain empty before receptor generation');
  lateHost.playFields.add(new NightmareVisionPlayFieldView(0, function():Bool return lateHost.demoMode));
  lateHost.playFields.add(new NightmareVisionPlayFieldView(1, function():Bool return true));
  lateHost.nightmareVisionFields = lateHost.playFields.members;
  var latePlayer = lateHost.getNightmareVisionField(0);
  eq(latePlayer.autoPlayed, true, 'late-created player field reads live demo state');
  lateHost.setSourceCpuControlled(false);
  eq(latePlayer.autoPlayed, false, 'late player field remains backed by updated demo state');
  var lateOpponent = lateHost.getNightmareVisionField(1);
  eq(lateOpponent.playerControls, false, 'late opponent field retains the source player-control policy');
  eq(lateOpponent.autoPlayed, true, 'field one keeps donor default auto-play policy');

  // Live flags must resolve through the currently selected dialect and owner object.
  var liveHost = new PlayState();
  var livePsych = new MockPrefs();
  livePsych.data = {ghostTapping:false, noReset:false};
  livePsych.view = {ghostTapping:true, noReset:true};
  liveHost.psychClientPrefs = livePsych;
  eq(liveHost.sourceLivePreference('ghostTapping', true), false, 'Psych reads live data, not view');
  eq(liveHost.sourceLivePreference('noReset', true), false, 'Psych reset flag reads live data');
  livePsych.data.ghostTapping = true; livePsych.data.noReset = true;
  eq(liveHost.sourceLivePreference('ghostTapping', false), true, 'Psych live ghost flag mutation is visible');
  eq(liveHost.sourceLivePreference('noReset', false), true, 'Psych live reset flag mutation is visible');
  var liveNv = new MockPrefs();
  liveNv.data = {ghostTapping:false, noReset:false};
  liveNv.view = {ghostTapping:true, noReset:true};
  liveHost.nightmareVisionPrefs = liveNv;
  liveHost.sourceScoreNightmare = true;
  eq(liveHost.sourceLivePreference('ghostTapping', false), true, 'NV reads live view, not data');
  eq(liveHost.sourceLivePreference('noReset', false), true, 'NV reset flag reads live view');
  liveNv.view.ghostTapping = false; liveNv.view.noReset = false;
  eq(liveHost.sourceLivePreference('ghostTapping', true), false, 'NV live ghost flag mutation is visible');
  eq(liveHost.sourceLivePreference('noReset', true), false, 'NV live reset flag mutation is visible');
 }
}'''


class SourceGameplayPreferencesWiringTest(unittest.TestCase):
    def test_extracted_playstate_preference_wiring(self):
        play = PLAY_STATE.read_text(encoding="utf-8")
        methods = [
            extract_method(play, "function initializeSourceGameplayPreferences(owner:Dynamic, nightmare:Bool):Void"),
            extract_method(play, "function setSourceCpuControlled(value:Bool):Void"),
            extract_method(play, "function sourceLivePreference(name:String, fallback:Bool):Bool"),
            extract_method(play, "public function getNightmareVisionField(id:Int):NightmareVisionPlayFieldView"),
        ]
        methods[0] = methods[0].replace("function initializeSourceGameplayPreferences", "public function initializeSourceGameplayPreferences", 1)
        methods[1] = methods[1].replace("function setSourceCpuControlled", "public function setSourceCpuControlled", 1)
        methods[2] = methods[2].replace("function sourceLivePreference", "public function sourceLivePreference", 1)
        fixture = MAIN.replace("__METHODS__", "\n".join(methods))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            (work / "Strumline.hx").write_text("class Strumline { public var members:Array<StrumNote> = []; public function new() {} } class StrumNote { public var resetAnim:Float=0; public function playAnim(name:String):Void {} public function new() {} }", newline="\n")
            write_nv_field_dependencies(work)
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_both_source_lifecycles_sample_before_callbacks_and_live_flag_gates(self):
        play = PLAY_STATE.read_text(encoding="utf-8")
        create = extract_method(play, "override public function create()")
        nv_init = extract_method(play, "function initializeNightmareVisionScripts():Void")
        psych_init = create.index("initializeSourceGameplayPreferences(psychClientPrefs, false)")
        self.assertLess(psych_init, create.index("initializeNightmareVisionScripts();"))
        self.assertLess(psych_init, create.index("PsychRuntimeBindings.dispatch(this, 'onCreatePost'"))
        self.assertLess(nv_init.index("initializeSourceGameplayPreferences(nightmareVisionPrefs, true)"),
                        nv_init.index("stage.runScript(nightmareVisionScripts.group)"))
        self.assertLess(nv_init.index("initializeSourceGameplayPreferences(nightmareVisionPrefs, true)"),
                        nv_init.index("callNightmareVision('onAddSpriteGroups'"))
        update = extract_method(play, "override public function update(elapsed:Float)")
        self.assertIn("!sourceLivePreference('noReset', false)", update)
        psych_press = extract_method(play, "function psychSourceKeyPressed(")
        self.assertIn("sourceLivePreference('ghostTapping', ghostTapping)", psych_press)
        note_miss = extract_method(play, "function noteMissCore(direction:Int = 1,")
        self.assertIn("sourceLivePreference('ghostTapping', ghostTapping)", note_miss)
        self.assertLess(create.index("RuntimeSmokeHarness.config().practice"),
                        create.index("initializeSourceGameplayPreferences(psychClientPrefs, false)"))
        self.assertLess(create.index("RuntimeSmokeHarness.config().botplay"),
                        create.index("initializeSourceGameplayPreferences(psychClientPrefs, false)"))


if __name__ == "__main__":
    unittest.main()
