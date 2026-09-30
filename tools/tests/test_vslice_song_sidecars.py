"""Owner-scoped V-Slice song sidecar import and HXC path resolution."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


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
    raise AssertionError(f"unterminated Haxe method: {marker}")


def hx_string(value: str) -> str:
    # The fixture paths are generated under the repository's tmp directory,
    # whose path has no Haxe escape sequences beyond ordinary slashes.
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


class VSliceSongSidecarsTest(unittest.TestCase):
    def test_sidecars_are_imported_per_owner_without_replacing_existing_files(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        markers = (
            "static function importPathKey(path:String):String",
            "static function importPathIsWithin(path:String, root:String):Bool",
            "static function findChildDirectory(parent:String, name:String):String",
            "static function validModuleName(name:String):Bool",
            "static function importSongFolderName(songData:SongImport):String",
            "static function ensureDirectory(path:String):Void",
            "static function existingImportChild(parent:String, name:String):String",
            "static function validImportEntryName(name:String):Bool",
            "static function mergeVSliceSongSidecars(sourceRoot:String, ownerRoot:String,",
            "static function mergeVSliceSongSidecarTree(source:String, sourceSongRoot:String,",
        )
        methods = "\n".join(extract_method(module, marker) for marker in markers)
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            base = Path(folder)
            root_a = base / "donor-a"
            root_b = base / "donor-b"
            owner_a = base / "assets/imported_mods/owner-a"
            owner_b = base / "assets/imported_mods/owner-b"
            for donor, lyric in ((root_a, b"owner A lyrics"), (root_b, b"owner B lyrics")):
                song = donor / "data/songs/our-harmony"
                (song / "nested").mkdir(parents=True)
                (song / "lyrics.txt").write_bytes(lyric)
                (song / "nested/cues.txt").write_bytes(lyric + b" cue")
                (song / "our-harmony-chart.json").write_text("{}")
                (song / "our-harmony-metadata.json").write_text("{}")
                (song / "our-harmony-chart-hard.jsonc").write_text("{}")
                (song / "our-harmony-metadata-hard.jsonc").write_text("{}")
            owner_a.mkdir(parents=True)
            owner_b.mkdir(parents=True)

            escape = base / "outside-owner.txt"
            escape.write_text("outside owner")
            owner_song = owner_a / "data/songs/our-harmony"
            owner_song.mkdir(parents=True)
            (owner_song / "linked.txt").symlink_to(escape)

            # A link that resolves outside the selected song folder must not be
            # imported, even when it remains inside the donor's broader root.
            (root_a / "data/songs/our-harmony/leak.txt").symlink_to(root_a / "outside.txt")
            (root_a / "outside.txt").write_text("must not leak")

            fixture = '''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
typedef ImportAssetMergeResult = { var copied:Int; var skipped:Int; var failed:Int; @:optional var errors:Array<String>; }
typedef SongImportSource = { var data:String; }
typedef SongImport = { var name:String; @:optional var engine:String; @:optional var vSliceRoot:String; @:optional var sourceFolder:String; @:optional var destinationFolder:String; @:optional var importSourceInfo:SongImportSource; }
class ImportSettings {
 public static function normalizeSourcePath(path:String):String return Path.normalize(path == null ? "" : path);
}
class ImportEngine { public static inline var V_SLICE:String = "v-slice"; }
class ModuleFunctions {
 static function importWorkCancelled():Bool return false;
 static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0, copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {}
'''
            fixture += methods
            fixture += '''
 public static function mergeForTest(source:String, owner:String, song:SongImport):ImportAssetMergeResult {
  var selected:Map<String, SongImport> = new Map();
  selected.set(song.name, song);
  return mergeVSliceSongSidecars(source, owner, selected);
 }
}
class Main {
 static function fail(message:String):Void throw message;
 static function check(actual:Dynamic, expected:Dynamic, message:String):Void
  if (actual != expected) fail(message + ": " + actual + " != " + expected);
 static function main():Void {
  var rootA = __ROOT_A__;
  var rootB = __ROOT_B__;
  var ownerA = __OWNER_A__;
  var ownerB = __OWNER_B__;
  var songA:SongImport = {name:"our-harmony", engine:ImportEngine.V_SLICE, vSliceRoot:rootA,
   sourceFolder:"our-harmony", importSourceInfo:{data:rootA + "/data/songs/our-harmony"}};
  var songB:SongImport = {name:"our-harmony", engine:ImportEngine.V_SLICE, vSliceRoot:rootB,
   sourceFolder:"our-harmony", importSourceInfo:{data:rootB + "/data/songs/our-harmony"}};
  var firstA = ModuleFunctions.mergeForTest(rootA, ownerA, songA);
  var firstB = ModuleFunctions.mergeForTest(rootB, ownerB, songB);
  check(firstA.copied, 2, "first owner's sidecar count");
  check(firstB.copied, 2, "second owner's sidecar count");
  check(firstA.failed, 1, "outside song symlink rejection");
  check(File.getContent(ownerA + "/data/songs/our-harmony/lyrics.txt"), "owner A lyrics", "first owner bytes");
  check(File.getContent(ownerB + "/data/songs/our-harmony/lyrics.txt"), "owner B lyrics", "second owner bytes");
  check(HxcOwnedPath.existingSongDataFile(ownerA, "songs/our-harmony/lyrics"),
   ownerA + "/data/songs/our-harmony/lyrics.txt", "owner A HXC path");
  check(HxcOwnedPath.existingSongDataFile(ownerB, "songs/our-harmony/lyrics"),
   ownerB + "/data/songs/our-harmony/lyrics.txt", "owner B HXC path");
  check(HxcOwnedPath.existingSongDataFile(ownerA, "songs/our-harmony/linked"), null,
   "owner HXC lookup followed an escaping symlink");
  for (key in ["../sibling/lyrics", "songs/../sibling/lyrics", "songs//our-harmony/lyrics",
   "/songs/our-harmony/lyrics", "songs/our-harmony/../../outside"])
   check(HxcOwnedPath.songDataRelative(key), null, "unsafe HXC song key accepted: " + key);
  if (FileSystem.exists(ownerA + "/data/songs/our-harmony/our-harmony-chart.json")
   || FileSystem.exists(ownerA + "/data/songs/our-harmony/our-harmony-metadata.json")
   || FileSystem.exists(ownerA + "/data/songs/our-harmony/our-harmony-chart-hard.jsonc")
   || FileSystem.exists(ownerA + "/data/songs/our-harmony/our-harmony-metadata-hard.jsonc"))
   fail("chart or metadata was copied as an opaque sidecar");
  File.saveContent(ownerA + "/data/songs/our-harmony/lyrics.txt", "user override");
  File.saveContent(rootA + "/data/songs/our-harmony/lyrics.txt", "updated source");
  var repeat = ModuleFunctions.mergeForTest(rootA, ownerA, songA);
  check(repeat.copied, 0, "refresh replaced or recopied owned files");
  check(repeat.skipped, 2, "refresh did not report existing owner files");
  check(File.getContent(ownerA + "/data/songs/our-harmony/lyrics.txt"), "user override", "existing owner bytes changed");
  File.saveContent(rootA + "/data/songs/our-harmony/nested/cues.txt", "updated source cue");
  FileSystem.deleteFile(ownerA + "/data/songs/our-harmony/nested/cues.txt");
  var repair = ModuleFunctions.mergeForTest(rootA, ownerA, songA);
  check(repair.copied, 1, "missing sidecar was not repaired");
  check(File.getContent(ownerA + "/data/songs/our-harmony/nested/cues.txt"), "updated source cue", "repaired nested sidecar");
 }
}'''
            fixture = fixture.replace("__ROOT_A__", hx_string(root_a.as_posix()))
            fixture = fixture.replace("__ROOT_B__", hx_string(root_b.as_posix()))
            fixture = fixture.replace("__OWNER_A__", hx_string(owner_a.as_posix()))
            fixture = fixture.replace("__OWNER_B__", hx_string(owner_b.as_posix()))
            (base / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hxc_text_lookup_rewrite_scopes_vslice_song_keys(self):
        source = (ROOT / "source/EngineCompat.hx").read_text()
        markers = (
            "static function isLegacyFrameDeltaSpace(value:String):Bool",
            "static function isLegacyFrameDeltaIdentifierPart(value:String):Bool",
            "static function maskLegacyFrameDeltaSource(source:String):String",
            "static function rewriteScopedSongTextReads(source:String):String",
        )
        methods = "\n".join(extract_method(source, marker) for marker in markers)
        rewrite = extract_method(source, "public static function rewriteScopedAssetPaths(source:String):String")
        fixture = '''import haxe.io.Path;
using StringTools;
class EngineCompat {
''' + methods + "\n" + rewrite + '''
}
class Main {
 static function main():Void {
  var localSource = "function coolTextFile(path) { return Assets.getText(Paths.txt(path)); }\\n"
   + "var lyric = coolTextFile('songs/' + currentSong.id.toLowerCase() + '/lyrics');\\n";
  var local = EngineCompat.rewriteScopedAssetPaths(localSource);
  if (local.indexOf("return hxcAssets.getText(hxcPaths.txt(path))") < 0) throw local;
  if (local.indexOf("coolTextFile('songs/' + currentSong.id.toLowerCase() + '/lyrics')") < 0) throw local;
  if (local.indexOf("CoolUtil.coolTextFile") >= 0) throw local;
  var globalSource = "var lyric = coolTextFile('songs/' + currentSong.id.toLowerCase() + '/lyrics');\\n"
   + "var other = coolTextFile('assets/data/dialog');\\n"
   + "// coolTextFile('songs/fake/lyrics')\\n";
  var global = EngineCompat.rewriteScopedAssetPaths(globalSource);
  if (global.indexOf("CoolUtil.coolTextFile(hxcPaths.txt('songs/' + currentSong.id.toLowerCase() + '/lyrics'))") < 0) throw global;
  if (global.indexOf("coolTextFile('assets/data/dialog')") < 0) throw global;
  if (global.indexOf("// coolTextFile('songs/fake/lyrics')") < 0) throw global;
 }
}'''
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
