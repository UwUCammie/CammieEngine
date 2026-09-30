"""Psych stage songName follows Paths.formatToSongPath, not chart title case."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class PsychStageSongNameTest(unittest.TestCase):
    def test_source_song_path_format_is_shared_with_stage_view(self):
        stage = (ROOT / "source/PsychBaseStageCompat.hx").read_text()
        paths = (ROOT / "source/PsychOwnerPaths.hx").read_text()
        self.assertIn("PsychSongNameCompat.format(Std.string(value))", stage)
        self.assertNotIn("readField('songName')", stage)
        self.assertIn("return PsychSongNameCompat.format(path);", paths)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(
                """class Main {
 static function main():Void {
  if(PsychSongNameCompat.format('2Hot')!='2hot') throw 'stage title case';
  if(PsychSongNameCompat.format('Dad Battle!')!='dad-battle') throw 'stage punctuation';
  if(PsychSongNameCompat.format('  Pico, Erect  ')!='--pico-erect--')
   throw 'source path convention';
 }
}
""", encoding="utf-8")
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
