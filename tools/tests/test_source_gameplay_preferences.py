"""Exercise the shared Psych/Nightmare Vision gameplay preference contract."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
PSYCH_DONOR = ROOT.parent / "fnf_sources/FNF-PsychEngine/source"
NV_DONOR = ROOT.parent / "fnf_sources/NightmareVision/source"

KEYS = r'''package flixel.input.keyboard;
enum abstract FlxKey(Int) from Int to Int {
 var NONE=-1; var A=65; var B=66; var D=68; var R=82; var S=83; var W=87;
 var ZERO=48; var SEVEN=55; var EIGHT=56; var SPACE=32; var ENTER=13;
 var BACKSPACE=8; var ESCAPE=27; var PLUS=187; var MINUS=189;
 var UP=38; var DOWN=40; var LEFT=37; var RIGHT=39; var F3=114; var F5=116;
 var F6=117; var F11=122; var NUMPADPLUS=107; var NUMPADMINUS=109;
}'''

GAMEPAD = r'''package flixel.input.gamepad;
enum abstract FlxGamepadInputID(Int) from Int to Int {
 var NONE=-1; var A=0; var B=1; var X=2; var Y=3; var BACK=6; var START=7;
 var DPAD_UP=11; var DPAD_DOWN=12; var DPAD_LEFT=13; var DPAD_RIGHT=14; var GUIDE=5;
 var LEFT_STICK_DIGITAL_UP=34; var LEFT_STICK_DIGITAL_DOWN=35;
 var LEFT_STICK_DIGITAL_LEFT=36; var LEFT_STICK_DIGITAL_RIGHT=37;
}'''

MAIN = r'''package;
import haxe.ds.StringMap;

class MemoryOwnerSave {
 public var values:Dynamic = {};
 public function new() {}
 public function getField(name:String):Dynamic return Reflect.field(values, name);
 public function setField(name:String, value:Dynamic):Dynamic {
  Reflect.setField(values, name, value); return value;
 }
 public function flush():Void {}
}

class RecordingPrefs {
 public var calls:Array<String> = [];
 public function new() {}
 public function getGameplaySetting(name:String, fallback:Dynamic):Dynamic {
  calls.push(name + ':' + Std.string(fallback));
  return switch name {
   case 'healthgain': -2.75;
   case 'healthloss': 3.125;
   case 'instakill': true;
   case 'practice': true;
   case 'botplay': true;
   default: fallback;
  };
 }
}

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function eq(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) throw message + ': expected ' + Std.string(expected) + ', got ' + Std.string(actual);
 static function throws(call:Void->Void, marker:String, message:String):Void {
  var didThrow = false;
  try call() catch (error:Dynamic) didThrow = Std.string(error).indexOf(marker) >= 0;
  check(didThrow, message);
 }
 static function main():Void {
  // Exercise the actual owner preference APIs and their real default maps.
  var psych = new PsychOwnerClientPrefs('assets/imported_mods/psych-owner', new MemoryOwnerSave());
  var psychDefault = SourceGameplayPreferences.snapshot(psych, false);
  eq(psychDefault.healthGain, 1.0, 'Psych source default healthgain');
  eq(psychDefault.healthLoss, 1.0, 'Psych source default healthloss');
  eq(psychDefault.instakillOnMiss, false, 'Psych source default instakill');
  eq(psychDefault.practiceMode, false, 'Psych source default practice');
  eq(psychDefault.cpuControlled, false, 'Psych source default botplay');
  eq(psychDefault.guitarHeroSustains, true, 'Psych source default guitarHeroSustains');

  psych.data.gameplaySettings.set('healthgain', -2.75);
  psych.data.gameplaySettings.set('healthloss', 3.125);
  psych.data.gameplaySettings.set('instakill', true);
  psych.data.gameplaySettings.set('practice', true);
  psych.data.gameplaySettings.set('botplay', true);
  psych.data.gameplaySettings.set('opponentplay', true);
  psych.data.guitarHeroSustains = false;
  var psychCapture = SourceGameplayPreferences.snapshot(psych, false);
  eq(psychCapture.healthGain, -2.75, 'Psych snapshot preserves authored healthgain');
  eq(psychCapture.healthLoss, 3.125, 'Psych snapshot preserves authored healthloss');
  eq(psychCapture.instakillOnMiss, true, 'Psych snapshot reads instakill');
  eq(psychCapture.practiceMode, true, 'Psych snapshot reads practice');
  eq(psychCapture.cpuControlled, true, 'Psych snapshot reads botplay');
  eq(psychCapture.guitarHeroSustains, false, 'Psych snapshot reads direct data flag');
  check(!Reflect.hasField(psychCapture, 'opponentplay') && !Reflect.hasField(psychCapture, 'opponentPlay'),
   'opponentplay is not consumed by either source PlayState create path');
  psych.data.gameplaySettings.set('healthgain', 5.5);
  psych.data.gameplaySettings.set('botplay', false);
  psych.data.guitarHeroSustains = true;
  eq(psychCapture.healthGain, -2.75, 'captured Psych health setting must not track later map changes');
  eq(psychCapture.cpuControlled, true, 'captured Psych botplay must not track later map changes');
  eq(psychCapture.guitarHeroSustains, false, 'captured Psych sustain setting must not track later data changes');

  // Nightmare Vision uses explicit getter defaults and has no GH-sustains gameplay setting.
  var nv = new NightmareVisionClientPrefs('assets/imported_mods/nv-owner', new MemoryOwnerSave());
  var nvDefault = SourceGameplayPreferences.snapshot(nv, true);
  eq(nvDefault.healthGain, 1.0, 'Nightmare Vision source default healthgain');
  eq(nvDefault.healthLoss, 1.0, 'Nightmare Vision source default healthloss');
  eq(nvDefault.instakillOnMiss, false, 'Nightmare Vision source default instakill');
  eq(nvDefault.practiceMode, false, 'Nightmare Vision source default practice');
  eq(nvDefault.cpuControlled, false, 'Nightmare Vision source default botplay');
  eq(nvDefault.guitarHeroSustains, false, 'Nightmare Vision has no GH-sustains gameplay preference');
  nv.view.gameplaySettings.set('healthgain', -2.75);
  nv.view.gameplaySettings.set('healthloss', 3.125);
  nv.view.gameplaySettings.set('instakill', true);
  nv.view.gameplaySettings.set('practice', true);
  nv.view.gameplaySettings.set('botplay', true);
  nv.view.guitarHeroSustains = true;
  var nvCapture = SourceGameplayPreferences.snapshot(nv, true);
  eq(nvCapture.healthGain, -2.75, 'NV snapshot preserves authored healthgain');
  eq(nvCapture.healthLoss, 3.125, 'NV snapshot preserves authored healthloss');
  eq(nvCapture.instakillOnMiss, true, 'NV snapshot reads instakill');
  eq(nvCapture.practiceMode, true, 'NV snapshot reads practice');
  eq(nvCapture.cpuControlled, true, 'NV snapshot reads botplay');
  eq(nvCapture.guitarHeroSustains, false, 'NV ignores an unsupported GH-sustains field');
  nv.view.gameplaySettings.set('healthgain', 0.25);
  nv.view.gameplaySettings.set('botplay', false);
  eq(nvCapture.healthGain, -2.75, 'captured NV health setting must not track later map changes');
  eq(nvCapture.cpuControlled, true, 'captured NV botplay must not track later map changes');

  // These two preference flags stay live and resolve through the dialect's own container.
  psych.data.ghostTapping = true; psych.data.noReset = false;
  eq(SourceGameplayPreferences.liveBool(psych, false, 'ghostTapping', false), true, 'Psych live ghostTapping');
  eq(SourceGameplayPreferences.liveBool(psych, false, 'noReset', true), false, 'Psych live noReset');
  psych.data.ghostTapping = false; psych.data.noReset = true;
  eq(SourceGameplayPreferences.liveBool(psych, false, 'ghostTapping', true), false, 'Psych ghostTapping updates live');
  eq(SourceGameplayPreferences.liveBool(psych, false, 'noReset', false), true, 'Psych noReset updates live');
  nv.view.ghostTapping = true; nv.view.noReset = false;
  eq(SourceGameplayPreferences.liveBool(nv, true, 'ghostTapping', false), true, 'NV live ghostTapping');
  eq(SourceGameplayPreferences.liveBool(nv, true, 'noReset', true), false, 'NV live noReset');
  nv.view.ghostTapping = false; nv.view.noReset = true;
  eq(SourceGameplayPreferences.liveBool(nv, true, 'ghostTapping', true), false, 'NV ghostTapping updates live');
  eq(SourceGameplayPreferences.liveBool(nv, true, 'noReset', false), true, 'NV noReset updates live');
  var dialects:Dynamic = {data:{ghostTapping:true}, view:{ghostTapping:false}};
  eq(SourceGameplayPreferences.liveBool(dialects, false, 'ghostTapping', false), true,
   'Psych live lookup must use data');
  eq(SourceGameplayPreferences.liveBool(dialects, true, 'ghostTapping', true), false,
   'NV live lookup must use view');
  eq(SourceGameplayPreferences.liveBool(null, false, 'ghostTapping', true), true,
   'null live owner uses the caller native fallback');
  eq(SourceGameplayPreferences.liveBool({data:{}}, false, 'ghostTapping', true), true,
   'missing live flag uses the caller fallback');
  eq(SourceGameplayPreferences.liveBool({data:{ghostTapping:'true'}}, false, 'ghostTapping', true), true,
   'non-boolean live value uses the caller fallback');

  var recording = new RecordingPrefs();
  var recorded = SourceGameplayPreferences.snapshot(recording, true);
  eq(recorded.healthGain, -2.75, 'getter result is not sanitized');
  eq(recorded.healthLoss, 3.125, 'getter result is not sanitized');
  eq(recording.calls.join('|'), 'healthgain:1|healthloss:1|instakill:false|practice:false|botplay:false',
   'snapshot must call the owner getter with donor gameplay keys and fallbacks');
  throws(function() SourceGameplayPreferences.snapshot(null, false), 'Missing owner preferences',
   'snapshot should diagnose a missing owner');
  throws(function() SourceGameplayPreferences.snapshot({}, false), 'getGameplaySetting',
   'snapshot should diagnose a malformed owner instead of hiding a missing getter');
  throws(function() SourceGameplayPreferences.snapshot({getGameplaySetting:function(name, fallback) return fallback}, false),
   'no data object', 'Psych snapshot should diagnose missing data');
  throws(function() SourceGameplayPreferences.liveBool({}, true, 'ghostTapping', true), 'no view object',
   'live read should diagnose a malformed non-null owner');
  throws(function() SourceGameplayPreferences.snapshot({getGameplaySetting:function(name, fallback) throw 'getter failed'}, true),
   'healthgain', 'getter errors should include the failing setting');
 }
}
'''


class SourceGameplayPreferencesTest(unittest.TestCase):
    def test_owner_snapshots_and_live_flags_execute(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            for rel, content in (
                ("flixel/input/keyboard/FlxKey.hx", KEYS),
                ("flixel/input/gamepad/FlxGamepadInputID.hx", GAMEPAD),
                ("Main.hx", MAIN),
            ):
                target = work / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pinned_donor_defaults_and_create_sampling_match_contract(self):
        psych_prefs = (PSYCH_DONOR / "backend/ClientPrefs.hx").read_text(encoding="utf-8")
        psych_play = (PSYCH_DONOR / "states/PlayState.hx").read_text(encoding="utf-8")
        nv_prefs = (NV_DONOR / "funkin/data/ClientPrefs.hx").read_text(encoding="utf-8")
        nv_play = (NV_DONOR / "funkin/states/PlayState.hx").read_text(encoding="utf-8")
        for field, default in (("healthgain", "1.0"), ("healthloss", "1.0"),
                               ("instakill", "false"), ("practice", "false"), ("botplay", "false")):
            with self.subTest(dialect="Psych", field=field):
                self.assertIn(f"'{field}' => {default}", psych_prefs)
                self.assertIn(f"ClientPrefs.getGameplaySetting('{field}')", psych_play)
            with self.subTest(dialect="Nightmare Vision", field=field):
                self.assertIn(f"'{field}' => {default}", nv_prefs)
                self.assertIn(f"ClientPrefs.getGameplaySetting('{field}',", nv_play)
        self.assertIn("guitarHeroSustains = ClientPrefs.data.guitarHeroSustains;", psych_play)
        self.assertNotIn("guitarHeroSustains", nv_play)
        self.assertIn("ClientPrefs.data.ghostTapping", psych_play)
        self.assertIn("ClientPrefs.data.noReset", psych_play)
        self.assertIn("ClientPrefs.ghostTapping", nv_play)
        self.assertIn("ClientPrefs.noReset", nv_play)
        self.assertNotIn("getGameplaySetting('opponentplay'", psych_play)
        self.assertNotIn("getGameplaySetting('opponentplay'", nv_play)


if __name__ == "__main__":
    unittest.main()
