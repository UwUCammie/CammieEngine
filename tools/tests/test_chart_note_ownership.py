"""Psych v1 absolute note lanes stay separate from legacy section-relative lanes."""

import json
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'
ARCHIVE = Path('/run/media/cammie/External Storage/FNF-Example-Mods/FNF-PsychEngine-main.zip')
SOURCE_DATA = Path('/run/media/cammie/External Storage/FNF-Example-Mods/misc/psych_source_code/assets/base_game/shared/data')


def source_charts():
    """Use the supplied source tree when the original archive has been unpacked."""
    prefix = 'FNF-PsychEngine-main/assets/base_game/shared/data/'
    if ARCHIVE.is_file():
        with ZipFile(ARCHIVE) as archive:
            for name in archive.namelist():
                if name.startswith(prefix) and name.endswith('.json'):
                    yield name, archive.read(name)
    elif SOURCE_DATA.is_dir():
        for path in sorted(SOURCE_DATA.glob('*/*.json')):
            yield prefix + path.relative_to(SOURCE_DATA).as_posix(), path.read_bytes()


def extract_method(source, marker):
    start = source.index(marker)
    brace = source.index('{', start)
    depth = 0
    for position in range(brace, len(source)):
        if source[position] == '{':
            depth += 1
        elif source[position] == '}':
            depth -= 1
            if depth == 0:
                return source[start:position + 1]
    raise AssertionError(f'unterminated method: {marker}')


