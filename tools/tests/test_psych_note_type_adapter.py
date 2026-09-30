"""Psych/Kade sectionNotes[3] noteType compatibility stays engine-level."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class PsychNoteTypeAdapterTest(unittest.TestCase):
    def test_common_psych_note_types_resolve_without_mutating_authored_rows(self):
        adapter = (ROOT / "source/NoteTypeCompat.hx").read_text()
        main = r'''class Main {
  static function main() {
    var rows:Array<Dynamic> = [
        [100, 0, 0, "Alt Animation"],
        [200, 1, 0, "Hurt Note"],
        [300, 2, 0, "GF Sing"],
        [400, 3, 0, "No Animation"],
        [500, 4, 0, "Can't Hit"]
    ];
    var chart:Dynamic = {song:{preferredNoteAmount:4, notes:[
      {sectionNotes:rows}
    ]}};
    var defs:Array<Dynamic> = [];
    var original:Array<Dynamic> = [for (row in rows) row[3]];
    if (NoteTypeCompat.nativeNoteData(rows[0], 4, defs) != 0) throw 'alt animation lane was not retained';
    if (NoteTypeCompat.nativeNoteData(rows[1], 4, defs) != 41) throw 'first custom note index is not native';
    if (NoteTypeCompat.nativeNoteData(rows[2], 4, defs) != 50) throw 'custom note lane was not retained';
    if (NoteTypeCompat.nativeNoteData(rows[3], 4, defs) != 59) throw 'third custom note lane was not retained';
    if (NoteTypeCompat.nativeNoteData(rows[4], 4, defs) != 64) throw 'fourth custom note lane was not retained';
    for (i in 0...rows.length)
      if (rows[i][3] != original[i]) throw 'runtime resolution mutated authored row ' + i;
    if (defs.length != 4) throw 'expected four custom definitions, got ' + defs.length;
    if (defs[0].sourceNoteType != 'Hurt Note') throw 'definitions are not ordered by first occurrence';
    if (defs[0].damageAmount >= 0) throw 'hurt note is not damaging';
    if (defs[1].shouldSing != true) throw 'GF Sing must remain a hittable/singable note';
    if (defs[2].shouldSing != false) throw 'No Animation should not sing';
    if (defs[3].damageAmount != 0) throw "Can't Hit should not change health";
    var vsliceGf:Dynamic = {sourceKind:'gf'};
    var vsliceHurt:Dynamic = {sourceKind:'hurt'};
    var vsliceNoAnim:Dynamic = {sourceKind:'noanim'};
    var vsliceUnknown:Dynamic = {sourceKind:'duet-owner'};
    if (!NoteTypeCompat.applyVSliceKind(vsliceGf, 'gf')
      || vsliceGf.sourceNoteType != 'GF Sing' || vsliceGf.shouldSing != true)
      throw 'V-Slice GF alias was not routed';
    if (!NoteTypeCompat.applyVSliceKind(vsliceHurt, 'hurt')
      || vsliceHurt.sourceNoteType != 'Hurt Note' || vsliceHurt.damageAmount >= 0)
      throw 'V-Slice hurt alias was not routed';
    if (!NoteTypeCompat.applyVSliceKind(vsliceNoAnim, 'noanimation')
      || vsliceNoAnim.sourceNoteType != 'No Animation' || vsliceNoAnim.shouldSing != false)
      throw 'V-Slice no-animation alias was not routed';
    if (NoteTypeCompat.applyVSliceKind(vsliceUnknown, 'duet-owner')
      || Reflect.hasField(vsliceUnknown, 'sourceNoteType'))
      throw 'unknown V-Slice kind was guessed';
    trace('OK');
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            (temp / "NoteTypeCompat.hx").write_text(adapter)
            (temp / "Main.hx").write_text(main)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "--run", "Main"],
                cwd=folder,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout + result.stderr)

    def test_importer_collects_note_definitions_without_rewriting_charts(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("static function prepareSongNoteDefinitions", source)
        self.assertIn("The authored row remains unchanged", source)
        self.assertNotIn("normalizeImportedChartNoteTypes(coolSong", source)

    def test_gf_note_and_section_routes_are_engine_level(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        section = (ROOT / "source/Section.hx").read_text()
        self.assertIn("@:optional var gfSection:Null<Bool>;", section)
        self.assertIn("swagNote.forceGfSing = true;", play_state)
        self.assertIn("note.forceGfSing && gf != null ? gf : getOpponentSinger()", play_state)
        self.assertIn("PlayState.SONG.notes[curSection].gfSection == true", play_state)


if __name__ == "__main__":
    unittest.main()
