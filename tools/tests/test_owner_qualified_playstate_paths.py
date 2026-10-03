"""Owner-qualified songs keep chart identity while sidecars/audio use storage keys."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
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
    raise AssertionError(f"unterminated method: {marker}")


class OwnerQualifiedPlayStatePathTest(unittest.TestCase):
    def test_storage_key_drives_song_local_paths_without_changing_chart_identity(self):
        play_state = (ROOT / "source/PlayState.hx").read_text()
        helpers = "\n".join(extract_method(play_state, marker) for marker in (
            "function currentSongStorageFolder()",
            "function currentSongDataPath(file:String)",
            "function currentSongDataFolder()",
            "function currentSongAudioFolder()",
        ))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            fixture = Path(tmp) / "Main.hx"
            fixture.write_text(f'''import haxe.io.Path;
using StringTools;
class Song {{
  public static function storageFolder(chart:Dynamic):String
    return Reflect.field(chart, 'compatStorageFolder');
}}
class Main {{
  var SONG:Dynamic;
  public function new() {{}}
{helpers}
  static function main() {{
    var main = new Main();
    main.SONG = {{song:'improbable-outset', compatStorageFolder:'improbable-outset--codename-abcdef0123'}};
    if (main.currentSongStorageFolder() != 'improbable-outset--codename-abcdef0123')
      throw 'storage key not selected';
    if (main.currentSongDataPath('events.json') != 'assets/data/improbable-outset--codename-abcdef0123/events.json')
      throw 'song sidecar path used chart identity';
    if (main.currentSongAudioFolder() != 'assets/songs/improbable-outset--codename-abcdef0123')
      throw 'audio path used chart identity';
    main.SONG = {{song:'Canonical Song', compatStorageFolder:'../escape'}};
    if (main.currentSongStorageFolder() != 'canonical song')
      throw 'invalid storage key was accepted';
  }}
}}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(tmp), "--run", "Main"],
                                    cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        for marker in (
            "currentSongDataPath(CompatScriptManifest.FILE_NAME)",
            "currentSongDataPath('noteInfo.json')",
            "var eventPath = currentSongDataPath('events.json')",
            "currentSongAudioFolder() + '/'",
            "currentSongDataPath('preload.txt')",
            "currentSongDataPath('0.offset')",
        ):
            self.assertIn(marker, play_state)
        importer = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("Reflect.field(songData, 'ownerQualifiedCollision') != true", importer)
        self.assertIn("prepareImportedSongIdentity(coolSongSong, songData, targetFolder)", importer)


if __name__ == "__main__":
    unittest.main()
