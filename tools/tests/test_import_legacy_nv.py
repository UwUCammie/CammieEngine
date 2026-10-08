"""Legacy NV executable evidence and inherited content ownership."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


class LegacyNightmareVisionTest(unittest.TestCase):
    def test_legacy_identity_beats_inherited_psych_and_owns_content(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = FixturePath(folder)
            for name in ('ImportEngine', 'ImportRootScanner', 'ImportDirectoryListing', 'PsychSongNameCompat', 'NightmareVisionAssetCollector'):
                (work / (name + '.hx')).write_text((ROOT / 'source' / (name + '.hx')).read_text(), newline='\n')
            for name, markers in (
                ('legacy', b'PsychEngineVersion\0Nightmare Vision Engine\0meta.data.scripts.IFunkinScript'),
                ('mention', b'PsychEngineVersion\0Nightmare Vision Engine'),
                ('interface', b'PsychEngineVersion\0meta.data.scripts.IFunkinScript'),
                ('modern', b'PsychEngineVersion\0com.nmvTeam.nightmareEngine'),
            ):
                root = work / name
                for child in ('assets/data/demo', 'assets/songs/demo', 'assets/images', 'content/addon/data/demo', 'content/addon/songs/demo'):
                    (root / child).mkdir(parents=True, exist_ok=True)
                (root / 'pack.json').write_text('{}', newline='\n')
                (root / 'custom_events').mkdir()
                (root / 'game.exe').write_bytes(b'x' * 65525 + markers)
                (root / 'assets/data/demo/demo.json').write_text('{"song":{"song":"demo","notes":[]}}', newline='\n')
                (root / 'content/addon/data/demo/demo.json').write_text('{"song":{"song":"demo","notes":[]}}', newline='\n')
                (root / 'content/addon/pack.json').write_text('{}', newline='\n')
            (work / 'Main.hx').write_text('''class Main {
 static function check(ok:Bool, why:String):Void { if (!ok) throw why; }
 static function main():Void {
  for (name in ['legacy', 'modern']) {
   var root = ImportRootScanner.inspectRoot(name, ImportEngine.AUTO);
   check(root != null && root.engine == ImportEngine.NIGHTMARE_VISION, name + ': inherited Psych won');
   var child = ImportRootScanner.inspectRoot(name + '/content/addon', ImportEngine.AUTO);
   check(child != null && child.engine == ImportEngine.NIGHTMARE_VISION, name + ': content owner identity lost');
   var core = NightmareVisionAssetCollector.resolveCoreAssetsRoot(name + '/content/addon');
   check(core == ImportRootScanner.canonicalize(name + '/assets'), name + ': authenticated core was not inherited');
   check(ImportRootScanner.hasNightmareVisionContainerProof(root.evidence), name + ': container proof was lost');
   var explicit = ImportRootScanner.inspectRoot(name, ImportEngine.PSYCH);
   check(explicit != null && explicit.engine == ImportEngine.PSYCH, 'explicit choice changed');
  }
  for (name in ['mention', 'interface']) {
   var root = ImportRootScanner.inspectRoot(name, ImportEngine.AUTO);
   check(root != null && root.engine == ImportEngine.PSYCH, 'incomplete NV identity accepted: ' + name);
   check(NightmareVisionAssetCollector.resolveCoreAssetsRoot(name + '/content/addon') == '',
    'unproven root supplied a core dependency');
  }
 }
}''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '--run', 'Main'], cwd=work, capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