class ChartNoteOwnershipTest(unittest.TestCase):
    def test_source_psych_v1_rows_and_legacy_rows(self):
        if not HAXE.is_file():
            self.skipTest('portable Haxe interpreter is unavailable')
        fixture = '''class ChartNoteOwnershipFixture {
 static function check(actual:Bool, expected:Bool):Void {
  if (actual != expected) throw 'note side mismatch';
 }
 static function main():Void {
  for (mustHit in [false, true]) {
   for (lane in 0...8) {
    check(ChartNoteOwnership.mustPress("psych_v1_convert", lane, mustHit, 4), lane < 4);
    check(ChartNoteOwnership.mustPress(null, lane, mustHit, 4),
     lane < 4 ? mustHit : !mustHit);
   }
  }
  check(ChartNoteOwnership.mustPress(null, 8, true, 4), true);
  check(ChartNoteOwnership.mustPress(null, 12, true, 4), false);
  check(ChartNoteOwnership.mustPress("psych_v1_convert", 4, false, 6), false);
  for (format in ["nmv2", "psych_v1"]) {
   for (sectionOwner in [false, true]) {
    for (field in 0...4) {
     var lane = field * 6 + 5;
     var address = ChartNoteOwnership.address(format, lane, sectionOwner, 6);
     if (address.playfieldIndex != field || address.direction != 5)
      throw 'NMV field address did not use the authored key count';
     if (address.playerControlled != (field != 1)
      || address.autoPlay != (field != 0))
      throw 'NMV actor/autoplay policy differed from generatePlayfields';
     if (ChartNoteOwnership.mustPress(format, lane, sectionOwner, 6) != (field == 0))
      throw 'NMV source field identity was collapsed into legacy hit side';
    }
   }
  }
  var legacyOpponent = ChartNoteOwnership.address(null, 5, false, 4);
  if (legacyOpponent.playfieldIndex != 0 || legacyOpponent.direction != 1
   || !legacyOpponent.playerControlled || legacyOpponent.autoPlay)
   throw 'legacy section-relative field address changed';
  if (ChartNoteOwnership.playerControlOverride(null, legacyOpponent) != null
   || ChartNoteOwnership.playerControlOverride("psych_v1_convert",
    ChartNoteOwnership.address("psych_v1_convert", 5, false, 4)) != null)
   throw 'legacy owner override would freeze mutable mustPress ownership';
  var extraNmvOwner = ChartNoteOwnership.playerControlOverride("nmv2",
   ChartNoteOwnership.address("nmv2", 8, false, 4));
  if (extraNmvOwner != true)
   throw 'NMV extra BF field lost its independent source owner';
  var eventAddress = ChartNoteOwnership.address("nmv2", -1, false, 4);
  if (eventAddress.playfieldIndex != -1 || eventAddress.direction != -1
   || eventAddress.playerControlled || eventAddress.autoPlay)
   throw 'event rows must not be treated as chart notes';
  for (path in Sys.args()) {
   var chart:Dynamic = haxe.Json.parse(sys.io.File.getContent(path)).song;
   if (Reflect.field(chart, "format") != "psych_v1_convert")
    throw 'missing source format';
   var player = 0; var opponent = 0;
   for (section in (cast Reflect.field(chart, "notes"):Array<Dynamic>))
    for (row in (cast Reflect.field(section, "sectionNotes"):Array<Array<Dynamic>>)) {
     var lane = Std.int(row[1]);
     if (lane < 0) continue;
     if (ChartNoteOwnership.mustPress(Reflect.field(chart, "format"), lane,
      Reflect.field(section, "mustHitSection") == true, 4)) player++;
     else opponent++;
    }
   Sys.println(player + "/" + opponent);
  }
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            directory = Path(folder)
            (directory / 'ChartNoteOwnershipFixture.hx').write_text(fixture)
            paths = []
            source = dict(source_charts())
            if source:
                for difficulty in ('easy', '', 'hard'):
                    name = 'ugh' + (f'-{difficulty}' if difficulty else '') + '.json'
                    path = directory / name
                    path.write_bytes(source[
                        'FNF-PsychEngine-main/assets/base_game/shared/data/ugh/' + name])
                    paths.append(str(path))
            result = subprocess.run(
                [str(HAXE), '-cp', str(directory), '-cp', str(ROOT / 'source'),
                 '--run', 'ChartNoteOwnershipFixture', *paths],
                cwd=directory, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        if paths:
            self.assertEqual(result.stdout.strip().splitlines(),
                             ['141/155', '227/241', '256/270'])

    def test_playstate_carries_source_field_address_to_heads_sustains_and_lifts(self):
        note = (ROOT / 'source/Note.hx').read_text()
        play = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn('public var sourcePlayfieldIndex:Int = -1;', note)
        self.assertIn('public var sourceDirection:Int = -1;', note)
        self.assertIn('public var sourcePlayfieldPlayerControlled:Null<Bool> = null;', note)
        self.assertIn('public var sourcePlayfieldAutoPlay:Bool = false;', note)
        self.assertIn('ChartNoteOwnership.address(SONG.format,', play)
        self.assertIn('ChartNoteOwnership.playerControlOverride(', play)
        for variable in ('swagNote', 'sustainNote', 'liftNote'):
            self.assertIn(f'{variable}.sourcePlayfieldIndex = chartAddress.playfieldIndex;', play)
            self.assertIn(f'{variable}.sourceDirection = chartAddress.direction;', play)
            self.assertIn(f'{variable}.sourcePlayfieldPlayerControlled = sourcePlayerControlled;', play)
            self.assertIn(f'{variable}.sourcePlayfieldAutoPlay = chartAddress.autoPlay;', play)

    def test_runtime_keeps_chart_format_through_difficulty_merge(self):
        song = (ROOT / 'source/Song.hx').read_text()
        runtime = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn('ChartNoteOwnership.mustPress(SONG.format,', runtime)
        fields = song[song.index('\tstatic var gameplayFields'):song.index('\tstatic var registryCache')]
        methods = '\n'.join(extract_method(song, marker) for marker in (
            '\tstatic function chartHasValue(',
            '\tstatic function isValidVisualValue(',
            '\tstatic function visualValueIsValid(',
            '\tpublic static function resolveChartData(',
        ))
        fixture = 'using StringTools;\nclass NoteFormatMerge {\n' + fields + methods + '''
 static function validCharacter(v:String):Bool return true;
 static function validStage(v:String):Bool return true;
 static function validUIType(v:String):Bool return true;
 static function validCutscene(v:String):Bool return true;
 static function validLayout(v:String):Bool return true;
 static function main():Void {
  var base:Dynamic = {song:"Ugh", notes:[], bpm:160, format:"psych_v1_convert"};
  var selected:Dynamic = {song:"Ugh", notes:[{mustHitSection:false,
   sectionNotes:[[0,7,0],[100,1,0]]}], bpm:160, format:"psych_v1_convert"};
  var merged = resolveChartData(selected, [], base);
  if (Reflect.field(merged, "format") != "psych_v1_convert")
   throw 'selected difficulty lost source format';
  if ((cast Reflect.field(merged, "notes"):Array<Dynamic>).length != 1)
   throw 'selected difficulty lost its own note rows';
  var other = resolveChartData({song:"Other", notes:[], bpm:120}, [],
   {song:"Other", notes:[], bpm:120});
  if (Reflect.hasField(other, "format")) throw 'unmarked chart acquired Psych format';
  var layout = resolveChartData({song:"Fields", notes:[], bpm:120, format:"nmv2",
   keys:6, lanes:3, arrowSkins:["selected"], trackSwap:false}, [],
   {song:"Fields", notes:[], bpm:120, format:"nmv2", keys:4, lanes:2,
    arrowSkins:["default"], trackSwap:true});
  if (layout.keys != 6 || layout.lanes != 3 || layout.arrowSkins[0] != "selected"
   || layout.trackSwap != false)
   throw 'selected chart inherited a sibling field layout';
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'NoteFormatMerge.hx').write_text(fixture)
            result = subprocess.run(
                [str(HAXE), '-cp', folder, '-main', 'NoteFormatMerge', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_installed_archive_note_sides_match_every_available_source_chart(self):
        runtime_data = ROOT / 'export/release/linux/bin/assets/data'
        if not (ARCHIVE.is_file() or SOURCE_DATA.is_dir()) or not runtime_data.is_dir():
            self.skipTest('mounted Psych source or installed runtime is unavailable')

        owners = {}
        for receipt in runtime_data.glob('*/importProvenance.json'):
            try:
                data = json.loads(receipt.read_text())
            except (OSError, ValueError):
                continue
            if (data.get('sourceEngine') == 'Psych Engine'
                    and 'fnf-psychengine-main' in data.get('sourceOwner', '')):
                owners[data.get('sourceFolder')] = receipt.parent

        def sides(chart):
            return Counter('player' if row[1] < 4 else 'opponent'
                           for section in chart['notes']
                           for row in section.get('sectionNotes', [])
                           if len(row) > 1 and row[1] >= 0)

        checked = 0
        for name, payload in source_charts():
            try:
                source = json.loads(payload).get('song')
            except (ValueError, KeyError):
                continue
            if not isinstance(source, dict) or not isinstance(source.get('notes'), list):
                continue
            folder, filename = name.split('/')[-2:]
            owner = owners.get(folder)
            if owner is None or not (owner / filename).is_file():
                continue  # source entries without imported instrumental remain blocked
            installed = json.loads((owner / filename).read_text())['song']
            self.assertEqual(source.get('format'), 'psych_v1_convert', name)
            self.assertEqual(installed.get('format'), source.get('format'), name)
            self.assertEqual(sides(installed), sides(source), name)
            checked += 1
        self.assertEqual(checked, 76)


if __name__ == '__main__':
    unittest.main()
