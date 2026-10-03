"""Execute a mounted HXC character's authored note-kind override."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
LIQUID = DONOR / "v-slice/singstarchallengespc_22f3d/data/stages/LiquidChrisCharInstructions.hxc"


def haxe_string(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def extract_method(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated source method: {signature}")


class HxcCharacterNoteKindTest(unittest.TestCase):
    def run_fixture(self, main: str, extra_classpaths=()):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp", prefix="hxc-character-note-kind-") as folder:
            fixture = Path(folder)
            (fixture / "Main.hx").write_text(main, newline='\n')
            classpaths = [ROOT / "source", fixture, *extra_classpaths]
            command = [*HAXE_COMMAND]
            for classpath in classpaths:
                command.extend(["-cp", str(classpath)])
            command.extend(["-main", "Main", "--interp"])
            return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180)

    def test_mounted_liquid_altanim_callback_preserves_kind_and_owns_animation(self):
        if not LIQUID.exists():
            self.skipTest("mounted Singstar Liquid character source is unavailable")

        runtime_source = (ROOT / "source/HxcCompatRuntime.hx").read_text()
        runtime_methods = "\n".join(
            extract_method(runtime_source, signature)
            for signature in (
                "\tstatic function runtimeField(",
                "\tstatic function runtimeIntValue(",
                "\tpublic static function markCharacterNoteHandled(",
                "\tpublic static function characterDefaultNoteHit(",
            )
        )
        runtime_class = "class HxcCompatRuntimeProbe {\n" + runtime_methods + "\n}"

        main = f'''import hscript.Interp;
import hscript.Parser;
import sys.io.File;
{runtime_class}
class Main {{
  static function fail(message:String):Void throw message;
  static function main():Void {{
    var path = {haxe_string(str(LIQUID))};
    var source = File.getContent(path);
    var result = HxcCompat.analyze(source, path);
    if (result.kind != "character" || result.identifier != "liquid")
      fail("mounted character declaration was not selected: " + result.kind + "/" + result.identifier);
    if (result.characterHookGaps.indexOf("onNoteHit") >= 0)
      fail("mounted onNoteHit was rejected: " + result.characterHookGaps);
    if (result.generatedHscript.indexOf('case "altAnim"') < 0
      || result.generatedHscript.indexOf("playSingAnimation(event.note.noteData.getDirection(), false, 'alt')") < 0)
      fail("generated callback lost authored altAnim branch");

    var singCalls:Array<String> = [];
    var actor:Dynamic = {{holdTimer: 8, playSingAnimation: function(direction:Int, miss:Bool, suffix:String):Void {{
      singCalls.push(direction + ":" + miss + ":" + suffix);
    }}}};
    var defaultCalls = 0;
    var runtime:Dynamic = {{
      characterType: function(character:Dynamic):String return "dad",
      markCharacterNoteHandled: function(event:Dynamic):Void
        HxcCompatRuntimeProbe.markCharacterNoteHandled(event),
      characterDefaultNoteHit: function(character:Dynamic, event:Dynamic):Void {{
        defaultCalls++;
        HxcCompatRuntimeProbe.characterDefaultNoteHit(character, event);
      }}
    }};
    var interp = new Interp();
    interp.variables.set("HxcCompatRuntime", runtime);
    interp.variables.set("hxcCharacter", function():Dynamic return actor);
    interp.variables.set("hxcAssetRoot", "owner");
    interp.execute(new Parser().parseString(result.generatedHscript));
    var callback:Dynamic = interp.variables.get("noteHit");
    if (callback == null) fail("generated character noteHit callback missing");

    function makeEvent(kind:String, mustHit:Bool):Dynamic {{
      var nativeNote:Dynamic = {{}};
      var noteData:Dynamic = {{
        getMustHitNote: function():Bool return mustHit,
        getDirection: function():Int return 2
      }};
      return {{note:{{
        kind:kind, nativeNote:nativeNote, noteData:noteData, altNum:0, shouldBeSung:true
      }}, nativeNote:nativeNote, characterHandled:false}};
    }}

    var alt = makeEvent("altAnim", false);
    Reflect.callMethod(null, callback, [alt]);
    if (alt.characterHandled != true) fail("authored callback did not mark its note handled");
    if (singCalls.length != 1 || singCalls[0] != "2:false:alt")
      fail("altAnim did not use the authored alt sing: " + singCalls);
    if (defaultCalls != 0) fail("altAnim fell through to the base singer");
    // PlayState's handled gate must not issue a second native sing after the
    // custom callback returned early.
    if (alt.characterHandled != true)
      runtime.characterDefaultNoteHit(actor, alt);
    if (singCalls.length != 1) fail("handled altAnim note was sung twice");

    var ordinary = makeEvent("normal", true);
    Reflect.callMethod(null, callback, [ordinary]);
    if (ordinary.characterHandled != true) fail("ordinary callback did not mark its note handled");
    if (defaultCalls != 1 || singCalls.length != 2 || singCalls[1] != "2:false:")
      fail("ordinary kind did not fall through to exactly one inherited base sing: " + singCalls);
    if (ordinary.characterHandled != true)
      runtime.characterDefaultNoteHit(actor, ordinary);
    if (defaultCalls != 1 || singCalls.length != 2)
      fail("handled ordinary note was sung twice");
  }}
}}
'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("Reflect.field(hxcHitEvent, 'characterHandled') == true", play_state)
        self.assertIn("if (note.shouldBeSung && !hxcCharacterHandled)", play_state)
        engine = (ROOT / "source/EngineCompat.hx").read_text()
        self.assertIn("hxcField(note, 'sourceKind')", engine)
        importer = (ROOT / "source/VSliceImporter.hx").read_text()
        self.assertIn("sourceKind: kind", importer)

    def test_manual_judgement_stays_scored_while_auto_route_uses_perfect(self):
        engine_source = (ROOT / "source/EngineCompat.hx").read_text()
        method = extract_method(engine_source, "\tstatic function hxcJudgementName(")
        method = method.replace("static function hxcJudgementName(", "public static function hxcJudgementName(", 1)
        main = f'''using StringTools;
class JudgementProbe {{
{method}
}}
class Main {{
  static function main():Void {{
    if (JudgementProbe.hxcJudgementName("GOOD") != "good") throw "manual rating was not normalized as authored";
    if (JudgementProbe.hxcJudgementName("sick") != "sick") throw "manual sick rating changed";
    if (JudgementProbe.hxcJudgementName("perfect") != "perfect") throw "perfect rating changed";
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        play_state = (ROOT / "source/PlayState.hx").read_text()
        manual = play_state[play_state.index("\tfunction goodNoteHit(note:Note, playerOne:Bool"):]
        manual = manual[:manual.index("\n\tfunction ", 1)]
        self.assertIn("function goodNoteHit(note:Note, playerOne:Bool, sourceHold:Bool = false)", manual)
        self.assertIn("note.rating = noteRatingAtHit(note);", manual)
        self.assertIn("if ((!note.canBeHit && !sourceHold) || note.tooLate)", manual)
        self.assertIn('EngineCompat.hxcNoteCallbackPayload([playerOne, note, false], "noteHit")', manual)
        auto_start = play_state.index("\tfunction dispatchHxcAutoNoteHit(")
        auto_end = play_state.index("\n\tfunction goodNoteHit(", auto_start)
        self.assertIn("event.judgement = 'perfect';", play_state[auto_start:auto_end])


if __name__ == "__main__":
    unittest.main()
