"""Source-level contracts for V-Slice split-vocal imports and playback."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class VSliceSplitVocalsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.song = (ROOT / "source/Song.hx").read_text()
        cls.importer = (ROOT / "source/ModuleFunctions.hx").read_text()
        cls.vslice_importer = (ROOT / "source/VSliceImporter.hx").read_text()
        cls.play_state = (ROOT / "source/PlayState.hx").read_text()
        cls.tracks = (ROOT / "source/VocalTracks.hx").read_text()

    def test_chart_schema_keeps_split_stems_as_gameplay_metadata(self):
        self.assertIn("@:optional var vocalStems:Array<Dynamic>;", self.song)
        self.assertIn("'vocalStems'", self.song)
        self.assertIn("VSliceImporter.vocalStemReferences(metadata)", self.importer)
        self.assertIn("vocalStemMetadata(metadata)", self.vslice_importer)
        self.assertIn("public static function vocalStemReferences(metadata:Dynamic)", self.vslice_importer)
        self.assertIn("nativeVocalStemFile(stemId, extension)", self.importer)

    def test_unselected_split_stems_are_never_used_as_a_mixed_track_fallback(self):
        self.assertIn("Split V-Slice vocals are selected from metadata", self.importer)
        self.assertIn("return findImportFile(folder, ['Voices.ogg', 'voices.ogg']);", self.importer)
        self.assertNotIn("return stems.length == 0 ? null : stems[0];", self.importer)

    def test_auto_import_copies_every_stem_to_a_safe_deterministic_name(self):
        self.assertIn("audioEntries.sort(function(a, b)", self.importer)
        self.assertIn("lowerCompare == 0 ? Reflect.compare(a, b)", self.importer)
        self.assertIn("copyIfPresent(source, Path.join([songFolder, destination]))", self.importer)
        self.assertIn("Reflect.setField(convertedChart.chart.song, 'vocalStems'", self.importer)
        self.assertIn("Reflect.setField(convertedChart.chart.song, 'needsVoices', true)", self.importer)
        # The source plan carries donor paths only in memory. Native chart
        # metadata receives the destination basename, never the donor path.
        self.assertIn("file:Reflect.field(stem, 'destination')", self.importer)

    def test_playstate_transport_and_script_compatibility_reach_all_tracks(self):
        for operation in ("play", "pause", "stop", "seek", "setVolume", "setPitch", "destroy"):
            self.assertIn(f"public function {operation}", self.tracks)
        for wrapper in (
            "playVocals();",
            "pauseVocals();",
            "seekVocals(Conductor.songPosition);",
            "setVocalsVolume(0);",
            "destroyVocals();",
        ):
            self.assertIn(wrapper, self.play_state)
        self.assertIn("interp.variables.set(\"vocals\", vocals);", self.play_state)
        self.assertIn("if (playing && !sound.playing)", self.play_state)
        self.assertIn("else if (!playing && sound.playing)", self.play_state)
        self.assertIn("Math.abs(sound.time - time) > 20", self.play_state)

    def test_destroy_removes_and_destroys_each_split_sound(self):
        self.assertIn("for (sound in vocalTracks.tracks)", self.play_state)
        self.assertIn("FlxG.sound.list.remove(sound);", self.play_state)
        self.assertIn("vocalTracks.destroy();", self.play_state)
        self.assertIn("for (sound in tracks)", self.tracks)
        self.assertIn("sound.destroy();", self.tracks)

    def test_native_stem_selection_keeps_one_supported_encoding_per_voice(self):
        self.assertIn("VocalStemSelection.sameStem(existing.path, path)", self.play_state)
        self.assertIn("VocalStemSelection.prefer(path, existing.path, TitleState.soundExt)", self.play_state)
        main = r'''class Main {
    static function fail(message:String):Void throw message;
    static function main():Void {
        var root = "assets/songs/dad-battle/";
        if (!VocalStemSelection.sameStem(root + "Voices-Player.mp3", root + "Voices-Player.ogg"))
            fail("alternate encoding split");
        if (VocalStemSelection.sameStem(root + "Voices-Player.ogg", root + "Voices-Opponent.ogg"))
            fail("distinct voices merged");
        if (!VocalStemSelection.prefer(root + "Voices-Player.ogg", root + "Voices-Player.mp3", ".ogg"))
            fail("native encoding not preferred");
        if (VocalStemSelection.prefer(root + "Voices-Player.mp3", root + "Voices-Player.ogg", ".ogg"))
            fail("unsupported encoding replaced native stem");
    }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(main)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vocal_tracks_behavior_with_a_minimal_sound_backend(self):
        """Exercise the adapter without building the full Flixel game."""

        stub = r'''package flixel.sound;
class FlxSound {
    public var id:Int;
    public var playing:Bool = false;
    public var time:Float = 0;
    public var volume:Float = 1;
    public var pitch:Float = 1;
    public var destroyed:Bool = false;
    public var playCount:Int = 0;
    public var pauseCount:Int = 0;
    public var stopCount:Int = 0;
    public function new(id:Int) this.id = id;
    public function play():FlxSound { playing = true; playCount++; return this; }
    public function pause():FlxSound { playing = false; pauseCount++; return this; }
    public function stop():FlxSound { playing = false; stopCount++; return this; }
    public function getActualVolume():Float return volume;
    public function destroy():Void destroyed = true;
}
'''
        main = r'''import flixel.sound.FlxSound;
class Main {
    static function fail(message:String):Void throw message;
    static function main():Void {
        var first = new FlxSound(1);
        var second = new FlxSound(2);
        var third = new FlxSound(3);
        var group = new VocalTracks(first, [second, third, first]);
        if (group.tracks.length != 3 || group.primary != first) fail("dedupe/primary");
        group.play();
        if (!first.playing || !second.playing || !third.playing) fail("play");
        group.pause();
        if (first.playing || second.playing || third.playing) fail("pause");
        group.seek(1234);
        group.setVolume(0.25);
        group.setPitch(1.5);
        for (sound in group.tracks)
            if (sound.time != 1234 || sound.volume != 0.25 || sound.pitch != 1.5) fail("transport/volume/pitch");
        group.setRole(first, "opponent");
        group.setRole(second, "player");
        group.setRole(third, "opponent");
        group.setPlayerVolume(0.8);
        if (first.volume != 0.25 || second.volume != 0.8 || third.volume != 0.25)
            fail("player bus changed opponent stems");
        if (group.getPlayerVolume() != 0.8) fail("player bus getter");
        group.syncPrimaryVolume();
        if (second.volume != 0.8) fail("player bus did not survive ordinary sync");
        group.setRole(second, "shared");
        group.setPlayerVolume(0.7);
        if (group.getPlayerVolume() != 0.7 || first.volume != 0.25 || third.volume != 0.25)
            fail("shared fallback vocal bus");
        first.volume = 0.6;
        group.syncPrimaryVolume();
        if (second.volume != 0.6 || third.volume != 0.6)
            fail("direct legacy primary write did not reach every stem");
        group.stop();
        if (first.stopCount != 1 || second.stopCount != 1 || third.stopCount != 1) fail("stop");
        group.destroy();
        if (group.primary != null || group.tracks.length != 0) fail("group cleanup");
        if (!first.destroyed || !second.destroyed || !third.destroyed) fail("track cleanup");
    }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "flixel/sound").mkdir(parents=True)
            (root / "flixel/sound/FlxSound.hx").write_text(stub)
            (root / "VocalTracks.hx").write_text(self.tracks)
            (root / "Main.hx").write_text(main)
            result = subprocess.run(
                [str(HAXE), "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
