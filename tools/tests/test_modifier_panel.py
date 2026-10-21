"""Modifiers panel: plain names, sections, conflicts explained instead of silent toggles."""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


def modifier_rules() -> str:
    """ModifierState without its screen: the data and the static rules only."""
    source = (ROOT / "source/ModifierState.hx").read_text(encoding="utf-8")
    start = source.index("class ModifierState extends MusicBeatState {")
    end = source.index("\t/** The song setup screen")
    return ("package;\n" + source[source.index("typedef TModifierNoName"):start]
            + "class ModifierState {" + source[start + len("class ModifierState extends MusicBeatState {"):end] + "}\n")


class ModifierPanelTest(unittest.TestCase):
    def run_main(self, main: str) -> str:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            work = Path(temp)
            (work / "ModifierState.hx").write_text(modifier_rules(), encoding="utf-8")
            for name in ("StandardScore.hx", "ModifierMenuRows.hx"):
                (work / name).write_text((ROOT / "source" / name).read_text(encoding="utf-8"), encoding="utf-8")
            (work / "Main.hx").write_text(main, encoding="utf-8")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "--run", "Main"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_rules_rows_and_labels(self):
        out = self.run_main(r'''
class Main {
 static function check(v:Bool, s:String) if (!v) throw s;
 static function main() {
  ModifierState.init();
  // Speed modifiers and the old menu rows are gone from the list but stay readable as off.
  for (id in ["slow", "fast", "accel", "play", "charselect", "antijank"]) {
   check(ModifierState.find(id) == null, "retired in list " + id);
   check(Reflect.field(ModifierState.namedModifiers, id).value == false, "retired readable " + id);
  }
  for (m in ModifierState.modifiers) {
   check(ModifierState.GROUPS.indexOf(m.group) >= 0, "group " + m.internName);
   check(m.name.length > 0 && m.desc.length > 0, "named " + m.internName);
   for (c in m.conflicts) check(ModifierState.find(c) != null, m.internName + " conflicts with unknown " + c);
  }
  // Turning one on never turns another off; a clashing one is refused with the reason.
  check(ModifierState.setOn("fc", true), "fc on");
  check(ModifierState.blockedBy("mfc") == "Full Combo", "mfc blocked by fc");
  check(!ModifierState.setOn("mfc", true) && !ModifierState.find("mfc").value, "mfc refused");
  check(ModifierState.find("fc").value, "fc stays on");
  check(!ModifierState.changeAmount("healthloss", true), "health amount refused while fc is on");
  check(ModifierState.find("healthloss").amount == 1, "amount unchanged when refused");
  ModifierState.setOn("fc", false);
  // Amounts: on exactly while away from the default.
  check(ModifierState.changeAmount("healthloss", true) && ModifierState.find("healthloss").value, "amount on");
  check(ModifierState.find("healthloss").amount == 1.5, "step 0.5");
  check(ModifierState.changeAmount("healthloss", false) && !ModifierState.find("healthloss").value, "back to default is off");
  check(!ModifierState.changeAmount("regen", false), "cannot go below minimum");
  check(ModifierState.setOn("regen", true) && ModifierState.find("regen").amount == 5, "switching on takes one step");
  check(ModifierState.multiplierLabel() == "Score x0.50", "health group label " + ModifierState.multiplierLabel());
  ModifierState.resetAll();
  check(ModifierState.modifierIds().length == 0 && ModifierState.find("regen").amount == 0, "reset");
  ModifierState.setOn("invis", true);
  check(ModifierState.multiplierLabel() == "Score x1.06", "visual label " + ModifierState.multiplierLabel());
  ModifierState.setOn("demo", true);
  check(StringTools.startsWith(ModifierState.multiplierLabel(), "Unranked"), "unranked label");
  ModifierState.resetAll();

  // Rows: Start, Characters, each section header before its modifiers, Reset last.
  var groups = [for (m in ModifierState.modifiers) m.group];
  var ids = [for (m in ModifierState.modifiers) m.internName];
  var rows = ModifierMenuRows.build(true, true, ModifierState.GROUPS, groups, ids);
  check(rows[0].kind == "start" && rows[1].kind == "characters" && rows[rows.length - 1].kind == "reset", "row ends");
  check(rows[2].kind == "header" && rows[2].id == "Rules", "first header");
  var headers = [for (r in rows) if (r.kind == "header") r.id];
  check(headers.join(",") == ModifierState.GROUPS.join(","), "headers " + headers.join(","));
  check(ModifierMenuRows.first(rows) == 0, "cursor starts on Start");
  var plain = ModifierMenuRows.build(false, false, ModifierState.GROUPS, groups, ids);
  check(ModifierMenuRows.first(plain) == 1, "cursor skips the first header");
  var at = ModifierMenuRows.first(plain);
  for (_ in 0...plain.length * 2) { at = ModifierMenuRows.move(plain, at, 1); check(plain[at].kind != "header", "lands on header"); }
  check(ModifierMenuRows.move(plain, ModifierMenuRows.first(plain), -1) == plain.length - 1, "wraps up to Reset");
  check(ModifierMenuRows.firstVisible(0, 25, 13) == 0 && ModifierMenuRows.firstVisible(24, 25, 13) == 12, "scroll bounds");
  check(ModifierMenuRows.firstVisible(12, 25, 13) == 6, "scroll centres");
  check(ModifierMenuRows.valueLabel(true, null, null, null) == "ON" && ModifierMenuRows.valueLabel(false, null, null, null) == "OFF", "switch label");
  check(ModifierMenuRows.valueLabel(true, 1.5, 1, 0.5) == "x1.5" && ModifierMenuRows.valueLabel(true, 25, 0, 5) == "25", "amount label");
  Sys.println("ok");
 }
}
''')
        self.assertIn("ok", out)

    def test_freeplay_and_story_launch_without_the_old_screen(self):
        freeplay = (ROOT / "source/FreeplayState.hx").read_text(encoding="utf-8")
        story = (ROOT / "source/StoryMenuState.hx").read_text(encoding="utf-8")
        launch = freeplay[freeplay.index("function openSelection("):freeplay.index("function openModifiers(")]
        self.assertNotIn("new ModifierState()", launch)
        self.assertIn("new ChooseCharState(PlayState.SONG.player1)", launch)
        self.assertIn("FlxG.keys.justPressed.F2", freeplay)
        self.assertNotIn("new ModifierState()", story)
        self.assertIn("new ModifierMenuSubState(false)", story)
        pulse = (ROOT / "source/FreeplayPulse.hx").read_text(encoding="utf-8")
        self.assertIn("{key:'F2', action:'Modifiers'}", pulse)
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertNotIn("namedModifiers.slow", play)
        self.assertNotIn("namedModifiers.fast", play)
        self.assertNotIn("namedModifiers.accel", play)
        self.assertNotIn("if (!OptionsHandler.options.skipModifierMenu) {\n\t\t\tfullComboMode", play)


if __name__ == "__main__":
    unittest.main()
