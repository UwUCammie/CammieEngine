"""Content packages keep their namespace across re-imports, and empty leftovers are removed."""
from haxe_test_support import HAXE_COMMAND

from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]

STUBS = {
    "ImportIO.hx": r'''class ImportIO {
  public var bound:Map<String, String> = new Map();
  public var resolved:Map<String, String> = new Map();
  public var written:Array<String> = [];
  public function new() {}
  public static function key(path:String, engine:String):String
    return haxe.io.Path.normalize(path).toLowerCase() + '|' + engine.toLowerCase();
  public function setNamespace(path:String, engine:String, namespace:String):Void bound.set(key(path, engine), namespace);
  public function namespace(path:String, engine:String):Null<String> return bound.get(key(path, engine));
  public function resolvedNamespace(path:String, engine:String):Null<String> return resolved.get(key(path, engine));
  public function writtenPaths():Array<String> return written;
}''',
    "CompatScriptManifest.hx": r'''class CompatScriptManifest {
  public static inline var ROOT_PREFIX:String = 'assets/imported_mods';
  public static function namespaceLabel(source:String, engine:String):String
    return 'nightmare-vision-' + haxe.io.Path.withoutDirectory(haxe.io.Path.normalize(source)).toLowerCase();
}''',
    "ImportWorkScheduler.hx": r'''class ImportWorkScheduler {
  public static function cooperate(?cancel:Void->Bool):Bool return true;
}''',
}

FIXTURE = r'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;

class NamespaceFixture {
  static function check(value:Bool, message:String) if (!value) throw message;
  static function dir(path:String) FileSystem.createDirectory(path);
  static function manifest(paths:Array<String>):Dynamic return {files:[for (path in paths) {path:path, sha256:'0'}]};

