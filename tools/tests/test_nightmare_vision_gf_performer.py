"""Exercise NMV gfSection singer routing and verify it stays separate from ownership."""

from haxe_test_support import FixturePath as Path, HAXE_COMMAND
import subprocess
import tempfile
import unittest


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
                return source[start:index + 1]
    raise AssertionError(f"Unclosed method: {marker}")


class NightmareVisionGFPerformerTest(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")

    def test_production_helpers_select_only_the_authored_gf_section_field(self):
        helpers = "\n".join(extract_method(self.source, marker) for marker in [
            "function nightmareVisionGfSectionNote(",
            "function isNightmareVisionGfPerformer(",
            "function noteSingerForSide(",
        ])
        fixture = r"""
class SwagSection {
 public var gfSection:Bool;
 public var mustHitSection:Bool;
 public function new(gf:Bool, mustHit:Bool) {gfSection=gf;mustHitSection=mustHit;}
}
class Note {
 public var forceGfSing:Bool;
 public function new(forceGf:Bool=false) forceGfSing=forceGf;
}
class Character {
 public var name:String;
 public var holdTimer:Float=1;
 public function new(value:String) name=value;
}
class SingerRoutingState {
 public var nightmareVisionScripts:Dynamic=null;
 public var gf:Character;
 public var boyfriend:Character;
 public var dad:Character;
 public function new() {
  gf=new Character('police-gf');
  boyfriend=new Character('vedplayable');
  dad=new Character('opponent');
 }
 function getOpponentSinger():Character return dad;
__HELPERS__
 public function selectGfSection(section:SwagSection,field:Int):Bool
  return nightmareVisionGfSectionNote(section,field);
 public function isGfPerformer(note:Note,player:Bool):Bool
  return isNightmareVisionGfPerformer(note,player);
 public function singerFor(note:Note,player:Bool):Character
  return noteSingerForSide(note,player);
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var native=new SingerRoutingState();
  var playerGfSection=new SwagSection(true,true);
  check(!native.selectGfSection(playerGfSection,0), 'native Psych GF section keeps its legacy generation path');
  check(native.singerFor(new Note(true),true)==native.boyfriend, 'native Psych player GF Sing note still routes to BF');
  check(native.singerFor(new Note(true),false)==native.gf, 'native Psych opponent GF Sing note still routes to GF');
  check(!native.isGfPerformer(new Note(true),true), 'native player note is not tagged as NMV GF performer');

  var nmv=new SingerRoutingState();
  nmv.nightmareVisionScripts={active:true};
  check(nmv.selectGfSection(playerGfSection,0), 'player-side GF section targets primary player field 0');
  check(!nmv.selectGfSection(playerGfSection,1), 'player-side GF section does not redirect opponent field 1');
  check(!nmv.selectGfSection(playerGfSection,2), 'player-side GF section does not redirect additional fields');
  var opponentGfSection=new SwagSection(true,false);
  check(nmv.selectGfSection(opponentGfSection,1), 'opponent-side GF section targets field 1');
  check(!nmv.selectGfSection(opponentGfSection,0), 'opponent-side GF section does not redirect player field 0');
  check(!nmv.selectGfSection(new SwagSection(false,true),0), 'ordinary section does not select GF');
  nmv.gf=null;
  check(!nmv.selectGfSection(playerGfSection,0), 'missing GF safely disables section performer routing');
  nmv.gf=new Character('police-gf');

  var gfNote=new Note(true);
  var normalNote=new Note(false);
  check(nmv.singerFor(gfNote,true)==nmv.gf, 'NMV player GF note sings with GF');
  check(nmv.singerFor(normalNote,true)==nmv.boyfriend, 'ordinary NMV player note still sings with BF');
  check(nmv.singerFor(gfNote,false)==nmv.gf, 'NMV opponent GF note sings with GF');
  check(nmv.singerFor(normalNote,false)==nmv.dad, 'ordinary NMV opponent note still sings with opponent');
  check(nmv.isGfPerformer(gfNote,true), 'player GF note uses NMV solo-mode exception');
  check(!nmv.isGfPerformer(gfNote,false), 'opponent GF note keeps the ordinary solo-mode behavior');
  check(!nmv.isGfPerformer(normalNote,true), 'ordinary player note keeps the ordinary solo-mode behavior');
  nmv.gf=null;
  check(nmv.singerFor(gfNote,true)==nmv.boyfriend, 'missing GF falls back to the player singer');
  check(!nmv.isGfPerformer(gfNote,true), 'missing GF cannot activate the solo-mode exception');
  Sys.println('nightmare-vision-gf-performer-ok');
 }
}
""".replace("__HELPERS__", helpers)

        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            (work / "Main.hx").write_text(fixture, encoding="utf-8")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(work), "--run", "Main"], cwd=ROOT,
                                    text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("nightmare-vision-gf-performer-ok", result.stdout)

    def test_note_paths_route_performer_without_changing_player_ownership(self):
        self.assertEqual(self.source.count(
            "nightmareVisionGfSectionNote(section, chartAddress.playfieldIndex)"), 2,
            "heads and sustain segments both inherit GF performer routing from their authored source field")
        self.assertEqual(self.source.count("else if (section.gfSection == true && !gottaHitNote)"), 2,
                         "classic Psych retains its existing opponent-only gfSection generation")

        for marker in ["function noteMissCore(", "function goodNoteHit("]:
            method = extract_method(self.source, marker)
            self.assertIn("var actingOn = noteSingerForSide(note, playerOne);", method)
            self.assertIn("var nightmareVisionGfPerformer = isNightmareVisionGfPerformer(note, playerOne);", method)
            self.assertIn("note.soloMode && !nightmareVisionGfPerformer", method,
                          "NMV GF section notes stay with GF when soloMode would ordinarily swap the singer")

        good_hit = extract_method(self.source, "function goodNoteHit(")
        self.assertIn("realActor.holdTimer = 0;", good_hit)
        self.assertIn("spawnCrossFade(realActor, note);", good_hit)
        self.assertIn("popUpScore(note.strumTime, note, playerOne);", good_hit,
                      "field ownership still controls scoring")
        self.assertIn('callAllHScript("playerOneSing", []);', good_hit,
                      "player-owned GF notes keep player callback identity")

        note_miss = extract_method(self.source, "function noteMissCore(")
        self.assertIn('callAllHScript("playerOneMiss", []);', note_miss,
                      "player-owned GF misses keep player callback identity")

        auto_player = self.source[
            self.source.rfind("applyDemoHealth(daNote);", 0,
                               self.source.index("var singer = noteSingerForSide(daNote, true);")):
            self.source.index("if (nightmareVisionScripts == null && (daNote.aiShouldHit", self.source.index(
                "var singer = noteSingerForSide(daNote, true);"))
        ]
        for expected in [
            "Character.animationName(singer)", "singer.playAnim", "singer.sing(",
            "spawnCrossFade(singer, daNote)", "singer.holdTimer = 0;",
            'callAllHScript("playerOneSing", []);',
        ]:
            self.assertIn(expected, auto_player)
        self.assertIn("var actingOn:Character = playerOne ? boyfriend : getOpponentSinger();", self.source,
                      "player input ownership remains independent from the selected performer")

        hit_pre = extract_method(self.source, "function dispatchNightmareVisionNoteHitPre(")
        self.assertIn("strum.lastNote = note;", hit_pre)
        self.assertIn("var activeField = field == null ? nightmareVisionFieldForNote(note) : field;", hit_pre)
        self.assertIn("var line = activeField.strumline;", hit_pre)
        self.assertIn("var direction = note.sourceDirection;", hit_pre)
        self.assertIn("line.members[direction]", hit_pre,
                      "lastNote remains on the field's authored receptor while singer changes")


if __name__ == "__main__":
    unittest.main()
