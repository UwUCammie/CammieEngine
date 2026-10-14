"""Psych's uiGroup and noteGroup reach the engine's HUD and note layer without re-parenting them."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest

from test_psych_playstate_member_surface import method


ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''class Part {
 public var alpha:Float; public var visible = true; public var name:String;
 public function new(name:String, alpha:Float) {this.name = name; this.alpha = alpha;}
}
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var bar = new Part('bar', 1);
  var icon = new Part('icon', 0.5);
  var hud:Array<Dynamic> = [bar, null, icon, bar];
  var view = new PsychHudGroupView(function() return hud);
  check(view.members.length == 2 && view.length == 2 && view.indexOf(icon) == 1, 'members skip gaps and repeats');
  // fading the group keeps each member's own alpha relative to it, like a sprite group
  view.alpha = 0.0001;
  check(Math.abs(bar.alpha - 0.0001) < 1e-9 && Math.abs(icon.alpha - 0.00005) < 1e-9, 'fade out');
  view.alpha = 1;
  check(Math.abs(bar.alpha - 1) < 1e-6 && Math.abs(icon.alpha - 0.5) < 1e-6 && view.alpha == 1, 'fade back in');
  // from zero there is nothing to scale, so the value goes straight through
  view.alpha = 0;
  view.alpha = 0.75;
  check(bar.alpha == 0.75 && icon.alpha == 0.75, 'from zero');
  view.visible = false;
  check(!bar.visible && !icon.visible && !view.visible, 'hide');
  var seen = 0;
  view.forEach(function(member) seen++);
  check(seen == 2, 'forEach');
  // objects created later are part of the group as soon as they exist
  hud.push(new Part('late', 1));
  check(view.members.length == 3, 'late member');
  Sys.println('ok');
 }
}
'''


class PsychUiNoteGroupsTest(unittest.TestCase):
    def test_hud_view_fades_and_hides_every_member(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            (Path(work) / "Main.hx").write_text(FIXTURE, newline="\n")
            (Path(work) / "PsychHudGroupView.hx").write_text(
                (ROOT / "source/PsychHudGroupView.hx").read_text(encoding="utf-8"), newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", work, "--run", "Main"], cwd=ROOT,
                                    capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_playstate_exposes_both_groups_for_reflection(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("@:keep public var uiGroup(get, never):PsychHudGroupView;", play)
        self.assertIn("@:keep public var noteGroup(get, never):Dynamic;", play)
        hud = method(play, "function psychHudMembers()")
        for name in ("healthBar", "iconP1", "iconP2", "scoreTxt", "timeTxt", "botplayTxt"):
            self.assertIn(name, hud)
        notes = method(play, "function get_noteGroup()")
        # the earliest drawn note layer, so inserting at its index lands below all of them
        self.assertIn("var index = members.indexOf(layer);", notes)
        self.assertIn("index < firstIndex", notes)
        for layer in ("strumLineNotes", "enemyStrums", "playerStrums", "notes", "grpNoteSplashes"):
            self.assertIn(layer, notes)


if __name__ == "__main__":
    unittest.main()
