"""One owner root and owner-relative file module for the Psych and NV layers."""
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile
import unittest

from haxe_test_support import ROOT, HAXE_COMMAND


MAIN = r'''class Main {
 static function eq(actual:Dynamic, expected:Dynamic, label:String):Void
  if (actual != expected) throw label + ': ' + actual + ' != ' + expected;
 static function main() {
  var args = sys.io.File.getContent('args.txt').split('\n');
  var owner = args[0];
  var caseSensitive = args[1] == '1';
  var outsideLink = args[2];

  // Owner roots: the union of the cases the old copies disagreed on.
  eq(SourceOwnerFiles.normalizeRoot('assets/imported_mods/pack'), 'assets/imported_mods/pack', 'plain root');
  eq(SourceOwnerFiles.normalizeRoot('assets\\imported_mods\\pack\\'), 'assets/imported_mods/pack', 'backslashes and trailing slash');
  eq(SourceOwnerFiles.normalizeRoot('assets/imported_mods//pack///'), 'assets/imported_mods/pack', 'doubled slashes');
  eq(SourceOwnerFiles.normalizeRoot('assets/imported_mods/'), null, 'bare prefix');
  eq(SourceOwnerFiles.normalizeRoot('assets/imported_mods'), null, 'prefix without slash');
  eq(SourceOwnerFiles.normalizeRoot('assets/imported_mods/pack/../other'), null, 'parent segment');
  eq(SourceOwnerFiles.normalizeRoot('assets/imported_mods/./pack'), null, 'dot segment');
  eq(SourceOwnerFiles.normalizeRoot('assets/images/pack'), null, 'outside imported mods');
  eq(SourceOwnerFiles.normalizeRoot(null), null, 'null root');
  eq(SourceOwnerFiles.normalizeRoot('assets/imported_mods/C:pack'), null, 'drive colon');
  // Owner roots read back from saved data (score receipts, handoff keys) use the same rule.
  eq(SourceOwnerFiles.ownerFromData('  assets/imported_mods/pack/  '), 'assets/imported_mods/pack', 'saved root is trimmed then normalized');
  eq(SourceOwnerFiles.ownerFromData(42), null, 'saved root that is not text');
  eq(SourceOwnerFiles.ownerFromData('assets/imported_mods/pack/../other'), null, 'saved root with a parent segment');
  eq(SourceOwnerFiles.ownerFromData('assets/imported_mods/'), null, 'saved bare prefix');
  eq(SourceOwnerFiles.ownerFromData(null), null, 'missing saved root');
  eq(SourceOwnerFiles.normalizeRoot('assets/imported_mods/pa' + String.fromCharCode(0) + 'ck'), null, 'NUL');
  // The Psych asset facade and the owner preferences use the same rule.
  eq(PsychOwnerAssetPath.normalizeOwner('assets/imported_mods/pack/../other'), '', 'psych refuses a parent segment');
  var refused = false;
  try SourceOwnerPreferences.normalizeOwner('assets/imported_mods/', 'test') catch (_:Dynamic) refused = true;
  eq(refused, true, 'preferences refuse the bare prefix');

  // Owner-relative paths.
  eq(SourceOwnerFiles.cleanRelative('data/characters/bf.json'), 'data/characters/bf.json', 'nested file');
  for (bad in ['', '/abs', 'a/../b', 'a/./b', './a', 'a//b', 'C:/x', 'a:b/c', 'a\\b', 'a' + String.fromCharCode(0) + 'b'])
   eq(SourceOwnerFiles.cleanRelative(bad), null, 'refused ' + bad);

  // Case-insensitive lookup keeps the owner root as given.
  var found = SourceOwnerFiles.resolveFile(owner, 'data/characters/bf.json');
  if (found == null) throw 'case-insensitive character file';
  if (caseSensitive) eq(found, owner + '/Data/Characters/BF.json', 'on-disk spelling');
  eq(found.toLowerCase(), (owner + '/data/characters/bf.json').toLowerCase(), 'resolved path');
  eq(SourceOwnerFiles.resolveFile(owner, 'data/characters'), null, 'a directory is not a file');
  if (SourceOwnerFiles.resolveDirectory(owner, 'DATA/characters') == null) throw 'directory lookup';
  eq(SourceOwnerFiles.resolveFile(owner, 'data/characters/missing.json'), null, 'missing file');
  if (caseSensitive) eq(SourceOwnerFiles.resolveFile(owner, 'twins/same.txt'), null, 'ambiguous spelling');

  // The Nightmare Vision loaders get the same lookup.
  var definition = NightmareVisionCharacterData.definitionPath(owner, 'bf');
  if (definition == null) throw 'NV character definition through the shared lookup';
  eq(definition.toLowerCase(), found.toLowerCase(), 'NV definition path');
  if (NightmareVisionStageData.getStageFromDir(owner, 'stages', 'stage') == null) throw 'NV stage lookup';

  // Containment.
  eq(SourceOwnerFiles.within(owner, found), true, 'inside');
  eq(SourceOwnerFiles.within(owner, owner), true, 'root counts by default');
  eq(SourceOwnerFiles.within(owner, owner, false), false, 'root refused when asked');
  eq(PsychOwnerAssetPath.withinOwner(owner, owner), false, 'psych owner itself is not an owned file');
  eq(PsychOwnerAssetPath.withinOwner(owner, found), true, 'psych owned file');
  if (outsideLink != '') {
   eq(SourceOwnerFiles.resolveFile(owner, 'escape/secret.txt'), null, 'link out of the owner');
   eq(PsychOwnerAssetPath.withinOwner(owner, owner + '/escape/secret.txt'), false, 'psych link out of the owner');
  }
  trace('owner-files-ok');
 }
}
'''

