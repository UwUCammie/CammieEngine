"""Codename's built-in no-animation note behavior remains engine-level."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameNoteTypeCompatTest(unittest.TestCase):
    def test_builtin_no_anim_hit_and_miss_cancel_without_rewriting_type(self):
        adapter = (ROOT / "source/CodenameNoteTypeCompat.hx").read_text()
        main = r'''class Main {
  static function main() {
    var hit:Dynamic = {noteType:"No Anim Note", animCancelled:false, score:250};
    CodenameNoteTypeCompat.applyHit(hit);
    if (hit.animCancelled != true) throw 'No Anim Note hit did not cancel animation';
    if (hit.noteType != "No Anim Note") throw 'hit noteType text was rewritten';
    if (hit.score != 250) throw 'hit adapter changed unrelated event data';

    var miss:Dynamic = {noteType:"No Anim Note", animCancelled:false};
    CodenameNoteTypeCompat.applyPlayerMiss(miss);
    if (miss.animCancelled != true) throw 'No Anim Note miss did not cancel animation';
    if (miss.noteType != "No Anim Note") throw 'miss noteType text was rewritten';

    var other:Dynamic = {noteType:"Alt Anim Note", animCancelled:false};
    CodenameNoteTypeCompat.applyHit(other);
    CodenameNoteTypeCompat.applyPlayerMiss(other);
    if (other.animCancelled != false) throw 'other note type was changed';

    var cancelled:Dynamic = {noteType:"No Anim Note", animCancelled:true};
    CodenameNoteTypeCompat.applyHit(cancelled);
    if (cancelled.animCancelled != true) throw 'existing cancellation was cleared';

    var spaced:Dynamic = {noteType:"  NO ANIM NOTE  ", animCancelled:false};
    CodenameNoteTypeCompat.applyHit(spaced);
    if (spaced.animCancelled != true || spaced.noteType != "  NO ANIM NOTE  ")
      throw 'matching normalized the callback value instead of preserving authored text';
  }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            temp = Path(folder)
            (temp / "CodenameNoteTypeCompat.hx").write_text(adapter, newline='\n')
            (temp / "Main.hx").write_text(main, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(temp), "--run", "Main"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_applies_builtin_semantics_after_mutable_callbacks(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        hit = source.index("callCodenameEvent('onNoteHit', event);")
        hit_adapter = source.index("CodenameNoteTypeCompat.applyHit(event);", hit)
        hit_animation = source.index("if (!event.animCancelled && event.characters != null)", hit)
        self.assertLess(hit, hit_adapter)
        self.assertLess(hit_adapter, hit_animation)

        miss = source.index("callCodenameEvent('onPlayerMiss', event);")
        miss_adapter = source.index("CodenameNoteTypeCompat.applyPlayerMiss(event);", miss)
        miss_animation = source.index("if (!event.animCancelled && event.characters != null)", miss)
        self.assertLess(miss, miss_adapter)
        self.assertLess(miss_adapter, miss_animation)

        self.assertIn("player, note.sourceKind,", source)
        self.assertIn("note == null ? null : note.sourceKind,", source)


if __name__ == "__main__":
    unittest.main()
