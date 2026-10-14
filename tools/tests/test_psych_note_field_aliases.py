"""Notes expose the script-facing gf, hitsound, extra data and was-hit members."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def member(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    return source[start:source.index(end_marker, start)]


class PsychNoteFieldAliasTest(unittest.TestCase):
    def test_members_are_kept_for_reflection(self):
        note = (ROOT / "source/Note.hx").read_text(encoding="utf-8")
        for name in ("gfNote", "extraData", "noteWasHit", "hitsound", "hitsoundForce", "hitsoundVolume"):
            self.assertRegex(note, r"@:keep public var " + name + r"\b", name)
        self.assertIn("function get_gfNote():Bool return forceGfSing;", note)
        self.assertIn("function set_gfNote(value:Bool):Bool return forceGfSing = value;", note)
        self.assertIn("@:keep public var hitsound:String = 'hitsound';", note)

    def test_accessors_alias_latch_and_follow_the_volume_rule(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file() and not (ROOT / ".tools/haxe/haxe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        note = (ROOT / "source/Note.hx").read_text(encoding="utf-8")
        surface = "\n".join((
            member(note, "\t@:keep public var hitsound:String", "\tpublic var nightmareVisionLegacyGeometry"),
            member(note, "\tpublic var wasGoodHit:Bool = false;", "\t/** NMV source marker"),
            member(note, "\tpublic var forceGfSing:Bool", "\tpublic var customNotePath"),
        ))
        self.assertNotIn("class ", surface)
        fixture = r'''class PlayState {
 public static var instance:PlayState;
 public var preference:Float = 0;
 public function new() {}
 public function sourceHitsoundPreference():Float return preference;
}
class Note {
 public function new() {}
__SURFACE__
}
class NoteAliasFixture {
 static function main():Void {
  var note = new Note();
  note.gfNote = true;
  if (!note.forceGfSing) throw 'gfNote did not reach the singer switch';
  note.forceGfSing = false;
  if (note.gfNote) throw 'gfNote did not read the singer switch';
  if (Reflect.getProperty(note, 'gfNote') != false) throw 'reflection read';
  Reflect.setProperty(note, 'gfNote', true);
  if (!note.forceGfSing) throw 'reflection write';

  // No state yet behaves like hitsounds turned off.
  if (note.hitsoundVolume != 0) throw 'volume without a state';
  PlayState.instance = new PlayState();
  if (note.hitsoundVolume != 0) throw 'pref 0, not forced';
  note.hitsoundForce = true;
  note.hitsoundVolume = 0.7;
  if (note.hitsoundVolume != 0.7) throw 'pref 0, forced should use the note volume';
  PlayState.instance.preference = 0.5;
  if (note.hitsoundVolume != 0.5) throw 'a set preference wins';
  note.hitsoundForce = false;
  if (note.hitsoundVolume != 0.5) throw 'a set preference wins when not forced';
  if (Note.sourceHitsoundVolume(0, false, 1) != 0 || Note.sourceHitsoundVolume(0, true, 0.25) != 0.25
   || Note.sourceHitsoundVolume(0.5, true, 0.25) != 0.5) throw 'volume rule';

  if (note.noteWasHit) throw 'fresh note already hit';
  note.wasGoodHit = true;
  if (!note.noteWasHit) throw 'hit was not recorded';
  note.wasGoodHit = false;
  if (note.noteWasHit) throw 'a hit the engine took back should read as not hit';
  note.noteWasHit = true;
  if (!note.noteWasHit || note.wasGoodHit) throw 'a script write should stick without faking a real hit';
  if (Reflect.getProperty(note, 'noteWasHit') != true) throw 'reflection read of the hit flag';

  note.extraData.set('tag', 5);
  if (note.extraData.get('tag') != 5) throw 'extra data did not persist';
  var replacement:Map<String, Dynamic> = ['other' => 1];
  note.extraData = replacement;
  if (note.extraData != replacement) throw 'extra data could not be replaced';
  Sys.println('OK');
 }
}
'''.replace("__SURFACE__", surface)
        with tempfile.TemporaryDirectory(prefix="note-alias-", dir=ROOT / "tmp") as folder:
            scratch = Path(folder)
            (scratch / "NoteAliasFixture.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(scratch), "--run", "NoteAliasFixture"],
                                    cwd=ROOT, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)

    def test_hitsound_preference_reads_the_active_preference_set(self):
        play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        start = play.index("\t@:keep public function sourceHitsoundPreference():Float {")
        body = play[start:play.index("\n\t}\n", start)]
        self.assertIn("nightmareVisionPrefs.view", body)
        self.assertIn("psychClientPrefs.data", body)
        self.assertTrue(re.search(r"Reflect\.getProperty\(prefs, 'hitsoundVolume'\)", body))


if __name__ == "__main__":
    unittest.main()