SUPPORT = {
    'CoolUtil.hx': 'class CoolUtil { public static function parseJson(v:String):Dynamic return haxe.Json.parse(v); }',
    'RuntimeOwnerAssetIdentity.hx': 'class RuntimeOwnerAssetIdentity { public static function releaseOwner(o:String):Void {} }',
    'FNFAssets.hx': 'class FNFAssets { public static function resolveCaseInsensitivePath(p:String):String return sys.FileSystem.exists(p) ? p : null; }',
}


class SourceOwnerFilesTest(unittest.TestCase):
    def test_owner_roots_relative_paths_lookup_and_containment(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            owner = work / 'assets' / 'imported_mods' / 'pack'
            (owner / 'Data' / 'Characters').mkdir(parents=True)
            (owner / 'Data' / 'Characters' / 'BF.json').write_text('{}', encoding='utf-8')
            (owner / 'stages').mkdir()
            (owner / 'stages' / 'stage.json').write_text('{}', encoding='utf-8')
            case_sensitive = not (owner / 'data').exists()
            if case_sensitive:
                (owner / 'Twins').mkdir()
                (owner / 'Twins' / 'Same.txt').write_text('a', encoding='utf-8')
                (owner / 'Twins' / 'SAME.txt').write_text('b', encoding='utf-8')
            outside = work / 'outside'
            outside.mkdir()
            (outside / 'secret.txt').write_text('x', encoding='utf-8')
            # A link out of the owner. The interpreter's physical resolve is
            # FileSystem.fullPath, which only follows links off Windows; the
            # native Windows build resolves junctions itself.
            link = ''
            if sys.platform != 'win32':
                try:
                    os.symlink(outside, owner / 'escape', target_is_directory=True)
                    link = str(owner / 'escape')
                except OSError:
                    link = ''
            for name, text in SUPPORT.items():
                (work / name).write_text(text, encoding='utf-8', newline='\n')
            (work / 'Main.hx').write_text(MAIN, encoding='utf-8', newline='\n')
            relative_owner = 'assets/imported_mods/pack'
            (work / 'args.txt').write_text('\n'.join([relative_owner, '1' if case_sensitive else '0', link]),
                encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(work),
                '-main', 'Main', '--interp'], cwd=work, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('owner-files-ok', result.stdout)

    def test_loaders_use_the_shared_module(self):
        for name in ('NightmareVisionCharacterData.hx', 'NightmareVisionStageData.hx',
                'NightmareVisionScriptDiscovery.hx', 'PsychOwnerAssetPath.hx', 'SourceOwnerPreferences.hx',
                'NightmareVisionSaveData.hx', 'NightmareVisionModFamilySession.hx', 'NightmareVisionSourceOptions.hx'):
            text = (ROOT / 'source' / name).read_text(encoding='utf-8')
            self.assertIn('SourceOwnerFiles.', text, name)
            # A containment check built on fullPath is lexical on Windows.
            lexical = re.search(r'candidate\s*=\s*(Path\.normalize\(|normalize\()?(FileSystem\.fullPath|canonical)\(path\)', text)
            self.assertIsNone(lexical, name + ' keeps a lexical containment check')


if __name__ == '__main__':
    unittest.main()
