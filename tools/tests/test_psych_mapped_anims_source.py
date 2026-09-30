"""Pin owner-source animation map extraction without actor or chart constants."""
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT / "tmp/psych-archive-source/FNF-PsychEngine-main/source/objects/Character.hx"


class PsychMappedAnimsSourceTest(unittest.TestCase):
    def test_source_declared_mapping(self):
        fixture = r'''class Main {
 static function check(ok:Bool, label:String):Void if (!ok) throw label;
 static function main():Void {
  var source = "switch(curCharacter) { case 'actor-singer': skipDance = true; loadMappedAnims(); playAnim('shoot1'); } "
   + "function loadMappedAnims() { var songData = Song.getChart('actorMap', Song.loadedSongName); "
   + "Backdrop.animationNotes = animationNotes; }";
  var result = PsychMappedAnimsSource.discover(source);
  check(result != null && result.character == 'actor-singer' && result.chart == 'actorMap', "source names");
  check(result.className == 'Backdrop' && result.field == 'animationNotes', "source static target");
  check(result.initialAnim == 'shoot1' && result.skipDance, "source initial pose and dance");
  check(PsychMappedAnimsSource.discover("switch(curCharacter) { case 'actor': dance(); }") == null,
   "no invented mapped behavior");
  var unsafe = StringTools.replace(source, "actorMap", "../outside");
  check(PsychMappedAnimsSource.discover(unsafe) == null, "unsafe companion chart");
  if (Sys.args().length > 0) {
   var archive = PsychMappedAnimsSource.discover(sys.io.File.getContent(Sys.args()[0]));
   check(archive != null && archive.character == 'pico-speaker'
    && archive.chart == 'picospeaker' && archive.className == 'TankmenBG'
    && archive.field == 'animationNotes' && archive.initialAnim == 'shoot1'
    && archive.skipDance, "selected archive source mapping");
  }
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch)
            (path / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(path), "--run", "Main",
                 *([str(DONOR)] if DONOR.exists() else [])],
                cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
