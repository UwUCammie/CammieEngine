"""Pin Nightmare Vision's authored flip and player-slot orientation semantics."""
from haxe_test_support import HAXE_COMMAND
from test_nv_multifield_routes import method

from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"
NV_DONOR_CHARACTER = (ROOT.parent / "FNF-Example-Mods" / "misc" / "nightmare_vision_source_code"
                     / "source" / "funkin" / "objects" / "Character.hx")


class NightmareVisionCharacterOrientationTest(unittest.TestCase):
    def test_host_reuses_the_source_shared_slot_orientation(self):
        character = (ROOT / "source/Character.hx").read_text()
        self.assertIn(
            "flipX = PsychCharacterOrientation.flipX(Reflect.field(definition, 'flip_x') == true, isPlayer);",
            character,
        )
        self.assertNotIn("authoredSlotFlipX", character)
        self.assertIn("public var isPlayer:Bool = false;", character)

        # The real source group constructs by its live type and then places through
        # actual startPos/group.add, preserving the captured player's orientation.
        play_state = (ROOT / "source/PlayState.hx").read_text(encoding='utf-8')
        role = method(play_state, 'function constructNightmareVisionRole(')
        self.assertIn('owner.construct(name, type == 0)', role)
        bindings = (ROOT / 'source/NightmareVisionCharacterGroupBindings.hx').read_text(encoding='utf-8')
        owner = method(bindings, 'public static function owner(')
        self.assertIn('new Character(0, 0, name, player, null, construction)', owner)
        group = (ROOT / 'source/NightmareVisionCharacterGroup.hx').read_text(encoding='utf-8')
        self.assertIn('owner.construct(newCharacter, type == BF)', method(group, 'public function addToList('))
        add = method(group, 'public function addChar(')
        self.assertLess(add.index('startPos(char)'), add.index('add(char)'))
        change = method(group, 'public function change(')
        self.assertIn('parent = map.get(name);', change)
        self.assertNotIn('isPlayer =', change)
        cache = (ROOT / "source/PsychCharacterCache.hx").read_text()
        self.assertIn("public function change(name:String):T", cache)
        self.assertIn("parent = next;", cache)

        helper = (ROOT / "source/PsychCharacterOrientation.hx").read_text()
        self.assertIn("return authoredFlipX != isPlayer;", helper)
        if NV_DONOR_CHARACTER.is_file():
            donor = NV_DONOR_CHARACTER.read_text()
            self.assertIn("this.flipX = (json.flip_x != isPlayer);", donor)

    def test_authored_values_in_both_roles_survive_cached_swaps(self):
        with tempfile.TemporaryDirectory(dir=TMP) as folder:
            work = Path(folder)
            for name in ("PsychCharacterOrientation.hx", "PsychCharacterCache.hx",
                         "NightmareVisionCharacterBank.hx"):
                (work / name).write_text((ROOT / "source" / name).read_text(), newline='\n')

            (work / "OrientationActor.hx").write_text(r'''class OrientationActor {
  public var requestedCharacter:String;
  public var isPlayer:Bool;
  public var flipX:Bool;
  public var alpha:Float = 1;
  public function new(name:String, player:Bool, authored:Bool) {
    requestedCharacter=name;
    isPlayer=player;
    flipX=PsychCharacterOrientation.flipX(authored, player);
  }
}''', newline='\n')
            (work / "NightmareVisionCharacterOrientationProbe.hx").write_text(r'''import NightmareVisionCharacterBank;
import OrientationActor;
import PsychCharacterOrientation;
class NightmareVisionCharacterOrientationProbe {
  static function check(ok:Bool, label:String):Void if (!ok) throw label;
  static function main():Void {
    check(!PsychCharacterOrientation.flipX(true, true), 'authored true/player must face left');
    check(PsychCharacterOrientation.flipX(false, true), 'authored false/player must face right');
    check(PsychCharacterOrientation.flipX(true, false), 'authored true/opponent must face right');
    check(!PsychCharacterOrientation.flipX(false, false), 'authored false/opponent must face left');

    var boyfriend = new OrientationActor('bf-authored-true', true, true);
    var playerBank = new NightmareVisionCharacterBank(boyfriend, function(name:String):Dynamic {
      return new OrientationActor(name, true, name == 'bf-authored-true');
    }, function(_old:Dynamic, _next:Dynamic):Void {});
    var playerAlt:OrientationActor = cast playerBank.addToList('bf-authored-false');
    check(playerAlt.isPlayer && playerAlt.flipX, 'cached player with authored false lost slot flip');
    check(playerBank.change('bf-authored-false') == playerAlt, 'player cache did not activate replacement');
    check(playerAlt.isPlayer && playerAlt.flipX, 'player orientation changed on activation');
    check(playerBank.change('bf-authored-true') == boyfriend, 'player cache did not restore original actor');
    check(boyfriend.isPlayer && !boyfriend.flipX, 'restored player actor lost authored slot orientation');

    var opponent = new OrientationActor('dad-authored-false', false, false);
    var opponentBank = new NightmareVisionCharacterBank(opponent, function(name:String):Dynamic {
      return new OrientationActor(name, false, name == 'dad-authored-true');
    }, function(_old:Dynamic, _next:Dynamic):Void {});
    var opponentAlt:OrientationActor = cast opponentBank.addToList('dad-authored-true');
    check(!opponentAlt.isPlayer && opponentAlt.flipX, 'cached opponent with authored true lost authored flip');
    check(opponentBank.change('dad-authored-true') == opponentAlt, 'opponent cache did not activate replacement');
    check(!opponentAlt.isPlayer && opponentAlt.flipX, 'opponent orientation changed on activation');
    check(opponentBank.change('dad-authored-false') == opponent, 'opponent cache did not restore original actor');
    check(!opponent.isPlayer && !opponent.flipX, 'restored opponent actor lost authored slot orientation');
  }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run",
                 "NightmareVisionCharacterOrientationProbe"],
                cwd=work, env={**os.environ, "TMPDIR": str(TMP)},
                capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
