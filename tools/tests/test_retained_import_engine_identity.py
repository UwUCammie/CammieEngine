"""Retained source rescans keep engine evidence after executable exclusion."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

MAIN = r'''import sys.FileSystem;
import sys.io.File;
import ImportEngine;
class RetainedEngineFixture {
 static function check(value:Bool,message:String) if(!value) throw message;
 static function main() {
  var base=Sys.args()[0];
  var donor=base+"/donor";
  var detected=ImportRootScanner.inspectRoot(donor);
  check(detected!=null && detected.engine==ImportEngine.NIGHTMARE_VISION,"original executable marker was not detected");
  var captured=ImportSourceSnapshot.capture(donor,base+"/cache",detected.engine,"0.0.10");
  check(captured.complete,"source capture failed: "+captured.error);
  var source=captured.snapshotRoot+"/content";
  check(File.getBytes(source+"/Game.exe").toString()==File.getBytes(donor+"/Game.exe").toString(),"executable source bytes were not retained");
  check(ImportRootScanner.inspectRoot(source).engine==detected.engine,"retained executable marker was not detected");
  // Simulate a v0.0.9 cache, which excluded the executable before this fix.
  FileSystem.deleteFile(source+"/Game.exe");
  var plain=ImportRootScanner.inspectRoot(source);
  check(plain==null || plain.engine!=ImportEngine.NIGHTMARE_VISION,"fixture still has a Nightmare Vision marker");
  var siblingBefore=ImportRootScanner.inspectRoot(source+"/mods/psych-sibling");
  var install=base+"/install";
  var context=ImportIO.begin(install,install+"/import-cache/staging/identity");
  context.setNamespace(source,detected.engine,"retained-owner");
  var previous=ImportRootScanner.setRetainedSourceEngines([source=>detected.engine]);
  var retained=ImportRootScanner.inspectRoot(source);
  check(retained!=null && retained.engine==detected.engine,"retained root lost its original engine");
  var nested=ImportRootScanner.inspectRoot(source+"/content/pack");
  check(nested!=null && nested.engine==ImportEngine.NIGHTMARE_VISION,"nested content lost its retained parent's engine");
  var sibling=ImportRootScanner.inspectRoot(source+"/mods/psych-sibling");
  check((sibling==null && siblingBefore==null) || (sibling!=null && siblingBefore!=null
   && sibling.engine==siblingBefore.engine),"retained hint leaked into a sibling package");
  check(ImportRootScanner.inspectRoot(source+"/absent")==null,"retained identity invented a missing root");
  ImportIO.end();
  ImportRootScanner.setRetainedSourceEngines(previous);
  var after=ImportRootScanner.inspectRoot(source);
  check(after==null || after.engine!=ImportEngine.NIGHTMARE_VISION,"retained identity escaped its import context");
  check(FileSystem.exists(donor+"/Game.exe"),"donor executable was removed");
 }
}'''


class RetainedImportEngineIdentityTest(unittest.TestCase):
    def test_executable_marker_is_retained_per_root_without_mutating_donor(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temporary:
            base = Path(temporary)
            (base / 'install').mkdir()
            donor = base / 'donor'
            for root in (donor / 'assets', donor / 'content/pack', donor / 'mods/psych-sibling'):
                chart = root / 'data/song/song.json'
                chart.parent.mkdir(parents=True)
                chart.write_text('{"song":{"song":"song","bpm":100,"notes":[]}}', encoding='utf-8')
                (root / 'songs/song').mkdir(parents=True)
                (root / 'songs/song/Inst.ogg').write_bytes(b'fixture audio')
                (root / 'scripts').mkdir()
                (root / 'scripts/script.lua').write_text('function onCreate() end', encoding='utf-8')
            (donor / 'Game.exe').write_bytes(b'MZ\x00com.nmvTeam.nightmareEngine\x00')
            (base / 'RetainedEngineFixture.hx').write_text(MAIN, encoding='utf-8', newline='\n')
            process = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(base),
                                      '--run', 'RetainedEngineFixture', str(base)],
                                     cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == '__main__':
    unittest.main()
