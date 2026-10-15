"""Identical Nightmare Vision core files of one import are stored once after commit."""
from haxe_test_support import HAXE_COMMAND

from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;

class SharedCoreFixture {
  static var groupOf:Map<String, String> = new Map();
  static var links:Array<String> = [];
  static var refuseLinks = false;
  static var refuseReplaceOf:String = null;
  // Stored files that already carry the most names the filesystem allows.
  static var fullGroups:Map<String, Bool> = new Map();

  static function check(value:Bool, message:String) if (!value) throw message;
  static function key(path:String):String return Path.normalize(path).toLowerCase();
  static function group(path:String):String {
    var k = key(path);
    return groupOf.exists(k) ? groupOf.get(k) : k;
  }
  static function write(root:String, path:String, text:String):Dynamic {
    var full = root + '/' + path;
    FileSystem.createDirectory(Path.directory(full));
    File.saveContent(full, text);
    return {path:path, sha256:ImportSourceSnapshot.sha256File(full)};
  }

  static function main() {
    var install = Sys.args()[0];
    // A fake filesystem with hard links: a link copies the bytes and records
    // that both names are one stored file.
    NightmareVisionSharedCore.fileOps = {
      link:function(existing:String, created:String):Bool {
        if (refuseLinks || fullGroups.exists(group(existing))) return false;
        File.copy(existing, created);
        groupOf.set(key(created), group(existing));
        links.push(created);
        return true;
      },
      replace:function(source:String, target:String):Bool {
        if (refuseReplaceOf != null && StringTools.endsWith(key(target), refuseReplaceOf)) return false;
        if (FileSystem.exists(target)) FileSystem.deleteFile(target);
        FileSystem.rename(source, target);
        groupOf.set(key(target), group(source));
        return true;
      },
      sameFile:function(left:String, right:String):Bool return group(left) == group(right),
      linkCount:function(path:String):Int return fullGroups.exists(group(path)) ? 1023 : 1
    };
    var files:Array<Dynamic> = [];
    for (pack in ['a', 'b', 'c', 'd']) {
      files.push(write(install, 'assets/imported_mods/nightmare-vision-' + pack + '-0123456789/__nmv_core/images/shared.png', 'core image'));
      files.push(write(install, 'assets/imported_mods/nightmare-vision-' + pack + '-0123456789/images/own.png', 'package image'));
    }
    // Same bytes outside the imported namespaces stay separate.
    files.push(write(install, 'assets/songs/song/Inst.ogg', 'core image'));
    // A package file repeated inside the core joins it; identical package
    // files with no core copy are left alone.
    files.push(write(install, 'assets/imported_mods/nightmare-vision-g-0123456789/images/pack.png', 'pack art'));
    files.push(write(install, 'assets/imported_mods/nightmare-vision-g-0123456789/__nmv_core/content/G/images/pack.png', 'pack art'));
    files.push(write(install, 'assets/imported_mods/nightmare-vision-h-0123456789/images/own.png', 'only packages'));
    files.push(write(install, 'assets/imported_mods/nightmare-vision-i-0123456789/images/own.png', 'only packages'));
    // A core file edited after the commit no longer matches its manifest hash.
    var edited = write(install, 'assets/imported_mods/nightmare-vision-e-0123456789/__nmv_core/images/shared.png', 'core image');
    File.saveContent(install + '/' + edited.path, 'edited by hand');
    files.push(edited);
    // A listed file that is missing is skipped.
    files.push({path:'assets/imported_mods/nightmare-vision-f-0123456789/__nmv_core/images/shared.png', sha256:files[0].sha256});
    var manifest = {files:files};

    refuseReplaceOf = 'nightmare-vision-d-0123456789/__nmv_core/images/shared.png';
    var result = NightmareVisionSharedCore.linkCommitted(install, manifest);
    check(result.supported, 'links reported unsupported');
    check(result.linked == 3, 'linked ' + result.linked + ' ' + links.join(','));
    check(result.bytesShared == 2 * 'core image'.length + 'pack art'.length, 'bytes ' + result.bytesShared);
    check(group(install + '/assets/imported_mods/nightmare-vision-g-0123456789/images/pack.png')
      == group(install + '/assets/imported_mods/nightmare-vision-g-0123456789/__nmv_core/content/G/images/pack.png'),
      'package file repeated in the core is not shared');
    check(group(install + '/assets/imported_mods/nightmare-vision-h-0123456789/images/own.png')
      != group(install + '/assets/imported_mods/nightmare-vision-i-0123456789/images/own.png'),
      'package files without a core copy were linked');
    var anchor = install + '/assets/imported_mods/nightmare-vision-a-0123456789/__nmv_core/images/shared.png';
    for (pack in ['b', 'c'])
      check(group(install + '/assets/imported_mods/nightmare-vision-' + pack + '-0123456789/__nmv_core/images/shared.png') == group(anchor),
        'core file of ' + pack + ' is not shared');
    check(group(install + '/assets/imported_mods/nightmare-vision-d-0123456789/__nmv_core/images/shared.png') != group(anchor),
      'a file that could not be replaced must stay its own copy');
    check(!FileSystem.exists(install + '/assets/imported_mods/nightmare-vision-d-0123456789/__nmv_core/images/shared.png.shared-core.tmp'),
      'temporary link left behind');
    check(File.getContent(install + '/' + edited.path) == 'edited by hand', 'an edited file was replaced');
    check(group(install + '/assets/songs/song/Inst.ogg') != group(anchor), 'a non-core file was linked');
    for (pack in ['a', 'b', 'c', 'd'])
      check(File.getContent(install + '/assets/imported_mods/nightmare-vision-' + pack + '-0123456789/__nmv_core/images/shared.png') == 'core image',
        'core bytes changed for ' + pack);

    // A second pass finds everything already shared and does nothing new.
    refuseReplaceOf = null;
    links = [];
    var again = NightmareVisionSharedCore.linkCommitted(install, manifest);
    check(again.linked == 1 && links.length == 1, 'second pass relinked shared files: ' + links.join(','));

    // A stored file at the link limit hands over to the next copy: the rest of
    // its group and later groups are still shared, and the pass is not reported
    // as unsupported.
    var full = install + '/full';
    var fullFiles = [for (pack in ['a', 'b', 'c'])
      write(full, 'assets/imported_mods/nightmare-vision-' + pack + '-0123456789/__nmv_core/many.png', 'many')];
    fullFiles.push(write(full, 'assets/imported_mods/nightmare-vision-a-0123456789/__nmv_core/z.png', 'later'));
    fullFiles.push(write(full, 'assets/imported_mods/nightmare-vision-b-0123456789/__nmv_core/z.png', 'later'));
    var fullAnchor = full + '/assets/imported_mods/nightmare-vision-a-0123456789/__nmv_core/many.png';
    fullGroups.set(group(fullAnchor), true);
    var limited = NightmareVisionSharedCore.linkCommitted(full, {files:fullFiles});
    check(limited.supported, 'a full stored file was taken for a filesystem without links');
    check(limited.linked == 2, 'linked at the limit ' + limited.linked);
    var second = full + '/assets/imported_mods/nightmare-vision-b-0123456789/__nmv_core/many.png';
    check(group(second) != group(fullAnchor), 'a link to the full stored file was made');
    check(group(full + '/assets/imported_mods/nightmare-vision-c-0123456789/__nmv_core/many.png') == group(second),
      'the copy after the full stored file was not shared');
    check(!FileSystem.exists(second + '.shared-core.tmp'), 'temporary link left at the limit');
    fullGroups = new Map();

    // Without hard link support nothing changes.
    var fresh = install + '/fresh';
    var freshFiles = [for (pack in ['a', 'b'])
      write(fresh, 'assets/imported_mods/nightmare-vision-' + pack + '-0123456789/__nmv_core/x.json', '{}')];
    refuseLinks = true;
    var unsupported = NightmareVisionSharedCore.linkCommitted(fresh, {files:freshFiles});
    check(!unsupported.supported && unsupported.linked == 0, 'unsupported filesystem changed files');

    check(!NightmareVisionSharedCore.isCoreFile('assets/imported_mods/x/__nmv_core'), 'core folder itself is not a file');
    check(!NightmareVisionSharedCore.isCoreFile('assets/imported_mods/x/images/__nmv_core/a.png'), 'nested name is not the core');
    check(!NightmareVisionSharedCore.isCoreFile('assets/imported_mods/x/__nmv_core/../a.png'), 'escaping path');
  }
}
'''


class NightmareVisionSharedCoreTest(unittest.TestCase):
    def test_identical_core_files_are_linked_once_and_safely(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "SharedCoreFixture.hx").write_text(FIXTURE, newline='\n')
            (Path(folder) / "ImportWorkScheduler.hx").write_text(
                "class ImportWorkScheduler { public static function cooperate(?c:Void->Bool):Bool return true; }",
                newline='\n')
            install = Path(folder) / "install"
            install.mkdir()
            # The fixture folder comes last so its scheduler stub wins over the game's.
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
                                     "--run", "SharedCoreFixture", str(install)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
