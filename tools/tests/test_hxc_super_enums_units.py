"""HXC lowering: inherited super calls, script enums, field initializers and
per-unit parse failures.

- `super.<hook>(...)` used as a value, or standing alone after `if (...)`,
  `else` or a `case` label, used to keep the whole callback out of the
  generated script.  It now lowers to the base value (or an empty statement,
  since the engine runs the base hook itself).
- Script enums (declared in the file, or imported from another script the
  engine does not bind) become constant objects, and a field initializer may
  read earlier fields and enum values.
- A character body's object literal keys (`{alpha: 0}` in a tween) are no
  longer rewritten into `{hxcCharacter().alpha: 0}`.
- When one callback's translation does not parse, only that callback is left
  out instead of the whole script failing to load.
"""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]


def hx(value: str) -> str:
    return json.dumps(value)


class HxcSuperEnumsUnitsTest(unittest.TestCase):
    def run_probe(self, body: str) -> str:
        with tempfile.TemporaryDirectory(prefix="hxc-super-enums-", dir=ROOT / "tmp") as folder:
            Path(folder, "Probe.hx").write_text(body, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", folder, "--run", "Probe"],
                cwd=folder, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def analyze(self, source: str, path: str) -> dict:
        out = self.run_probe(f'''class Probe {{
  static function main() {{
    var r = HxcCompat.analyze({hx(source)}, {hx(path)});
    var parses = true;
    try new hscript.Parser().parseString(r.generatedHscript) catch (_:Dynamic) parses = false;
    var callbacks = [for (c in r.callbackAdapters) c.sourceName + "=" + (c.safe ? "safe" : "unsafe")];
    Sys.println("JSON" + haxe.Json.stringify({{kind: r.kind, gen: r.generatedHscript, parses: parses,
      callbacks: callbacks, codes: [for (d in r.diagnostics) d.code]}}));
  }}
}}
''')
        return json.loads(out[out.index("JSON") + 4:].strip())

    def test_super_calls_lower_to_base_behaviour(self):
        out = self.run_probe('''@:access(HxcCompat)
class Probe {
  static function main() {
    Sys.println("A|" + HxcCompat.translateBody("switch (k) { case 1: trace(1); default: super.onNoteHit(event); }"));
    Sys.println("B|" + StringTools.replace(HxcCompat.translateBody("if (ready) super.onBeatHit(event);\\nelse super.onStepHit(event);"), "\n", " "));
    Sys.println("C|" + StringTools.replace(HxcCompat.translateBody("if (!super.beatHit()) return false;\\nflip = !flip;"), "\n", " "));
    Sys.println("D|" + StringTools.replace(HxcCompat.translateBody("var list = super.queryAssets(type);\\nlist.push('x');"), "\n", " "));
    Sys.println("E|" + HxcCompat.translateBody("return super.getDeathQuote();", "getDeathQuote", [], true));
    Sys.println("F|" + HxcCompat.translateBody("return super.getDeathQuote();"));
    Sys.println("G|" + HxcCompat.translateBody("var all = super.listDifficulties(a, b);"));
    Sys.println("H|" + HxcCompat.translateBody("trace('super.custom(event)'); // super.custom(event)"));
  }
}
''')
        lines = {line.split("|", 1)[0]: line.split("|", 1)[1] for line in out.splitlines() if "|" in line}
        self.assertIn("default: null;", lines["A"])
        self.assertIn("if (ready) null;", lines["B"])
        self.assertIn("else null;", lines["B"])
        self.assertIn("if (!true) return false;", lines["C"])
        self.assertIn("var list = [];", lines["D"])
        # A character's base death quote is none; other bases keep the call.
        self.assertIn("return null;", lines["E"])
        self.assertIn("super.getDeathQuote()", lines["F"])
        # No known base value: the call stays, so the safety check still sees it.
        self.assertIn("super.listDifficulties(a, b)", lines["G"])
        # Strings and comments are never rewritten.
        self.assertIn("trace('super.custom(event)');", lines["H"])

    def test_super_call_in_value_position_after_colon_is_kept(self):
        # A ternary branch or an object key's value is not a case label:
        # turning the call into null would silently change the computed value,
        # so the call stays and the safety check decides about the callback.
        out = self.run_probe('''@:access(HxcCompat)
class Probe {
  static function main() {
    Sys.println("T|" + HxcCompat.translateBody("var x = ready ? 1 : super.custom(a);"));
    Sys.println("O|" + HxcCompat.translateBody("var o = {key: super.custom(a)};"));
    Sys.println("C|" + HxcCompat.translateBody("switch (k) { case 1: x = r ? 2 : super.custom(a); default: super.other(); }"));
    Sys.println("P|" + HxcCompat.translateBody("switch (k) { case A | B: super.custom(a); case _: super.other(); }"));
  }
}
''')
        lines = {line.split("|", 1)[0]: line.split("|", 1)[1] for line in out.splitlines() if "|" in line}
        self.assertIn("ready ? 1 : super.custom(a);", lines["T"])
        self.assertIn("{key: super.custom(a)}", lines["O"])
        self.assertIn("r ? 2 : super.custom(a);", lines["C"])
        self.assertIn("default: null;", lines["C"])
        self.assertIn("case A | B: null;", lines["P"])
        self.assertIn("case _: null;", lines["P"])

    def test_module_callback_with_case_super_call_is_kept(self):
        result = self.analyze('''import funkin.modding.module.Module;
class HitModule extends Module {
  public function new() { super('hit-module'); }
  override function onNoteHit(event) {
    switch (event.note.kind) {
      case "danger":
        PlayState.instance.health -= 0.5;
      default: super.onNoteHit(event);
    }
  }
}''', "assets/imported_mods/synthetic/scripts/modules/HitModule.hxc")
        self.assertIn("onNoteHit=safe", result["callbacks"])
        self.assertTrue(result["parses"], result["gen"])
        self.assertIn("default: null;", result["gen"])

    def test_character_object_keys_stay_property_names(self):
        out = self.run_probe('''@:access(HxcCompat)
class Probe {
  static function main() {
    Sys.println(HxcCompat.translateCharacterBody("FlxTween.tween(this, {alpha: 0, angle: 5}, 1);\\nalpha = 0.5;\\nvar t = fading ? alpha : 1;\\nvar o = {x: 1, alpha: alpha};", "onUpdate", ["event"]));
  }
}
''')
        self.assertIn("{alpha: 0, angle: 5}", out)
        self.assertIn("hxcCharacter().alpha = 0.5;", out)
        self.assertIn("fading ? hxcCharacter().alpha : 1", out)
        self.assertIn("{x: 1, alpha: hxcCharacter().alpha}", out)
        self.assertNotIn("hxcCharacter().alpha:", out)

    def test_script_enums_and_field_initializers_run(self):
        result = self.analyze('''import funkin.play.character.MultiAnimateAtlasCharacter;
import funkin.play.character.PupilState;
enum MoodState {
  CALM;
  ANGRY;
}
class MoodCharacter extends MultiAnimateAtlasCharacter {
  var mood:MoodState = MoodState.CALM;
  var pupil:PupilState = PupilState.RIGHT;
  final MIN_DELAY:Int = 3;
  final DOUBLE:Float = MIN_DELAY * 2;
  var countdown:Int = MIN_DELAY;
  public function new() { super('mood'); }
  function onBeatHit(event) {
    if (mood == MoodState.CALM) mood = MoodState.ANGRY;
    if (pupil == PupilState.LEFT) pupil = PupilState.RIGHT;
  }
}''', "assets/imported_mods/synthetic/scripts/characters/mood.hxc")
        gen = result["gen"]
        self.assertTrue(result["parses"], gen)
        self.assertIn('var MoodState = {CALM: "CALM", ANGRY: "ANGRY"};', gen)
        self.assertIn('var PupilState = {RIGHT: "RIGHT", LEFT: "LEFT"};', gen)
        for line in ("var mood = MoodState.CALM;", "var pupil = PupilState.RIGHT;",
                     "var DOUBLE = MIN_DELAY * 2;", "var countdown = MIN_DELAY;"):
            self.assertIn(line, gen)
        # The enum objects come before the fields that read them.
        self.assertLess(gen.index("var MoodState"), gen.index("var mood ="))
        # The declarations evaluate in a plain interpreter.
        header = "\n".join(line for line in gen.splitlines() if line.startswith("var "))
        header += "\n[mood, countdown, DOUBLE, pupil == PupilState.RIGHT, mood == MoodState.ANGRY];"
        out = self.run_probe(f'''class Probe {{
  static function main() {{
    var interp = new hscript.Interp();
    var v:Array<Dynamic> = interp.execute(new hscript.Parser().parseString({hx(header)}));
    if (v[0] != "CALM" || v[1] != 3 || v[2] != 6) throw "values " + v;
    if (v[3] != true || v[4] != false) throw "enum identity " + v;
    Sys.println("enum-fields-ok");
  }}
}}
''')
        self.assertIn("enum-fields-ok", out)

    def test_character_field_never_reads_a_later_field(self):
        # Initializers are emitted in authored order.  A field that reads one
        # declared after it must not be emitted as `var early = LATER;`, which
        # would stop the script at load with an unknown variable.
        result = self.analyze('''import funkin.play.character.MultiAnimateAtlasCharacter;
class OrderCharacter extends MultiAnimateAtlasCharacter {
  var early:Int = LATER;
  final LATER:Int = 3;
  var after:Int = LATER + 1;
  public function new() { super('order'); }
  function onBeatHit(event) { early = after; }
}''', "assets/imported_mods/synthetic/scripts/characters/order.hxc")
        gen = result["gen"]
        self.assertNotIn("var early = LATER", gen)
        self.assertIn("var after = LATER + 1;", gen)
        self.assertLess(gen.index("var LATER = 3;"), gen.index("var after = LATER + 1;"))
        header = "\n".join(line for line in gen.splitlines() if line.startswith("var "))
        header += "\n[LATER, after];"
        out = self.run_probe(f'''class Probe {{
  static function main() {{
    var v:Array<Dynamic> = new hscript.Interp().execute(new hscript.Parser().parseString({hx(header)}));
    if (v[0] != 3 || v[1] != 4) throw "values " + v;
    Sys.println("field-order-ok");
  }}
}}
''')
        self.assertIn("field-order-ok", out)

    def test_constants_classes_and_lowered_enums_get_no_object(self):
        result = self.analyze('''import funkin.modding.module.Module;
import funkin.util.Constants;
class MenuModule extends Module {
  public function new() { super('menu-module'); }
  override function onCreate(event) {
    var v = {variation: Constants.DEFAULT_VARIATION};
    var w = ready ? Constants.DEFAULT_VARIATION : null;
  }
}''', "assets/imported_mods/synthetic/scripts/modules/MenuModule.hxc")
        self.assertNotIn("var Constants = {", result["gen"])

    def test_one_unparseable_callback_is_left_out(self):
        out = self.run_probe('''@:access(HxcCompat)
class Probe {
  static function main() {
    // Links the parser the unit check resolves at run time.
    new hscript.Parser();
    var r = HxcCompat.analyze("import funkin.play.song.Song;\\nclass S extends Song {\\n  public function new() { super('s'); }\\n  function onBeatHit(event) { trace('beat'); }\\n  function onStepHit(event) { trace('step'); }\\n}", "assets/imported_mods/synthetic/scripts/songs/s.hxc");
    for (c in r.callbackAdapters) if (c.sourceName == "onStepHit") c.body = "var = ;";
    r.generatedHscript = HxcScriptSyntaxLowering.lower(HxcCompat.generateHscript(r));
    if (HxcCompat.hscriptParses(r.generatedHscript)) throw "fixture should not parse";
    if (!HxcCompat.disableUnparseableUnits(r)) throw "nothing disabled";
    r.generatedHscript = HxcScriptSyntaxLowering.lower(HxcCompat.generateHscript(r));
    if (!HxcCompat.hscriptParses(r.generatedHscript)) throw "still unparseable";
    if (r.generatedHscript.indexOf("trace('beat')") < 0) throw "healthy callback lost";
    if (r.generatedHscript.indexOf("var = ;") >= 0) throw "broken callback emitted";
    var reported = false;
    for (d in r.diagnostics) if (d.code == "hxc-generated-syntax" && d.message.indexOf("onStepHit") >= 0) reported = true;
    if (!reported) throw "no diagnostic";
    Sys.println("unit-drop-ok");
  }
}
''')
        self.assertIn("unit-drop-ok", out)


if __name__ == "__main__":
    unittest.main()
