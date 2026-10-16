"""A package that was removed keeps one archived destination per chart, so it can be imported again."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''import ImportInstalledOwnership.InstalledLibraryIdentity;
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static inline var ENGINE = "V-Slice";
 static inline var IDENTITY = "v-slice|package-name|tricky";
 static inline var FINGERPRINT = "18feb7e57468f1e7eca1121600a6a68c";
 static inline var OWNER = "assets/imported_mods/v-slice-trickyclownedout-dcafb4ac88";
 static function record(source:String, folder:String, ?owner:String):InstalledLibraryIdentity
  return {folder:folder, ownerRoot:owner == null ? OWNER : owner, sourceFolder:source, engine:ENGINE,
   sourceIdentity:IDENTITY, sourceFingerprint:FINGERPRINT};
 static function destination(archive:LibraryIdentityArchive, source:String, ?planned:String):Null<String>
  return archive.destinationFor(ENGINE, IDENTITY, FINGERPRINT, source, planned);
 static function ambiguous(archive:LibraryIdentityArchive, source:String, ?planned:String):Bool {
  var failed = false;
  try destination(archive, source, planned) catch (error:Dynamic) failed = Std.string(error).indexOf("ambiguous") >= 0;
  return failed;
 }
 static function main():Void {
  // A V-Slice song and its erect variation share one source folder; one of the songs
  // may have had to take an owner-qualified folder when it was first imported.
  var archive = new LibraryIdentityArchive([
   record("assault", "assault"),
   record("expurgation", "expurgation"), record("expurgation", "expurgation-erect"),
   record("improbable-outset", "improbable-outset--v-slice-dcafb4ac88"), record("improbable-outset", "improbable-outset-erect")]);
  check(destination(archive, "assault") == "assault", "a single destination changed");
  check(destination(archive, "assault", "assault") == "assault", "a single destination changed with a planned folder");
  check(destination(archive, "expurgation", "expurgation") == "expurgation", "the song lost its own destination: " + destination(archive, "expurgation", "expurgation"));
  check(destination(archive, "expurgation", "expurgation-erect") == "expurgation-erect", "the erect variation lost its destination");
  check(destination(archive, "expurgation", "Expurgation-Erect") == "expurgation-erect", "the planned folder was matched case sensitively");
  check(destination(archive, "improbable-outset", "improbable-outset") == "improbable-outset--v-slice-dcafb4ac88",
   "the owner-qualified destination was not matched to its planned folder");
  check(destination(archive, "improbable-outset", "improbable-outset-erect") == "improbable-outset-erect", "the erect variation was taken for the qualified song");
  // Several destinations are still never guessed.
  check(ambiguous(archive, "expurgation"), "several destinations were guessed without a planned folder");
  check(ambiguous(archive, "expurgation", "somewhere-else"), "several destinations were guessed for an unrelated planned folder");
  check(ambiguous(archive, "expurgation", ""), "an empty planned folder picked a destination");
  check(destination(archive, "unknown-source", "unknown-source") == null, "an unarchived source folder found a destination");
  // The same destination archived twice is not a second destination.
  var repeated = new LibraryIdentityArchive([record("song", "song"), record("song", "song")]);
  check(destination(repeated, "song") == "song", "a repeated destination was treated as ambiguous");
  Sys.println("archive variations passed");
 }
}
'''


class LibraryIdentityArchiveVariationsTest(unittest.TestCase):
    def test_planned_folder_picks_between_a_song_and_its_variation(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(FIXTURE, encoding="utf-8")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work),
                                     "--run", "Main"],
                                    cwd=work, capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("archive variations passed", result.stdout)

    def test_the_importer_passes_the_folder_it_is_planning(self):
        source = (ROOT / "source/ImportSongOwnership.hx").read_text(encoding="utf-8")
        self.assertIn("sourceFolder == null ? folder : sourceFolder, folder);", source)


if __name__ == "__main__":
    unittest.main()
