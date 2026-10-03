"""Regression coverage for Psych countdown defaults and script-local gates."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
COUNTDOWN_SCRIPTS = (
    DONOR / "psych/PERFEXION Demo1/data/Extra/function.lua",
    DONOR / "psych/PERFEXION Demo1/data/Extras/function.lua",
)
BALLISTIC = DONOR / "psych/vswhitty/data/ballistic/script.lua"


class PsychAllowCountdownTest(unittest.TestCase):
    def run_fixture(self, source: str):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            path = Path(folder) / "PsychAllowCountdownCompat.hx"
            path.write_text(source, newline='\n')
            return subprocess.run(
                [
                    *HAXE_COMMAND,
                    "-cp",
                    folder,
                    "-cp",
                    str(ROOT / "source"),
                    "-cp",
                    str(HSCRIPT),
                    "-main",
                    "PsychAllowCountdownCompat",
                    "--interp",
                ],
                cwd=ROOT,
                env={**__import__("os").environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True,
                text=True,
                timeout=300,
            )

    def test_synthetic_countdown_gate_translates_without_chart_local_shim(self):
        fixture = r'''
import hscript.Parser;
class PsychAllowCountdownCompat {
    static function main() {
        var source = "function onStartCountdown()\n"
            + "  if not allowCountdown then\n"
            + "    return Function_Stop\n"
            + "  end\n"
            + "  return Function_Continue\n"
            + "end";
        var converted = LuaCompat.translate(source, "countdown.lua");
        if (!converted.supported)
            throw converted.diagnostics.join(" | ");
        if (converted.hscript.indexOf("allowCountdown") < 0)
            throw "countdown gate was dropped";
        new Parser().parseString(converted.hscript);
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_song_local_countdown_gate_survives_callback_reentry(self):
        fixture = r'''
import hscript.Parser;
import hscript.Interp;
class PsychAllowCountdownCompat {
    static function main() {
        var source = "local allowCountdown = false\n"
            + "function onStartCountdown()\n"
            + "  if not allowCountdown and isStoryMode and not seenCutscene then\n"
            + "    allowCountdown = true\n"
            + "    return Function_Stop\n"
            + "  end\n"
            + "  return Function_Continue\n"
            + "end";
        var converted = LuaCompat.translate(source, "song/script.lua");
        if (!converted.supported) throw converted.diagnostics.join(" | ");
        var interp = new Interp();
        interp.variables.set('allowCountdown', true); // engine default before script load
        interp.variables.set('isStoryMode', true);
        interp.variables.set('seenCutscene', false);
        interp.variables.set('Function_Stop', 1);
        interp.variables.set('Function_Continue', 0);
        interp.execute(new Parser().parseString(converted.hscript));
        var callback = interp.variables.get('onStartCountdown');
        if (callback() != 1) throw 'local false did not stop the first countdown';
        if (callback() != 0) throw 'local true did not release the second countdown';
        var freeplay = new Interp();
        freeplay.variables.set('allowCountdown', true);
        freeplay.variables.set('isStoryMode', false);
        freeplay.variables.set('seenCutscene', false);
        freeplay.variables.set('Function_Stop', 1);
        freeplay.variables.set('Function_Continue', 0);
        freeplay.execute(new Parser().parseString(converted.hscript));
        if (freeplay.variables.get('onStartCountdown')() != 0)
            throw 'story-only intro ran in Freeplay';
    }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(BALLISTIC.is_file(), "mounted Whitty donor unavailable")
    def test_forced_freeplay_projects_story_gates_for_authored_intro_and_ending(self):
        path = str(BALLISTIC).replace("\\", "\\\\").replace('"', '\\"')
        fixture = r'''
import hscript.Parser;
import hscript.Interp;
import sys.io.File;
class PsychAllowCountdownCompat {
    static function setup(source:String, projectedStory:Bool):Interp {
        var converted = LuaCompat.translate(source, 'ballistic/script.lua');
        if (!converted.supported) throw converted.diagnostics.join(' | ');
        var interp = new Interp();
        interp.variables.set('allowCountdown', true);
        interp.variables.set('isStoryMode', projectedStory);
        interp.variables.set('seenCutscene', false);
        interp.variables.set('Function_Stop', 1);
        interp.variables.set('Function_Continue', 0);
        for (name in ['triggerEvent', 'setProperty', 'makeAnimatedLuaSprite',
            'addAnimationByPrefix', 'objectPlayAnimation', 'addLuaSprite',
            'cameraShake', 'doTweenZoom', 'doTweenAngle', 'runTimer',
            'playSound', 'cameraFade'])
            interp.variables.set(name, Reflect.makeVarArgs(function(_args:Array<Dynamic>) return null));
        interp.execute(new Parser().parseString(converted.hscript));
        return interp;
    }
    static function main() {
        var source = File.getContent("{path}");
        var forced = setup(source, true); // Freeplay with force-cutscene projection
        if (forced.variables.get('onStartCountdown')() != 1)
            throw 'Ballistic intro did not block forced Freeplay countdown';
        if (forced.variables.get('onEndSong')() != 1)
            throw 'Ballistic ending did not block forced Freeplay completion';
        var plain = setup(source, false);
        if (plain.variables.get('onStartCountdown')() != 0)
            throw 'Ballistic intro incorrectly ran in ordinary Freeplay';
    }
}
'''.replace("{path}", path)
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(BALLISTIC.is_file(), "mounted Whitty donor unavailable")
    def test_psych_intro_returns_to_countdown_after_timed_dialogue(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        for binding in ("startDialogue", "cameraFlash", "cameraFade"):
            self.assertIn(f"interp.variables.set('{binding}', compat{binding[0].upper() + binding[1:]});", play_state)
        self.assertIn("compatSoundPath(Std.string(path), true)", play_state)

        path = str(BALLISTIC).replace("\\", "\\\\").replace('"', '\\"')
        fixture = r'''
import hscript.Parser;
import hscript.Interp;
import sys.io.File;
class PsychAllowCountdownCompat {
    static function main() {
        var converted = LuaCompat.translate(File.getContent("{path}"), "ballistic/script.lua");
        if (!converted.supported) throw converted.diagnostics.join(" | ");
        var interp = new Interp();
        var timers = new Array<String>();
        var dialogueStarted = false;
        for (name in ['triggerEvent', 'setProperty', 'makeAnimatedLuaSprite',
            'addAnimationByPrefix', 'objectPlayAnimation', 'addLuaSprite',
            'cameraShake', 'doTweenZoom', 'doTweenAngle', 'doTweenY', 'playSound',
            'cameraFade', 'cameraFlash'])
            interp.variables.set(name, Reflect.makeVarArgs(function(_args:Array<Dynamic>) return null));
        interp.variables.set('runTimer', function(tag:String, seconds:Float) timers.push(tag));
        interp.variables.set('startDialogue', function(file:String, music:String) dialogueStarted = true);
        interp.variables.set('startCountdown', function() {});
        interp.variables.set('allowCountdown', true);
        interp.variables.set('isStoryMode', true);
        interp.variables.set('seenCutscene', false);
        interp.variables.set('Function_Stop', 1);
        interp.variables.set('Function_Continue', 0);
        interp.execute(new Parser().parseString(converted.hscript));
        var countdown = interp.variables.get('onStartCountdown');
        var timer = interp.variables.get('onTimerCompleted');
        if (countdown() != 1 || timers.indexOf('kfin') < 0)
            throw 'first intro countdown did not stop';
        if (countdown() != 1 || timers.indexOf('startDialogue') < 0)
            throw 'second intro countdown did not schedule dialogue';
        timer('startDialogue', 1, 0);
        if (!dialogueStarted) throw 'Psych dialogue callback was lost';
        if (countdown() != 0) throw 'dialogue completion did not release gameplay';
    }
}
'''.replace("{path}", path)
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DONOR.is_dir(), "mounted FNF-Example-Mods corpus is unavailable")
    def test_mounted_extra_scripts_use_the_seeded_engine_gate(self):
        for path in COUNTDOWN_SCRIPTS:
            self.assertTrue(path.is_file(), path)
            source = path.read_text(errors="ignore")
            self.assertEqual(source.count("allowCountdown"), 2, path)

        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("interp.variables.set('allowCountdown', true);", play_state)
        self.assertIn("interp.variables.set('seenCutscene', watchedCutscene);", play_state)
        self.assertNotIn("setAllHaxeVar('allowCountdown', true);", play_state)

        paths = [
            str(path).replace("\\", "\\\\").replace('"', '\\"')
            for path in COUNTDOWN_SCRIPTS
        ]
        fixture = r'''
import hscript.Parser;
import sys.io.File;
class PsychAllowCountdownCompat {
    static function main() {
        var paths = ["{first}", "{second}"];
        for (path in paths) {
            var converted = LuaCompat.translate(File.getContent(path), path);
            if (!converted.supported)
                throw "mounted countdown script was diagnosed: " + converted.diagnostics.join(" | ");
            if (converted.hscript.indexOf("allowCountdown") < 0)
                throw "mounted countdown gate was dropped: " + path;
            new Parser().parseString(converted.hscript);
        }
    }
}
'''.replace("{first}", paths[0]).replace("{second}", paths[1])
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