  static function main() {
    var work = Sys.args()[0];
    var source = work + '/snapshot/content';
    var game = 'game';
    for (pack in ['Alpha', 'Beta', 'Cobalt/assets', 'Delta'])
      dir(source + '/' + game + '/content/' + pack);
    dir(source + '/other/content/Ignored');
    var record:Dynamic = {roots:[
      {relative:game, engine:'Nightmare Vision', namespace:'nightmare-vision-game-0000000001'},
      {relative:'other', engine:'Psych Engine', namespace:'psych-engine-other-0000000002'}
    ]};

    var roots = ImportPackageNamespaces.packageRoots(source, record);
    check(roots.join(',') == 'game/content/Alpha,game/content/Beta,game/content/Cobalt,game/content/Cobalt/assets,game/content/Delta',
      'package roots: ' + roots.join(','));

    // Receipts from before the field existed: the earlier namespace is found by
    // its readable label, only when that is unambiguous.
    var previous = manifest([
      'assets/imported_mods/nightmare-vision-game-0000000001/meta.json',
      'assets/imported_mods/nightmare-vision-alpha-1a2b3c4d5e/data/song/song.json',
      'assets/imported_mods/nightmare-vision-beta-aaaaaaaaaa/a.png',
      'assets/imported_mods/nightmare-vision-beta-bbbbbbbbbb/a.png',
      'assets/data/song/song.json'
    ]);
    var io = new ImportIO();
    ImportPackageNamespaces.retain(io, source, record, previous);
    check(io.namespace(source + '/game/content/Alpha', 'Nightmare Vision') == 'nightmare-vision-alpha-1a2b3c4d5e',
      'legacy package namespace was not kept');
    check(io.namespace(source + '/game/content/Beta', 'Nightmare Vision') == null,
      'two earlier namespaces with one label must not be guessed');
    check(io.namespace(source + '/game/content/Delta', 'Nightmare Vision') == null,
      'a package without an earlier namespace stays unbound');

    // After conversion only namespaces with outputs are stored.
    io.resolved.set(ImportIO.key(source + '/game/content/Alpha', 'Nightmare Vision'), 'nightmare-vision-alpha-1a2b3c4d5e');
    io.resolved.set(ImportIO.key(source + '/game/content/Delta', 'Nightmare Vision'), 'nightmare-vision-delta-1234567890');
    io.resolved.set(ImportIO.key(source + '/game/content/Beta', 'Nightmare Vision'), 'nightmare-vision-game-0000000001');
    io.written = ['assets/imported_mods/nightmare-vision-alpha-1a2b3c4d5e/data/song/song.json',
      'assets/imported_mods/nightmare-vision-game-0000000001/meta.json'];
    ImportPackageNamespaces.capture(io, source, record);
    var stored:Array<Dynamic> = Reflect.field(record, 'packageNamespaces');
    check(stored != null && stored.length == 1 && stored[0].relative == 'game/content/Alpha'
      && stored[0].namespace == 'nightmare-vision-alpha-1a2b3c4d5e' && stored[0].engine == 'Nightmare Vision',
      'stored namespaces: ' + haxe.Json.stringify(stored));

    // A later import from a new snapshot binds the stored namespace directly,
    // without looking at the earlier manifest.
    var moved = work + '/snapshot2/content';
    dir(moved + '/game/content/Alpha');
    var next = new ImportIO();
    ImportPackageNamespaces.retain(next, moved, record, null);
    check(next.namespace(moved + '/game/content/Alpha', 'Nightmare Vision') == 'nightmare-vision-alpha-1a2b3c4d5e',
      'stored namespace was not bound for the new snapshot');
    // A stored namespace that a recorded root now uses is never reused.
    Reflect.setField(record, 'packageNamespaces', [{relative:'game/content/Alpha', engine:'Nightmare Vision',
      namespace:'nightmare-vision-game-0000000001'}]);
    var claimed = new ImportIO();
    ImportPackageNamespaces.retain(claimed, moved, record, null);
    check(claimed.namespace(moved + '/game/content/Alpha', 'Nightmare Vision') == null, 'root namespace reused');
    io.written = [];
    ImportPackageNamespaces.capture(io, source, record);
    check(!Reflect.hasField(record, 'packageNamespaces'), 'empty capture must clear the field');

    // Empty folders left by an earlier namespace are removed; folders with any
    // file, and unrelated labels, stay.
    var install = work + '/install';
    var mods = install + '/assets/imported_mods';
    dir(mods + '/nightmare-vision-alpha-1a2b3c4d5e/__nmv_core/images');
    File.saveContent(mods + '/nightmare-vision-alpha-1a2b3c4d5e/__nmv_core/images/a.png', 'x');
    dir(mods + '/nightmare-vision-alpha-6f7a8b9c0d/data/song');
    dir(mods + '/nightmare-vision-alpha-6f7a8b9c0d/__nmv_core/tools');
    dir(mods + '/nightmare-vision-old-1111111111/stages');
    dir(mods + '/nightmare-vision-alpha-dddddddddd/data');
    File.saveContent(mods + '/nightmare-vision-alpha-dddddddddd/data/kept.json', '{}');
    dir(mods + '/psych-engine-unrelated-2222222222');
    var committed = manifest(['assets/imported_mods/nightmare-vision-alpha-1a2b3c4d5e/__nmv_core/images/a.png']);
    var before = manifest(['assets/imported_mods/nightmare-vision-old-1111111111/stages/a.json']);
    var removed = ImportPackageNamespaces.pruneEmptyNamespaces(install, before, committed);
    check(removed == 2, 'removed count ' + removed);
    check(!FileSystem.exists(mods + '/nightmare-vision-alpha-6f7a8b9c0d'), 'empty same-label leftover kept');
    check(!FileSystem.exists(mods + '/nightmare-vision-old-1111111111'), 'empty formerly owned namespace kept');
    check(FileSystem.exists(mods + '/nightmare-vision-alpha-dddddddddd/data/kept.json'), 'a namespace with files was touched');
    check(FileSystem.exists(mods + '/nightmare-vision-alpha-1a2b3c4d5e/__nmv_core/images/a.png'), 'current namespace touched');
    check(FileSystem.exists(mods + '/psych-engine-unrelated-2222222222'), 'unrelated empty folder removed');
  }
}
'''


class ImportPackageNamespacesTest(unittest.TestCase):
    def test_retain_capture_and_prune(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            for name, text in STUBS.items():
                (Path(folder) / name).write_text(text, newline='\n')
            (Path(folder) / "NamespaceFixture.hx").write_text(FIXTURE, newline='\n')
            work = Path(folder) / "work"
            work.mkdir()
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                                     "--run", "NamespaceFixture", str(work)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
