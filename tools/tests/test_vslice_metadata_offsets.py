"""V-Slice metadata offsets reach the native chart and the song clock."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]


def extract_block(source: str, start_marker: str, end_marker: str) -> str:
    start = source.index(start_marker)
    end = source.index(end_marker, start) + len(end_marker)
    return source[start:end]


def extract_class(source: str, marker: str) -> str:
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
    raise AssertionError(f"unterminated class: {marker}")


def run_main(main_source: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        (Path(folder) / "Main.hx").write_text(main_source, newline="\n")
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder, "-main", "Main", "--interp"],
            cwd=ROOT, capture_output=True, text=True,
        )


def metadata(**extra):
    value = {
        "version": "2.2.4",
        "songName": "Offset Song",
        "playData": {
            "difficulties": ["normal"],
            "characters": {"player": "bf", "opponent": "dad", "girlfriend": "gf"},
            "stage": "mainStage",
        },
        "timeChanges": [{"t": 0, "bpm": 120}],
    }
    for key, item in extra.items():
        if key == "playData":
            value["playData"].update(item)
        else:
            value[key] = item
    return value


CHART = {"version": "2.0.0", "scrollSpeed": {"normal": 1}, "notes": {"normal": [{"t": 500, "d": 1}]}}


class VSliceMetadataOffsetsTest(unittest.TestCase):
    def convert_and_check(self, meta: dict, checks: str) -> None:
        offsets_class = extract_class((ROOT / "source/Song.hx").read_text(encoding="utf-8"), "class SongVocalOffsets")
        main = f'''{offsets_class}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = VSliceImporter.convertJson({json.dumps(json.dumps(meta))}, {json.dumps(json.dumps(CHART))}, "fixture");
    var song:Dynamic = result.charts[0].chart.song;
{checks}
  }}
}}
'''
        result = run_main(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_offsets_preview_and_sticker_pack_are_written_to_the_chart(self):
        meta = metadata(
            offsets={"instrumental": 35, "vocals": {"bf": -10, "dad": 4.5}, "altVocals": {"erect": {"bf": 7}}},
            playData={"previewStart": 12000, "previewEnd": 27000, "stickerPack": "custom-pack"},
        )
        self.convert_and_check(meta, '''
    if (song.instrumentalOffset != 35) fail("instrumental offset " + song.instrumentalOffset);
    var vocals = new SongVocalOffsets(song.vocalOffsets);
    if (vocals.getVocalOffset("bf") != -10) fail("player vocal offset");
    if (vocals.getVocalOffset("dad") != 4.5) fail("opponent vocal offset");
    if (vocals.getVocalOffset("bf", "erect") != 7) fail("alternate instrumental vocal offset");
    if (song.previewStart != 12000 || song.previewEnd != 27000) fail("preview window");
    if (song.stickerPack != "custom-pack") fail("sticker pack");
''')

    def test_selected_alternate_instrumental_picks_its_own_offset(self):
        meta = metadata(
            offsets={"instrumental": 35, "altInstrumentals": {"pico": -120}},
            playData={"characters": {"player": "pico", "opponent": "dad", "instrumental": "pico"}},
        )
        self.convert_and_check(meta, '''
    if (song.instrumentalOffset != -120) fail("alternate instrumental offset " + song.instrumentalOffset);
''')

    def test_absent_or_zero_offsets_leave_the_chart_unchanged(self):
        self.convert_and_check(metadata(), '''
    for (name in ["instrumentalOffset", "vocalOffsets", "previewStart", "previewEnd", "stickerPack"])
      if (Reflect.hasField(song, name)) fail("unexpected " + name);
''')
        self.convert_and_check(metadata(offsets={"instrumental": 0, "vocals": {}}), '''
    if (Reflect.hasField(song, "instrumentalOffset") || Reflect.hasField(song, "vocalOffsets")) fail("zero offsets written");
''')

    def test_conductor_maps_between_chart_and_audio_time(self):
        conductor = (ROOT / "source/Conductor.hx").read_text(encoding="utf-8")
        offset_api = extract_block(conductor, "public static var instrumentalOffset",
                                   "return Math.isFinite(number) ? number : 0;\n\t}")
        result = run_main('''class Conductor {
\t''' + offset_api + '''
}
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    if (Conductor.chartInstrumentalOffset({instrumentalOffset: 35}) != 35) fail("read offset");
    if (Conductor.chartInstrumentalOffset({instrumentalOffset: "35"}) != 0) fail("text is not an offset");
    if (Conductor.chartInstrumentalOffset({}) != 0) fail("absent offset");
    Conductor.instrumentalOffset = 0;
    if (Conductor.songStartThreshold(0) != 0 || Conductor.audioStartSongTime(2500) != 2500) fail("zero offset start");
    if (Conductor.songTimeFromAudio(1000) != 1000 || Conductor.audioTimeFromSong(1000) != 1000) fail("zero offset map");
    // Positive: the chart runs ahead, so the music joins after that much silence.
    Conductor.instrumentalOffset = 300;
    if (Conductor.songTimeFromAudio(1000) != 1300 || Conductor.audioTimeFromSong(1300) != 1000) fail("positive map");
    if (Conductor.songStartThreshold(0) != 300 || Conductor.audioStartSongTime(0) != 300) fail("positive start");
    if (Conductor.songStartThreshold(5000) != 0 || Conductor.audioStartSongTime(5000) != 5000) fail("positive start past offset");
    // Scripts sync media with songPosition - combinedOffset; that has to be the audio time.
    if (Conductor.combinedOffset != 300 || 1300 - Conductor.combinedOffset != Conductor.audioTimeFromSong(1300)) fail("combined offset");
    // Negative: the audio has a lead-in that the chart skips.
    Conductor.instrumentalOffset = -5000;
    if (Conductor.audioTimeFromSong(Conductor.audioStartSongTime(0)) != 5000) fail("negative start skips lead-in");
    if (Conductor.songStartThreshold(0) != 0) fail("negative start threshold");
    Conductor.instrumentalOffset = 0;
  }
}
''')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_runs_audio_and_conductor_through_the_offset(self):
        source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("Conductor.instrumentalOffset = Conductor.chartInstrumentalOffset(SONG);", source)
        self.assertIn("Conductor.songPosition = Conductor.audioStartSongTime(startTimestamp);", source)
        self.assertIn("FlxG.sound.music.time = Conductor.audioTimeFromSong(Conductor.songPosition);", source)
        self.assertIn("Conductor.songPosition = Conductor.songTimeFromAudio(FlxG.sound.music.time);", source)
        self.assertIn("var audioTarget = Math.max(0, Conductor.audioTimeFromSong(target));", source)
        self.assertIn("if (Conductor.songPosition >= Conductor.songStartThreshold(startTimestamp))", source)
        self.assertIn("var vocalDrift = vocalTime() - Conductor.audioTimeFromSong(Conductor.songPosition);", source)
        # Steps can tick during a positive offset's silent lead-in; the drift
        # resync must wait for startSong or it would start the music early.
        self.assertIn("if (SONG.needsVoices && !demoSongFinished && !startingSong) {", source)
        song = (ROOT / "source/Song.hx").read_text(encoding="utf-8")
        self.assertIn("'instrumentalOffset', 'mania'", song)


if __name__ == "__main__":
    unittest.main()
