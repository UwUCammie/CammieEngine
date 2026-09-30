"""Regression coverage for FPS/Kade JSON sidecars at the shared adapter boundary."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


def hx_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class LegacySidecarCompatibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = (ROOT / "source/EngineCompat.hx").read_text()
        cls.module = (ROOT / "source/ModuleFunctions.hx").read_text()
        cls.play_state = (ROOT / "source/PlayState.hx").read_text()
        cls.dialogue_box = (ROOT / "source/DialogueBox.hx").read_text()

    def test_shared_import_and_runtime_hooks_are_wired(self):
        self.assertIn("VoicesTogether.ogg", self.module)
        self.assertIn("convertImportDialogue", self.module)
        self.assertIn("importCutsceneScript", self.module)
        self.assertIn("writeGeneratedDialogue", self.module)
        self.assertIn("copyIfPresent(songData.dialogueJson", self.module)
        self.assertIn("copyIfPresent(songData.cutsceneJson", self.module)
        self.assertIn("copyIfPresent(songData.events", self.module)
        self.assertIn("chartFieldString(chartSong, 'gfVersion', 'gf')", self.module)
        self.assertIn("findImportFile(chartRoot, ['events.json', 'events.jsonc'])", self.module)
        self.assertIn("Path.join([songFolder, 'Voices.ogg'])", self.module)
        self.assertIn("cutsceneScript", self.module)
        self.assertIn("loadHxcCutsceneCompat", self.play_state)
        self.assertIn("importedCutsceneScript()", self.play_state)
        self.assertIn("shouldPlayImportedCutscene", self.play_state)
        self.assertIn("pendingCutsceneHandoff = true", self.play_state)
        self.assertIn("if (dialogueBox != null)\n\t\t\t\tschoolIntro(dialogueBox);", self.play_state)
        self.assertIn("no compatible start callback", self.play_state)
        self.assertIn("images/ui/dialogue/portraits/", self.dialogue_box)

    def test_synthetic_sidecars_are_normalized(self):
        fixture = r'''
import haxe.Json;
class SidecarCompat {
  static function fail(message:String):Void throw message;
  static function main() {
    var dialogue:Dynamic = {dialogue:[
      {portraits:["whittyPort"], text:"One line", box:"normal"},
      {portraits:["boyfriendPort"], text:"Bip: bop", box:"normal"}
    ]};
    var text = EngineCompat.legacyDialogueText(dialogue, "bf", "Whitty");
    if (text == null || text.indexOf(":Whitty: !whittyPort!") < 0
        || text.indexOf(":bf: !boyfriendPort!") < 0 || text.indexOf("Bip: bop") < 0)
      fail("dialogue JSON conversion lost speaker, portrait, or text");
    var cutscene:Dynamic = {startCutscene:{name:"TogetherIntro", storyOnly:true, playOnce:true}};
    Reflect.setField(cutscene, "cutsceneScript", "TogetherIntro");
    if (EngineCompat.legacyCutsceneScript(cutscene) != "TogetherIntro"
        || !EngineCompat.legacyCutsceneBool(cutscene, "storyOnly", false)
        || !EngineCompat.legacyCutsceneBool(cutscene, "playOnce", false))
      fail("cutscene JSON conversion lost metadata");
    if (EngineCompat.importedCutsceneAllowed(cutscene, false, false, false))
      fail("story-only cutscene leaked into freeplay");
    Reflect.setField(cutscene, "cutsceneStoryOnly", false);
    Reflect.setField(cutscene, "cutscenePlayOnce", false);
    if (!EngineCompat.importedCutsceneAllowed(cutscene, false, false, true))
      fail("freeplay/replay cutscene policy was not honored");
    Reflect.setField(cutscene, "cutscenePlayOnce", true);
    if (EngineCompat.importedCutsceneAllowed(cutscene, false, false, true))
      fail("one-shot cutscene replayed after watched state");
    trace("OK");
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "SidecarCompat.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "--run", "SidecarCompat"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_hxc_cutscene_start_uses_native_countdown_abi(self):
        fixture = r'''
import hscript.Interp;
import hscript.Parser;
class SidecarCompat {
  static function fail(message:String):Void throw message;
  static function main() {
    var source = 'class Intro extends ScriptedCutscene { function onCreate() { startCountdown(); } }';
    var converted = HxcCompat.translate(source, "data/cutscenes/Intro.hxc");
    if (converted.generatedHscript.indexOf("function start()") < 0)
      fail("HXC onCreate was not lowered to native start");
    var count = 0;
    var interp = new Interp();
    interp.variables.set("startCountdown", function() count++);
    interp.execute(new Parser().parseString(converted.generatedHscript));
    var start:Dynamic = interp.variables.get("start");
    start("song");
    if (count != 1) fail("HXC start callback did not hand off to countdown");
    trace("OK");
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "SidecarCompat.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "--run", "SidecarCompat"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    @unittest.skipUnless((DONOR / "whitty").is_dir(), "the external example-mod fixture is not mounted")
    def test_mounted_whitty_sidecars_keep_native_fallback_content(self):
        dialogue = DONOR / "whitty/data/songs/ballistic/dialogue.json"
        cutscene = DONOR / "whitty/data/songs/ballistic/cutscene.json"
        if not dialogue.is_file() or not cutscene.is_file():
            self.skipTest("mounted Whitty sidecars are unavailable")
        fixture = f'''
import haxe.Json;
import sys.io.File;
class SidecarCompat {{
  static function fail(message:String):Void throw message;
  static function main() {{
    var dialogue:Dynamic = Json.parse(File.getContent({hx_string(str(dialogue))}));
    var cutscene:Dynamic = Json.parse(File.getContent({hx_string(str(cutscene))}));
    var text = EngineCompat.legacyDialogueText(dialogue, "bf", "WhitBonkers");
    if (text == null || text.indexOf("ENOUGH.") < 0 || text.indexOf("atomizing") < 0)
      fail("mounted dialogue sidecar did not retain text");
    if (EngineCompat.legacyCutsceneScript(cutscene) != "BallisticIntro")
      fail("mounted cutscene sidecar did not retain script name");
    trace("OK");
  }}
}}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "SidecarCompat.hx"
            path.write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", folder, "-cp", str(ROOT / "source"),
                 "--run", "SidecarCompat"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
